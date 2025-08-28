"""
Gradescope Online Assignment Batch Creator
"""

import os
import json
import time
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from getpass import getpass
from datetime import datetime

import pyperclip
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class OnlineAssignment:
    name: str
    release_date: str  # 'YYYY-MM-DD HH:MM' 24h
    due_date: str      # 'YYYY-MM-DD HH:MM' 24h
    total_points: int
    anonymous_grading: Optional[bool] = None
    group_submission: Optional[bool] = None
    late_due_date: Optional[str] = None
    enforce_time_limit: Optional[bool] = None
    time_limit: Optional[int] = None
    group_size: Optional[int] = None
    question_text: Optional[str] = None
    rubric: Optional[Dict[str, float]] = None


class GSOnlineCreator:
    base_url = "https://www.gradescope.com"

    SELECTORS = {
        "btn_create_assignment": ".js-newAssignment",
        "type_button": ".treeSelectorNode",
        "btn_next": "//button[contains(., 'Next') and not(contains(@class,'disabled'))]",
        "btn_create": "//button[contains(., 'Create Assignment')]",
        "fld_title": "assignment[title]",
        "fld_release": "assignment[release_date_string]",
        "fld_due": "assignment[due_date_string]",
        "chk_allow_late": "assignment[allow_late_submissions]",
        "fld_late": "assignment[hard_due_date_string]",
        "chk_enforce_time": "//input[@name='assignment[enforce_time_limit]' and @type='checkbox']",
        "fld_time_limit": "assignment[time_limit_in_minutes]",
        "chk_anon": "//input[@name='assignment[submissions_anonymized]' and @type='checkbox']",
        "chk_group": "//input[@name='assignment[group_submission]' and @type='checkbox']",
        "fld_group_size": "assignment[group_size]",
    }

    def __init__(self, email: str, password: str, course_url: str, headless: bool = False):
        self.email = email
        self.password = password
        self.course_url = course_url.rstrip('/')
        self.driver = None
        self.wait: Optional[WebDriverWait] = None

        opts = ChromeOptions()
        if headless:
            opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option('useAutomationExtension', False)
        opts.add_argument('--window-size=1920,1080')
        self.chrome_options = opts

    def start(self):
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 20)
        logger.info("WebDriver started")

    def stop(self):
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")

    def login(self) -> bool:
        try:
            self.driver.get(f"{self.base_url}/login")
            self.wait.until(EC.presence_of_element_located((By.ID, "session_email"))).send_keys(self.email)
            self.driver.find_element(By.ID, "session_password").send_keys(self.password)
            self.driver.find_element(By.NAME, "commit").click()
            time.sleep(3)
            success = "login" not in self.driver.current_url
            logger.info("Login successful" if success else "Login failed")
            return success
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False

    def goto_assignments(self) -> bool:
        try:
            self.driver.get(f"{self.course_url}/assignments")
            time.sleep(1.5)
            return True
        except:
            return False

    def _ensure_element_visible(self, element) -> bool:
        try:
            self.driver.execute_script("""
                arguments[0].scrollIntoView({block: 'center'});
            """, element)
            time.sleep(0.2)
            return True
        except:
            return False

    def _parse_24h_to_datetime(self, date_str: str) -> Optional[datetime]:
        for fmt in ('%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y-%m-%dT%H:%M'):
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        return None

    def _set_datetime_field(self, field_name: str, date_str: str) -> bool:
        dt = self._parse_24h_to_datetime(date_str)
        if not dt:
            return False
        
        human_format = dt.strftime('%Y-%m-%d %H:%M')
        
        element = self.wait.until(EC.presence_of_element_located((By.NAME, field_name)))
        self._ensure_element_visible(element)
        
        pyperclip.copy(human_format)
        element.click()
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.CONTROL + "v")
        element.send_keys(Keys.TAB)
        time.sleep(0.3)
        return True

    def _fill_create_form(self, a: OnlineAssignment):
        d, S = self.driver, self.SELECTORS
        
        title_elem = self.wait.until(EC.presence_of_element_located((By.NAME, S["fld_title"])))
        title_elem.clear()
        title_elem.send_keys(a.name)
        
        self._set_datetime_field(S["fld_release"], a.release_date)
        self._set_datetime_field(S["fld_due"], a.due_date)
        time.sleep(0.5)
        
        if a.late_due_date:
            try:
                chk = d.find_element(By.NAME, S["chk_allow_late"])
                if not chk.is_selected():
                    chk.click()
                    time.sleep(0.3)
                self._set_datetime_field(S["fld_late"], a.late_due_date)
            except:
                pass
        
        if a.enforce_time_limit:
            try:
                chk = d.find_element(By.XPATH, S["chk_enforce_time"])
                if not chk.is_selected():
                    chk.click()
                    time.sleep(0.3)
                if a.time_limit:
                    tl_elem = d.find_element(By.NAME, S["fld_time_limit"])
                    tl_elem.clear()
                    tl_elem.send_keys(str(a.time_limit))
            except:
                pass
        
        if a.anonymous_grading:
            try:
                chk = d.find_element(By.XPATH, S["chk_anon"])
                if not chk.is_selected():
                    chk.click()
            except:
                pass
        
        if a.group_submission:
            try:
                chk = d.find_element(By.XPATH, S["chk_group"])
                if not chk.is_selected():
                    chk.click()
                    time.sleep(0.3)
                if a.group_size:
                    gs_elem = d.find_element(By.NAME, S["fld_group_size"])
                    gs_elem.clear()
                    gs_elem.send_keys(str(a.group_size))
            except:
                pass
        
        time.sleep(0.5)

    def _fill_outline_page(self, a: OnlineAssignment):
        time.sleep(2)
        
        try:
            if a.question_text:
                title = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Title']")
                title.clear()
                title.send_keys(a.question_text)
            
            points = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='0.0']")
            points.clear()
            points.send_keys(str(a.total_points))
            
            problem = self.driver.find_element(By.CSS_SELECTOR, "textarea[placeholder='Type your problem here']")
            problem.clear()
            problem.send_keys("\n\n|____|")
            
            time.sleep(1)
            save_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'Save') and not(contains(@class,'disabled'))]")
            save_btn.click()
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Outline page filling issue: {e}")

    def _setup_rubric(self, rubric_data: Dict[str, float]):
        try:
            current_url = self.driver.current_url
            
            if '/assignments/' in current_url:
                parts = current_url.split('/assignments/')
                assignment_id = parts[1].split('/')[0]
                rubric_url = f"{self.course_url}/assignments/{assignment_id}/rubric/edit"
                
                self.driver.get(rubric_url)
                time.sleep(3)
                
                rubric_items = []
                for description, points in rubric_data.items():
                    rubric_items.append({
                        "description": description.capitalize(),
                        "points": points
                    })
                
                for i, item in enumerate(rubric_items):                  
                    if i == 0:
                        try:
                            p_elements = self.driver.find_elements(By.TAG_NAME, "p")
                            for p in p_elements:
                                if p.text.strip() == "Correct":
                                    pyperclip.copy(item['description'])
                                    p.click()
                                    time.sleep(0.5)
                                    
                                    active = self.driver.switch_to.active_element
                                    active.send_keys(Keys.CONTROL + "a")
                                    active.send_keys(Keys.CONTROL + "v")
                                    active.send_keys(Keys.TAB)
                                    time.sleep(0.5)
                                    break
                            
                            pyperclip.copy(str(item['points']))
                            points_btn = self.driver.find_element(By.CSS_SELECTOR, ".rubricField-points")
                            points_btn.click()
                            time.sleep(0.5)
                            
                            active = self.driver.switch_to.active_element
                            active.send_keys(Keys.CONTROL + "a")
                            active.send_keys(Keys.CONTROL + "v")
                            active.send_keys(Keys.TAB)
                            time.sleep(0.5)
                            
                        except Exception as e:
                            logger.warning(f"Error updating first rubric item: {e}")
                    
                    else:
                        # Add new rubric item
                        try:
                            # Find and click Add Rubric Item button
                            buttons = self.driver.find_elements(By.TAG_NAME, "button")
                            for btn in buttons:
                                aria_label = btn.get_attribute('aria-label') or ''
                                btn_text = btn.text or ''
                                if 'Add Rubric Item' in aria_label or 'Add Rubric Item' in btn_text:
                                    btn.click()
                                    break
                            
                            time.sleep(2)
                            
                            rubric_items_elements = self.driver.find_elements(By.CLASS_NAME, "rubricItem")
                            if rubric_items_elements and len(rubric_items_elements) > i:
                                last_item = rubric_items_elements[-1]
                                
                                p_elements = last_item.find_elements(By.TAG_NAME, "p")
                                clicked = False
                                for p in p_elements:
                                    text = p.text.strip()
                                    if text in ["Correct", "Incorrect", ""] or len(text) < 20:
                                        pyperclip.copy(item['description'])
                                        p.click()
                                        clicked = True
                                        break
                                
                                if not clicked and p_elements:
                                    pyperclip.copy(item['description'])
                                    p_elements[0].click()
                                
                                time.sleep(0.5)
                                active = self.driver.switch_to.active_element
                                active.send_keys(Keys.CONTROL + "a")
                                active.send_keys(Keys.CONTROL + "v")
                                active.send_keys(Keys.TAB)
                                time.sleep(0.5)
                                
                                rubric_items_elements = self.driver.find_elements(By.CLASS_NAME, "rubricItem")
                                if rubric_items_elements and len(rubric_items_elements) > i:
                                    last_item = rubric_items_elements[-1]
                                    points_btns = last_item.find_elements(By.CSS_SELECTOR, ".rubricField-points")
                                    if points_btns:
                                        pyperclip.copy(str(item['points']))
                                        points_btns[0].click()
                                        time.sleep(0.5)
                                        
                                        active = self.driver.switch_to.active_element
                                        active.send_keys(Keys.CONTROL + "a")
                                        active.send_keys(Keys.CONTROL + "v")
                                        active.send_keys(Keys.TAB)
                                        time.sleep(0.5)
                                    
                        except Exception as e:
                            logger.warning(f"Error adding rubric item {i+1}: {e}")
                    
                    time.sleep(1)
                
        except Exception as e:
            logger.warning(f"Rubric setup issue: {e}")

    def create(self, a: OnlineAssignment) -> bool:
        d, S = self.driver, self.SELECTORS
        
        try:
            logger.info(f"Creating: {a.name}")
            
            create_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, S["btn_create_assignment"])))
            create_btn.click()
            time.sleep(1)
            
            for btn in d.find_elements(By.CSS_SELECTOR, S["type_button"]):
                if 'Online Assignment' in (btn.text or ''):
                    btn.click()
                    break
            
            next_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, S["btn_next"])))
            next_btn.click()
            time.sleep(1.5)
            
            self._fill_create_form(a)
            
            next_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, S["btn_next"])))
            next_btn.click()
            time.sleep(2)
            
            create_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, S["btn_create"])))
            create_btn.click()
            time.sleep(3)
            
            self._fill_outline_page(a)
            
            if a.rubric:
                logger.info("Setting up rubric...")
                self._setup_rubric(a.rubric)
            
            self.goto_assignments()
            logger.info(f"Created: {a.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed: {a.name} - {e}")
            self.goto_assignments()
            return False

    def batch_create(self, assignments: List[OnlineAssignment]) -> Tuple[int, List[str]]:
        success_count = 0
        failed_names = []
        
        for i, assignment in enumerate(assignments, 1):
            logger.info(f"[{i}/{len(assignments)}] {assignment.name}")
            
            if self.create(assignment):
                success_count += 1
            else:
                failed_names.append(assignment.name)
            
            if i < len(assignments):
                time.sleep(2)
        
        return success_count, failed_names

    @staticmethod
    def load_from_json(path: str) -> List[OnlineAssignment]:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assignments = []
        for item in data:
            details = item.get('assignment_details', {})
            assignments.append(OnlineAssignment(
                name=item['name'],
                release_date=item['release_date'],
                due_date=item['due_date'],
                total_points=int(item['total_points']),
                anonymous_grading=item.get('anonymous_grading'),
                group_submission=item.get('group_submission'),
                late_due_date=item.get('late_due_date'),
                enforce_time_limit=item.get('enforce_time_limit'),
                time_limit=item.get('time_limit'),
                group_size=item.get('group_size'),
                question_text=details.get('question'),
                rubric=details.get('rubric')
            ))
        
        logger.info(f"Loaded {len(assignments)} assignments from {path}")
        return assignments


def main():
    email = os.getenv("GS_EMAIL") or input("GS email: ").strip()
    password = os.getenv("GS_PASSWORD") or getpass("GS password: ")
    course_url = os.getenv("GS_COURSE_URL") or input("Course URL (e.g., https://www.gradescope.com/courses/xxxxxx): ").strip()
    json_file = os.getenv("GS_JSON") or input("JSON file name: ")
    
    bot = GSOnlineCreator(email, password, course_url, headless=False)
    
    try:
        bot.start()
        
        if not bot.login():
            print("Login failed")
            return
        
        if not bot.goto_assignments():
            print("Cannot access assignments")
            return
        
        assignments = bot.load_from_json(json_file)
        success, failed = bot.batch_create(assignments)
        
        print(f"Complete: {success} successful")
        if failed:
            print(f"{len(failed)} failed: {', '.join(failed)}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        input("\nPress Enter to close...")
        bot.stop()

if __name__ == '__main__':
    main()


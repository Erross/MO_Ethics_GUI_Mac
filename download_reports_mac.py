"""
Multi-Year Processing with Captcha Avoidance – macOS Version
Downloads to ~/Downloads/MEC_Reports/{MECID}/ using mac-compatible ChromeDriver setup.
"""

import random
import time
import re
import os
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import pyautogui
import platform

from config import Config


class StealthBrowser:
    """Enhanced stealth browser with anti-detection measures."""

    def __init__(self, driver):
        self.driver = driver
        self.actions = ActionChains(driver)

    def human_delay(self, a=0.5, b=2.0):
        time.sleep(random.uniform(a, b))

    def long_human_delay(self, a=3, b=8):
        delay = random.uniform(a, b)
        print(f"      Taking {delay:.1f}s break (captcha avoidance)...")
        time.sleep(delay)

    def human_click(self, element):
        self.actions.move_to_element(element).perform()
        self.human_delay(0.4, 1.2)
        element.click()
        self.human_delay(0.4, 1.2)

    def mimic_reading(self, duration=None):
        duration = duration or random.uniform(2, 5)
        print(f"      Reading page for {duration:.1f}s...")
        time.sleep(duration)


def download_pdf_mac(downloads_dir: Path, target_filename: str):
    """Save PDF via keyboard shortcut (Command-S on macOS)."""
    MIN_VALID_SIZE = 10000
    try:
        # mac uses command key instead of ctrl
        if platform.system() == "Darwin":
            pyautogui.hotkey('command', 's')
        else:
            pyautogui.hotkey('ctrl', 's')

        time.sleep(3)
        pyautogui.hotkey('command' if platform.system() == "Darwin" else 'ctrl', 'a')
        time.sleep(0.5)
        full_path = str(downloads_dir.resolve() / target_filename)
        pyautogui.write(full_path, interval=0.03)
        time.sleep(1)
        pyautogui.press('enter')

        for _ in range(25):
            time.sleep(1)
            pdf_path = downloads_dir / target_filename
            if pdf_path.exists():
                size = pdf_path.stat().st_size
                if size < MIN_VALID_SIZE:
                    print(f"        WARNING: File too small ({size:,} bytes). Retrying.")
                    pdf_path.unlink(missing_ok=True)
                    return False, 0
                return True, size
        return False, 0
    except Exception as e:
        print(f"        ERROR saving PDF: {e}")
        return False, 0


def run_step_8_multi_year_mac():
    """Full multi-year scraping and download workflow for macOS."""
    if not Config.COMMITTEE_MECID:
        print("ERROR: MECID must be set before downloading.")
        return False

    downloads_dir = Config.ensure_mecid_folder()
    existing_reports = set()
    if downloads_dir.exists():
        for pdf in downloads_dir.glob("*.pdf"):
            parsed = Config.parse_filename(pdf.name)
            if parsed:
                existing_reports.add((parsed['report_id'], parsed['year']))

    print(f"\nTarget MECID: {Config.COMMITTEE_MECID}")
    print(f"Saving to: {downloads_dir}")
    print(f"Existing reports: {len(existing_reports)}")

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--window-size=1440,900")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )

    prefs = {
        "plugins.always_open_pdf_externally": False,
        "download.default_directory": str(downloads_dir),
    }
    chrome_options.add_experimental_option("prefs", prefs)

    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_path):
        chrome_options.binary_location = chrome_path

    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                              options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    stealth = StealthBrowser(driver)

    try:
        print("\nNavigating to MEC Search...")
        driver.get("https://mec.mo.gov/MEC/Campaign_Finance/CFSearch.aspx#gsc.tab=0")
        stealth.mimic_reading(3)
        wait = WebDriverWait(driver, 15)

        # Populate search fields
        if Config.SEARCH_TYPE == "candidate":
            field = wait.until(EC.presence_of_element_located(("name",
                "ctl00$ctl00$ContentPlaceHolder$ContentPlaceHolder1$txtCand")))
            for c in Config.CANDIDATE_NAME:
                field.send_keys(c)
                time.sleep(random.uniform(0.05, 0.15))
        elif Config.SEARCH_TYPE == "mecid":
            field = wait.until(EC.presence_of_element_located(("name",
                "ctl00$ctl00$ContentPlaceHolder$ContentPlaceHolder1$txtMECID")))
            field.send_keys(Config.COMMITTEE_MECID)
        else:
            field = wait.until(EC.presence_of_element_located(("name",
                "ctl00$ctl00$ContentPlaceHolder$ContentPlaceHolder1$txtComm")))
            for c in Config.COMMITTEE_NAME:
                field.send_keys(c)
                time.sleep(random.uniform(0.05, 0.15))

        search_btn = driver.find_element("name",
            "ctl00$ctl00$ContentPlaceHolder$ContentPlaceHolder1$btnSearch")
        stealth.human_click(search_btn)
        stealth.mimic_reading(5)

        # Try to go to Reports
        try:
            reports_link = driver.find_element("link text", "Reports")
        except:
            results_table = driver.find_element("id", "ContentPlaceHolder_ContentPlaceHolder1_gvResults")
            first_link = results_table.find_element("tag name", "a")
            stealth.human_click(first_link)
            stealth.mimic_reading(3)
            reports_link = driver.find_element("link text", "Reports")

        stealth.human_click(reports_link)
        stealth.mimic_reading(3)

        # Discover year sections
        main_table = driver.find_element("id", "ContentPlaceHolder_ContentPlaceHolder1_grvReportOutside")
        year_labels = main_table.find_elements("css selector", "span[id*='lblYear']")
        available_years = sorted(
            {int(y) for lbl in year_labels for y in re.findall(r'(20\d{2})', lbl.text)}, reverse=True
        )
        print(f"Years found: {available_years}")

        for year in available_years:
            print(f"\n=== Processing {year} ===")
            expanders = main_table.find_elements("css selector", "input[id*='ImgRptRight']")
            labels = main_table.find_elements("css selector", "span[id*='lblYear']")
            idx = next((i for i, l in enumerate(labels) if str(year) in l.text), None)
            if idx is None:
                continue
            stealth.human_click(expanders[idx])
            stealth.mimic_reading(4)

            inner_tables = driver.find_elements("css selector", "table[id*='grvReports']")
            table = next((t for t in inner_tables if t.is_displayed()), None)
            if not table:
                continue
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"  Found {len(rows)} rows")

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 3:
                    continue
                date_text = cells[2].text.strip()
                if not re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_text):
                    continue
                try:
                    link = cells[0].find_element(By.TAG_NAME, "a")
                    report_id = link.text.strip()
                except:
                    report_id = cells[0].text.strip()
                report_name = cells[1].text.strip() if len(cells) > 1 else None
                if not report_id.isdigit():
                    continue

                filename = Config.get_filename_pattern(report_name, report_id, year)
                if (report_id, year) in existing_reports:
                    print(f"    Skipping existing {filename}")
                    continue

                print(f"    Downloading {filename}")
                original_window = driver.current_window_handle
                stealth.human_click(link)
                new_tab = None
                for _ in range(10):
                    time.sleep(1)
                    for w in driver.window_handles:
                        if w != original_window:
                            new_tab = w
                            break
                    if new_tab:
                        break
                if not new_tab:
                    print("      ERROR: no new tab")
                    continue
                driver.switch_to.window(new_tab)
                time.sleep(8)
                success, size = download_pdf_mac(downloads_dir, filename)
                driver.close()
                driver.switch_to.window(original_window)
                if success:
                    existing_reports.add((report_id, year))
                    print(f"      SUCCESS {size:,} bytes")
                else:
                    print(f"      FAILED to download {filename}")
                stealth.human_delay(1, 2)

        print("\nAll years processed successfully.")
        return True

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    run_step_8_multi_year_mac()

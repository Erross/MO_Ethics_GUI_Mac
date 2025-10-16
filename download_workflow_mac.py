"""
MEC Report Download Workflow (macOS)
Downloads and validates reports only — NO extraction.

Parity with Windows workflow:
- Step 1: Discover expected reports on MEC site
- Step 2: Repeatedly run downloader until all are present (max retries)
- Step 3: Validate reports (reuses existing filename/date logic)
"""

import sys
import time
import re
import argparse
import os
import io
from pathlib import Path
from typing import Set, Tuple

# Keep stdout/stderr Unicode-friendly if present
if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from config import Config


def _build_driver() -> webdriver.Chrome:
    """Create a Chrome WebDriver suitable for macOS with sensible defaults."""
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--window-size=1440,900')
    chrome_options.add_argument(
        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
    )

    # Prefer the standard Chrome install path on macOS if present
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_path):
        chrome_options.binary_location = chrome_path

    service = webdriver.chrome.service.Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    # Stealth tweak
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def get_expected_reports_from_website() -> Set[Tuple[str, str, int]]:
    """
    Navigate to MEC website and discover all available report metadata.
    Returns set of tuples: (report_id, report_name, year)
    """
    print("=" * 80)
    print("CHECKING MEC WEBSITE FOR AVAILABLE REPORTS")
    print("=" * 80)

    expected_reports: Set[Tuple[str, str, int]] = set()
    driver = None

    try:
        print("Initializing Chrome driver...")
        driver = _build_driver()
        print("Chrome driver initialized successfully")

        print("Navigating to MEC website...")
        driver.get("https://mec.mo.gov/MEC/Campaign_Finance/CFSearch.aspx#gsc.tab=0")
        time.sleep(3)

        wait = WebDriverWait(driver, 15)

        if Config.SEARCH_TYPE == "candidate":
            print(f"Searching by candidate: {Config.CANDIDATE_NAME}")
            candidate_input = wait.until(EC.presence_of_element_located(
                ("name", "ctl00$ctl00$ContentPlaceHolder$ContentPlaceHolder1$txtCand")
            ))
            candidate_input.clear()
            candidate_input.send_keys(Config.CANDIDATE_NAME)

        elif Config.SEARCH_TYPE == "mecid":
            print(f"Searching by MECID: {Config.COMMITTEE_MECID}")
            mecid_input = wait.until(EC.presence_of_element_located(
                ("name", "ctl00$ctl00$ContentPlaceHolder$ContentPlaceHolder1$txtMECID")
            ))
            mecid_input.clear()
            mecid_input.send_keys(Config.COMMITTEE_MECID)

        else:  # committee
            print(f"Searching by committee: {Config.COMMITTEE_NAME}")
            committee_input = wait.until(EC.presence_of_element_located(
                ("name", "ctl00$ctl00$ContentPlaceHolder$ContentPlaceHolder1$txtComm")
            ))
            committee_input.clear()
            committee_input.send_keys(Config.COMMITTEE_NAME)

        time.sleep(2)

        search_button = driver.find_element(
            "name", "ctl00$ctl00$ContentPlaceHolder$ContentPlaceHolder1$btnSearch"
        )
        search_button.click()
        time.sleep(5)

        # Check if exact match (already on committee page)
        try:
            reports_link = driver.find_element("link text", "Reports")
            print("Direct match - already on committee page")
        except:
            # On results page
            results_table = driver.find_element("id", "ContentPlaceHolder_ContentPlaceHolder1_gvResults")
            all_links = results_table.find_elements("tag name", "a")

            mecid_link = None
            discovered_mecid = None
            mecid_pattern = re.compile(r'^[A-Z]\d{5,7}$')

            if Config.SEARCH_TYPE == "mecid":
                target_mecid = Config.COMMITTEE_MECID
                print(f"Looking for exact MECID match: {target_mecid}")

                for link in all_links:
                    link_text = link.text.strip()
                    if link_text == target_mecid:
                        mecid_link = link
                        discovered_mecid = link_text
                        print(f"Found exact MECID: {link_text}")
                        break

                if not mecid_link:
                    print(f"ERROR: MECID {target_mecid} not found")
                    return set()
            else:
                for link in all_links:
                    link_text = link.text.strip()
                    if mecid_pattern.match(link_text):
                        mecid_link = link
                        discovered_mecid = link_text
                        print(f"Found MECID: {link_text}")
                        Config.COMMITTEE_MECID = discovered_mecid
                        print(f"Discovered and saved MECID: {discovered_mecid}")
                        break

            if mecid_link:
                mecid_link.click()
            else:
                print("WARNING: No MECID link found")
                return set()

            time.sleep(3)
            reports_link = driver.find_element("link text", "Reports")

        reports_link.click()
        time.sleep(4)

        print("Discovering available years...")
        main_table = driver.find_element("id", "ContentPlaceHolder_ContentPlaceHolder1_grvReportOutside")
        year_labels = main_table.find_elements("css selector", "span[id*='lblYear']")

        available_years = []
        for label in year_labels:
            year_text = label.text.strip()
            year_matches = re.findall(r'(20\d{2})', year_text)
            for year_match in year_matches:
                year = int(year_match)
                if year not in available_years:
                    available_years.append(year)

        available_years.sort(reverse=True)
        print(f"Found years: {available_years}")

        date_pattern = re.compile(r'^\d{1,2}/\d{1,2}/\d{4}$')

        for year in available_years:
            print(f"\nChecking year {year}...")
            main_table = driver.find_element("id", "ContentPlaceHolder_ContentPlaceHolder1_grvReportOutside")
            expand_buttons = main_table.find_elements("css selector", "input[id*='ImgRptRight']")
            year_labels = main_table.find_elements("css selector", "span[id*='lblYear']")

            year_index = None
            for i, label in enumerate(year_labels):
                if str(year) in label.text.strip():
                    year_index = i
                    break

            if year_index is not None and year_index < len(expand_buttons):
                expand_buttons[year_index].click()
                time.sleep(5)

                inner_tables = driver.find_elements("css selector", "table[id*='grvReports']")
                report_table = next((t for t in inner_tables if t.is_displayed()), None)

                if report_table:
                    rows = report_table.find_elements(By.TAG_NAME, "tr")

                    for row in rows:
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) < 3:
                                continue

                            third_cell_text = cells[2].text.strip()
                            if not date_pattern.match(third_cell_text):
                                continue

                            # Extract report ID (cell 0) & report name (cell 1)
                            try:
                                link = cells[0].find_element(By.TAG_NAME, "a")
                                report_id = link.text.strip()
                            except:
                                report_id = cells[0].text.strip()

                            report_name = cells[1].text.strip() if len(cells) > 1 else None

                            if report_id and report_id.isdigit() and len(report_id) >= 5 and report_name:
                                expected_reports.add((report_id, report_name, year))
                        except Exception:
                            continue

                    print(f"  Found {sum(1 for r in expected_reports if r[2] == year)} reports for {year}")

        print(f"\nTotal expected reports: {len(expected_reports)}")
        return expected_reports

    except Exception as e:
        print(f"\nERROR checking website: {e}")
        import traceback
        traceback.print_exc()
        return set()

    finally:
        if driver:
            print("Closing browser...")
            driver.quit()


def get_existing_files(downloads_dir: Path) -> Set[Tuple[str, int]]:
    """
    Get set of existing report metadata from downloaded files.
    Returns set of tuples: (report_id, year)
    """
    if not downloads_dir.exists():
        return set()

    existing = set()
    for pdf_file in downloads_dir.glob("*.pdf"):
        parsed = Config.parse_filename(pdf_file.name)
        if parsed:
            existing.add((parsed['report_id'], parsed['year']))
    return existing


def run_downloader() -> bool:
    """Run mac downloader by importing it directly."""
    print("\n" + "=" * 80)
    print("RUNNING DOWNLOADER (macOS)")
    print("=" * 80)

    try:
        import download_reports_mac as download_reports  # mac-specific module

        original_argv = sys.argv.copy()
        sys.argv = ['download_reports_mac.py']  # the module reads Config, not argv, but we mirror shape

        try:
            ok = download_reports.run_step_8_multi_year_mac()
            return bool(ok)
        finally:
            sys.argv = original_argv

    except Exception as e:
        print(f"ERROR running downloader: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_validation() -> bool:
    """Run validation by importing directly (reuses your existing logic)."""
    print("\n" + "=" * 80)
    print("VALIDATING REPORTS")
    print("=" * 80)

    try:
        import validate_reports_mac  # same logic/format; cross-platform

        original_argv = sys.argv.copy()
        sys.argv = ['validate_reports_mac.py', '--mecid', Config.COMMITTEE_MECID]

        try:
            validate_reports_mac.main()
        except SystemExit as e:
            if e.code != 0:
                print("\n[WARNING] Validation found issues")
                print("Continuing anyway...")
        finally:
            sys.argv = original_argv

        return True

    except Exception as e:
        print(f"ERROR running validation: {e}")
        print("Continuing anyway...")
        return True


def main():
    """Main download workflow (macOS)."""
    parser = argparse.ArgumentParser(description='MEC Report Download Workflow (macOS)')
    search_group = parser.add_mutually_exclusive_group()
    search_group.add_argument('--committee', type=str, help='Committee name')
    search_group.add_argument('--candidate', type=str, help='Candidate name')
    search_group.add_argument('--mecid-only', type=str, dest='mecid_only', help='MEC ID only')
    parser.add_argument('--mecid', type=str, help='MEC ID for filtering')

    args = parser.parse_args()

    if args.mecid_only:
        Config.set_search(mecid=args.mecid_only)
    elif args.candidate:
        Config.set_search(candidate=args.candidate, mecid=args.mecid)
    elif args.committee:
        Config.set_search(committee=args.committee, mecid=args.mecid)

    print(f"Search configured:")
    print(f"  Type: {Config.SEARCH_TYPE}")
    print(f"  Value: {Config.get_search_value()}")
    print(f"  File prefix: {Config.get_file_prefix()}")

    MAX_RETRIES = 20

    print("\n" + "=" * 80)
    print("MEC REPORT DOWNLOAD WORKFLOW (macOS)")
    print("=" * 80)
    print(f"Target: {Config.get_display_name()}")
    print(f"Max retry attempts: {MAX_RETRIES}")

    print("\n" + "=" * 80)
    print("STEP 1: CHECKING WHAT REPORTS SHOULD EXIST")
    print("=" * 80)
    expected_reports = get_expected_reports_from_website()

    if not expected_reports:
        print("\nERROR: Could not determine expected reports")
        sys.exit(1)

    if not Config.COMMITTEE_MECID:
        print("\nERROR: Could not determine MECID")
        sys.exit(1)

    downloads_dir = Config.ensure_mecid_folder()
    print(f"\nMECID: {Config.COMMITTEE_MECID}")
    print(f"Downloads directory: {downloads_dir}")
    print(f"Expected {len(expected_reports)} total reports")

    print("\n" + "=" * 80)
    print("STEP 2: DOWNLOAD LOOP")
    print("=" * 80)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n--- Attempt {attempt}/{MAX_RETRIES} ---")
        existing_files = get_existing_files(downloads_dir)

        expected_keys = {(r[0], r[2]) for r in expected_reports}
        missing_keys = expected_keys - existing_files

        print(f"Existing files: {len(existing_files)}")
        print(f"Missing files: {len(missing_keys)}")

        if not missing_keys:
            print("\n[OK] ALL REPORTS DOWNLOADED!")
            break

        print("\nSample missing reports:")
        for i, (report_id, year) in enumerate(sorted(missing_keys)[:5]):
            report_name = next((r[1] for r in expected_reports if r[0] == report_id and r[2] == year), "Unknown")
            filename = Config.get_filename_pattern(report_name, report_id, year)
            print(f"  - {filename}")
        if len(missing_keys) > 5:
            print(f"  ... and {len(missing_keys) - 5} more")

        print(f"\nRunning downloader (attempt {attempt})...")
        success = run_downloader()
        if not success:
            print("WARNING: Downloader returned error")

        time.sleep(5)
    else:
        existing_files = get_existing_files(downloads_dir)
        expected_keys = {(r[0], r[2]) for r in expected_reports}
        missing_keys = expected_keys - existing_files

        print("\n" + "=" * 80)
        print("MAX RETRIES REACHED")
        print("=" * 80)
        print(f"Still missing {len(missing_keys)} files")
        print("\n[WARNING] Proceeding with validation anyway...")

    print("\n" + "=" * 80)
    print("STEP 3: VALIDATING REPORTS")
    print("=" * 80)

    run_validation()

    print("\n" + "=" * 80)
    print("DOWNLOAD WORKFLOW COMPLETE (macOS)")
    print("=" * 80)
    print(f"MECID: {Config.COMMITTEE_MECID}")
    print(f"Download directory: {downloads_dir}")

    existing_files = get_existing_files(downloads_dir)
    expected_keys = {(r[0], r[2]) for r in expected_reports}
    print(f"Final file count: {len(existing_files)}/{len(expected_keys)}")

    if existing_files == expected_keys:
        print("\n[OK] All reports downloaded!")
    else:
        missing_count = len(expected_keys - existing_files)
        print(f"\n[WARNING] {missing_count} reports still missing")


if __name__ == "__main__":
    main()

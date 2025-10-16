"""
Report Validation Script (macOS)
Validates that MEC PDF filenames match their filing dates.

File format: {PREFIX}_{REPORT_NAME}_{REPORT_ID}_{YEAR}.pdf
Example: FHF_October_Quarterly_Report_261218_2025.pdf
"""

import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional
import pdfplumber
from config import Config


def extract_filename_info(filename: str) -> Optional[Dict]:
    """Extract components from filename using standard Config parser."""
    return Config.parse_filename(filename)


def extract_filing_date_from_pdf(pdf_path: str) -> Optional[str]:
    """Extract filing date from PDF contents using common patterns."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text() or ""

            date_patterns = [
                r'Report Date\s*\n\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'DATE OF REPORT.*?(\d{1,2}/\d{1,2}/\d{4})',
                r'Filed\s+on\s+(\d{1,2}/\d{1,2}/\d{4})'
            ]

            for pattern in date_patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1)

    except Exception as e:
        print(f"  ERROR reading {Path(pdf_path).name}: {e}")

    return None


def get_year_from_date(date_str: str) -> Optional[int]:
    """Return numeric year from MM/DD/YYYY string."""
    if not date_str:
        return None
    try:
        parts = date_str.split('/')
        return int(parts[2])
    except Exception:
        return None


def validate_reports(mecid: str = None) -> tuple:
    """Validate that each report PDF matches expected year from its filename."""
    if not mecid:
        print("ERROR: MECID is required")
        return False, []

    Config.COMMITTEE_MECID = mecid
    pdfs_folder = Config.get_mecid_folder()

    if not pdfs_folder.exists():
        print(f"ERROR: Folder '{pdfs_folder}' not found")
        return False, []

    pdf_files = list(pdfs_folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in '{pdfs_folder}'")
        return True, []

    print("=" * 80)
    print("VALIDATING REPORT FILENAMES (macOS)")
    print("=" * 80)
    print(f"MECID: {mecid}")
    print(f"Folder: {pdfs_folder}")
    print(f"Checking {len(pdf_files)} files...\n")

    by_report_id = defaultdict(list)

    for pdf_file in pdf_files:
        info = extract_filename_info(pdf_file.name)
        if info:
            by_report_id[info['report_id']].append({**info, 'path': pdf_file})

    duplicate_ids = []
    for report_id, files in by_report_id.items():
        if len(files) > 1:
            years = {f['year'] for f in files}
            if len(years) > 1:
                duplicate_ids.append(report_id)

    if not duplicate_ids:
        print("No duplicate report IDs with conflicting years found.")
        return True, []

    print(f"Found {len(duplicate_ids)} report IDs with multiple year versions.\n")

    issues = []

    for report_id in duplicate_ids:
        files = by_report_id[report_id]
        print(f"--- Report ID: {report_id} ---")

        for file_info in files:
            filename = file_info['filename']
            filename_year = file_info['year']
            report_name = file_info['report_name']
            pdf_path = file_info['path']

            filing_date = extract_filing_date_from_pdf(str(pdf_path))
            filing_year = get_year_from_date(filing_date)

            if not filing_date:
                issues.append({
                    'filename': filename,
                    'report_id': report_id,
                    'report_name': report_name,
                    'status': 'ERROR',
                    'message': 'Could not extract filing date'
                })
                print(f"  [ERROR] {filename} - missing filing date")
                continue

            if not filing_year:
                issues.append({
                    'filename': filename,
                    'report_id': report_id,
                    'report_name': report_name,
                    'status': 'ERROR',
                    'message': f'Could not parse year from {filing_date}'
                })
                print(f"  [ERROR] {filename} - invalid date format ({filing_date})")
                continue

            if filename_year != filing_year:
                issues.append({
                    'filename': filename,
                    'report_id': report_id,
                    'report_name': report_name,
                    'status': 'MISMATCH',
                    'message': f'Filename year {filename_year} != filing year {filing_year}'
                })
                print(f"  [MISMATCH] {filename}: filename says {filename_year}, filed {filing_year}")
            else:
                print(f"  [OK] {filename}: {filing_date}")

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    if not issues:
        print("[OK] All reports validated successfully!")
        return True, []
    else:
        mismatches = [i for i in issues if i['status'] == 'MISMATCH']
        errors = [i for i in issues if i['status'] == 'ERROR']
        print(f"[ERROR] Found {len(issues)} issue(s):")
        print(f"  - {len(mismatches)} mismatches")
        print(f"  - {len(errors)} errors")
        return False, issues


def main():
    """Entry point for standalone run."""
    import argparse
    parser = argparse.ArgumentParser(description='Validate MEC report filenames (macOS)')
    parser.add_argument('--mecid', type=str, required=True, help='MEC Committee ID')
    args = parser.parse_args()
    all_valid, issues = validate_reports(mecid=args.mecid)
    if all_valid:
        print("\n[OK] Validation complete — all reports OK")
        return 0
    else:
        print("\n[WARNING] Validation found issues — review needed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

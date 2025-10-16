"""
Configuration for MEC Report Processing (macOS version)
Centralized settings for committee name and derived values.
This file is functionally identical to the Windows version.
"""

import re
import os
from pathlib import Path


class Config:
    """Configuration container for MEC processing"""

    # Default settings
    COMMITTEE_NAME = "Francis Howell Families"
    COMMITTEE_MECID = "C2116"
    CANDIDATE_NAME = None
    SEARCH_TYPE = "committee"  # 'candidate', 'committee', or 'mecid'

    @classmethod
    def set_search(cls, committee: str = None, candidate: str = None, mecid: str = None):
        if mecid and not (committee or candidate):
            cls.SEARCH_TYPE = "mecid"
            cls.COMMITTEE_MECID = mecid
            cls.COMMITTEE_NAME = None
            cls.CANDIDATE_NAME = None
        elif candidate:
            cls.SEARCH_TYPE = "candidate"
            cls.CANDIDATE_NAME = candidate
            cls.COMMITTEE_NAME = None
            cls.COMMITTEE_MECID = mecid if mecid else None
        else:
            cls.SEARCH_TYPE = "committee"
            cls.COMMITTEE_NAME = committee or cls.COMMITTEE_NAME
            cls.CANDIDATE_NAME = None
            cls.COMMITTEE_MECID = mecid if mecid else None

    @classmethod
    def get_search_value(cls) -> str:
        if cls.SEARCH_TYPE == "candidate":
            return cls.CANDIDATE_NAME
        elif cls.SEARCH_TYPE == "mecid":
            return cls.COMMITTEE_MECID
        else:
            return cls.COMMITTEE_NAME

    @classmethod
    def get_display_name(cls) -> str:
        if cls.SEARCH_TYPE == "candidate":
            return f"Candidate: {cls.CANDIDATE_NAME}"
        elif cls.SEARCH_TYPE == "mecid":
            return f"MECID: {cls.COMMITTEE_MECID}"
        else:
            return f"Committee: {cls.COMMITTEE_NAME}"

    @classmethod
    def get_file_prefix(cls) -> str:
        if cls.SEARCH_TYPE == "mecid":
            return cls.COMMITTEE_MECID

        name = cls.CANDIDATE_NAME if cls.SEARCH_TYPE == "candidate" else cls.COMMITTEE_NAME
        if not name:
            return "UNKNOWN"

        words = name.split()
        skip_words = {'for', 'to', 'the', 'of', 'and', 'a', 'an', 'elect'}

        initials = [w[0].upper() for w in words if w.lower() not in skip_words]
        prefix = ''.join(initials)
        if len(prefix) < 2:
            prefix = re.sub(r'[^A-Za-z0-9]', '', words[0])[:10].upper()
        if len(prefix) > 10:
            prefix = prefix[:10]
        return prefix

    @classmethod
    def clean_report_name(cls, report_name: str, max_length: int = 50) -> str:
        if not report_name:
            return "Unknown_Report"
        cleaned = re.sub(r'[^\w\s-]', '', report_name)
        cleaned = re.sub(r'[\s-]+', '_', cleaned.strip())
        cleaned = cleaned.strip('_')
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rstrip('_')
        return cleaned or "Unknown_Report"

    @classmethod
    def get_base_pdfs_dir(cls) -> Path:
        if 'PDFS_BASE_DIR' in os.environ:
            return Path(os.environ['PDFS_BASE_DIR'])
        else:
            return Path.home() / "Downloads" / "MEC_Reports"

    @classmethod
    def get_mecid_folder(cls, base_dir: str = None) -> Path:
        if not cls.COMMITTEE_MECID:
            raise ValueError("COMMITTEE_MECID must be set to use MECID folders")
        base_dir = base_dir or cls.get_base_pdfs_dir()
        return Path(base_dir) / cls.COMMITTEE_MECID

    @classmethod
    def ensure_mecid_folder(cls, base_dir: str = None) -> Path:
        folder = cls.get_mecid_folder(base_dir)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    @classmethod
    def get_filename_pattern(cls, report_name: str, report_id: str, year: int) -> str:
        prefix = cls.get_file_prefix()
        clean_name = cls.clean_report_name(report_name)
        return f"{prefix}_{clean_name}_{report_id}_{year}.pdf"

    @classmethod
    def parse_filename(cls, filename: str):
        prefix = re.escape(cls.get_file_prefix())
        pattern = rf"{prefix}_(.+?)_(\d+)_(\d{{4}})\.pdf"
        match = re.match(pattern, filename)
        if match:
            return {
                'report_name': match.group(1),
                'report_id': match.group(2),
                'year': int(match.group(3)),
                'filename': filename
            }
        return None

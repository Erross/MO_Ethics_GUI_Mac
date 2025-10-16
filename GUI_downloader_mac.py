"""
Missouri Ethics Commission Report Downloader (macOS)
Full-featured GUI for downloading and validating MEC reports.
"""

import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from pathlib import Path
import sys
import time
import os
import io

from config import Config
import download_workflow_mac as workflow


class MECDownloaderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Missouri Ethics Commission Report Downloader (macOS)")
        self.geometry("940x720")
        self.minsize(920, 680)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.is_downloading = False
        self.output_dir = tk.StringVar(value=str(Config.get_base_pdfs_dir()))
        self.search_mode = tk.StringVar(value="committee")
        self.committee_name = tk.StringVar(value=Config.COMMITTEE_NAME)
        self.candidate_name = tk.StringVar()
        self.mecid = tk.StringVar(value=Config.COMMITTEE_MECID)

        # === Header ===
        header_frame = ctk.CTkFrame(self, corner_radius=6)
        header_frame.pack(fill="x", padx=10, pady=(10, 6))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Missouri Ethics Commission Report Downloader",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side="left", padx=10, pady=10)

        open_site_btn = ctk.CTkButton(
            header_frame, text="Open MEC Search Website", command=self.open_mec_site
        )
        open_site_btn.pack(side="right", padx=10, pady=10)

        # === Instructions ===
        instructions = (
            "1. Choose your search type (Committee, Candidate, or MECID)\n"
            "2. Enter the name or ID\n"
            "3. Choose output directory (default is ~/Downloads/MEC_Reports)\n"
            "4. Click 'Start Download' to begin."
        )
        instr_label = ctk.CTkLabel(self, text=instructions, justify="left")
        instr_label.pack(anchor="w", padx=20, pady=(0, 10))

        # === Search Selection ===
        search_frame = ctk.CTkFrame(self, corner_radius=6)
        search_frame.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(search_frame, text="Search Type:").grid(row=0, column=0, padx=10, pady=6, sticky="e")
        for idx, (mode, text) in enumerate([
            ("committee", "Committee"),
            ("candidate", "Candidate"),
            ("mecid", "MEC ID")
        ]):
            rb = ctk.CTkRadioButton(
                search_frame, text=text, value=mode, variable=self.search_mode, command=self.update_search_fields
            )
            rb.grid(row=0, column=idx + 1, padx=10, pady=6, sticky="w")

        ctk.CTkLabel(search_frame, text="Committee Name:").grid(row=1, column=0, padx=10, pady=6, sticky="e")
        self.committee_entry = ctk.CTkEntry(search_frame, textvariable=self.committee_name, width=300)
        self.committee_entry.grid(row=1, column=1, padx=10, pady=6, columnspan=3, sticky="w")

        ctk.CTkLabel(search_frame, text="Candidate Name:").grid(row=2, column=0, padx=10, pady=6, sticky="e")
        self.candidate_entry = ctk.CTkEntry(search_frame, textvariable=self.candidate_name, width=300)
        self.candidate_entry.grid(row=2, column=1, padx=10, pady=6, columnspan=3, sticky="w")

        ctk.CTkLabel(search_frame, text="MEC ID:").grid(row=3, column=0, padx=10, pady=6, sticky="e")
        self.mecid_entry = ctk.CTkEntry(search_frame, textvariable=self.mecid, width=150)
        self.mecid_entry.grid(row=3, column=1, padx=10, pady=6, sticky="w")

        # === Output Folder ===
        output_frame = ctk.CTkFrame(self, corner_radius=6)
        output_frame.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(output_frame, text="Output Directory:").pack(side="left", padx=10)
        output_entry = ctk.CTkEntry(output_frame, textvariable=self.output_dir)
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(output_frame, text="Browse…", command=self.choose_output_dir).pack(side="right", padx=10)

        # === Buttons ===
        button_frame = ctk.CTkFrame(self, corner_radius=6)
        button_frame.pack(fill="x", padx=10, pady=(10, 4))

        self.start_button = ctk.CTkButton(button_frame, text="Start Download", command=self.start_download)
        self.start_button.pack(side="left", padx=10, pady=8)

        validate_button = ctk.CTkButton(button_frame, text="Validate Reports", command=self.run_validation)
        validate_button.pack(side="left", padx=10, pady=8)

        open_folder_button = ctk.CTkButton(button_frame, text="Open Output Folder", command=self.open_output_folder)
        open_folder_button.pack(side="left", padx=10, pady=8)

        # === Log Output ===
        log_frame = ctk.CTkFrame(self, corner_radius=6)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(8, 10))

        ctk.CTkLabel(log_frame, text="Process Log:").pack(anchor="w", padx=10, pady=(8, 2))

        self.log_box = ctk.CTkTextbox(log_frame)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_box.configure(state="disabled")

        self.update_search_fields()

    # === GUI Logic ===
    def update_search_fields(self):
        mode = self.search_mode.get()
        if mode == "committee":
            self.committee_entry.configure(state="normal")
            self.candidate_entry.configure(state="disabled")
            self.mecid_entry.configure(state="normal")
        elif mode == "candidate":
            self.committee_entry.configure(state="disabled")
            self.candidate_entry.configure(state="normal")
            self.mecid_entry.configure(state="normal")
        else:  # mecid
            self.committee_entry.configure(state="disabled")
            self.candidate_entry.configure(state="disabled")
            self.mecid_entry.configure(state="normal")

    def choose_output_dir(self):
        path = filedialog.askdirectory(initialdir=self.output_dir.get())
        if path:
            self.output_dir.set(path)
            os.environ['PDFS_BASE_DIR'] = path

    def open_mec_site(self):
        subprocess.run(["open", "https://mec.mo.gov/MEC/Campaign_Finance/CFSearch.aspx#gsc.tab=0"])

    def log(self, message: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.update_idletasks()

    def start_download(self):
        if self.is_downloading:
            return
        self.is_downloading = True
        self.start_button.configure(state="disabled")
        self.log("\n=== Starting MEC Report Download ===\n")

        mode = self.search_mode.get()
        Config.set_search(
            committee=self.committee_name.get() if mode == "committee" else None,
            candidate=self.candidate_name.get() if mode == "candidate" else None,
            mecid=self.mecid.get() if mode in ("mecid", "candidate", "committee") else None,
        )
        os.environ['PDFS_BASE_DIR'] = self.output_dir.get()

        t = threading.Thread(target=self._run_workflow_thread, daemon=True)
        t.start()

    def _run_workflow_thread(self):
        try:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()

            workflow.main()

            output = sys.stdout.getvalue() + sys.stderr.getvalue()
            for line in output.splitlines():
                self.log(line)
        except Exception as e:
            self.log(f"\nERROR: {e}")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.is_downloading = False
            self.start_button.configure(state="normal")

    def run_validation(self):
        mecid_value = self.mecid.get().strip()
        if not mecid_value:
            messagebox.showwarning("Missing MECID", "Please enter a MECID before validating reports.")
            return

        from validate_reports_mac import validate_reports

        self.log("\n=== Running Report Validation ===\n")
        all_valid, issues = validate_reports(mecid=mecid_value)

        if all_valid:
            self.log("[OK] All reports validated successfully!")
        else:
            self.log(f"[WARNING] Validation found {len(issues)} issues")

    def open_output_folder(self):
        try:
            path = Path(self.output_dir.get())
            if path.exists():
                subprocess.run(["open", str(path)])
            else:
                messagebox.showerror("Error", "Output folder not found.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def on_close(self):
        if self.is_downloading:
            if not messagebox.askokcancel("Quit", "A download is running. Stop and exit?"):
                return
        self.destroy()


def main():
    app = MECDownloaderGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

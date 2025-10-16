# Missouri Ethics Commission Report Downloader (macOS Version)

This repository is the **macOS-native deployment** of the [MO_Ethics_GUI](https://github.com/Erross/MO_Ethics_GUI) project — a complete, GUI-based automation tool that downloads and validates campaign finance reports from the **Missouri Ethics Commission (MEC)** website.

It replicates all the core functionality of the Windows version, rewritten and adjusted for macOS-specific dependencies and system calls, so that it can be executed and packaged into a standalone `.app` bundle for direct use on macOS systems.

---

## 🧩 Functionality Overview

The application provides an **end-to-end workflow** for collecting MEC report data:

1. **User-Friendly GUI**  
   - Built using `customtkinter` for a modern, responsive interface.  
   - Allows users to search by **Committee**, **Candidate**, or **MEC ID**.  
   - Offers a configurable download directory and displays a real-time activity log.  

2. **Automated Report Discovery & Download**  
   - Launches a Chrome browser through Selenium.  
   - Navigates the MEC campaign finance portal.  
   - Expands year sections and downloads every available report for the specified committee or candidate.  
   - Automatically skips files that already exist in the output folder.

3. **Anti-Detection & Stealth Measures**  
   - Human-like behavior: random delays, scrolling, and pauses between actions.  
   - Removes Selenium automation flags to reduce the chance of MEC site blocking.  

4. **Report Validation**  
   - After downloading, the app validates each report’s filename and PDF content.  
   - Ensures filing dates in the document match the year embedded in the filename.  
   - Reports inconsistencies directly in the log output.

5. **Directory Management & Naming Standards**  
   - Files are saved in structured folders by MEC ID (e.g., `~/Downloads/MEC_Reports/C2116`).  
   - Consistent naming convention:  
     ```
     {PREFIX}_{REPORT_NAME}_{REPORT_ID}_{YEAR}.pdf
     ```
     Example:  
     `FHF_October_Quarterly_Report_261218_2025.pdf`

6. **Full Logging and Multi-Threaded Operation**  
   - GUI remains responsive while Selenium runs in a background thread.  
   - Real-time output is captured and streamed to the user log window.

---

## 🔧 Windows vs macOS Differences

The macOS build preserves **all business logic** and structure from the original Windows version but introduces targeted platform-specific adjustments to ensure compatibility with macOS’s architecture and security model.

| Category | Windows Implementation | macOS Implementation | Reason for Change |
|-----------|------------------------|----------------------|-------------------|
| **Browser Control** | Uses `webdriver_manager` + ChromeDriver (Windows Chrome path) | Uses same, but detects `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` | macOS has a different Chrome binary path; direct detection avoids missing driver errors |
| **Keyboard Automation** | `pyautogui.hotkey('ctrl', 's')` for save dialogs | `pyautogui.hotkey('command', 's')` | macOS uses Command instead of Control for keyboard shortcuts |
| **File Opening** | `os.startfile(path)` | `subprocess.run(["open", path])` | macOS does not support `os.startfile`; `open` is the system-equivalent shell command |
| **Chrome Binary Access** | Relies on PATH or registry | Checks and assigns absolute Chrome path | macOS does not register Chrome in PATH by default |
| **Window Management** | Windows handles PDF save dialogs differently | Added stability delays for macOS Save dialogs | macOS Chrome introduces a short lag when the Save dialog spawns |
| **Executable Packaging** | Uses `.exe` or Windows installer | Built using PyInstaller with `--onefile --windowed --name "MO_Ethics_Tool_Mac"` | macOS apps are packaged as `.app` bundles rather than `.exe` binaries |
| **System Commands** | Uses `os.startfile`, PowerShell, or Explorer | Uses macOS-native `open` and POSIX pathing | macOS requires `open` for launching files/folders from scripts |
| **Output Directory Defaults** | Typically `C:\Users\<User>\Documents\MEC_PDFs` | Defaults to `~/Downloads/MEC_Reports` | Follows macOS sandbox-safe convention for user files |

---

## 🏗️ Project Structure


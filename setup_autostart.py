"""
Sets up notion-auto-meet to run automatically on system startup.
Supports macOS (Login Items via LaunchAgent) and Windows (Task Scheduler).
"""

import os
import sys
import platform
import subprocess
import logging

log = logging.getLogger("notion-auto-meet")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "main.py")
PYTHON_PATH = sys.executable


def setup_mac():
    """Create a LaunchAgent plist to auto-start on login."""
    plist_name = "com.notion-auto-meet.plist"
    plist_dir = os.path.expanduser("~/Library/LaunchAgents")
    plist_path = os.path.join(plist_dir, plist_name)

    os.makedirs(plist_dir, exist_ok=True)

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.notion-auto-meet</string>

    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON_PATH}</string>
        <string>{MAIN_SCRIPT}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{os.path.join(SCRIPT_DIR, "notion-auto-meet.log")}</string>

    <key>StandardErrorPath</key>
    <string>{os.path.join(SCRIPT_DIR, "notion-auto-meet-error.log")}</string>

    <key>WorkingDirectory</key>
    <string>{SCRIPT_DIR}</string>
</dict>
</plist>
"""
    with open(plist_path, "w") as f:
        f.write(plist_content)

    # Load the agent
    subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
    subprocess.run(["launchctl", "load", plist_path], check=True)

    print(f"macOS LaunchAgent installed at: {plist_path}")
    print("The tool will now start automatically on login.")
    print()
    print("IMPORTANT: You must grant Accessibility permissions:")
    print("  System Settings > Privacy & Security > Accessibility")
    print(f"  Add: {PYTHON_PATH}")
    print("  (or Terminal.app if running from terminal)")
    print()
    print("To stop:  launchctl unload ~/Library/LaunchAgents/com.notion-auto-meet.plist")
    print("To start: launchctl load ~/Library/LaunchAgents/com.notion-auto-meet.plist")


def setup_windows():
    """Create a Windows Task Scheduler task to auto-start on login."""
    task_name = "NotionAutoMeet"

    # Create the task using schtasks
    cmd = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", f'"{PYTHON_PATH}" "{MAIN_SCRIPT}"',
        "/SC", "ONLOGON",
        "/RL", "HIGHEST",
        "/F",  # Force overwrite if exists
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Windows Task Scheduler task '{task_name}' created.")
        print("The tool will now start automatically on login.")
        print()
        print("To remove: schtasks /Delete /TN NotionAutoMeet /F")
        print(f"To run now: schtasks /Run /TN NotionAutoMeet")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create scheduled task: {e}")
        print("Try running this script as Administrator.")

    # Also create a VBS wrapper to run without a visible console window
    vbs_path = os.path.join(SCRIPT_DIR, "run_hidden.vbs")
    vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{PYTHON_PATH}"" ""{MAIN_SCRIPT}""", 0, False
"""
    with open(vbs_path, "w") as f:
        f.write(vbs_content)
    print(f"\nAlternative: Add '{vbs_path}' to your Startup folder for silent launch.")


def remove_mac():
    """Remove the macOS LaunchAgent."""
    plist_path = os.path.expanduser("~/Library/LaunchAgents/com.notion-auto-meet.plist")
    if os.path.exists(plist_path):
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        os.remove(plist_path)
        print("macOS LaunchAgent removed.")
    else:
        print("No LaunchAgent found.")


def remove_windows():
    """Remove the Windows scheduled task."""
    subprocess.run(["schtasks", "/Delete", "/TN", "NotionAutoMeet", "/F"],
                    capture_output=True)
    print("Windows scheduled task removed.")


def main():
    system = platform.system()
    action = "install"
    if len(sys.argv) > 1 and sys.argv[1] == "--remove":
        action = "remove"

    if action == "remove":
        if system == "Darwin":
            remove_mac()
        elif system == "Windows":
            remove_windows()
    else:
        if system == "Darwin":
            setup_mac()
        elif system == "Windows":
            setup_windows()
        else:
            print(f"Unsupported platform: {system}")
            sys.exit(1)


if __name__ == "__main__":
    main()

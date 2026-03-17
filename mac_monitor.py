"""
macOS monitor: Uses Accessibility APIs to detect Notion's meeting popup
and automatically click the start/join button.
"""

import subprocess
import time
import logging
import re

log = logging.getLogger("notion-auto-meet")

# How often to check for the popup (seconds)
POLL_INTERVAL = 1.0

# AppleScript to find and click the Notion meeting popup button
# Notion shows a small popup with a button like "Start recording" or "Start notes"
# We look for buttons in Notion windows that match meeting-related text
DETECT_AND_CLICK_SCRIPT = '''
tell application "System Events"
    if not (exists process "Notion") then
        return "NO_NOTION"
    end if

    tell process "Notion"
        set allWindows to every window
        repeat with w in allWindows
            try
                -- Look for the meeting notes popup elements
                -- Notion's popup typically has buttons like "Start", "Start notes",
                -- "Start recording", "Join", or similar
                set allButtons to every button of w
                repeat with b in allButtons
                    set btnName to name of b
                    if btnName is not missing value then
                        if btnName contains "Start" or btnName contains "Record" or btnName contains "Join" then
                            -- Found the meeting start button, click it
                            click b
                            return "CLICKED:" & btnName
                        end if
                    end if
                end repeat

                -- Also check for buttons inside groups/containers
                set allGroups to every group of w
                repeat with g in allGroups
                    set groupButtons to every button of g
                    repeat with b in groupButtons
                        set btnName to name of b
                        if btnName is not missing value then
                            if btnName contains "Start" or btnName contains "Record" or btnName contains "Join" then
                                click b
                                return "CLICKED:" & btnName
                            end if
                        end if
                    end repeat
                end repeat

                -- Check UI elements / static texts for meeting-related content
                -- to confirm we're looking at the right popup
                set allTexts to every static text of w
                repeat with t in allTexts
                    set tVal to value of t
                    if tVal contains "meeting" or tVal contains "recording" or tVal contains "call" then
                        -- This window has meeting-related text, look harder for a start button
                        set allUIElems to every UI element of w
                        repeat with elem in allUIElems
                            try
                                if role of elem is "AXButton" then
                                    set elemName to name of elem
                                    if elemName is not missing value then
                                        if elemName contains "Start" or elemName contains "Record" or elemName contains "Join" or elemName contains "Yes" or elemName contains "Accept" then
                                            click elem
                                            return "CLICKED:" & elemName
                                        end if
                                    end if
                                end if
                            end try
                        end repeat
                    end if
                end repeat
            end try
        end repeat
    end tell
    return "NO_POPUP"
end tell
'''

# Alternative: Also monitor for meeting apps starting, to be ready
DETECT_MEETING_APP_SCRIPT = '''
tell application "System Events"
    set runningApps to name of every process
    set meetingApps to {}
    repeat with appName in runningApps
        if appName contains "zoom" or appName contains "Zoom" or appName contains "Teams" or appName contains "Webex" or appName contains "Google Meet" or appName contains "Slack" or appName contains "FaceTime" then
            set end of meetingApps to (appName as text)
        end if
    end repeat
    if (count of meetingApps) > 0 then
        set AppleScript's text item delimiters to ","
        return meetingApps as text
    else
        return "NONE"
    end if
end tell
'''


class MacNotionMonitor:
    def __init__(self):
        self.meeting_active = False
        self.last_click_time = 0
        # Cooldown: don't click again within 30 seconds of a successful click
        self.click_cooldown = 30

    def run_applescript(self, script: str) -> str:
        """Run an AppleScript and return its output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "TIMEOUT"
        except Exception as e:
            log.error(f"AppleScript error: {e}")
            return "ERROR"

    def check_meeting_apps(self) -> list[str]:
        """Check if any meeting apps are running."""
        result = self.run_applescript(DETECT_MEETING_APP_SCRIPT)
        if result and result != "NONE":
            return result.split(",")
        return []

    def try_click_popup(self) -> bool:
        """Try to find and click Notion's meeting popup. Returns True if clicked."""
        now = time.time()
        if now - self.last_click_time < self.click_cooldown:
            return False

        result = self.run_applescript(DETECT_AND_CLICK_SCRIPT)

        if result.startswith("CLICKED:"):
            button_name = result.split(":", 1)[1]
            log.info(f"Auto-clicked Notion meeting button: '{button_name}'")
            self.last_click_time = now
            return True
        elif result == "NO_NOTION":
            pass  # Notion not running, nothing to do
        elif result == "NO_POPUP":
            pass  # No popup found
        elif result == "TIMEOUT":
            log.warning("AppleScript timed out checking for popup")
        elif result == "ERROR":
            log.warning("Error running AppleScript")

        return False

    def run(self):
        """Main loop: continuously monitor for Notion meeting popup."""
        log.info("macOS monitor started. Watching for Notion meeting popups...")
        log.info("Tip: Grant Accessibility permissions to Terminal/Python in System Settings > Privacy & Security > Accessibility")

        while True:
            try:
                # Check if meeting apps are running
                meeting_apps = self.check_meeting_apps()
                if meeting_apps and not self.meeting_active:
                    log.info(f"Meeting app detected: {', '.join(meeting_apps)}")
                    self.meeting_active = True
                elif not meeting_apps and self.meeting_active:
                    log.info("Meeting apps closed")
                    self.meeting_active = False

                # Always check for the Notion popup (it can appear even without
                # a detected meeting app, e.g., for calendar-based meetings)
                self.try_click_popup()

                time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                log.info("Shutting down macOS monitor")
                break
            except Exception as e:
                log.error(f"Unexpected error: {e}")
                time.sleep(5)

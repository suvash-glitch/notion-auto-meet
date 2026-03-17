"""
Windows monitor: Uses UI Automation to detect Notion's meeting popup
and automatically click the start/join button.
"""

import time
import logging

log = logging.getLogger("notion-auto-meet")

# How often to check for the popup (seconds)
POLL_INTERVAL = 1.0

# Button text patterns that indicate a meeting start action
MEETING_BUTTON_PATTERNS = ["start", "record", "join", "yes", "accept"]

# Meeting app process names to watch for
MEETING_PROCESS_NAMES = [
    "zoom.exe", "teams.exe", "webex.exe", "slack.exe",
    "googlemeetdesktopapp.exe",
]


class WinNotionMonitor:
    def __init__(self):
        self.meeting_active = False
        self.last_click_time = 0
        self.click_cooldown = 30

        # Import Windows-specific modules
        try:
            import uiautomation as auto
            self.auto = auto
            log.info("Using uiautomation library")
        except ImportError:
            log.error(
                "uiautomation not installed. Run: pip install uiautomation"
            )
            raise

    def check_meeting_apps(self) -> list[str]:
        """Check if any meeting app processes are running."""
        import subprocess
        found = []
        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10
            )
            output_lower = result.stdout.lower()
            for proc in MEETING_PROCESS_NAMES:
                if proc in output_lower:
                    found.append(proc)
        except Exception as e:
            log.error(f"Error checking processes: {e}")
        return found

    def try_click_popup(self) -> bool:
        """Find Notion's meeting popup and auto-click the start button."""
        now = time.time()
        if now - self.last_click_time < self.click_cooldown:
            return False

        auto = self.auto
        try:
            # Find the Notion window
            notion_window = auto.WindowControl(
                searchDepth=1, Name="Notion", SubName="Notion"
            )
            if not notion_window.Exists(maxSearchSeconds=0.5):
                # Try alternative: Notion may have different window titles
                notion_window = auto.WindowControl(
                    searchDepth=1, AutomationId="", ClassName="Chrome_WidgetWin_1",
                    SubName="Notion"
                )
                if not notion_window.Exists(maxSearchSeconds=0.5):
                    return False

            # Search all buttons in the Notion window
            buttons = notion_window.GetChildren()
            return self._search_elements_recursive(notion_window, depth=0, max_depth=10)

        except Exception as e:
            log.debug(f"UI Automation search error: {e}")
            return False

    def _search_elements_recursive(self, element, depth: int, max_depth: int) -> bool:
        """Recursively search UI elements for a meeting-related button."""
        if depth > max_depth:
            return False

        auto = self.auto
        try:
            children = element.GetChildren()
            for child in children:
                try:
                    # Check if this is a button with meeting-related text
                    control_type = child.ControlTypeName
                    name = (child.Name or "").lower()

                    if control_type == "ButtonControl" and name:
                        for pattern in MEETING_BUTTON_PATTERNS:
                            if pattern in name:
                                # Verify it's in a meeting-related context
                                # by checking sibling/parent text
                                if self._has_meeting_context(element):
                                    log.info(
                                        f"Auto-clicking Notion meeting button: '{child.Name}'"
                                    )
                                    child.Click()
                                    self.last_click_time = time.time()
                                    return True

                    # Recurse into children
                    if self._search_elements_recursive(child, depth + 1, max_depth):
                        return True

                except Exception:
                    continue
        except Exception:
            pass

        return False

    def _has_meeting_context(self, element) -> bool:
        """Check if an element's context suggests it's a meeting popup."""
        try:
            children = element.GetChildren()
            for child in children:
                try:
                    name = (child.Name or "").lower()
                    if any(kw in name for kw in ["meeting", "recording", "call", "notes", "transcri"]):
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        # If we can't determine context, still proceed (better to click than miss)
        return True

    def run(self):
        """Main loop: continuously monitor for Notion meeting popup."""
        log.info("Windows monitor started. Watching for Notion meeting popups...")

        while True:
            try:
                # Check for meeting apps
                meeting_apps = self.check_meeting_apps()
                if meeting_apps and not self.meeting_active:
                    log.info(f"Meeting app detected: {', '.join(meeting_apps)}")
                    self.meeting_active = True
                elif not meeting_apps and self.meeting_active:
                    log.info("Meeting apps closed")
                    self.meeting_active = False

                # Check for Notion popup
                self.try_click_popup()

                time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                log.info("Shutting down Windows monitor")
                break
            except Exception as e:
                log.error(f"Unexpected error: {e}")
                time.sleep(5)

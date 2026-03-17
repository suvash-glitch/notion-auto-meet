"""
Browser-based monitor: Opens Notion in a Playwright-controlled browser
and auto-clicks the "Start Transcribing" button whenever it appears.

Works on both macOS and Windows — no Accessibility API needed.
"""

import asyncio
import logging
import os

from playwright.async_api import async_playwright, Page, BrowserContext

log = logging.getLogger("notion-auto-meet")

# How often to check for the button (seconds)
POLL_INTERVAL = 1.5

# Notion URL
NOTION_URL = "https://www.notion.so"

# Directory to persist browser session (so you don't re-login every time)
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".browser-data")

# JavaScript that finds and clicks the "Start Transcribing" button.
# Searches for buttons/elements containing meeting-related text.
AUTO_CLICK_JS = """
() => {
    // Selectors to find the "Start Transcribing" or similar meeting buttons
    const buttonTexts = [
        'start transcribing',
        'start recording',
        'start meeting',
        'start notes',
        'join meeting',
        'start',
    ];

    // Search all clickable elements
    const clickables = document.querySelectorAll(
        'button, [role="button"], div[class*="button"], div[class*="Button"], a[class*="button"]'
    );

    for (const el of clickables) {
        const text = (el.textContent || '').trim().toLowerCase();
        for (const target of buttonTexts) {
            if (text === target || text.includes(target)) {
                // Extra check: make sure it's visible
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    el.click();
                    return { clicked: true, text: el.textContent.trim() };
                }
            }
        }
    }

    // Also check for Notion's specific popup/modal for meeting notes
    // Notion uses portals/overlays for popups
    const overlays = document.querySelectorAll(
        '[class*="overlay"], [class*="modal"], [class*="popup"], [class*="Popup"], [class*="dialog"], [class*="Dialog"], [class*="toast"], [class*="Toast"]'
    );

    for (const overlay of overlays) {
        const overlayText = (overlay.textContent || '').toLowerCase();
        if (overlayText.includes('transcrib') || overlayText.includes('meeting') || overlayText.includes('recording')) {
            // Found a meeting-related overlay, look for action buttons inside
            const buttons = overlay.querySelectorAll(
                'button, [role="button"], div[class*="button"], div[class*="Button"]'
            );
            for (const btn of buttons) {
                const btnText = (btn.textContent || '').trim().toLowerCase();
                // Click the positive action button (not dismiss/close)
                if (btnText.includes('start') || btnText.includes('join') || btnText.includes('yes') || btnText.includes('accept') || btnText.includes('begin')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        btn.click();
                        return { clicked: true, text: btn.textContent.trim() };
                    }
                }
            }
        }
    }

    return { clicked: false };
}
"""

# JavaScript to inject a MutationObserver that auto-clicks as soon as
# the button appears (faster than polling)
MUTATION_OBSERVER_JS = """
() => {
    if (window.__notionAutoMeetObserver) return 'ALREADY_INSTALLED';

    const buttonTexts = [
        'start transcribing',
        'start recording',
        'start meeting',
        'start notes',
    ];

    function tryAutoClick(root) {
        const clickables = (root || document).querySelectorAll(
            'button, [role="button"], div[class*="button"], div[class*="Button"]'
        );
        for (const el of clickables) {
            const text = (el.textContent || '').trim().toLowerCase();
            for (const target of buttonTexts) {
                if (text === target || text.includes(target)) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        el.click();
                        console.log('[notion-auto-meet] Auto-clicked: ' + el.textContent.trim());
                        return true;
                    }
                }
            }
        }
        return false;
    }

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const text = (node.textContent || '').toLowerCase();
                    if (text.includes('transcrib') || text.includes('meeting') || text.includes('recording')) {
                        // Small delay to let the popup fully render
                        setTimeout(() => tryAutoClick(node) || tryAutoClick(document), 500);
                    }
                }
            }
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    window.__notionAutoMeetObserver = observer;
    console.log('[notion-auto-meet] MutationObserver installed');
    return 'INSTALLED';
}
"""


class NotionBrowserMonitor:
    def __init__(self):
        self.last_click_time = 0
        self.click_cooldown = 30  # seconds

    async def run(self):
        log.info("Starting Playwright browser...")

        async with async_playwright() as p:
            # Use persistent context so login session is saved
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,  # Must be headed so Notion can detect meetings
                args=[
                    "--window-size=800,600",
                    "--window-position=9999,9999",  # Start off-screen
                ],
                ignore_default_args=["--enable-automation"],
                no_viewport=True,
            )

            # Get the first page or create one
            if context.pages:
                page = context.pages[0]
            else:
                page = await context.new_page()

            # Navigate to Notion
            log.info(f"Navigating to {NOTION_URL}")
            await page.goto(NOTION_URL, wait_until="domcontentloaded")
            log.info(f"Page loaded: {page.url}")

            # Check if we need to log in
            if "login" in page.url.lower():
                log.info("=" * 50)
                log.info("LOGIN REQUIRED: A browser window has opened.")
                log.info("Please log in to Notion. The window will move")
                log.info("off-screen after login is detected.")
                log.info("=" * 50)

                # Move window on-screen so user can log in
                await page.evaluate("window.moveTo(100, 100)")

                # Wait for login to complete (URL changes away from /login)
                while "login" in page.url.lower():
                    await asyncio.sleep(2)

                log.info("Login detected! Moving window off-screen...")
                await page.evaluate("window.moveTo(9999, 9999)")

            # Install the MutationObserver for instant detection
            result = await page.evaluate(MUTATION_OBSERVER_JS)
            log.info(f"MutationObserver: {result}")

            # Listen for console messages from our injected script
            page.on("console", lambda msg: self._on_console(msg))

            # Also re-install observer on navigation
            page.on("load", lambda: asyncio.ensure_future(self._reinstall_observer(page)))

            log.info("Monitoring active. Will auto-click 'Start Transcribing' when it appears.")
            log.info("Press Ctrl+C to stop.")

            # Backup: poll as fallback in case MutationObserver misses something
            while True:
                try:
                    await self._poll_and_click(page)
                    await asyncio.sleep(POLL_INTERVAL)
                except KeyboardInterrupt:
                    log.info("Shutting down...")
                    break
                except Exception as e:
                    log.error(f"Poll error: {e}")
                    await asyncio.sleep(5)

            await context.close()

    async def _reinstall_observer(self, page: Page):
        """Re-install the MutationObserver after page navigation."""
        try:
            await asyncio.sleep(2)  # Wait for page to settle
            result = await page.evaluate(MUTATION_OBSERVER_JS)
            log.info(f"Re-installed MutationObserver: {result}")
        except Exception as e:
            log.debug(f"Observer reinstall error: {e}")

    async def _poll_and_click(self, page: Page):
        """Fallback: periodically check for the button via JS."""
        import time
        now = time.time()
        if now - self.last_click_time < self.click_cooldown:
            return

        try:
            result = await page.evaluate(AUTO_CLICK_JS)
            if result and result.get("clicked"):
                log.info(f"[Poll] Auto-clicked: '{result.get('text')}'")
                self.last_click_time = now
        except Exception as e:
            log.debug(f"Poll evaluate error: {e}")

    def _on_console(self, msg):
        """Log console messages from our injected scripts."""
        text = msg.text
        if "notion-auto-meet" in text:
            log.info(f"[Browser] {text}")

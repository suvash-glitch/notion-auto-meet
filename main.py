"""
Notion Auto-Meet: Instantly clicks "Start Transcribing" when
Notion shows its meeting popup. Scans all monitors.

Cross-platform: macOS (Quartz) and Windows (mss + win32api).

Optimized for speed:
- Only captures a thin strip (top 150px) of each display
- Raw numpy buffer — no PIL conversion
- Polls every 100ms

On Windows, first run auto-registers for startup. No installer needed.
"""

import sys
import os
import platform
import time
import logging
import numpy as np
import pyautogui

SYSTEM = platform.system()

# Windows: declare DPI awareness so coordinates are always in physical pixels
# This must happen before any GUI/screen calls
if SYSTEM == "Windows":
    try:
        ctypes = __import__("ctypes")
        # Per-Monitor DPI aware (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            # Fallback for older Windows
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

# Log to a writable location (next to exe, or AppData on Windows)
if SYSTEM == "Windows":
    _log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "NotionAutoMeet")
    os.makedirs(_log_dir, exist_ok=True)
    _log_file = os.path.join(_log_dir, "notion-auto-meet.log")
else:
    _log_file = "notion-auto-meet.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_log_file),
    ],
)
log = logging.getLogger("notion-auto-meet")

# --- Configuration ---
POLL_INTERVAL = 0.1  # 100ms — near-instant detection
SCAN_HEIGHT = 150    # Only capture top 150px of each display
CLICK_COOLDOWN = 30  # Seconds after a click before scanning again
MIN_MATCHING_PIXELS = 20

# Blue color of the "Start transcribing" button
R_MIN, R_MAX = 50, 130
G_MIN, G_MAX = 140, 200
B_MIN, B_MAX = 200, 255

# ──────────────────────────────────────────────
# Windows: first-run self-install
# ──────────────────────────────────────────────

def _windows_install_dir():
    r"""Return the fixed install directory: %LOCALAPPDATA%\NotionAutoMeet"""
    return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "NotionAutoMeet")


def _windows_first_run():
    """On first run, copy exe to install dir, register for autostart, and notify."""
    import winreg
    import shutil
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value_name = "NotionAutoMeet"

    install_dir = _windows_install_dir()
    os.makedirs(install_dir, exist_ok=True)
    installed_exe = os.path.join(install_dir, "NotionAutoMeet.exe")

    # Get current exe path
    if getattr(sys, 'frozen', False):
        current_exe = sys.executable
    else:
        # Running as script — register python + script for autostart
        current_exe = None

    # If running as a frozen exe, copy to install dir (self-install / update)
    if current_exe and os.path.normcase(os.path.abspath(current_exe)) != os.path.normcase(os.path.abspath(installed_exe)):
        try:
            shutil.copy2(current_exe, installed_exe)
            log.info(f"Installed/updated to: {installed_exe}")
        except PermissionError:
            # The installed copy is likely running; this is fine on update
            log.info("Could not overwrite installed exe (may be in use), skipping copy")
        except OSError as e:
            log.warning(f"Could not copy to install dir: {e}")

    # Determine what to register for autostart
    if current_exe:
        autostart_path = f'"{installed_exe}"'
    else:
        autostart_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'

    # Check if already registered with correct path
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            existing, _ = winreg.QueryValueEx(key, value_name)
            if existing == autostart_path:
                return  # already registered correctly
    except FileNotFoundError:
        pass
    except OSError:
        pass

    # Register for autostart (always points to installed_exe)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, autostart_path)
        log.info(f"Registered for autostart: {autostart_path}")
    except OSError as e:
        log.warning(f"Could not register autostart: {e}")

    # Show a Windows notification on first run
    try:
        from tkinter import Tk, messagebox
        root = Tk()
        root.withdraw()
        messagebox.showinfo(
            "Notion Auto-Meet",
            "Notion Auto-Meet is now running in the background.\n\n"
            "It will automatically start when you log in.\n"
            "It watches for Notion's meeting popup and clicks\n"
            "\"Start Transcribing\" for you.\n\n"
            f"Installed to: {install_dir}\n"
            f"Logs: {_log_file}"
        )
        root.destroy()
    except Exception:
        pass  # non-critical


# ──────────────────────────────────────────────
# Platform-specific: screen capture & process check
# ──────────────────────────────────────────────

if SYSTEM == "Darwin":
    from Quartz import (
        CGWindowListCreateImage, CGRectMake,
        kCGWindowListOptionOnScreenOnly, kCGNullWindowID,
        kCGWindowImageDefault,
        CGImageGetWidth, CGImageGetHeight,
        CGImageGetBytesPerRow, CGImageGetDataProvider,
        CGDataProviderCopyData,
        CGGetActiveDisplayList, CGDisplayBounds,
    )
    import subprocess

    def get_displays():
        err, display_ids, count = CGGetActiveDisplayList(10, None, None)
        displays = []
        for d in display_ids:
            bounds = CGDisplayBounds(d)
            displays.append({
                "id": d,
                "x": int(bounds.origin.x),
                "y": int(bounds.origin.y),
                "w": int(bounds.size.width),
                "h": int(bounds.size.height),
            })
        return displays

    def capture_strip(disp):
        """Capture top SCAN_HEIGHT px of a display. Returns (BGRA array, scale_x, scale_y) or None."""
        rect = CGRectMake(disp["x"], disp["y"], disp["w"], SCAN_HEIGHT)
        cg_image = CGWindowListCreateImage(
            rect, kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID, kCGWindowImageDefault,
        )
        if not cg_image:
            return None

        w = CGImageGetWidth(cg_image)
        h = CGImageGetHeight(cg_image)
        bpr = CGImageGetBytesPerRow(cg_image)
        raw = CGDataProviderCopyData(CGImageGetDataProvider(cg_image))

        buf = np.frombuffer(raw, dtype=np.uint8).reshape(h, bpr)
        arr = buf[:, :w * 4].reshape(h, w, 4)  # BGRA
        return arr, w / disp["w"], h / SCAN_HEIGHT

    def find_button_in_arr(arr, scale_x, scale_y, disp):
        """Scan BGRA array for the blue button. Returns screen (x,y) or None."""
        b, g, r = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        mask = (
            (r >= R_MIN) & (r <= R_MAX) &
            (g >= G_MIN) & (g <= G_MAX) &
            (b >= B_MIN) & (b <= B_MAX)
        )
        return _cluster_check(mask, scale_x, scale_y, disp)

    def is_notion_running():
        try:
            return subprocess.run(
                ["pgrep", "-x", "Notion"], capture_output=True, timeout=2
            ).returncode == 0
        except Exception:
            return False


elif SYSTEM == "Windows":
    import ctypes
    import ctypes.wintypes
    import mss

    # Win32 SendInput structures for reliable clicking
    INPUT_MOUSE = 0
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_ABSOLUTE = 0x8000

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.wintypes.LONG),
            ("dy", ctypes.wintypes.LONG),
            ("mouseData", ctypes.wintypes.DWORD),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("time", ctypes.wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.wintypes.DWORD),
            ("mi", MOUSEINPUT),
        ]

    def _win_click(x, y):
        """Click at screen coordinates using SendInput with absolute coords."""
        # Convert screen coords to absolute (0-65535) coordinate space
        # Use virtual screen metrics for multi-monitor support
        sm_xvscreen = ctypes.windll.user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        sm_yvscreen = ctypes.windll.user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        sm_cxvscreen = ctypes.windll.user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        sm_cyvscreen = ctypes.windll.user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN

        abs_x = int(((x - sm_xvscreen) * 65535) / sm_cxvscreen)
        abs_y = int(((y - sm_yvscreen) * 65535) / sm_cyvscreen)

        # Move to position
        move = INPUT()
        move.type = INPUT_MOUSE
        move.mi.dx = abs_x
        move.mi.dy = abs_y
        move.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
        ctypes.windll.user32.SendInput(1, ctypes.byref(move), ctypes.sizeof(INPUT))
        time.sleep(0.1)

        # Mouse down
        down = INPUT()
        down.type = INPUT_MOUSE
        down.mi.dx = abs_x
        down.mi.dy = abs_y
        down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE
        ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
        time.sleep(0.05)

        # Mouse up
        up = INPUT()
        up.type = INPUT_MOUSE
        up.mi.dx = abs_x
        up.mi.dy = abs_y
        up.mi.dwFlags = MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE
        ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))

        log.info(f"SendInput click at screen ({x},{y}) -> abs ({abs_x},{abs_y}), "
                 f"vscreen: origin=({sm_xvscreen},{sm_yvscreen}) size=({sm_cxvscreen}x{sm_cyvscreen})")

    _sct = mss.mss()

    def get_displays():
        displays = []
        for i, mon in enumerate(_sct.monitors[1:], start=1):  # skip the "all" monitor
            displays.append({
                "id": i,
                "x": mon["left"],
                "y": mon["top"],
                "w": mon["width"],
                "h": mon["height"],
            })
        return displays

    def capture_strip(disp):
        """Capture top SCAN_HEIGHT px of a display. Returns (BGRA array, scale_x, scale_y) or None."""
        region = {
            "left": disp["x"],
            "top": disp["y"],
            "width": disp["w"],
            "height": SCAN_HEIGHT,
        }
        try:
            shot = _sct.grab(region)
            # mss returns BGRA
            arr = np.frombuffer(shot.raw, dtype=np.uint8).reshape(shot.height, shot.width, 4)
            return arr, 1.0, 1.0  # mss returns at screen resolution (no retina on Windows)
        except Exception:
            return None

    def find_button_in_arr(arr, scale_x, scale_y, disp):
        """Scan BGRA array for the blue button. Returns screen (x,y) or None."""
        b, g, r = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        mask = (
            (r >= R_MIN) & (r <= R_MAX) &
            (g >= G_MIN) & (g <= G_MAX) &
            (b >= B_MIN) & (b <= B_MAX)
        )
        return _cluster_check(mask, scale_x, scale_y, disp)

    import subprocess

    # Prevent subprocess from flashing a console window on Windows
    _startupinfo = subprocess.STARTUPINFO()
    _startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _startupinfo.wShowWindow = 0  # SW_HIDE
    _creation_flags = subprocess.CREATE_NO_WINDOW

    def is_notion_running():
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Notion.exe", "/NH"],
                capture_output=True, text=True, timeout=2,
                startupinfo=_startupinfo,
                creationflags=_creation_flags,
            )
            return "Notion.exe" in result.stdout
        except Exception:
            return False

else:
    log.error(f"Unsupported platform: {SYSTEM}")
    sys.exit(1)


# ──────────────────────────────────────────────
# Shared logic
# ──────────────────────────────────────────────

def _cluster_check(mask, scale_x, scale_y, disp):
    """Given a boolean mask of matching pixels, check for a button-shaped cluster.
    Returns absolute screen (x,y) or None."""
    ys, xs = np.where(mask)
    if len(xs) < MIN_MATCHING_PIXELS:
        return None

    avg_x, avg_y = int(np.mean(xs)), int(np.mean(ys))
    cw, ch = int(100 * scale_x), int(25 * scale_y)

    cmask = (np.abs(xs - avg_x) < cw) & (np.abs(ys - avg_y) < ch)
    cxs, cys = xs[cmask], ys[cmask]

    if len(cxs) >= MIN_MATCHING_PIXELS:
        cx = int(np.mean(cxs))
        cy = int(np.mean(cys))
        return (disp["x"] + int(cx / scale_x), disp["y"] + int(cy / scale_y))

    return None


def _windows_uninstall():
    """Remove autostart registry entry and installed files."""
    import winreg
    import shutil
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, "NotionAutoMeet")
        print("Removed from startup.")
    except FileNotFoundError:
        print("Was not registered for startup.")
    except OSError as e:
        print(f"Registry error: {e}")

    # Clean up install directory
    install_dir = _windows_install_dir()
    if os.path.exists(install_dir):
        try:
            shutil.rmtree(install_dir)
            print(f"Removed install directory: {install_dir}")
        except OSError as e:
            print(f"Could not fully remove {install_dir}: {e}")
    print("Notion Auto-Meet uninstalled.")


def main():
    # Handle --uninstall flag
    if "--uninstall" in sys.argv:
        if SYSTEM == "Windows":
            _windows_uninstall()
        else:
            print("Use: python setup_autostart.py --remove")
        return

    # Windows: auto-register on first run
    if SYSTEM == "Windows":
        _windows_first_run()

    displays = get_displays()
    log.info(f"Notion Auto-Meet started (FAST MODE) on {SYSTEM}")
    log.info(f"{len(displays)} display(s):")
    for d in displays:
        log.info(f"  Display {d['id']}: {d['w']}x{d['h']} at ({d['x']},{d['y']})")
    log.info(f"Poll: {int(POLL_INTERVAL*1000)}ms | Cooldown: {CLICK_COOLDOWN}s")
    log.info("Watching...")

    last_click = 0
    notion_check_counter = 0
    notion_running = True  # assume running at start

    while True:
        try:
            now = time.time()

            if now - last_click < CLICK_COOLDOWN:
                time.sleep(POLL_INTERVAL)
                continue

            # Only check if Notion is running every ~2 seconds (20 loops)
            notion_check_counter += 1
            if notion_check_counter >= 20:
                notion_check_counter = 0
                notion_running = is_notion_running()
                if not notion_running:
                    time.sleep(1)
                    continue

            if not notion_running:
                time.sleep(1)
                continue

            # Scan all displays
            for disp in displays:
                result = capture_strip(disp)
                if result is None:
                    continue
                arr, sx, sy = result
                pos = find_button_in_arr(arr, sx, sy, disp)
                if pos:
                    x, y = pos[0], pos[1]
                    if SYSTEM == "Windows":
                        _win_click(x, y)
                    else:
                        pyautogui.click(x, y)
                    log.info(f"CLICKED 'Start transcribing' at ({x},{y}) on display {disp['id']}")
                    last_click = time.time()
                    break

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log.info("Shutting down.")
            break
        except Exception as e:
            log.error(f"Error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()

"""
Helper: Move your mouse over the "Start Transcribing" button,
then press Enter. This will print the exact coordinates to use.
"""
import pyautogui
import time

print("=" * 50)
print("STEP 1: Hover your mouse over the 'Start Transcribing' button")
print("STEP 2: Press Enter here (don't move the mouse)")
print("=" * 50)

input("Press Enter when your mouse is over the button...")

x, y = pyautogui.position()
screen_w, screen_h = pyautogui.size()

print(f"\nButton position: x={x}, y={y}")
print(f"Screen size: {screen_w}x{screen_h}")
print(f"\nAs percentage: x={x/screen_w:.3f}, y={y/screen_h:.3f}")
print(f"\nUse these in the auto-clicker script!")

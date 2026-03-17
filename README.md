# Notion Auto-Meet

Automatically starts Notion AI meeting notes when a call/meeting begins — no manual clicking required.

## How it works

1. Runs silently in the background
2. Polls every 1 second for Notion's meeting popup
3. When the popup appears (triggered by Zoom, Teams, Meet, etc.), it auto-clicks the "Start" button
4. Meeting notes begin recording without any user action

## Setup

### macOS

```bash
# 1. No extra dependencies needed
cd notion-auto-meet

# 2. Test it manually first
python main.py

# 3. Set up auto-start on login
python setup_autostart.py

# 4. IMPORTANT: Grant Accessibility permissions
#    System Settings > Privacy & Security > Accessibility
#    Add Python or Terminal.app
```

### Windows

```bash
# 1. Install dependencies
pip install uiautomation

# 2. Test it manually first
python main.py

# 3. Set up auto-start on login (run as Administrator)
python setup_autostart.py
```

## Uninstall

```bash
python setup_autostart.py --remove
```

## Logs

Check `notion-auto-meet.log` in the project directory for activity.

## Supported Meeting Apps

Zoom, Microsoft Teams, Google Meet, Webex, Slack, FaceTime

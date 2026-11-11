"""Experimental macOS backend: Chrome Apple Events + native display capture.

Hardware validation is intentionally tracked separately from build success.
No extension, remote debugging port, or network service is used.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import Quartz
from AppKit import NSWorkspace
from PIL import Image

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
CLOCK_LABEL = 'The macOS menu-bar date and clock are visible.'
LIVE_COMPANION = False


def invoke(action, **kwargs):
    result = subprocess.run(['/usr/bin/osascript', '-l', 'JavaScript', str(BASE / 'browser_macos.js'),
                             json.dumps(dict(action=action, **kwargs))],
                            capture_output=True, text=True, timeout=25)
    if result.returncode:
        raise RuntimeError('macOS browser automation failed. Allow Automation access to Google Chrome and enable Chrome → View → Developer → Allow JavaScript from Apple Events. ' + result.stderr.strip())
    data = json.loads(result.stdout)
    if not data.get('ok'): raise RuntimeError(data.get('error', 'Browser automation failed.'))
    return data


def monitors():
    error, ids, count = Quartz.CGGetActiveDisplayList(32, None, None)
    if error: raise RuntimeError('macOS could not enumerate the displays.')
    ids = list(ids[:count])
    main = Quartz.CGMainDisplayID()
    ids.sort(key=lambda display: display != main)
    result = []
    for display in ids:
        rect = Quartz.CGDisplayBounds(display)
        x, y = int(rect.origin.x), int(rect.origin.y)
        result.append((int(display), (x, y, x + int(rect.size.width), y + int(rect.size.height))))
    return result


def browsers():
    # Permission denial must remain visible to the user rather than an empty list.
    return [(item['id'], item['title']) for item in invoke('windows')['windows']]


def monitor_for_window(hwnd):
    bounds = invoke('bounds', hwnd=hwnd)['bounds']
    # Chromium's scripting rectangle is {left, top, right, bottom}.
    x, y = (bounds[0] + bounds[2])/2, (bounds[1] + bounds[3])/2
    displays = monitors()
    return next((display for display, r in displays if r[0] <= x < r[2] and r[1] <= y < r[3]), displays[0][0])


def foreground_window():
    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    if front.processIdentifier() == os.getpid(): return 'heyou-app'
    if front.bundleIdentifier() == 'com.google.Chrome':
        return invoke('front')['id']
    return None


def native_handle(root): return 'heyou-app'
def position_window(root, x, y, w, h):
    # Keep the live companion disabled for the initial Mac beta; its exact
    # placement across differently scaled screens requires hardware testing.
    root.withdraw()


def activate(hwnd): invoke('activate', hwnd=hwnd)
def window_title(hwnd): return invoke('title', hwnd=hwnd)['title']
def escape_pressed(): return bool(Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateCombinedSessionState, 53))


def taskbar_visible(bbox):
    if not Quartz.CGPreflightScreenCaptureAccess():
        Quartz.CGRequestScreenCaptureAccess()
        raise RuntimeError('Allow Heyou Capture in System Settings → Privacy & Security → Screen & System Audio Recording, then restart the app.')
    # Clock/date visibility is the user's confirmation in Capture settings.
    # This does not OCR or invent a timestamp.
    preference = subprocess.run(['/usr/bin/defaults', 'read', '-g', '_HIHideMenuBar'], capture_output=True, text=True)
    return preference.stdout.strip() not in ('1', 'true')


def grab(bbox):
    if not taskbar_visible(bbox):
        raise RuntimeError('Show the macOS menu bar and clock; disable automatically hiding the menu bar.')
    displays = monitors()
    index = next((i+1 for i, (_, rect) in enumerate(displays) if rect == tuple(bbox)), None)
    if index is None: raise RuntimeError('The selected display disconnected. Refresh sources and retry.')
    with tempfile.TemporaryDirectory(prefix='heyou-capture-') as directory:
        path = Path(directory) / 'screen.png'
        result = subprocess.run(['/usr/sbin/screencapture', '-x', '-D', str(index), str(path)], capture_output=True, text=True, timeout=15)
        if result.returncode or not path.is_file(): raise RuntimeError('macOS screen capture failed. Check Screen Recording permission. ' + result.stderr.strip())
        with Image.open(path) as image: return image.convert('RGB')


def open_file(path): subprocess.Popen(['/usr/bin/open', str(Path(path).resolve())])
def log_directory(): return Path.home() / 'Library' / 'Application Support' / 'Heyou Capture' / 'logs'


class Automation:
    def __init__(self):
        self.hwnd = None
        self.original = None
        self.tab_ids = []

    def call(self, action, **kwargs):
        self.hwnd = kwargs.get('hwnd', self.hwnd)
        if action == 'tabs':
            data = invoke('tabs', hwnd=self.hwnd)
            self.tab_ids = [tab['id'] for tab in data['tabs']]
            return data
        if action in ('select_tab', 'tab_selected'):
            return invoke(action, hwnd=self.hwnd, tab_id=self.tab_ids[kwargs['index']])
        if action == 'url': return invoke('url', hwnd=self.hwnd)
        if action == 'attach':
            data = invoke('metrics', hwnd=self.hwnd)
            self.original = data['percent']
            return data
        if action == 'status': return invoke('metrics', hwnd=self.hwnd)
        if action == 'scroll': return invoke('scroll', hwnd=self.hwnd, percent=kwargs['percent'])
        if action == 'restore':
            if self.original is not None and self.original >= 0:
                return invoke('scroll', hwnd=self.hwnd, percent=self.original)
            return dict(ok=True)
        raise RuntimeError('Unsupported browser action: ' + action)

    def close(self): pass

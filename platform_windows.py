"""Windows display capture and native browser accessibility."""
import ctypes
from ctypes import wintypes
import json, os, queue, subprocess, sys, threading
from pathlib import Path
from PIL import ImageGrab
BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
user32 = ctypes.windll.user32
user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
user32.GetForegroundWindow.restype = wintypes.HWND
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
kernel32 = ctypes.windll.kernel32
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]


def is_browser(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    if not handle: return False
    try:
        size = wintypes.DWORD(32768)
        path = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)): return False
        return Path(path.value).name.lower() in {'chrome.exe', 'msedge.exe', 'brave.exe', 'vivaldi.exe', 'opera.exe', 'firefox.exe'}
    finally:
        kernel32.CloseHandle(handle)


def taskbar_visible(bbox):
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, data):
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value in ('Shell_TrayWnd', 'Shell_SecondaryTrayWnd') and user32.IsWindowVisible(hwnd):
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            visible_height = min(rect.bottom, bbox[3]) - max(rect.top, bbox[1])
            if visible_height >= 20 and abs(rect.bottom - bbox[3]) <= 5 and rect.left < bbox[2] and rect.right > bbox[0]:
                found.append(True)
        return True
    user32.EnumWindows(callback_type(callback), 0)
    return bool(found)


def monitors():
    result = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    def callback(handle, dc, rect, data):
        r = rect.contents
        result.append((handle, (r.left, r.top, r.right, r.bottom)))
        return True
    user32.EnumDisplayMonitors(None, None, callback_type(callback), 0)
    return result


def browsers():
    result = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, data):
        title, cls = ctypes.create_unicode_buffer(1024), ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 1024)
        user32.GetClassNameW(hwnd, cls, 256)
        if user32.IsWindowVisible(hwnd) and title.value and cls.value in ('Chrome_WidgetWin_1', 'MozillaWindowClass') and is_browser(hwnd):
            result.append((hwnd, title.value))
        return True
    user32.EnumWindows(callback_type(callback), 0)
    return result


class Automation:
    def __init__(self):
        self.process = subprocess.Popen(
            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(BASE / 'automation.ps1')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        self.responses = queue.Queue()
        threading.Thread(target=self.read, daemon=True).start()

    def read(self):
        for line in self.process.stdout:
            self.responses.put(line)

    def call(self, action, **kwargs):
        self.process.stdin.write(json.dumps(dict(action=action, **kwargs)) + '\n')
        self.process.stdin.flush()
        try:
            data = json.loads(self.responses.get(timeout=20))
        except queue.Empty:
            self.process.kill()
            raise RuntimeError('The browser did not respond within 20 seconds.')
        if not data['ok']:
            raise RuntimeError(data['error'])
        return data

    def close(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.process.stdin.close()
        self.process.stdout.close()



CLOCK_LABEL = 'The Windows date and clock are visible.'
LIVE_COMPANION = True
def monitor_for_window(hwnd): return user32.MonitorFromWindow(hwnd, 2)
def foreground_window(): return user32.GetForegroundWindow()
def escape_pressed(): return bool(user32.GetAsyncKeyState(0x1B) & 0x8000)
def activate(hwnd):
    user32.ShowWindow(hwnd, 3)
    user32.SetForegroundWindow(hwnd)
def window_title(hwnd):
    title = ctypes.create_unicode_buffer(1024)
    user32.GetWindowTextW(hwnd, title, 1024)
    return title.value
def native_handle(root): return user32.GetAncestor(root.winfo_id(), 2)
def position_window(root, x, y, w, h):
    user32.SetWindowPos(native_handle(root), None, x, y, w, h, 0x0014)
def grab(bbox): return ImageGrab.grab(bbox=bbox, all_screens=True)
def open_file(path): os.startfile(str(path))
def log_directory(): return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ScreenRecord' / 'logs'

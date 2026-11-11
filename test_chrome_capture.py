"""Manual integration check: opens an isolated Chrome window on local test pages."""
import ctypes
import json
from pathlib import Path
import queue
import subprocess
import time
import uuid
import sys
import tkinter as tk
from unittest.mock import patch

from app import App, Automation, browsers, monitors
from platform_windows import user32


def run_case(height):
    workspace = Path(__file__).resolve().parent / '.browser-test' / uuid.uuid4().hex
    workspace.mkdir(parents=True)
    title = f'ScreenRecord integration {height} {uuid.uuid4().hex[:8]}'
    page = workspace / 'page.html'
    page.write_text(f'''<!doctype html><title>{title}</title>
<style>body {{margin:0;background:#f3f5f8;font:28px Arial}} section {{height:{height}px;background:linear-gradient(#dcecff,#ffe5d3);padding:24px;box-sizing:border-box}} h1{{margin:0}}</style>
<section><h1>Screen Record capture test</h1><p>Local fixture, height {height}px.</p></section><footer>END OF TEST PAGE</footer>''')
    short = workspace / 'short.html'
    short.write_text(f'<!doctype html><title>{title} short</title><h1>Short second tab</h1>')
    previous = user32.GetForegroundWindow()
    chrome = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    process = subprocess.Popen([str(chrome), '--user-data-dir=' + str(workspace / 'profile'), '--no-first-run',
                                '--no-default-browser-check', '--new-window', page.as_uri(), short.as_uri()],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    window = None
    root = None
    try:
        for _ in range(100):
            window = next((w for w in browsers() if title in w[1]), None)
            if window: break
            time.sleep(0.1)
        if not window: raise AssertionError('Test Chrome window did not open')
        time.sleep(1)
        monitor = user32.MonitorFromWindow(window[0], 2)
        bbox = next(rect for handle, rect in monitors() if handle == monitor)
        if '--ui' in sys.argv:
            root = tk.Tk()
            app = App(root)
            root.update()
        else:
            app = App.__new__(App)
            app.events = queue.Queue()
        bridge = Automation()
        try:
            original_url = bridge.call('url', hwnd=window[0])['url']
        finally:
            bridge.close()
        with patch('app.save_log') as logger:
            if root:
                app.browser.current(next(i for i, item in enumerate(app.windows) if item[0] == window[0]))
                app.follow_browser_display()
                app.output.set(str(workspace / 'captures'))
                app.delay.set(0.5)
                app.start()
                deadline = time.monotonic() + 120
                while app.busy and time.monotonic() < deadline:
                    root.update()
                    time.sleep(0.05)
                assert not app.busy, 'Live UI did not finish'
            else:
                app.capture(bbox, window, str(workspace / 'captures'), 15, 0.5)
            batch = logger.call_args.args[0]
        progress = []
        if root:
            message, folder = app.status.get(), app.last_folder
        else:
            event = app.events.get(timeout=1)
            while event['kind'] != 'complete':
                progress.append(event)
                event = app.events.get(timeout=1)
            message, folder = event['message'], event['folder']
        if not folder: raise AssertionError(message)
        print(json.dumps({'status': batch['status'], 'tabs': [dict(status=r['status'], images=len(r['images']), url=r.get('url'), error=r.get('error')) for r in batch['tabs']]}))
        assert batch['status'] == 'complete', message
        assert len(batch['tabs']) == 2
        if root:
            assert len(app.collection.rows) == 2
            assert app.collection.count == sum(len(r['images']) for r in batch['tabs'])
        else:
            assert sum(e['kind'] == 'folder' for e in progress) == 2
            assert sum(e['kind'] == 'image' for e in progress) == sum(len(r['images']) for r in batch['tabs'])
        assert all(Path(e['path']).exists() for e in progress if e['kind'] == 'image')
        reports = sorted(batch['tabs'], key=lambda r: len(r['images']), reverse=True)
        assert len(reports[0]['images']) >= 3
        assert reports[0]['images'][0]['scroll_percent'] <= 0.1
        assert reports[0]['images'][-1]['scroll_percent'] >= 99.99
        assert len(reports[1]['images']) == 1
        assert len(list(Path(folder).iterdir())) == 2
        assert all(p.suffix == '.png' for p in Path(folder).rglob('*') if p.is_file())
        bridge = Automation()
        try:
            assert bridge.call('url', hwnd=window[0])['url'] == original_url
        finally:
            bridge.close()
    finally:
        if root:
            from test_app import close_root
            close_root(root)
        if window:
            user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
            user32.PostMessageW(window[0], 0x0010, 0, 0)
        user32.SetForegroundWindow(previous)
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: pass


if __name__ == '__main__':
    run_case(4000)

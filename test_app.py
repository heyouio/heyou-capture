import tempfile
import sys
import unittest
from unittest.mock import patch
import tkinter as tk
import subprocess
import time
import queue
import threading
from pathlib import Path
from app import App, Automation, BASE, next_percent, session_folder, save_log


def close_root(root):
    for job in root.tk.splitlist(root.tk.call('after', 'info')):
        root.tk.call('after', 'cancel', job)
    root.destroy()


class CaptureTests(unittest.TestCase):
    def test_savings_estimate_is_explicit_and_never_negative(self):
        from live import estimated_savings
        self.assertEqual(estimated_savings(8, 2, 20), 250)
        self.assertEqual(estimated_savings(1, 1, 100), 0)

    def test_progress_window_is_hidden_if_it_moves_into_capture(self):
        app = App.__new__(App)
        app.events = queue.Queue()
        app.live_visible = True
        app._app_bounds = (0, 0, 800, 700)
        worker = threading.Thread(target=app.ensure_capture_clear, args=((0, 0, 1920, 1080),))
        worker.start()
        event = app.events.get(timeout=1)
        self.assertEqual(event['kind'], 'hide')
        event['ready'].set()
        worker.join(timeout=1)
        self.assertFalse(worker.is_alive())
    def test_logs_are_outside_shareable_capture_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            exports = Path(directory) / 'exports'
            tab_folder = session_folder(exports, 'https://example.com')
            with patch.dict('os.environ', {'LOCALAPPDATA': str(Path(directory) / 'local-app-data')}):
                path = save_log({'id': 'test-batch', 'folder': str(tab_folder), 'status': 'complete'})
            self.assertTrue(path.is_file())
            self.assertNotIn(exports, path.parents)
            self.assertEqual(list(tab_folder.iterdir()), [])

    def test_overlap_has_no_gaps(self):
        # 1000 px document, 200 px viewport: each advance is 170 px.
        position = 0.0
        offsets = [0.0]
        while position < 100:
            position = next_percent(position, 20, 15)
            offsets.append(position / 100 * 800)
        self.assertEqual(offsets[-1], 800)
        self.assertTrue(all(0 < b - a <= 170.00001 for a, b in zip(offsets, offsets[1:])))

    def test_invalid_view_is_not_success(self):
        for view in (0, 100, -1):
            with self.assertRaises(ValueError):
                next_percent(0, view, 15)

    def test_sessions_never_overwrite_or_escape_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            a = session_folder(directory, '../../bad:page?')
            b = session_folder(directory, '../../bad:page?')
            self.assertNotEqual(a, b)
            self.assertEqual(a.parent, Path(directory))
            self.assertNotIn(':', a.name)

    def test_url_folder_uses_host_and_path_without_windows_restricted_chars(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = session_folder(directory, 'https://example.com/a/b?q="test"&x=1#part')
            self.assertTrue(folder.name.startswith('example.com_a_b_q='))
            self.assertFalse(any(c in folder.name for c in '<>:"/\\|?*'))

    def test_buttons_remain_visible_at_large_display_scaling(self):
        for scaling in (1, 1.5, 2, 3):
            root = tk.Tk()
            try:
                root.tk.call('tk', 'scaling', scaling)
                with patch('app.monitors', return_value=[(1, (0, 0, 1920, 1080))]), patch('app.browsers', return_value=[]):
                    app = App(root)
                    root.geometry('740x640')
                    root.update()
                    for button in (app.capture_button, app.open_button):
                        self.assertGreaterEqual(button.winfo_height(), button.winfo_reqheight())
                        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), root.winfo_rooty() + root.winfo_height())
            finally:
                close_root(root)

    def test_refresh_preserves_selection_and_confirmation(self):
        root = tk.Tk()
        try:
            with patch('app.monitors', return_value=[(1, (0, 0, 100, 100)), (2, (100, 0, 200, 100))]), patch('app.browsers', return_value=[(10, 'A'), (20, 'B')]):
                app = App(root)
                app.screen.current(1)
                app.browser.current(2)
                app.clock_ok.set(True)
                app.refresh()
                self.assertEqual(app.screen.current(), 1)
                self.assertEqual(app.browser.current(), 2)
                self.assertTrue(app.clock_ok.get())
                self.assertIsNotNone(app.preview_job)
                with patch('app.browsers', return_value=[(20, 'B'), (10, 'A')]):
                    app.refresh()
                    self.assertEqual(app.browser.current(), 1)
                    self.assertTrue(app.clock_ok.get())
        finally:
            close_root(root)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows UI Automation fixture')
    def test_reads_native_address_bar_instead_of_search_field(self):
        fixture = subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(BASE / 'test_url_fixture.ps1')],
                                   stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        automation = Automation()
        try:
            hwnd = int(fixture.stdout.readline().strip())
            self.assertEqual(automation.call('url', hwnd=hwnd)['url'], 'https://example.com/a/b?q=hello&x=1')
            attached = automation.call('attach', hwnd=hwnd)
            self.assertTrue(attached['scrollable'])
            self.assertGreater(attached['view'], 0)
            automation.call('scroll', percent=50)
            time.sleep(0.25)
            self.assertAlmostEqual(automation.call('status')['percent'], 50, delta=1)
            automation.call('scroll', percent=0)
            time.sleep(0.25)
            self.assertAlmostEqual(automation.call('status')['percent'], 0, delta=1)
        finally:
            automation.close()
            fixture.terminate()
            fixture.wait(timeout=5)
            fixture.stdout.close()

    def test_browser_selection_automatically_uses_page_capture(self):
        root = tk.Tk()
        try:
            with patch('app.monitors', return_value=[(1, (0, 0, 100, 100)), (2, (100, 0, 200, 100))]), patch('app.browsers', return_value=[(10, 'Test browser')]), patch('ui.ctk.ScalingTracker.get_window_dpi_scaling', return_value=1), patch('app.desktop.monitor_for_window', return_value=2), patch('app.threading.Thread') as worker:
                app = App(root)
                app.browser.current(1)
                app.follow_browser_display()
                self.assertEqual(app.screen.current(), 1)
                self.assertFalse(hasattr(app, 'mode'))
                app.clock_ok.set(True)
                app.start()
                self.assertEqual(worker.call_args.kwargs['args'][1], (10, 'Test browser'))
                worker.return_value.start.assert_called_once()
        finally:
            close_root(root)


if __name__ == '__main__':
    unittest.main()

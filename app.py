"""Heyou Capture: local screenshots with the real system clock."""
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox
import ui

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
from desktop import backend as desktop
monitors = desktop.monitors
browsers = desktop.browsers
taskbar_visible = desktop.taskbar_visible
Automation = desktop.Automation


def next_percent(percent, view, overlap):
    if view <= 0 or view >= 100:
        raise ValueError('The scrolling area changed or no longer supports scrolling.')
    return min(100.0, percent + (100.0 - overlap) * view / (100.0 - view))


def session_folder(parent, title):
    title = re.sub(r'^https?://', '', title, flags=re.IGNORECASE)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).strip(' .')[:90].rstrip(' .') or 'Capture'
    if name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        name = '_' + name
    folder = Path(parent) / (name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_' + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def save_log(report):
    """Diagnostics live outside the shareable capture tree."""
    directory = desktop.log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (report['id'] + '.json')
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return path


class CaptureInterrupted(RuntimeError):
    pass


class App:
    def __init__(self, root):
        self.root = root
        self.root.title('Screen Record — Screenshot capture')
        self.root.geometry('860x720')
        self.root.minsize(740, 640)
        self.events = queue.Queue()
        self.busy = False
        self.output = tk.StringVar(value=str(Path.home() / 'Pictures' / 'Screen Record'))
        self.clock_ok = tk.BooleanVar(value=True)
        self.overlap = tk.IntVar(value=15)
        self.delay = tk.DoubleVar(value=1.5)
        self.manual_seconds = tk.DoubleVar(value=30)
        self.live_visible = False
        self._app_bounds = None
        self.status = tk.StringVar(value='Ready when you are. Keep your browser visible during capture. Hold Esc to stop.')
        self.last_folder = None
        self.preview_job = None
        ui.build(self, BASE)
        self.root.bind('<FocusIn>', self.on_focus)
        self.root.bind('<Configure>', self.track_bounds, add='+')
        self.refresh()
        self.root.after(100, self.poll)
        self.root.after(2500, self.auto_refresh)

    def refresh(self):
        if self.busy: return
        old_displays, old_windows = getattr(self, 'displays', []), getattr(self, 'windows', [])
        selected_display = old_displays[self.screen.current()] if self.screen.current() >= 0 else None
        selected_window = old_windows[self.browser.current()] if self.browser.current() >= 0 else None
        self.displays = monitors()
        try:
            self.windows = [(None, 'Entire selected display')] + browsers()
        except Exception as error:
            self.windows = [(None, 'Entire selected display')]
            self.status.set(str(error))
        for widget, old, new, selected, labels in (
            (self.screen, old_displays, self.displays, selected_display, [f'Display {i+1} — {r[2]-r[0]} × {r[3]-r[1]} ({r[0]}, {r[1]})' for i, (_, r) in enumerate(self.displays)]),
            (self.browser, old_windows, self.windows, selected_window, [title if hwnd is None else f'{title} · Window {i}' for i, (hwnd, title) in enumerate(self.windows)]),
        ):
            if old != new:
                widget['values'] = labels
                index = next((i for i, item in enumerate(new) if selected and item[0] == selected[0]), 0)
                if new: widget.current(index)
                else: widget.set('')
        self.schedule_preview()
        if hasattr(self, 'source_badge'):
            browser_selected = self.browser.current() > 0
            self.source_badge.configure(text='ALL TABS → ONE COLLECTION' if browser_selected else 'SCREEN → SNAP')

    def source_changed(self, event=None):
        if event is not None and event.widget == self.browser:
            self.follow_browser_display()
        self.refresh()

    def follow_browser_display(self):
        if self.browser.current() < 0: return
        hwnd = self.windows[self.browser.current()][0]
        if hwnd is None: return
        monitor = desktop.monitor_for_window(hwnd)
        for i, (handle, _) in enumerate(self.displays):
            if handle == monitor:
                self.screen.current(i)
                break

    def on_focus(self, event):
        if event.widget == self.root: self.refresh()

    def track_bounds(self, event):
        if event.widget == self.root:
            x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
            self._app_bounds = (x, y, x + self.root.winfo_width(), y + self.root.winfo_height())

    def ensure_capture_clear(self, bbox):
        bounds = getattr(self, '_app_bounds', None)
        if getattr(self, 'live_visible', False) and bounds and max(bounds[0], bbox[0]) < min(bounds[2], bbox[2]) and max(bounds[1], bbox[1]) < min(bounds[3], bbox[3]):
            ready = threading.Event()
            self.events.put(dict(kind='hide', ready=ready))
            if not ready.wait(5): raise RuntimeError('Could not hide the progress window before taking a screenshot.')
            time.sleep(0.2)

    def capture_focus_ok(self, hwnd, bbox):
        foreground = desktop.foreground_window()
        if foreground == hwnd: return True
        bounds = getattr(self, '_app_bounds', None)
        # The companion may receive focus on the other monitor without
        # covering the browser pixels or changing the selected tab.
        if getattr(self, 'live_visible', False) and foreground == getattr(self, 'live_hwnd', None) and bounds:
            return bounds[2] <= bbox[0] or bounds[0] >= bbox[2] or bounds[3] <= bbox[1] or bounds[1] >= bbox[3]
        return False

    def auto_refresh(self):
        if not self.busy: self.refresh()
        self.root.after(2500, self.auto_refresh)

    def schedule_preview(self):
        if self.preview_job: self.root.after_cancel(self.preview_job)
        self.preview_job = self.root.after(180, self.preview)

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.output.set(folder)

    def preview(self):
        self.preview_job = None
        if self.busy: return
        if self.screen.current() < 0:
            self.preview_label.configure(image='', text='No display available.')
            return
        try:
            image = desktop.grab(self.displays[self.screen.current()][1])
            ui.show_preview(self, image)
        except OSError as error:
            self.preview_label.configure(image='', text=f'Preview unavailable: {error}')

    def open_last(self):
        if self.last_folder:
            try: desktop.open_file(self.last_folder)
            except OSError as error: messagebox.showerror('Cannot open folder', str(error))

    def start(self):
        if self.busy: return
        try:
            if not self.clock_ok.get(): raise ValueError('In Capture settings, confirm that the Windows date and clock are visible before capturing.')
            if self.screen.current() < 0: raise ValueError('Choose a display.')
            overlap, delay = self.overlap.get(), self.delay.get()
            if not 5 <= overlap <= 40 or not 0.5 <= delay <= 10: raise ValueError('Use 5–40% overlap and a 0.5–10 second delay.')
            if not 1 <= self.manual_seconds.get() <= 600: raise ValueError('Use 1–600 seconds for the manual screenshot time estimate.')
            monitor, bbox = self.displays[self.screen.current()]
            window = None
            if self.browser.current() >= 0 and self.windows[self.browser.current()][0] is not None:
                window = self.windows[self.browser.current()]
                if desktop.monitor_for_window(window[0]) != monitor:
                    raise ValueError('Move the browser onto the selected display first, then refresh sources.')
            parent = self.output.get()
            if not parent.strip(): raise ValueError('Choose an output folder.')
        except Exception as error:
            messagebox.showerror('Check capture settings', str(error))
            return
        self.busy = True
        self.manual_baseline = self.manual_seconds.get()
        self.capture_button.state(['disabled'])
        self.original_geometry = self.root.geometry()
        self.collection.begin()
        self.settings_window.withdraw()
        self.root.withdraw()
        self.live_visible = False
        other = next((rect for handle, rect in self.displays if handle != monitor and rect[2]-rect[0] >= 800 and rect[3]-rect[1] >= 720), None)
        if other and desktop.LIVE_COMPANION:
            width, height = min(1180, other[2]-other[0]-40), min(920, other[3]-other[1]-80)
            self.root.geometry(f'{width}x{height}')
            self.root.deiconify()
            self.root.update_idletasks()
            self.live_hwnd = desktop.native_handle(self.root)
            # Tk negative offsets are relative to the right/bottom edge, not
            # absolute virtual-desktop coordinates. Use Win32 for left monitors.
            desktop.position_window(self.root, other[0]+20, other[1]+20, width, height)
            self.root.update()
            self.track_bounds(type('Event', (), {'widget': self.root})())
            self.live_visible = True
        threading.Thread(target=self.capture, args=(bbox, window, parent, overlap, delay), daemon=True).start()

    def capture(self, bbox, window, parent, overlap, delay):
        started = time.monotonic()
        batch = dict(id=uuid.uuid4().hex, started=datetime.now().astimezone().isoformat(), tabs=[], status='incomplete')
        batch['manual_seconds_per_screenshot'] = getattr(self, 'manual_baseline', 30)
        folder = None
        automation = None
        original = -1
        try:
            if not window:
                report = self.capture_page(bbox, None, parent, overlap, delay)
                batch['tabs'].append(report)
                folder = report.get('folder')
            else:
                desktop.activate(window[0])
                time.sleep(1)
                automation = Automation()
                snapshot = automation.call('tabs', hwnd=window[0])
                self.events.put(dict(kind='plan', total=len(snapshot['tabs'])))
                original = snapshot['original']
                # Selection also activates the chosen browser when Windows
                # declines the initial SetForegroundWindow request.
                automation.call('select_tab', index=original if original >= 0 else snapshot['tabs'][0]['index'])
                time.sleep(0.5)
                folder = str(session_folder(parent, 'Browser tabs'))
                for tab in snapshot['tabs']:
                    if desktop.escape_pressed():
                        raise RuntimeError('Stopped with Esc. Saved images are retained.')
                    if not self.capture_focus_ok(window[0], bbox):
                        raise RuntimeError('Capture stopped because the browser lost focus.')
                    automation.call('select_tab', index=tab['index'])
                    # Selecting a suspended tab can load its document asynchronously.
                    end = time.monotonic() + 15
                    while not automation.call('tab_selected', index=tab['index'])['selected']:
                        if time.monotonic() >= end: raise RuntimeError('The browser could not activate a tab.')
                        time.sleep(0.1)
                    time.sleep(max(delay, 1))
                    title = desktop.window_title(window[0])
                    report = self.capture_page(bbox, (window[0], title), folder, overlap, delay, (automation, tab['index']))
                    report['tab_index'] = tab['index']
                    batch['tabs'].append(report)
                    # Fail visibly instead of proceeding while the user is interacting.
                    if report.get('interrupted'): raise RuntimeError(report['error'])
            failed = sum(r['status'] != 'complete' for r in batch['tabs'])
            count = sum(len(r['images']) for r in batch['tabs'])
            batch['status'] = 'incomplete' if failed else 'complete'
            message = f'Saved {count} screenshot(s) across {len(batch["tabs"])} tab(s).' if window else f'Saved {count} screenshot(s).'
            if failed: message += f' {failed} capture(s) incomplete: ' + next(r['error'] for r in batch['tabs'] if r['status'] != 'complete')
        except Exception as error:
            batch['error'] = str(error)
            message = str(error)
        finally:
            if automation:
                try:
                    if original >= 0: automation.call('select_tab', index=original)
                except Exception as error: batch['restore_warning'] = str(error)
                try: automation.close()
                except Exception: pass
            batch['folder'] = folder
            batch['elapsed_seconds'] = round(time.monotonic() - started, 2)
            try: save_log(batch)
            except OSError as error: message += f' Diagnostic log could not be saved: {error}'
            self.events.put(dict(kind='complete', message=message, folder=folder, batch=batch))

    def capture_page(self, bbox, window, parent, overlap, delay, tab_guard=None):
        automation = None
        folder = None
        report = dict(started=datetime.now().astimezone().isoformat(), source=window[1] if window else 'Screen', overlap=overlap, images=[], status='incomplete')
        def check():
            if desktop.escape_pressed(): raise CaptureInterrupted('Stopped with Esc. Saved images are retained.')
            if window and not self.capture_focus_ok(window[0], bbox): raise CaptureInterrupted('Capture stopped because the browser lost focus. Saved images are retained.')
            if window:
                title = desktop.window_title(window[0])
                if tab_guard is None and title != window[1]: raise CaptureInterrupted('The active tab or page title changed. Capture stopped to avoid mixing pages.')
        def check_page():
            check()
            if tab_guard:
                bridge, tab_index = tab_guard
                if not bridge.call('tab_selected', index=tab_index)['selected']:
                    raise CaptureInterrupted('The active tab changed. Capture stopped to avoid mixing pages.')
                if automation.call('url', hwnd=window[0])['url'] != report['url']:
                    raise CaptureInterrupted('The page navigated to a different URL. Capture stopped to avoid mixing pages.')
        def wait(seconds):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                check()
                time.sleep(0.05)
        try:
            if window:
                desktop.activate(window[0])
            wait(1.0)
            if window:
                automation = Automation()
                url = automation.call('url', hwnd=window[0])['url']
                check()
                report['url'] = url
                folder = session_folder(parent, url)
                self.events.put(dict(kind='folder', path=str(folder), title=url))
                attach_deadline = time.monotonic() + 10
                while True:
                    check()
                    try:
                        automation.call('attach', hwnd=window[0])
                        break
                    except RuntimeError as error:
                        if 'does not expose readable scrolling controls' not in str(error) or time.monotonic() >= attach_deadline:
                            raise
                        wait(0.3)
                automation.call('scroll', percent=0)
            else:
                folder = session_folder(parent, 'Screen')
                self.events.put(dict(kind='folder', path=str(folder), title='Screen capture'))
            wait(delay)
            if automation:
                initial = automation.call('status')
                if initial['scrollable'] and initial['percent'] > 0.1:
                    raise RuntimeError('The page did not reach the top. Capture stopped to avoid missing content.')
            for index in range(1, 501):
                check_page()
                state = automation.call('status') if automation else None
                if not taskbar_visible(bbox):
                    raise RuntimeError('The system clock area is not visible at the bottom of this display. Disable auto-hide and show the date and clock before retrying.')
                captured = datetime.now().astimezone()
                self.ensure_capture_clear(bbox)
                image = desktop.grab(bbox)
                check_page()
                filename = f'{index:04d}_{captured.strftime("%Y-%m-%d_%H-%M-%S")}.png'
                image.save(folder / filename)
                report['images'].append(dict(file=filename, captured=captured.isoformat(), scroll_percent=state['percent'] if state else None))
                self.events.put(dict(kind='image', path=str(folder / filename), folder=str(folder)))
                if not automation: break
                if not state['scrollable']: break
                if state['percent'] >= 99.999:
                    wait(max(delay, 2))
                    settled = automation.call('status')
                    if settled['percent'] >= 99.999: break
                    state = settled
                target = next_percent(state['percent'], state['view'], overlap)
                automation.call('scroll', percent=target)
                wait(delay)
                after = automation.call('status')
                if after['percent'] <= state['percent'] + 0.00001:
                    raise RuntimeError('The page did not advance. Capture is incomplete; saved images are retained.')
            else:
                raise RuntimeError('Stopped at the 500-image safety limit. This may be an infinite-scroll page.')
            report['status'] = 'complete'
            message = f'Saved {len(report["images"])} screenshot(s) to {folder}'
        except Exception as error:
            report['error'] = str(error)
            report['interrupted'] = isinstance(error, CaptureInterrupted) or (window is not None and not self.capture_focus_ok(window[0], bbox))
            message = str(error)
        finally:
            if automation:
                try: automation.call('restore')
                except Exception as error: report['restore_warning'] = str(error)
                try: automation.close()
                except Exception as error: report['cleanup_warning'] = str(error)
            report['folder'] = str(folder) if folder else None
        return report

    def poll(self):
        try:
            event = self.events.get_nowait()
            kind = event['kind']
            if kind == 'hide':
                self.root.withdraw()
                self.live_visible = False
                event['ready'].set()
            elif kind == 'folder': self.collection.folder(event['path'], event['title'])
            elif kind == 'image': self.collection.image(event['path'], event['folder'])
            elif kind == 'plan': self.status.set(f'Capturing {event["total"]} tabs. Watch your collection grow. Hold Esc to stop.')
            elif kind == 'complete': self.finish_capture(event)
        except queue.Empty:
            pass
        self.root.after(50, self.poll)

    def finish_capture(self, event):
            message, folder = event['message'], event['folder']
            if folder:
                self.last_folder = folder
                self.open_button.state(['!disabled'])
            self.busy = False
            self.live_visible = False
            self.capture_button.state(['!disabled'])
            self.root.deiconify()
            if hasattr(self, 'original_geometry'): self.root.geometry(self.original_geometry)
            self.collection.finish(event['batch'])
            self.status.set(message)
            self.refresh()


if __name__ == '__main__':
    App(tk.Tk()).root.mainloop()

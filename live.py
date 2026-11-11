"""Live, file-backed collection UI. No screenshot copies or export metadata."""
import json
import os
import time
from pathlib import Path
import customtkinter as ctk
from PIL import Image
from ui import label
from desktop import backend as desktop


def history():
    directory = desktop.log_directory()
    result = []
    if directory.exists():
        for path in sorted(directory.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if data.get('folder') and Path(data['folder']).is_dir():
                    result.append(data)
            except (OSError, ValueError):
                continue
    return result


def estimated_savings(images, folders, elapsed, per_image=30):
    return max(0, images * per_image + folders * 15 - elapsed)


class Collection:
    def __init__(self, app, stage):
        self.app = app
        self.panel = ctk.CTkFrame(stage, fg_color='#F6EEFF', bg_color='#24103F', corner_radius=28)
        self.rows = {}
        self.count = 0
        self.elapsed = 0
        self.running = False
        self.history = history()
        self.previous_count = sum(len(tab.get('images', [])) for run in self.history for tab in run.get('tabs', []))
        top = ctk.CTkFrame(self.panel, fg_color='transparent')
        top.pack(fill='x', padx=22, pady=(14, 6))
        self.title = label(top, 'Your collection is about to grow.', 19, '#24103F', True)
        self.title.pack(side='left')
        self.lifetime = label(top, f'{self.previous_count:,} captured so far', 11, '#735C91')
        self.lifetime.pack(side='right')
        metrics = ctk.CTkFrame(self.panel, fg_color='white', corner_radius=16)
        metrics.pack(fill='x', padx=22, pady=(0, 8))
        self.stats = []
        for i, text in enumerate(('SCREENSHOTS', 'TAB FOLDERS', 'EST. TIME SAVED')):
            metrics.grid_columnconfigure(i, weight=1, uniform='stats')
            value = label(metrics, '0' if i < 2 else '0s', 27, '#874EF9' if i < 2 else '#D41D6C', True, anchor='center')
            value.grid(row=0, column=i, sticky='ew', padx=10, pady=(6, 0))
            label(metrics, text, 9, '#735C91', True, anchor='center').grid(row=1, column=i, pady=(0, 8))
            self.stats.append(value)
        self.feed = ctk.CTkScrollableFrame(self.panel, fg_color='transparent',
            scrollbar_button_color='#D4BDE8', scrollbar_button_hover_color='#BA99D6')
        self.feed.pack(fill='both', expand=True, padx=16, pady=(0, 3))
        self.footnote = label(self.panel, 'Estimate: 30s per screenshot + 15s per folder, minus capture time.', 10, '#7B668E')
        self.footnote.pack(anchor='w', padx=22, pady=(0, 10))

    def show(self):
        self.panel.place(x=0, y=0, relwidth=1, relheight=1)
        self.panel.lift()

    def hide(self):
        self.panel.place_forget()

    def begin(self):
        for row in self.rows.values(): row['frame'].destroy()
        self.rows.clear()
        self.count = 0
        self.started = time.monotonic()
        self.running = True
        self.title.configure(text='A little screenshot magic is happening…')
        self.show()
        self.tick()

    def tick(self):
        if not self.running: return
        self.elapsed = time.monotonic() - self.started
        self.update_stats()
        self.app.root.after(500, self.tick)

    def update_stats(self):
        saved = estimated_savings(self.count, len(self.rows), self.elapsed, self.app.manual_seconds.get())
        text = f'{saved / 60:.1f} min' if saved >= 60 else f'{int(saved)}s'
        for widget, value in zip(self.stats, (str(self.count), str(len(self.rows)), text)):
            widget.configure(text=value)
        self.lifetime.configure(text=f'{self.previous_count + self.count:,} captured so far')
        self.footnote.configure(text=f'Estimate: {self.app.manual_seconds.get():g}s / screenshot + 15s / folder − {int(self.elapsed)}s capture time.')

    def folder(self, path, title):
        if path in self.rows: return
        frame = ctk.CTkFrame(self.feed, fg_color='#E5D3FC', corner_radius=14)
        frame.pack(fill='x', pady=(0, 8))
        line = ctk.CTkFrame(frame, fg_color='transparent')
        line.pack(fill='x', padx=12, pady=(8, 4))
        label(line, '▰', 23, '#874EF9').pack(side='left', padx=(0, 8))
        title = title.removeprefix('https://').removeprefix('http://')
        ctk.CTkButton(line, text=title[:58] + ('…' if len(title) > 58 else ''), anchor='w',
            fg_color='transparent', hover_color='#F0E5FC', text_color='#24103F',
            font=('Segoe UI', 12, 'bold'), command=lambda p=path: self.open_file(p)).pack(side='left', fill='x', expand=True)
        count = label(line, 'New folder ✦', 11, '#874EF9', True)
        count.pack(side='right')
        strip = ctk.CTkFrame(frame, fg_color='transparent')
        strip.pack(fill='x', padx=12, pady=(0, 10))
        self.rows[path] = dict(frame=frame, count=count, strip=strip, images=[], widgets=[], total=0)
        for delay, color in ((120, '#EEDFFA'), (260, '#F5ECFD'), (400, '#FFFFFF')):
            self.app.root.after(delay, lambda f=frame, c=color: f.configure(fg_color=c) if f.winfo_exists() else None)
        self.update_stats()
        self.feed._parent_canvas.yview_moveto(1)

    def open_file(self, path):
        from tkinter import messagebox
        if self.app.busy: return
        try: desktop.open_file(path)
        except OSError as error: messagebox.showerror('File unavailable', str(error))

    def image(self, path, folder):
        row = self.rows.get(folder)
        if not row: return
        self.count += 1
        row['total'] += 1
        row['count'].configure(text=f'{row["total"]} saved ✓', text_color='#008E83')
        try:
            with Image.open(path) as source:
                thumb = source.copy()
            thumb.thumbnail((112, 60))
            picture = ctk.CTkImage(thumb, size=(max(1, thumb.width), max(1, thumb.height)))
            tile = ctk.CTkButton(row['strip'], text='', image=picture, width=120, height=68,
                corner_radius=8, fg_color='#EEE4FA', hover_color='#DBC4F3', command=lambda p=path: self.open_file(p))
            tile.pack(side='left', padx=(0, 6))
            row['images'].append(picture)
            row['widgets'].append(tile)
            if len(row['widgets']) > 5:
                row['widgets'].pop(0).destroy()
                row['images'].pop(0)
            for delay, color in ((100, '#E5D1FC'), (220, '#F3ECFA'), (360, '#F8F4FC')):
                self.app.root.after(delay, lambda w=tile, c=color: w.configure(fg_color=c) if w.winfo_exists() else None)
        except OSError:
            pass
        self.update_stats()
        self.feed._parent_canvas.yview_moveto(1)

    def finish(self, batch):
        self.running = False
        self.elapsed = batch.get('elapsed_seconds', self.elapsed)
        complete = batch['status'] == 'complete'
        self.title.configure(text='That’s a wrap. Nicely captured. ✦' if complete else 'Saved what we could. Check the details below.')
        self.update_stats()
        self.previous_count += self.count
        self.history = history()
        self.show()
        self.feed._parent_canvas.yview_moveto(0)

    def show_history(self):
        win = ctk.CTkToplevel(self.app.root)
        win.title('Your capture collection')
        win.geometry('680x520')
        win.configure(fg_color='#24103F')
        label(win, 'Look at that collection grow.', 25, '#FFF9F4', True).pack(anchor='w', padx=24, pady=20)
        feed = ctk.CTkScrollableFrame(win, fg_color='#24103F')
        feed.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        runs = history()
        if not runs: label(feed, 'Your first capture is the start of something good.', 14, '#C9B5DE').pack(pady=30)
        for run in runs[:60]:
            count = sum(len(tab.get('images', [])) for tab in run.get('tabs', []))
            title = f'{run.get("started", "")[:16].replace("T", "  ")}    •    {count} images    •    {run["status"]}'
            ctk.CTkButton(feed, text=title, height=54, anchor='w', corner_radius=14,
                fg_color='#392151', hover_color='#4B2D69', text_color='white',
                command=lambda p=run['folder']: self.open_file(p)).pack(fill='x', pady=(0, 8))

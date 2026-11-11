"""A preview-first capture playground, with a floating control dock."""
from pathlib import Path
from types import SimpleNamespace
import math
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from ui import SourceMenu, ActionButton, label
from desktop import backend as desktop

NIGHT = '#24103F'
PINK = '#FF388C'
CREAM = '#FFF9F4'
PURPLE = '#874EF9'


def build(app, base):
    ctk.set_appearance_mode('light')
    root = app.root
    root.configure(bg=NIGHT)
    root.title('Heyou Capture • Screenshot magic')
    root.geometry('1180x920')
    root.minsize(740, 640)
    assets = Path(base) / 'assets'
    app.logo = ctk.CTkImage(Image.open(assets / 'heyou-logo.png'), size=(104, 46))
    try: root.iconbitmap(str(assets / 'heyou.ico'))
    except Exception: pass

    # Floating dock remains visible regardless of preview height or DPI.
    dock = ctk.CTkFrame(root, fg_color=CREAM, corner_radius=26)
    dock.pack(side='bottom', fill='x', padx=28, pady=(8, 20))
    sources = ctk.CTkFrame(dock, fg_color='transparent')
    sources.pack(fill='x', padx=22, pady=(16, 10))
    sources.grid_columnconfigure(0, weight=3, uniform='sources')
    sources.grid_columnconfigure(1, weight=2, uniform='sources')
    label(sources, 'WHAT ARE WE CAPTURING?', 10, '#735C91', True).grid(row=0, column=0, sticky='w', pady=(0, 4))
    label(sources, 'ON THIS DISPLAY', 10, '#735C91', True).grid(row=0, column=1, sticky='w', padx=(14, 0), pady=(0, 4))
    app.browser = SourceMenu(sources, command=lambda value: app.source_changed(SimpleNamespace(widget=app.browser)))
    app.browser.grid(row=1, column=0, sticky='ew')
    app.screen = SourceMenu(sources, command=lambda value: app.source_changed(SimpleNamespace(widget=app.screen)))
    app.screen.grid(row=1, column=1, sticky='ew', padx=(14, 0))
    for menu in (app.browser, app.screen):
        menu.configure(fg_color='#F2EAF7', border_width=0, button_color='#F2EAF7', corner_radius=14)
    actions = ctk.CTkFrame(dock, fg_color='transparent')
    actions.pack(fill='x', padx=22, pady=(0, 4))
    app.capture_button = ActionButton(actions, text='✦  Capture the magic', command=app.start,
        width=218, height=52, corner_radius=26, fg_color=PINK, hover_color='#E72378',
        font=('Segoe UI', 16, 'bold'), text_color='white')
    app.capture_button.pack(side='right', padx=(12, 0))
    app.open_button = ActionButton(actions, text='Open export  ↗', command=app.open_last,
        width=145, height=44, corner_radius=22, fg_color='#EDE1F6', hover_color='#DFC9F0',
        text_color=NIGHT, text_color_disabled='#AB99BD', state='disabled', font=('Segoe UI', 13, 'bold'))
    app.open_button.pack(side='right')
    app.destination = ctk.CTkButton(actions, text='↗  Save to Screen Record', command=app.choose_folder,
        fg_color='transparent', hover_color='#F0E6F5', text_color=NIGHT, anchor='w',
        height=38, corner_radius=12, font=('Segoe UI', 12))
    app.destination.pack(side='left', fill='x', expand=True, padx=(0, 12))
    def update_destination(*args):
        name = Path(app.output.get()).name or 'Choose folder'
        app.destination.configure(text='↗  Save to ' + (name[:30] + '…' if len(name) > 30 else name))
    app.output.trace_add('write', update_destination)
    app.status_label = label(dock, size=11, color='#7B668E', textvariable=app.status, wraplength=1050)
    app.status_label.pack(fill='x', padx=26, pady=(0, 14))

    header = ctk.CTkFrame(root, fg_color='transparent', height=76)
    header.pack(side='top', fill='x', padx=28, pady=(16, 0))
    header.pack_propagate(False)
    logo_pill = ctk.CTkFrame(header, fg_color='white', corner_radius=20, width=136, height=58)
    logo_pill.pack(side='left')
    logo_pill.pack_propagate(False)
    ctk.CTkLabel(logo_pill, image=app.logo, text='').pack(expand=True)
    label(header, 'capture', 21, '#E4D4F3', True).pack(side='left', padx=18)
    settings_button = ctk.CTkButton(header, text='⚙  Capture settings', width=158, height=38,
        fg_color='#392151', hover_color='#4A2B68', corner_radius=19, text_color='#F3E9FF', font=('Segoe UI', 12))
    settings_button.pack(side='right')
    label(header, '●  YOUR DEVICE. YOUR FILES.', 10, '#6CE3CD', True).pack(side='right', padx=24)

    body = ctk.CTkScrollableFrame(root, fg_color=NIGHT, corner_radius=0,
        scrollbar_button_color='#452962', scrollbar_button_hover_color='#694388')
    body.pack(fill='both', expand=True)
    main = ctk.CTkFrame(body, fg_color='transparent', width=1100, height=570)
    main.pack(pady=(8, 12))
    main.pack_propagate(False)
    hero = ctk.CTkFrame(main, fg_color='transparent', height=132)
    hero.pack(fill='x')
    hero.pack_propagate(False)
    label(hero, 'LESS CLICK-CLICK. MORE TA-DA.', 11, '#FFA8D0', True).pack(anchor='w')
    title = label(hero, 'Catch the whole thing.', 47, CREAM, True)
    title.pack(anchor='w', pady=(0, 0))
    label(hero, 'All your tabs. Every last scroll. One happy little folder.', 15, '#C9B5DE').pack(anchor='w')
    # Decorative orbit and stars are vector UI, not screenshots or controls.
    doodle = tk.Canvas(hero, width=185, height=118, bg=NIGHT, highlightthickness=0)
    doodle.place(relx=1, x=-2, y=0, anchor='ne')
    doodle.create_oval(18, 26, 164, 98, outline='#874EF9', width=2)
    doodle.create_oval(48, 4, 128, 116, outline='#66418C', width=2)
    doodle.create_text(91, 60, text='✦', font=('Segoe UI', 55), fill='#FF8DBF')
    doodle.create_text(156, 20, text='+', font=('Segoe UI', 24), fill='#6CE3CD')
    doodle.create_oval(12, 70, 24, 82, fill='#FF388C', outline='')

    stage = ctk.CTkFrame(main, fg_color='#D9C7FA', corner_radius=28, height=420)
    stage.pack(fill='x', pady=(6, 0))
    stage.pack_propagate(False)
    art = tk.Canvas(stage, bg='#D9C7FA', highlightthickness=0)
    art.place(relx=.5, rely=.5, anchor='center', relwidth=.94, relheight=.94)
    def paint(event):
        art.delete('all')
        w, h = event.width, event.height
        for x in range(12, w, 24):
            for y in range(12, h, 24):
                art.create_oval(x, y, x+2, y+2, fill='#BFA7E5', outline='')
        art.create_polygon(w*.14, h*.15, w*.84, h*.08, w*.89, h*.91, w*.18, h*.96, fill='#B397DD', outline='')
        art.create_polygon(w*.18, h*.06, w*.89, h*.17, w*.84, h*.95, w*.13, h*.84, fill='#CBB5EF', outline='')
        art.create_text(w*.05, h*.26, text='✦', font=('Segoe UI', 28), fill='#874EF9')
        art.create_text(w*.95, h*.68, text='✧', font=('Segoe UI', 38), fill='#874EF9')
    art.bind('<Configure>', paint)
    app.preview_box = ctk.CTkFrame(stage, fg_color='white', corner_radius=12)
    app.preview_box.place(relx=.5, rely=.51, anchor='center', relwidth=.76, relheight=.83)
    browser_bar = ctk.CTkFrame(app.preview_box, fg_color='#FFF9F4', height=28, corner_radius=8)
    browser_bar.pack(fill='x', padx=5, pady=(4, 0))
    browser_bar.pack_propagate(False)
    label(browser_bar, '●  ●  ●', 10, '#C8ACDD').pack(side='left', padx=10)
    label(browser_bar, 'a little preview of the big picture', 10, '#8C789F').pack(side='left', padx=8)
    app.preview_label = ctk.CTkLabel(app.preview_box, text='Your screen is getting its close-up…',
        text_color='#7B668E', font=('Segoe UI', 14), fg_color='white')
    app.preview_label.pack(fill='both', expand=True, padx=8, pady=(0, 8))
    app.preview_box.bind('<Configure>', lambda e: app.schedule_preview(), add='+')
    label(stage, '●  LIVE', 11, NIGHT, True, fg_color='#6CE3CD', corner_radius=14,
          width=76, height=30, anchor='center').place(relx=.92, y=20, anchor='ne')
    app.source_badge = label(stage, 'SCREEN → SNAP', 11, 'white', True, fg_color=PURPLE,
          corner_radius=16, height=34, padx=14)
    app.source_badge.place(x=24, rely=1, y=-20, anchor='sw')
    label(stage, 'PNG. ZIP. SEND.  ↗', 11, NIGHT, True, fg_color='#FFACD2', corner_radius=16,
          height=34, padx=14).place(relx=1, x=-24, rely=1, y=-20, anchor='se')
    from live import Collection
    app.collection = Collection(app, stage)
    nav = ctk.CTkFrame(hero, fg_color='transparent')
    nav.place(relx=1, rely=1, y=-4, anchor='se')
    ctk.CTkButton(nav, text='Preview', width=72, height=26, corner_radius=13, fg_color='#392151',
        hover_color='#4B2D69', command=app.collection.hide, font=('Segoe UI', 11)).pack(side='left', padx=4)
    ctk.CTkButton(nav, text='Live collection', width=105, height=26, corner_radius=13, fg_color='#874EF9',
        hover_color='#7139DC', command=app.collection.show, font=('Segoe UI', 11)).pack(side='left', padx=4)
    ctk.CTkButton(nav, text='History ↗', width=80, height=26, corner_radius=13, fg_color='#392151',
        hover_color='#4B2D69', command=app.collection.show_history, font=('Segoe UI', 11)).pack(side='left', padx=4)

    # Settings are an actual separate drawer window, not another form on the home screen.
    app.settings_window = ctk.CTkToplevel(root)
    app.settings_window.withdraw()
    app.settings_window.title('Capture settings')
    app.settings_window.geometry('580x500')
    app.settings_window.resizable(False, False)
    app.settings_window.configure(fg_color=CREAM)
    app.settings_window.protocol('WM_DELETE_WINDOW', app.settings_window.withdraw)
    app.settings_body = ctk.CTkFrame(app.settings_window, fg_color=CREAM)
    app.settings_body.pack(fill='both', expand=True, padx=24, pady=20)
    label(app.settings_body, 'Make it yours.', 27, NIGHT, True).pack(anchor='w')
    label(app.settings_body, 'The little details behind a great capture.', 13, '#7B668E').pack(anchor='w', pady=(0, 18))
    label(app.settings_body, 'Save screenshots to', 12, NIGHT, True).pack(anchor='w')
    ctk.CTkEntry(app.settings_body, textvariable=app.output, height=40, fg_color='white',
        border_color='#DDCFE8', text_color=NIGHT).pack(fill='x', pady=(4, 14))
    controls = ctk.CTkFrame(app.settings_body, fg_color='transparent')
    controls.pack(fill='x', pady=(0, 18))
    label(controls, 'Overlap %', 12, NIGHT).grid(row=0, column=0, sticky='w')
    ctk.CTkEntry(controls, textvariable=app.overlap, width=70, height=36,
        fg_color='white', border_color='#DDCFE8', text_color=NIGHT).grid(row=1, column=0, sticky='w')
    label(controls, 'Wait after scrolling (seconds)', 12, NIGHT).grid(row=0, column=1, sticky='w', padx=(30, 0))
    ctk.CTkEntry(controls, textvariable=app.delay, width=70, height=36,
        fg_color='white', border_color='#DDCFE8', text_color=NIGHT).grid(row=1, column=1, sticky='w', padx=(30, 0))
    app.clock_check = ctk.CTkCheckBox(app.settings_body, text=desktop.CLOCK_LABEL,
        variable=app.clock_ok, text_color=NIGHT, font=('Segoe UI', 12), fg_color=PURPLE,
        hover_color='#7139DC', border_color='#BDA6CF', checkbox_width=20, checkbox_height=20)
    app.clock_check.pack(anchor='w', pady=(0, 8))
    label(app.settings_body, 'Keep the system date and clock visible during capture.', 11, '#7B668E').pack(anchor='w')
    estimate = ctk.CTkFrame(app.settings_body, fg_color='transparent')
    estimate.pack(fill='x', pady=(12, 0))
    label(estimate, 'Manual time per screenshot (for savings estimate)', 12, NIGHT).pack(side='left')
    ctk.CTkEntry(estimate, textvariable=app.manual_seconds, width=60, height=32,
        fg_color='white', border_color='#DDCFE8', text_color=NIGHT).pack(side='right')
    ctk.CTkButton(app.settings_body, text='All set  ✓', command=app.settings_window.withdraw,
        fg_color=NIGHT, hover_color='#452962', corner_radius=20, height=40).pack(anchor='e', pady=(14, 0))
    def show_settings():
        app.settings_window.deiconify()
        app.settings_window.lift()
        app.settings_window.focus_set()
    settings_button.configure(command=show_settings)
    app._wide_layout = None
    def resize(event):
        if event.widget != root: return
        scale = stage._get_widget_scaling()
        width = max(640, min(1220, root.winfo_width()/scale - 64))
        main.configure(width=width)
        compact = width < 850
        title.configure(font=('Segoe UI', 34 if compact else 47, 'bold'))
        if compact: doodle.place_forget()
        else: doodle.place(relx=1, x=-2, y=0, anchor='ne')
        app.status_label.configure(wraplength=max(300, root.winfo_width()/scale - 110))
    root.bind('<Configure>', resize, add='+')

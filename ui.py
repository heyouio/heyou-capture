"""Heyou desktop presentation. Capture behavior lives in app.py."""
from pathlib import Path
from types import SimpleNamespace
import customtkinter as ctk
from PIL import Image

BG = '#F5F5F7'
WHITE = '#FFFFFF'
INK = '#2E1258'
PURPLE = '#874EF9'
PINK = '#FF388C'
MUTED = '#737380'
LINE = '#E9E5F0'
LILAC = '#F1EBFF'


class SourceMenu(ctk.CTkComboBox):
    """Keep source identity/index semantics used by the capture controller."""
    def __init__(self, master, **kwargs):
        super().__init__(master, values=[], state='readonly', height=44,
                         fg_color=BG, border_color=LINE, border_width=1,
                         button_color=LILAC, button_hover_color='#E3D7FF',
                         text_color=INK, dropdown_fg_color=WHITE,
                         dropdown_hover_color=LILAC, dropdown_text_color=INK,
                         font=('Segoe UI', 13), dropdown_font=('Segoe UI', 13),
                         corner_radius=10, **kwargs)
        self._selected_index = -1
        self.set('')

    def _create_bindings(self, sequence=None):
        super()._create_bindings(sequence)
        # Use one handler per surface, rather than both arrow-tag and canvas
        # handlers (which would open and immediately close the list).
        for tag in ('right_parts', 'dropdown_arrow'):
            self._canvas.tag_unbind(tag, '<Button-1>')
        self._canvas.bind('<Button-1>', self._surface_clicked)
        self._entry.bind('<Button-1>', self._surface_clicked)
        self._entry.configure(cursor='hand2')
        self._canvas.configure(cursor='hand2')

    def _surface_clicked(self, event):
        self._clicked(event)
        return 'break'

    def current(self, index=None):
        values = self.cget('values')
        if index is not None:
            self._selected_index = index
            super().set(values[index])
        return self._selected_index

    def set(self, value):
        values = self.cget('values')
        self._selected_index = values.index(value) if value in values else -1
        super().set(value)

    def _dropdown_callback(self, value):
        self._selected_index = self.cget('values').index(value)
        super()._dropdown_callback(value)

    def __setitem__(self, key, value):
        self.configure(**{key: value})


class ActionButton(ctk.CTkButton):
    def state(self, states):
        self.configure(state='disabled' if 'disabled' in states else 'normal')


def label(master, text='', size=13, color=INK, bold=False, **kwargs):
    return ctk.CTkLabel(master, text=text, text_color=color, anchor=kwargs.pop('anchor', 'w'),
                        font=('Segoe UI', size, 'bold' if bold else 'normal'), **kwargs)


def card(master):
    return ctk.CTkFrame(master, fg_color=WHITE, corner_radius=20, border_width=1, border_color=LINE)


def heading(master, number, title):
    row = ctk.CTkFrame(master, fg_color='transparent')
    row.pack(fill='x', padx=24, pady=(22, 12))
    label(row, number, 12, PURPLE, True, width=30, height=28,
          fg_color=LILAC, corner_radius=8, anchor='center').pack(side='left', padx=(0, 10))
    label(row, title, 17, bold=True).pack(side='left')


def build(app, base):
    from playground import build as create
    create(app, base)


def show_preview(app, image):
    scale = app.preview_label._get_widget_scaling()
    width = max(100, app.preview_label.winfo_width() - 8)
    height = max(80, app.preview_label.winfo_height() - 8)
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    app.preview_image = ctk.CTkImage(image, size=(max(1, int(image.width / scale)), max(1, int(image.height / scale))))
    app.preview_label.configure(image=app.preview_image, text='')

import tkinter as tk
from tkinter import Frame, Label

from src.ui.theme import COLORS, FONT_SMALL


def make_panel(parent, bg=COLORS["surface"], border=COLORS["line"]):
    return Frame(parent, bg=bg, highlightbackground=border, highlightthickness=1)


def make_button(parent, text, command, variant="primary"):
    styles = {
        "primary": (COLORS["accent"], "#16a085", "#061412"),
        "secondary": (COLORS["accent_2"], "#d99a24", "#171008"),
        "ghost": (COLORS["surface_2"], "#1f3350", COLORS["muted"]),
        "danger": (COLORS["danger"], "#b91c1c", COLORS["white"]),
    }
    bg, active_bg, fg = styles[variant]
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        activebackground=active_bg,
        fg=fg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        cursor="hand2",
        font=("Segoe UI", 11, "bold"),
        padx=18,
        pady=12,
    )


def labelled_value(parent, label_text, value_text, accent=COLORS["accent_2"]):
    row = Frame(parent, bg=parent["bg"])
    row.pack(fill="x", pady=6)
    Label(row, text=label_text.upper(), font=FONT_SMALL, fg=COLORS["muted"], bg=parent["bg"]).pack(anchor="w")
    value = Label(row, text=value_text, font=("Segoe UI", 14, "bold"), fg=accent, bg=parent["bg"])
    value.pack(anchor="w", pady=(2, 0))
    return value


def make_switch(parent, text, variable, command):
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        command=command,
        onvalue=True,
        offvalue=False,
        selectcolor=COLORS["surface_3"],
        activebackground=COLORS["surface"],
        activeforeground=COLORS["text"],
        bg=COLORS["surface"],
        fg=COLORS["text"],
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        cursor="hand2",
        anchor="w",
    )


def make_stat_chip(parent, label_text, value_text):
    chip = Frame(parent, bg=COLORS["surface_2"], highlightbackground=COLORS["surface_3"], highlightthickness=1)
    chip.pack(side="left", fill="x", expand=True, padx=(0, 10))
    Label(chip, text=label_text, font=FONT_SMALL, fg=COLORS["muted"], bg=COLORS["surface_2"]).pack(
        anchor="w", padx=14, pady=(10, 0)
    )
    value = Label(chip, text=value_text, font=("Segoe UI", 15, "bold"), fg=COLORS["text"], bg=COLORS["surface_2"])
    value.pack(anchor="w", padx=14, pady=(0, 10))
    return value

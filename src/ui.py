import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional
import os

FONT_LARGE = ("Helvetica", 14)
FONT_XL = ("Helvetica", 18, "bold")


class GroupPanel(tk.Frame):
    def __init__(self, master, group_index: int):
        super().__init__(master, bd=2, relief="ridge", padx=6, pady=6)
        self.group_index = group_index
        self.title = tk.Label(self, text=f"Group {group_index + 1}", font=FONT_XL, anchor='w')
        self.title.pack(fill='x')
        self.members_var = tk.StringVar(value="")
        self.members_label = tk.Label(self, textvariable=self.members_var, font=FONT_LARGE, anchor='w')
        self.members_label.pack(fill='x')

    def set_members(self, members: List[str]):
        # When a group is empty, show nothing instead of a placeholder like "(空)".
        self.members_var.set(", ".join(members) if members else "")


class AppUI:
    def __init__(self, root: tk.Tk, controller):
        self.root = root
        self.controller = controller
        self.special_person = None

        root.title("ランダムグループ分け")
        root.geometry("800x600")

        # Top controls
        ctrl_frame = ttk.Frame(root, padding=8)
        ctrl_frame.pack(fill="x")
        self.start_btn = ttk.Button(ctrl_frame, text="Start Auto", command=self.controller.start_auto)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(ctrl_frame, text="Stop", command=self.controller.request_stop)
        self.stop_btn.pack(side="left", padx=4)


        # Groups area
        self.groups_frame = ttk.Frame(root, padding=8)
        self.groups_frame.pack(fill="x")
        self.group_panels: List[GroupPanel] = []
        for i in range(self.controller.num_groups):
            p = GroupPanel(self.groups_frame, i)
            p.pack(side="left", expand=True, fill="both", padx=6, pady=6)
            self.group_panels.append(p)

        # Unassigned list (horiz scroll)
        bottom = ttk.Frame(root, padding=8)
        bottom.pack(fill="x", side="bottom")
        canvas = tk.Canvas(bottom, height=80)
        canvas.pack(side="left", fill="x", expand=True)
        self.unassigned_container = ttk.Frame(canvas)
        self.unassigned_window = canvas.create_window((0, 0), window=self.unassigned_container, anchor='nw')
        scrollbar = ttk.Scrollbar(bottom, orient="horizontal", command=canvas.xview)
        scrollbar.pack(side="bottom", fill="x")
        canvas.configure(xscrollcommand=scrollbar.set)

        def on_config(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self.unassigned_container.bind("<Configure>", on_config)

        # keyboard bindings
        root.bind_all('<space>', lambda e: self.controller.request_stop())
        root.bind_all('s', lambda e: self.controller.request_stop())
        root.bind_all('S', lambda e: self.controller.request_stop())
        root.bind_all('<Escape>', lambda e: self.controller.request_stop())
        root.bind_all('<Control-s>', lambda e: self.controller.request_stop())

        self.unassigned_buttons = {}

    def refresh(self):
        # update groups
        for i, g in enumerate(self.controller.groups):
            self.group_panels[i].set_members(g)
        # update unassigned
        # clear existing buttons and rebuild
        for w in self.unassigned_container.winfo_children():
            w.destroy()
        self.unassigned_buttons = {}
        unassigned = self.controller.get_unassigned()
        for p in unassigned:
            # use tk.Button to allow setting font reliably across platforms
            b = tk.Button(self.unassigned_container, text=p, command=lambda name=p: self.controller.on_unassigned_click(name), font=FONT_LARGE)
            b.pack(side="left", padx=4, pady=8)
            self.unassigned_buttons[p] = b
        # button states (disable while busy)
        if self.controller.flags.get('is_busy'):
            for b in list(self.unassigned_buttons.values()):
                try:
                    b.config(state='disabled')
                except Exception:
                    pass
        else:
            for b in list(self.unassigned_buttons.values()):
                try:
                    b.config(state='normal')
                except Exception:
                    pass
        if self.controller.flags.get('auto_assigning'):
            try:
                self.start_btn.state(['disabled'])
            except Exception:
                self.start_btn.config(state='disabled')
        else:
            try:
                self.start_btn.state(['!disabled'])
            except Exception:
                self.start_btn.config(state='normal')

    def highlight_group(self, index: int, preview_name: Optional[str]):
        # highlight panel visually for a brief moment
        for i, p in enumerate(self.group_panels):
            bg = "#ffe680" if i == index else "white"
            try:
                p.config(bg=bg)
            except Exception:
                pass
            try:
                p.title.config(bg=bg)
                p.members_label.config(bg=bg)
            except Exception:
                pass
        # show preview name only for the highlighted group, reset others to default
        for i, p in enumerate(self.group_panels):
            if i == index and preview_name:
                p.title.config(text=f"Group {i+1} ← {preview_name}")
            else:
                p.title.config(text=f"Group {i+1}")

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional
import os

FONT_LARGE = ("Helvetica", 14)
FONT_XL = ("Helvetica", 18, "bold")


class GroupPanel(tk.Frame):
    def __init__(self, master, group_index: int, title_font=None, text_font=None):
        # Use fixed borderwidth and padding so the frame size doesn't jump when content changes
        super().__init__(master, bd=2, relief="ridge", padx=6, pady=6, highlightthickness=0)
        self.group_index = group_index
        # Use provided fonts or fall back to defaults
        title_font = title_font or FONT_XL
        text_font = text_font or FONT_LARGE
        # helper to scale fonts (tuple: family, size, *style)
        def _scale_font(fnt, factor: float):
            try:
                family = fnt[0]
                size = fnt[1]
                style = list(fnt[2:]) if len(fnt) > 2 else []
                new_size = max(8, int(size * factor))
                return tuple([family, new_size] + style)
            except Exception:
                return fnt
        self._title_font = title_font
        self._text_font = text_font
        self._large_font = _scale_font(text_font, 2.0)

        # Title is fixed text to avoid changing layout when preview is shown
        self.title = tk.Label(self, text=f"Group {group_index + 1}", font=self._title_font, anchor='w')
        self.title.pack(fill='x')
        # Preview area: reserved space that will show preview name only when highlighted
        self.preview_var = tk.StringVar(value="")
        # preview uses normal font by default; when showing a preview it will switch to large font
        self.preview_label = tk.Label(self, textvariable=self.preview_var, font=self._text_font, anchor='center')
        self.preview_label.pack(fill='x')
        # Members label below preview; reserved space keeps layout stable
        self.members_var = tk.StringVar(value="")
        # members are shown vertically (one per line) and use the larger font
        self.members_label = tk.Label(self, textvariable=self.members_var, font=self._large_font, anchor='nw', justify='left')
        self.members_label.pack(fill='both', expand=True)

    def set_members(self, members: List[str]):
        # Show members as a vertical list (one per line); when empty show nothing
        if members:
            self.members_var.set("\n".join(members))
        else:
            self.members_var.set("")


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


        # Adjust window size and font scaling based on number of people / groups
        import math
        num_people = len(getattr(self.controller, 'people', []))
        num_groups = max(1, self.controller.num_groups)
        max_members = math.ceil(num_people / num_groups) if num_groups else num_people
        # compute geometry: width scales with number of groups, height with max members
        width = min(160 * num_groups + 200, 1600)
        height = min(220 + max_members * 28, 1000)
        try:
            root.geometry(f"{width}x{height}")
        except Exception:
            pass
        # compute font scaling: more groups -> smaller fonts
        scale = max(0.6, min(1.0, 6.0 / max(3, num_groups)))
        title_font = ("Helvetica", max(12, int(18 * scale)), "bold")
        text_font = ("Helvetica", max(10, int(14 * scale)))

        # Groups area (grid 4x2)
        self.groups_frame = ttk.Frame(root, padding=8)
        self.groups_frame.pack(fill="both", expand=True)
        self.group_panels: List[GroupPanel] = []
        cols = 4
        rows = (self.controller.num_groups + cols - 1) // cols
        for r in range(rows):
            self.groups_frame.rowconfigure(r, weight=1)
        for c in range(cols):
            self.groups_frame.columnconfigure(c, weight=1)
        for i in range(self.controller.num_groups):
            r = i // cols
            c = i % cols
            p = GroupPanel(self.groups_frame, i, title_font=title_font, text_font=text_font)
            p.grid(row=r, column=c, sticky='nsew', padx=6, pady=6)
            self.group_panels.append(p)

        # Unassigned list (two-column grid, vertical scroll)
        bottom = ttk.Frame(root, padding=8)
        bottom.pack(fill="both", side="bottom")
        num_people = len(getattr(self.controller, 'people', []))
        rows = max(1, (num_people + 1) // 2)
        canvas_height = min(400, max(140, rows * 70))
        self.unassigned_canvas = tk.Canvas(bottom, height=canvas_height)
        self.unassigned_canvas.pack(side="left", fill="both", expand=True)
        self.unassigned_container = ttk.Frame(self.unassigned_canvas)
        self.unassigned_window = self.unassigned_canvas.create_window((0, 0), window=self.unassigned_container, anchor='nw')
        # vertical scrollbar on the right, thicker for easier use
        self.unassigned_scrollbar = tk.Scrollbar(bottom, orient="vertical", command=self.unassigned_canvas.yview, width=20)
        self.unassigned_scrollbar.pack(side="right", fill="y", padx=(4,0))
        self.unassigned_canvas.configure(yscrollcommand=self.unassigned_scrollbar.set)
        # mousewheel support (bind when pointer is over canvas)
        def _on_mousewheel(event):
            delta = 0
            try:
                if hasattr(event, 'delta') and event.delta:
                    delta = int(-1 * (event.delta / 120))
                elif hasattr(event, 'num'):
                    if event.num == 4:
                        delta = -1
                    elif event.num == 5:
                        delta = 1
            except Exception:
                delta = 0
            try:
                if delta != 0:
                    self.unassigned_canvas.yview_scroll(delta, "units")
            except Exception:
                pass
        def _bind_mousewheel(event):
            self.unassigned_canvas.bind_all('<MouseWheel>', _on_mousewheel)
            self.unassigned_canvas.bind_all('<Button-4>', _on_mousewheel)
            self.unassigned_canvas.bind_all('<Button-5>', _on_mousewheel)
        def _unbind_mousewheel(event):
            self.unassigned_canvas.unbind_all('<MouseWheel>')
            self.unassigned_canvas.unbind_all('<Button-4>')
            self.unassigned_canvas.unbind_all('<Button-5>')
        self.unassigned_canvas.bind('<Enter>', _bind_mousewheel)
        self.unassigned_canvas.bind('<Leave>', _unbind_mousewheel)

        def on_config(event):
            # update scrollregion and make inner frame match canvas width
            try:
                self.unassigned_canvas.configure(scrollregion=self.unassigned_canvas.bbox("all"))
                self.unassigned_canvas.itemconfig(self.unassigned_window, width=self.unassigned_canvas.winfo_width())
            except Exception:
                pass
        self.unassigned_container.bind("<Configure>", on_config)
        def on_canvas_config(event):
            try:
                self.unassigned_canvas.itemconfig(self.unassigned_window, width=event.width)
                self.unassigned_canvas.configure(scrollregion=self.unassigned_canvas.bbox("all"))
            except Exception:
                pass
        self.unassigned_canvas.bind("<Configure>", on_canvas_config)

        # keyboard bindings
        root.bind_all('<space>', lambda e: self.controller.request_stop())
        root.bind_all('s', lambda e: self.controller.request_stop())
        root.bind_all('S', lambda e: self.controller.request_stop())
        root.bind_all('<Escape>', lambda e: self.controller.request_stop())
        root.bind_all('<Control-s>', lambda e: self.controller.request_stop())

        self.unassigned_buttons = {}
        # photo/emoji support for people: maps name -> PhotoImage or emoji string
        self._photos = {}  # name -> PhotoImage
        self._emoji_map = getattr(self.controller, 'PHOTO_EMOJI', {})
        self._current_preview_image = None
        # try to preload any image assets found in src/assets/
        photo_map = getattr(self.controller, 'PHOTO_MAP', {})
        for person in getattr(self.controller, 'people', []):
            asset_name = photo_map.get(person, person)
            photo = self._try_load_asset(asset_name)
            if photo is not None:
                # store under the person key so lookups by person name work later
                self._photos[person] = photo

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
        # arrange unassigned persons in two columns for better readability
        try:
            self.unassigned_container.columnconfigure(0, weight=1, uniform='col')
            self.unassigned_container.columnconfigure(1, weight=1, uniform='col')
        except Exception:
            pass
        for idx, p in enumerate(unassigned):
            r = idx // 2
            c = idx % 2
            img = self._photos.get(p)
            emoji = self._emoji_map.get(p)
            if img is not None:
                b = tk.Button(self.unassigned_container, image=img, command=lambda name=p: self.controller.on_unassigned_click(name), bd=1)
                b._img_ref = img
            elif emoji is not None:
                b = tk.Button(self.unassigned_container, text=emoji, command=lambda name=p: self.controller.on_unassigned_click(name), font=("Helvetica", 22), bd=1)
            else:
                b = tk.Button(self.unassigned_container, text=p, command=lambda name=p: self.controller.on_unassigned_click(name), font=FONT_LARGE, bd=1)
            b.grid(row=r, column=c, padx=12, pady=8, sticky='nsew')
            try:
                self.unassigned_container.rowconfigure(r, weight=0)
            except Exception:
                pass
            self.unassigned_buttons[p] = b
        # adjust canvas height to improve scrollbar thumb usability
        try:
            rows = max(1, (len(unassigned) + 1) // 2)
            self.unassigned_canvas.config(height=min(400, max(140, rows * 70)))
        except Exception:
            pass
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

    def _load_person_image(self, name: str):
        """Deprecated: kept for backward compat. Prefer _try_load_asset which returns a PhotoImage or None."""
        return self._try_load_asset(name) is not None

    # Thumbnail size for displayed images
    THUMB_SIZE = (64, 64)

    def _try_load_asset(self, asset_name: str):
        """Attempt to load an image asset by base name (without extension).

        Returns a PhotoImage on success, or None on failure. Images are scaled to
        THUMB_SIZE when possible to ensure they are visible in the UI.
        """
        thumb_w, thumb_h = self.THUMB_SIZE
        imgpath = os.path.join(os.path.dirname(__file__), 'assets', f"{asset_name}.png")
        if os.path.exists(imgpath):
            # Prefer PIL for reliable loading and resizing
            try:
                from PIL import Image, ImageTk
                im = Image.open(imgpath).convert('RGBA')
                im.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
                # If image is tiny (e.g. 1x1), create a visible placeholder instead
                if im.width <= 1 and im.height <= 1:
                    im2 = Image.new('RGBA', (thumb_w, thumb_h), (255, 211, 128, 255))
                    photo = ImageTk.PhotoImage(im2)
                    return photo
                photo = ImageTk.PhotoImage(im)
                return photo
            except Exception:
                pass
            # Fallback to Tk PhotoImage (use integer subsample to downscale if needed)
            try:
                photo = tk.PhotoImage(file=imgpath)
                w = photo.width()
                h = photo.height()
                # If the image is extremely small (e.g. 1x1 pixel base64 placeholder), create a visible placeholder
                if w <= 1 and h <= 1:
                    placeholder = tk.PhotoImage(width=thumb_w, height=thumb_h)
                    try:
                        placeholder.put("#ffd380", to=(0, 0, thumb_w - 1, thumb_h - 1))
                    except Exception:
                        pass
                    return placeholder
                if w > thumb_w or h > thumb_h:
                    factor = max(1, int(max(w / thumb_w, h / thumb_h)))
                    photo = photo.subsample(factor, factor)
                return photo
            except Exception:
                pass
        # try loading a base64-encoded image file assets/{asset_name}.b64 (useful for embedding small images)
        b64path = os.path.join(os.path.dirname(__file__), 'assets', f"{asset_name}.b64")
        if os.path.exists(b64path):
            try:
                with open(b64path, 'r', encoding='utf-8') as f:
                    b64data = f.read().strip()
                # If PIL is available we can decode and resize nicely
                try:
                    import base64
                    from io import BytesIO
                    from PIL import Image, ImageTk
                    raw = base64.b64decode(b64data)
                    im = Image.open(BytesIO(raw)).convert('RGBA')
                    im.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
                    # If image is tiny (e.g. 1x1), create a visible placeholder instead
                    if im.width <= 1 and im.height <= 1:
                        im2 = Image.new('RGBA', (thumb_w, thumb_h), (255, 211, 128, 255))
                        photo = ImageTk.PhotoImage(im2)
                        return photo
                    photo = ImageTk.PhotoImage(im)
                    return photo
                except Exception:
                    pass
                # Fallback to Tk PhotoImage(data=...)
                try:
                    photo = tk.PhotoImage(data=b64data)
                    w = photo.width()
                    h = photo.height()
                    if w <= 1 and h <= 1:
                        placeholder = tk.PhotoImage(width=thumb_w, height=thumb_h)
                        try:
                            placeholder.put("#ffd380", to=(0, 0, thumb_w - 1, thumb_h - 1))
                        except Exception:
                            pass
                        return placeholder
                    if w > thumb_w or h > thumb_h:
                        factor = max(1, int(max(w / thumb_w, h / thumb_h)))
                        photo = photo.subsample(factor, factor)
                    return photo
                except Exception:
                    pass
            except Exception:
                pass
        return None

    def highlight_group(self, index: int, preview_name: Optional[str]):
        # highlight panel visually for a brief moment without changing layout
        for i, p in enumerate(self.group_panels):
            bg = "#ffe680" if i == index else "white"
            try:
                p.config(bg=bg)
            except Exception:
                pass
            try:
                p.title.config(bg=bg)
                p.preview_label.config(bg=bg)
                p.members_label.config(bg=bg)
                # show image or emoji for preview if available
                if i == index and preview_name:
                    img = self._photos.get(preview_name)
                    emoji = self._emoji_map.get(preview_name)
                    if img is not None:
                        p.preview_label.config(image=img, text="")
                        p.preview_label._img_ref = img
                    elif emoji is not None:
                        p.preview_label.config(text=emoji, image='')
                        p.preview_label.config(font=("Helvetica", 20))
                    else:
                        # use larger font for the preview text during roulette
                        try:
                            p.preview_label.config(image='')
                        except Exception:
                            pass
                        p.preview_label.config(font=p._large_font)
                        p.preview_var.set(preview_name)
                else:
                    # clear preview image/text and restore normal font
                    p.preview_var.set("")
                    try:
                        p.preview_label.config(image='')
                        p.preview_label.config(font=p._text_font)
                    except Exception:
                        pass
            except Exception:
                pass

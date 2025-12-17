import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional
import os

FONT_LARGE = ("Helvetica", 14)
FONT_XL = ("Helvetica", 18, "bold")


class GroupPanel(tk.Frame):
    def __init__(self, master, group_index: int):
        # Use fixed borderwidth and padding so the frame size doesn't jump when content changes
        super().__init__(master, bd=2, relief="ridge", padx=6, pady=6, highlightthickness=0)
        self.group_index = group_index
        # Title is fixed text to avoid changing layout when preview is shown
        self.title = tk.Label(self, text=f"Group {group_index + 1}", font=FONT_XL, anchor='w')
        self.title.pack(fill='x')
        # Preview area: reserved space that will show preview name only when highlighted
        self.preview_var = tk.StringVar(value="")
        self.preview_label = tk.Label(self, textvariable=self.preview_var, font=FONT_LARGE, anchor='w')
        self.preview_label.pack(fill='x')
        # Members label below preview; reserved space keeps layout stable
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
        for p in unassigned:
            # Use image or emoji if available, otherwise show name text
            img = self._photos.get(p)
            emoji = self._emoji_map.get(p)
            if img is not None:
                b = tk.Button(self.unassigned_container, image=img, command=lambda name=p: self.controller.on_unassigned_click(name))
                # keep reference to avoid GC
                b._img_ref = img
            elif emoji is not None:
                b = tk.Button(self.unassigned_container, text=emoji, command=lambda name=p: self.controller.on_unassigned_click(name), font=("Helvetica", 20))
            else:
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
                        p.preview_var.set(preview_name)
                else:
                    # clear preview image/text
                    p.preview_var.set("")
                    try:
                        p.preview_label.config(image='')
                    except Exception:
                        pass
            except Exception:
                pass

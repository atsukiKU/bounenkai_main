import os, sys
import tkinter as tk
# make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.ui import AppUI
from src.controller import AppController
from src.scheduler import TkScheduler

root = tk.Tk()
root.withdraw()
# minimal controller with Alice -> cat
scheduler = TkScheduler(root)
controller = AppController(["Alice","Bob"], 2, None, scheduler)
controller.PHOTO_MAP = {"Alice": "cat"}
ui = AppUI(root, controller)
print("loaded photos:", list(ui._photos.keys()))
# Directly call loader to inspect returned image
img = ui._try_load_asset('cat')
print("_try_load_asset('cat') ->", type(img), getattr(img, 'width', None))
try:
    print("width,height:", img.width(), img.height())
except Exception as e:
    print("error reading size", e)
for name, img2 in ui._photos.items():
    try:
        print(f"{name} in _photos -> size: {img2.width()}x{img2.height()}")
    except Exception as e:
        print(name, "(no size)", e)
root.destroy()

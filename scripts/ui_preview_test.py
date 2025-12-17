import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk
from src.controller import AppController
from src.scheduler import TkScheduler
from src.ui import AppUI

root = tk.Tk()
root.withdraw()
scheduler = TkScheduler(root)
people = [f"P{i}" for i in range(1,9)]
controller = AppController(people, 4, None, scheduler)
controller.PHOTO_MAP = {}
ui = AppUI(root, controller)
controller.ui = ui
# simulate preview
ui.highlight_group(0, preview_name='P1')
print('preview font:', ui.group_panels[0].preview_label.cget('font'))
# simulate clear
ui.highlight_group(-1, preview_name=None)
print('after clear preview font:', ui.group_panels[0].preview_label.cget('font'))
# simulate assign
ui.group_panels[1].set_members(['A','B','C'])
print('members text:', ui.group_panels[1].members_var.get())
print('members font:', ui.group_panels[1].members_label.cget('font'))
root.destroy()

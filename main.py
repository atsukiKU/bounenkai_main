from tkinter import Tk
from src.ui import AppUI
from src.controller import AppController
from src.scheduler import TkScheduler


PEOPLE = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Heidi"]
NUM_GROUPS = 3
SPECIAL_PERSON = "Alice"


def main():
    root = Tk()
    scheduler = TkScheduler(root)
    controller = AppController(PEOPLE, NUM_GROUPS, None, scheduler)
    # attach special person attribute for UI
    controller.SPECIAL_PERSON = SPECIAL_PERSON
    ui = AppUI(root, controller)
    controller.ui = ui
    ui.refresh()
    root.mainloop()


if __name__ == '__main__':
    main()

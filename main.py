from tkinter import Tk
from src.ui import AppUI
from src.controller import AppController
from src.scheduler import TkScheduler


PEOPLE = [
    "Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Heidi",
    "Ivan", "Judy", "Mallory", "Niaj", "Olivia", "Peggy", "Quentin", "Rupert",
    "Sybil", "Trent", "Uma", "Victor", "Wendy", "Xavier", "Yvonne", "Zach",
    "Akira", "Hiro", "Sora", "Yuki", "Kenta", "Mika"
]
NUM_GROUPS = 8
SPECIAL_PERSON = "Alice"
# Images are loaded from src/assets/{Name}.png when present (e.g. src/assets/Alice.png)


def main():
    root = Tk()
    scheduler = TkScheduler(root)
    controller = AppController(PEOPLE, NUM_GROUPS, None, scheduler)
    # attach special person attribute for UI (images are loaded from src/assets/{Name}.png)
    controller.SPECIAL_PERSON = SPECIAL_PERSON
    # map person to asset base name: Alice -> cat (src/assets/cat.b64)
    controller.PHOTO_MAP = {"Alice": "cat"}
    ui = AppUI(root, controller)
    controller.ui = ui
    ui.refresh()
    root.mainloop()


if __name__ == '__main__':
    main()

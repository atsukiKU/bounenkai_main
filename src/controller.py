from typing import List, Optional, Callable
from . import model


class AppController:
    def __init__(self, people: List[str], num_groups: int, ui, scheduler):
        self.people = list(people)
        self.num_groups = num_groups
        self.ui = ui
        self.scheduler = scheduler
        self.groups: List[List[str]] = [[] for _ in range(num_groups)]
        self.flags = {
            "is_busy": False,
            "auto_assigning": False,
            "roulette_running": False,
            "stop_requested": False,
        }
        self._roulette_token = None
        self._current_highlight = 0

    def get_unassigned(self) -> List[str]:
        return model.get_unassigned(self.people, self.groups)

    def on_unassigned_click(self, person: str):
        """Respond to a manual click. For responsive UX, perform a short preview and auto-assign."""
        if self.flags["is_busy"]:
            return
        self.flags["is_busy"] = True
        target = model.choose_target(self.groups)
        # show quick preview and auto finish after short delay
        if self.ui is not None:
            self.ui.highlight_group(target, person)
        # schedule finish after a short delay (responsive)
        self.scheduler.call_after(600, lambda: self._finish_assign(person, target))

    def _finish_assign(self, person: str, target: int):
        model.assign(self.groups, person, target)
        self.flags["is_busy"] = False
        self.flags["roulette_running"] = False
        self.flags["stop_requested"] = False
        if self.ui is not None:
            self.ui.refresh()
        if self.flags["auto_assigning"]:
            # schedule next one shortly
            self.scheduler.call_after(300, self._auto_step)

    def request_stop(self):
        self.flags["stop_requested"] = True

    def start_auto(self):
        if self.flags["auto_assigning"]:
            return
        self.flags["auto_assigning"] = True
        self._auto_step()

    def _auto_step(self):
        # pick next unassigned in order
        unassigned = self.get_unassigned()
        if not unassigned:
            self.flags["auto_assigning"] = False
            return
        person = unassigned[0]
        target = model.choose_target(self.groups)
        self.flags["is_busy"] = True
        self.play_roulette(target, lambda: self._finish_assign(person, target), preview_name=person)

    def stop_auto(self):
        self.flags["auto_assigning"] = False

    def play_roulette(self, target_index: int, on_finish: Callable, preview_name: Optional[str] = None, interval_ms: int = 150, auto_stop_ms: int = 2000):
        """Start roulette animation highlighting groups until stop requested and stops at target_index.

        Auto-stop will request stop after `auto_stop_ms` milliseconds if provided (good for UX and auto mode).
        """
        if self.flags["roulette_running"]:
            return
        # mark busy
        self.flags["roulette_running"] = True
        self.flags["stop_requested"] = False
        self.flags["is_busy"] = True
        self._auto_stop_token = None

        def step():
            if not self.flags["roulette_running"]:
                return
            # advance highlight
            self._current_highlight = (self._current_highlight + 1) % self.num_groups
            if self.ui is not None:
                self.ui.highlight_group(self._current_highlight, preview_name)
            # If user requested stop and we reached target, finish
            if self.flags["stop_requested"] and self._current_highlight == target_index:
                self.flags["roulette_running"] = False
                # cancel auto-stop if any
                if getattr(self, '_auto_stop_token', None) is not None:
                    try:
                        self.scheduler.cancel(self._auto_stop_token)
                    except Exception:
                        pass
                    self._auto_stop_token = None
                on_finish()
                return
            # otherwise schedule next
            self._roulette_token = self.scheduler.call_after(interval_ms, step)

        # start immediately
        if self.ui is None:
            # run quickly without visuals (test mode)
            self.flags["roulette_running"] = False
            self.flags["is_busy"] = False
            on_finish()
            return

        # update UI to reflect busy state
        if self.ui is not None:
            try:
                self.ui.refresh()
            except Exception:
                pass
        # schedule auto-stop for improved UX
        if auto_stop_ms:
            try:
                self._auto_stop_token = self.scheduler.call_after(auto_stop_ms, self.request_stop)
            except Exception:
                self._auto_stop_token = None
        step()

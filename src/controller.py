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
        # deceleration configuration
        self.default_decel_steps = 6  # number of decel cycles after STOP is requested (tunable)
        self._decel_steps_remaining = 0

    def get_unassigned(self) -> List[str]:
        return model.get_unassigned(self.people, self.groups)

    def on_unassigned_click(self, person: str):
        """Respond to a manual click by starting the roulette and waiting for STOP to finalize."""
        if self.flags["is_busy"]:
            return
        self.flags["is_busy"] = True
        target = model.choose_target(self.groups)
        # start roulette; do not auto-stop on manual clicks (user must press Stop)
        # interval slightly longer for visibility
        self.play_roulette(target, lambda: self._finish_assign(person, target, manual=True), preview_name=person, interval_ms=200, auto_stop_ms=None)

    def _finish_assign(self, person: str, target: int, manual: bool = False):
        model.assign(self.groups, person, target)
        self.flags["is_busy"] = False
        self.flags["roulette_running"] = False
        self.flags["stop_requested"] = False
        # clear any visual preview highlight so titles don't keep showing the preview name
        if self.ui is not None:
            try:
                self.ui.highlight_group(-1, None)
            except Exception:
                pass
            self.ui.refresh()
        # If this was a manual assignment, blink the target group in red 3 times
        if manual:
            try:
                self._blink_group(target, times=3, color='red', interval_ms=300)
            except Exception:
                pass
        if self.flags["auto_assigning"]:
            # schedule next one shortly
            self.scheduler.call_after(300, self._auto_step)

    def request_stop(self, decel_steps: Optional[int] = None):
        """Request stop; begin deceleration over multiple steps.

        Optionally provide `decel_steps` to override default duration.
        """
        self.flags["stop_requested"] = True
        self._decel_steps_remaining = decel_steps if decel_steps is not None else self.default_decel_steps

    def start_auto(self):
        """Start auto-assign: assign all remaining participants immediately for a fast outcome."""
        if self.flags["auto_assigning"]:
            return
        self.flags["auto_assigning"] = True
        # Fast-assignment mode: assign everyone left immediately to minimize waiting time.
        unassigned = self.get_unassigned()
        for person in list(unassigned):
            target = model.choose_target(self.groups)
            model.assign(self.groups, person, target)
        # refresh UI and finish
        if self.ui is not None:
            try:
                self.ui.refresh()
            except Exception:
                pass
        self.flags["auto_assigning"] = False

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

        # deceleration variables
        current_interval = interval_ms
        decel_factor = 1.15  # reduced factor for a longer, smoother deceleration
        max_interval = 2200  # allow longer maximum interval so stopping takes longer
        # blink state will use the scheduler to toggle UI colors

        def step():
            nonlocal current_interval
            if not self.flags["roulette_running"]:
                return
            # advance highlight
            self._current_highlight = (self._current_highlight + 1) % self.num_groups
            if self.ui is not None:
                self.ui.highlight_group(self._current_highlight, preview_name)
            # If stop requested, enforce deceleration steps first
            if self.flags["stop_requested"]:
                if getattr(self, '_decel_steps_remaining', 0) > 0:
                    # still decelerating: slow down and consume a step
                    current_interval = min(int(current_interval * decel_factor), max_interval)
                    self._decel_steps_remaining -= 1
                    self._roulette_token = self.scheduler.call_after(current_interval, step)
                    return
                else:
                    # deceleration phase complete: now only stop when we land on the target
                    if self._current_highlight == target_index:
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
                    # not yet landed on target - do one more slowed step
                    current_interval = min(int(current_interval * decel_factor), max_interval)
                    self._roulette_token = self.scheduler.call_after(current_interval, step)
                    return
            # otherwise keep the original pace
            self._roulette_token = self.scheduler.call_after(current_interval, step)

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

    def _blink_group(self, index: int, times: int = 3, color: str = 'red', interval_ms: int = 300):
        """Blink the group panel at `index` `times` times using the scheduler.

        This toggles the panel background between `color` and the default background, then refreshes the UI.
        """
        if self.ui is None:
            return
        total_toggles = times * 2
        state = {"count": 0}
        default_bg = "white"

        def blink_step():
            try:
                p = self.ui.group_panels[index]
            except Exception:
                p = None
            if state["count"] >= total_toggles:
                # restore and refresh
                if p is not None:
                    try:
                        p.config(bg=default_bg)
                        p.title.config(bg=default_bg)
                        p.members_label.config(bg=default_bg)
                    except Exception:
                        pass
                try:
                    self.ui.refresh()
                except Exception:
                    pass
                return
            on = (state["count"] % 2 == 0)
            bg = color if on else default_bg
            if p is not None:
                try:
                    p.config(bg=bg)
                    p.title.config(bg=bg)
                    p.members_label.config(bg=bg)
                except Exception:
                    pass
            state["count"] += 1
            self.scheduler.call_after(interval_ms, blink_step)

        # start blinking
        blink_step()

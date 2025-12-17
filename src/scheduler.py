from typing import Callable, Any, Optional, Protocol


class Scheduler(Protocol):
    def call_after(self, ms: int, callback: Callable) -> Any: ...
    def cancel(self, token: Any) -> None: ...


class TkScheduler:
    def __init__(self, tkroot):
        self._root = tkroot

    def call_after(self, ms: int, callback: Callable) -> Any:
        return self._root.after(ms, callback)

    def cancel(self, token: Any) -> None:
        try:
            self._root.after_cancel(token)
        except Exception:
            pass


class TestScheduler:
    """Immediate scheduler for testing: calls callbacks synchronously."""

    def call_after(self, ms: int, callback: Callable) -> Any:
        # ignore ms, run immediately
        callback()
        return None

    def cancel(self, token: Any) -> None:
        return

# bauble/uihelpers.py
from typing import Optional


class StatusbarCtx:
    """
    Thread-friendly wrapper around a Gtk.Statusbar.
    - Lazily resolves bauble.gui.widgets.statusbar if not injected.
    - Caches the context id.
    - Push/pop happens on the main thread via GLib.idle_add.
    """
    def __init__(self, statusbar=None, context_key: str = "searchview.nresults"):
        self.statusbar = statusbar
        self.context_key = context_key
        self._ctx_id: Optional[int] = None

    def _ensure(self) -> bool:
        if self.statusbar is None:
            from bauble import gui as _gui
            self.statusbar = getattr(getattr(_gui, "widgets", None), "statusbar", None)
            if self.statusbar is None:
                return False
        if self._ctx_id is None:
            self._ctx_id = self.statusbar.get_context_id(self.context_key)
        return True

    def push(self, text: str) -> None:
        if not self._ensure():
            return
        from bauble.gtkinit import GLib
        def _do():
            self.statusbar.pop(self._ctx_id)
            self.statusbar.push(self._ctx_id, text)
            return False
        GLib.idle_add(_do)

    def clear(self) -> None:
        if not self._ensure():
            return
        from bauble.gtkinit import GLib
        GLib.idle_add(lambda: (self.statusbar.pop(self._ctx_id), False)[1])

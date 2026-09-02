"""Global X11 hotkey integration through Keybinder."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Keybinder", "3.0")
from gi.repository import Gtk, Keybinder


class Hotkey:
    def __init__(self, application: Gtk.Application, callback, accelerator: str = "<Super>v") -> None:
        self.application = application
        self.callback = callback
        self.accelerator = accelerator
        self.registered = False
        Keybinder.init()

    def _on_activate(self, *_args) -> None:
        self.callback()

    def register(self) -> bool:
        if self.registered:
            return True
        if not Keybinder.bind(self.accelerator, self._on_activate, None):
            return False
        self.registered = True
        return True

    def unregister(self) -> None:
        if self.registered:
            Keybinder.unbind(self.accelerator)
            self.registered = False

    def set_accelerator(self, accelerator: str) -> bool:
        self.unregister()
        self.accelerator = accelerator
        return self.register()
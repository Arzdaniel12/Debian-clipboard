"""Best-effort global hotkey integration with a GTK fallback."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk


class Hotkey:
    def __init__(self, application: Gtk.Application, callback, accelerator: str = "<Super>v") -> None:
        self.application = application
        self.callback = callback
        self.accelerator = accelerator
        self.action = "app.show-history"

    def register(self) -> None:
        action = self.application.lookup_action("show-history")
        if action is None:
            action = Gio.SimpleAction.new("show-history", None)
            action.connect("activate", lambda *_: self.callback())
            self.application.add_action(action)
        self.application.set_accels_for_action(self.action, [self.accelerator])

    def set_accelerator(self, accelerator: str) -> None:
        self.accelerator = accelerator
        self.register()
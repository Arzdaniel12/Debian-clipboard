"""GTK clipboard monitoring and copy helpers."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from .storage import ClipboardItem, ClipboardStore


class ClipboardMonitor:
    def __init__(self, store: ClipboardStore, on_change: Callable[[], None]) -> None:
        self.store = store
        self.on_change = on_change
        self.clipboard = Gtk.Clipboard.get_default(Gdk.Display.get_default())
        self.paused = False
        self.private_mode = False
        self.excluded_apps: set[str] = set()
        self._last_fingerprint: bytes | None = None
        self._timer_id: int | None = None

    def start(self) -> None:
        if self._timer_id is None:
            self._timer_id = GLib.timeout_add(500, self._poll)

    def stop(self) -> None:
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def _poll(self) -> bool:
        if not self.paused and not self.private_mode:
            text = self.clipboard.wait_for_text()
            if text:
                fingerprint = b"text\0" + text.encode("utf-8")
                if fingerprint != self._last_fingerprint and self.store.add_text(text):
                    self._last_fingerprint = fingerprint
                    self.on_change()
            else:
                pixbuf = self.clipboard.wait_for_image()
                if pixbuf:
                    success, data = pixbuf.save_to_bufferv("png", [], [])
                    if success and data:
                        fingerprint = b"image\0" + bytes(data)
                        if fingerprint != self._last_fingerprint and self.store.add_image(bytes(data)):
                            self._last_fingerprint = fingerprint
                            self.on_change()
        return True

    def copy_item(self, item: ClipboardItem) -> None:
        if item.kind == "text":
            self.clipboard.set_text(item.text or "", -1)
        else:
            loader = GdkPixbuf.PixbufLoader.new_with_type("png")
            loader.write(item.data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf:
                self.clipboard.set_image(pixbuf)
        self.clipboard.store()
        self._last_fingerprint = None
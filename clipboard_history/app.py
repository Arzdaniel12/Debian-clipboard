"""GTK application entry point."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from threading import Thread

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio, GLib, Gtk

from . import __version__
from .hotkey import Hotkey
from .monitor import ClipboardMonitor
from .storage import ClipboardItem, ClipboardStore
from .updater import Updater


APP_ID = "org.debian.ClipboardHistory"


class HistoryWindow(Gtk.Window):
    def __init__(self, app: "ClipboardApplication") -> None:
        super().__init__(title="Clipboard History", application=app)
        self.app = app
        self.set_default_size(560, 520)
        self.set_border_width(12)
        self.connect("delete-event", self._hide)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(root)
        search_row = Gtk.Box(spacing=8)
        root.pack_start(search_row, False, False, 0)
        self.search = Gtk.SearchEntry(placeholder_text="Buscar en el historial")
        self.search.connect("search-changed", lambda *_: self.refresh())
        search_row.pack_start(self.search, True, True, 0)
        clear = Gtk.Button(label="Borrar todo")
        clear.connect("clicked", self._clear)
        search_row.pack_start(clear, False, False, 0)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self._copy_row)
        root.pack_start(self.listbox, True, True, 0)
        self.refresh()

    def _hide(self, *_args) -> bool:
        self.hide()
        return True

    def _clear(self, *_args) -> None:
        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL, "¿Borrar todo el historial?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.app.store.clear()
            self.refresh()

    def refresh(self) -> None:
        for row in self.listbox.get_children():
            row.destroy()
        for item in self.app.store.items(self.search.get_text() if hasattr(self, "search") else ""):
            row = Gtk.ListBoxRow()
            row.item = item
            box = Gtk.Box(spacing=10, margin=8)
            if item.kind == "image":
                loader = GdkPixbuf.PixbufLoader.new_with_type("png")
                loader.write(item.data)
                loader.close()
                pixbuf = loader.get_pixbuf()
                if pixbuf:
                    pixbuf = pixbuf.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
                    box.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)
                label = Gtk.Label(label="Imagen", xalign=0)
            else:
                preview = (item.text or "").replace("\n", " ")[:100]
                label = Gtk.Label(label=preview, xalign=0)
            box.pack_start(label, True, True, 0)
            delete = Gtk.Button(label="Eliminar")
            delete.connect("clicked", lambda _button, current=item: self._delete(current))
            box.pack_start(delete, False, False, 0)
            row.add(box)
            self.listbox.add(row)
        self.listbox.show_all()

    def _delete(self, item: ClipboardItem) -> None:
        self.app.store.delete(item.id)
        self.refresh()

    def _copy_row(self, _listbox, row: Gtk.ListBoxRow) -> None:
        self.app.monitor.copy_item(row.item)
        self.hide()


class PreferencesDialog(Gtk.Dialog):
    def __init__(self, app: "ClipboardApplication") -> None:
        super().__init__(title="Preferencias", transient_for=app.window, flags=Gtk.DialogFlags.MODAL)
        self.add_button("Cerrar", Gtk.ResponseType.CLOSE)
        self.app = app
        self.connect("response", self._save_and_close)
        box = self.get_content_area()
        box.set_spacing(10)
        self.pause = Gtk.CheckButton(label="Pausar monitoreo")
        self.pause.set_active(app.monitor.paused)
        self.pause.connect("toggled", lambda widget: setattr(app.monitor, "paused", widget.get_active()))
        box.pack_start(self.pause, False, False, 0)
        self.private = Gtk.CheckButton(label="Modo privado: no guardar nuevos elementos")
        self.private.set_active(app.monitor.private_mode)
        self.private.connect("toggled", lambda widget: setattr(app.monitor, "private_mode", widget.get_active()))
        box.pack_start(self.private, False, False, 0)
        self.startup = Gtk.CheckButton(label="Iniciar automáticamente")
        self.startup.set_active(app.startup_enabled())
        self.startup.connect("toggled", lambda widget: app.set_startup(widget.get_active()))
        box.pack_start(self.startup, False, False, 0)
        self.hotkey = Gtk.Entry(text=app.hotkey.accelerator)
        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Atajo global", xalign=0), True, True, 0)
        row.pack_start(self.hotkey, False, False, 0)
        box.pack_start(row, False, False, 0)
        self.show_all()

    def _save_and_close(self, _dialog, _response) -> None:
        accelerator = self.hotkey.get_text().strip()
        key, _modifiers = Gtk.accelerator_parse(accelerator)
        if key:
            self.app.hotkey.set_accelerator(accelerator)
        self.destroy()


class ClipboardApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        data_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "clipboard-history"
        self.store = ClipboardStore(data_dir / "history.db")
        self.hidden = "--hidden" in sys.argv
        self.hotkey = Hotkey(self, self.show_history)
        self.updater = Updater(__version__, self._offer_update)

    def do_activate(self) -> None:
        if not hasattr(self, "window"):
            self.window = HistoryWindow(self)
            self.monitor = ClipboardMonitor(self.store, self.window.refresh)
            self.monitor.start()
            if not self.hotkey.register():
                print("No se pudo registrar Super+V; puede estar en uso.", file=sys.stderr)
            self._create_tray()
            self.updater.check_async()
            self.update_timer = GLib.timeout_add_seconds(21600, self._check_updates)
        if not self.hidden:
            self.show_history()

    def do_shutdown(self) -> None:
        if hasattr(self, "update_timer"):
            GLib.source_remove(self.update_timer)
        if hasattr(self, "hotkey"):
            self.hotkey.unregister()
        if hasattr(self, "monitor"):
            self.monitor.stop()
        self.store.close()
        super().do_shutdown()

    def _check_updates(self) -> bool:
        self.updater.check_async()
        return True

    def _offer_update(self, version: str, package_path) -> None:
        GLib.idle_add(self._show_update_dialog, version, package_path)

    def _show_update_dialog(self, version: str, package_path) -> bool:
        if not hasattr(self, "window"):
            return False
        dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO, Gtk.ButtonsType.YES_NO, f"Hay una actualización disponible: {version}. ¿Instalarla ahora?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            Thread(target=self._install_update, args=(package_path,), daemon=True).start()
        return False

    def _install_update(self, package_path) -> None:
        if self.updater.install(package_path):
            GLib.idle_add(self._restart_after_update)

    def _restart_after_update(self) -> bool:
        self.quit()
        subprocess.Popen(["clipboard-history", "--hidden"])
        return False

    def show_history(self) -> None:
        self.window.show_all()
        self.window.present()
        self.window.search.grab_focus()

    def _create_tray(self) -> None:
        self.tray = Gtk.StatusIcon.new_from_icon_name("edit-paste")
        self.tray.set_tooltip_text("Clipboard History")
        self.tray.connect("activate", lambda *_: self.show_history())
        self.tray.connect("popup-menu", self._tray_menu)

    def _tray_menu(self, _icon, button, timestamp) -> None:
        menu = Gtk.Menu()
        show = Gtk.MenuItem(label="Mostrar historial")
        show.connect("activate", lambda *_: self.show_history())
        preferences = Gtk.MenuItem(label="Preferencias")
        preferences.connect("activate", lambda *_: PreferencesDialog(self).run())
        updates = Gtk.MenuItem(label="Buscar actualizaciones")
        updates.connect("activate", lambda *_: self.updater.check_async())
        quit_item = Gtk.MenuItem(label="Salir")
        quit_item.connect("activate", lambda *_: self.quit())
        for item in (show, preferences, updates, quit_item):
            menu.append(item)
        menu.show_all()
        menu.popup(None, None, Gtk.StatusIcon.position_menu, self.tray, button, timestamp)

    def startup_enabled(self) -> bool:
        return (Path.home() / ".config/autostart/clipboard-history.desktop").exists()

    def set_startup(self, enabled: bool) -> None:
        path = Path.home() / ".config/autostart/clipboard-history.desktop"
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[Desktop Entry]\nType=Application\nName=Clipboard History\nExec=clipboard-history --hidden\nX-GNOME-Autostart-enabled=true\n", encoding="utf-8")
        elif path.exists():
            path.unlink()


def main() -> int:
    return ClipboardApplication().run(None)
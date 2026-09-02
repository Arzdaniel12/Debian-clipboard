import unittest
from unittest.mock import Mock, patch

from clipboard_history.hotkey import Hotkey


class HotkeyTests(unittest.TestCase):
    @patch("clipboard_history.hotkey.Keybinder")
    def test_register_and_unregister_global_shortcut(self, keybinder):
        callback = Mock()
        hotkey = Hotkey(Mock(), callback)

        keybinder.bind.return_value = True
        self.assertTrue(hotkey.register())
        keybinder.bind.assert_called_once()
        self.assertTrue(hotkey.register())
        keybinder.unbind.assert_not_called()

        hotkey.unregister()
        keybinder.unbind.assert_called_once_with("<Super>v")

    @patch("clipboard_history.hotkey.Keybinder")
    def test_rebinding_releases_previous_shortcut(self, keybinder):
        keybinder.bind.return_value = True
        hotkey = Hotkey(Mock(), Mock())
        hotkey.register()

        self.assertTrue(hotkey.set_accelerator("<Control><Shift>v"))
        keybinder.unbind.assert_called_once_with("<Super>v")
        keybinder.bind.assert_called_with("<Control><Shift>v", hotkey._on_activate, None)

    @patch("clipboard_history.hotkey.Keybinder")
    def test_binding_failure_is_reported(self, keybinder):
        keybinder.bind.return_value = False
        hotkey = Hotkey(Mock(), Mock())

        self.assertFalse(hotkey.register())
        self.assertFalse(hotkey.registered)


if __name__ == "__main__":
    unittest.main()
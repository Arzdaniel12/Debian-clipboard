import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from clipboard_history.updater import Updater, version_tuple


class UpdaterTests(unittest.TestCase):
    def test_version_tuple_supports_release_tags(self):
        self.assertGreater(version_tuple("v1.0.2"), version_tuple("1.0.1"))

    @patch("clipboard_history.updater.subprocess.run")
    def test_install_uses_pkexec_and_apt(self, run):
        run.return_value.returncode = 0
        self.assertTrue(Updater.install(Path("/tmp/update.deb")))
        run.assert_called_once_with(["pkexec", "apt-get", "install", "-y", "/tmp/update.deb"], check=False)

    def test_checker_does_not_download_same_version(self):
        callback = Mock()
        updater = Updater("1.0.2", callback)
        with patch("clipboard_history.updater.urlopen") as open_url:
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.return_value = b'{"tag_name":"v1.0.2","assets":[]}'
            open_url.return_value = response
            updater._check()
        callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
"""Release checking and Debian package installation."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from threading import Thread
from typing import Callable
from urllib.request import Request, urlopen


RELEASES_URL = "https://api.github.com/repos/Arzdaniel12/Debian-clipboard/releases/latest"


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.lstrip("v").split("."))


class Updater:
    def __init__(self, current_version: str, on_update: Callable[[str, Path], None]) -> None:
        self.current_version = current_version
        self.on_update = on_update
        self.checking = False

    def check_async(self) -> None:
        if self.checking:
            return
        self.checking = True
        Thread(target=self._check, daemon=True).start()

    def _check(self) -> None:
        try:
            request = Request(RELEASES_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "Clipboard-History"})
            with urlopen(request, timeout=10) as response:
                release = json.load(response)
            release_version = release.get("tag_name", "")
            if version_tuple(release_version) <= version_tuple(self.current_version):
                return
            asset = next((item for item in release.get("assets", []) if item.get("name", "").endswith(".deb")), None)
            if not asset:
                return
            package_path = Path(tempfile.gettempdir()) / asset["name"]
            with urlopen(Request(asset["browser_download_url"], headers={"User-Agent": "Clipboard-History"}), timeout=30) as response:
                package_path.write_bytes(response.read())
            self.on_update(release_version, package_path)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return
        finally:
            self.checking = False

    @staticmethod
    def install(package_path: Path) -> bool:
        result = subprocess.run(["pkexec", "apt-get", "install", "-y", str(package_path)], check=False)
        return result.returncode == 0

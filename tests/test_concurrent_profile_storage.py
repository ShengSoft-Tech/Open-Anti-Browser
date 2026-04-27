from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.browser_manager import BrowserManager
from backend.storage import JsonStorage


class _TempJsonStorage(JsonStorage):
    def __init__(self, root: str) -> None:
        super().__init__()
        self.data_dir = Path(root)
        self.downloads_dir = self.data_dir / "downloads"
        self.settings_file = self.data_dir / "settings.json"
        self.profiles_file = self.data_dir / "profiles.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)


class ConcurrentProfileStorageTests(unittest.TestCase):
    def test_concurrent_firefox_profile_creates_are_all_persisted(self):
        with TemporaryDirectory() as temp_dir:
            manager = BrowserManager()
            manager.storage = _TempJsonStorage(temp_dir)

            results: list[dict] = []
            errors: list[str] = []

            def create_profile(index: int) -> dict:
                return manager.save_profile({"engine": "firefox", "name": f"profile-{index}"})

            with ThreadPoolExecutor(max_workers=24) as executor:
                futures = [executor.submit(create_profile, index) for index in range(24)]
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as exc:  # pragma: no cover - message is asserted below
                        errors.append(repr(exc))

            self.assertEqual(errors, [])
            stored_profiles = manager.storage.load_profiles()
            stored_ids = {profile.id for profile in stored_profiles}
            returned_ids = {item["id"] for item in results}
            self.assertEqual(len(results), 24)
            self.assertEqual(len(stored_profiles), 24)
            self.assertEqual(returned_ids, stored_ids)

            for profile_id in returned_ids:
                self.assertEqual(manager.get_profile(profile_id).id, profile_id)

    def test_concurrent_blank_names_receive_unique_sequence_names(self):
        with TemporaryDirectory() as temp_dir:
            manager = BrowserManager()
            manager.storage = _TempJsonStorage(temp_dir)

            results: list[dict] = []
            errors: list[str] = []

            def create_profile(_: int) -> dict:
                return manager.save_profile({"engine": "firefox", "name": ""})

            with ThreadPoolExecutor(max_workers=16) as executor:
                futures = [executor.submit(create_profile, index) for index in range(16)]
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as exc:  # pragma: no cover - message is asserted below
                        errors.append(repr(exc))

            self.assertEqual(errors, [])
            names = sorted(int(item["name"]) for item in results)
            self.assertEqual(names, list(range(1, 17)))


if __name__ == "__main__":
    unittest.main()

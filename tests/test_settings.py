from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.media_info import format_size_change
from app.settings import AppSettings, load_settings, save_settings, settings_path


class SettingsTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "VideoFormatConverter" / "settings.json"
            with patch("app.settings.settings_path", return_value=fake):
                original = AppSettings(
                    last_input_dir=r"D:\视频",
                    last_output_dir=r"D:\输出",
                    last_preset_id="mp4_small",
                    window_width=1280,
                    window_height=800,
                )
                save_settings(original)
                loaded = load_settings()
                self.assertEqual(loaded.last_input_dir, original.last_input_dir)
                self.assertEqual(loaded.last_output_dir, original.last_output_dir)
                self.assertEqual(loaded.last_preset_id, "mp4_small")
                self.assertEqual(loaded.window_width, 1280)
                self.assertEqual(loaded.window_height, 800)

    def test_corrupt_json_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "settings.json"
            fake.write_text("{not-json", encoding="utf-8")
            with patch("app.settings.settings_path", return_value=fake):
                loaded = load_settings()
                self.assertEqual(loaded.last_preset_id, "mp4_compat")
                self.assertEqual(loaded.window_width, 1100)

    def test_settings_path_under_appdata(self) -> None:
        path = settings_path()
        self.assertTrue(str(path).endswith("VideoFormatConverter\\settings.json") or str(path).endswith("VideoFormatConverter/settings.json"))


class SizeChangeTests(unittest.TestCase):
    def test_compress(self) -> None:
        text = format_size_change(12_300_000, 4_100_000)
        self.assertIn("→", text)
        self.assertIn("压缩", text)
        self.assertIn("%", text)

    def test_increase(self) -> None:
        text = format_size_change(1_000_000, 2_000_000)
        self.assertIn("增大", text)

    def test_almost_same(self) -> None:
        text = format_size_change(1_000_000, 995_000)
        self.assertIn("体积基本不变", text)


if __name__ == "__main__":
    unittest.main()

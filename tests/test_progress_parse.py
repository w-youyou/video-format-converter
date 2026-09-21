from __future__ import annotations

import unittest

from app.core.ffmpeg_service import (
    build_convert_cmd,
    parse_out_time_sec,
    percent_from_out_time_sec,
)
from app.core.presets import get_preset


class ProgressParseTests(unittest.TestCase):
    def test_parse_clock_out_time(self) -> None:
        value = parse_out_time_sec("out_time=00:00:12.345678")
        self.assertAlmostEqual(value or 0, 12.345678, places=6)

    def test_parse_out_time_us(self) -> None:
        value = parse_out_time_sec("out_time_us=12345678")
        self.assertAlmostEqual(value or 0, 12.345678, places=6)

    def test_unrelated_line_is_none(self) -> None:
        self.assertIsNone(parse_out_time_sec("frame=123"))
        self.assertIsNone(parse_out_time_sec("progress=continue"))
        self.assertIsNone(parse_out_time_sec("out_time=N/A"))

    def test_out_time_ms_is_microseconds_by_default(self) -> None:
        value = parse_out_time_sec("out_time_ms=1234000")
        self.assertIsNotNone(value)
        self.assertAlmostEqual(value or 0, 1.234, places=3)
        self.assertNotAlmostEqual(value or 0, 1234, places=0)

    def test_out_time_ms_fallback_to_milliseconds(self) -> None:
        value = parse_out_time_sec("out_time_ms=5000000", duration_sec=1.0)
        self.assertAlmostEqual(value or 0, 5000.0, places=1)

    def test_percent_clamps_to_99(self) -> None:
        self.assertEqual(percent_from_out_time_sec(13, 12), 99)
        self.assertNotEqual(percent_from_out_time_sec(13, 12), 100)
        self.assertEqual(percent_from_out_time_sec(6, 12), 50)
        self.assertEqual(percent_from_out_time_sec(0, 12), 0)
        self.assertEqual(percent_from_out_time_sec(1, 0), 0)

    def test_progress_flags_before_input(self) -> None:
        cmd = build_convert_cmd(
            "ffmpeg",
            "in.mp4",
            "out.mp4",
            get_preset("mp4_compat"),
            overwrite=True,
            with_progress=True,
        )
        self.assertEqual(cmd[1], "-y")
        self.assertIn("-nostats", cmd)
        self.assertIn("-progress", cmd)
        self.assertEqual(cmd[cmd.index("-progress") + 1], "pipe:1")
        self.assertLess(cmd.index("-y"), cmd.index("-i"))
        self.assertLess(cmd.index("-progress"), cmd.index("-i"))


if __name__ == "__main__":
    unittest.main()

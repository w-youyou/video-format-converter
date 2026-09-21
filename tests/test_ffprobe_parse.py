from __future__ import annotations

import unittest

from app.core.ffprobe_service import build_cmd, parse
from app.core.media_info import (
    UNKNOWN,
    format_bit_rate,
    format_duration,
    format_fps,
    format_size,
)


COMPLETE_JSON = """
{
  "format": {
    "duration": "83.2",
    "bit_rate": "2100000"
  },
  "streams": [
    {
      "codec_type": "video",
      "codec_name": "h264",
      "width": 1920,
      "height": 1080,
      "avg_frame_rate": "30/1",
      "disposition": {"attached_pic": 0}
    },
    {
      "codec_type": "audio",
      "codec_name": "aac"
    }
  ]
}
"""

COVER_ONLY_JSON = """
{
  "format": {},
  "streams": [
    {
      "codec_type": "video",
      "codec_name": "mjpeg",
      "width": 640,
      "height": 640,
      "disposition": {"attached_pic": 1}
    },
    {
      "codec_type": "audio",
      "codec_name": "mp3"
    }
  ]
}
"""

MISSING_JSON = """
{
  "format": {},
  "streams": [
    {
      "codec_type": "video",
      "codec_name": "hevc",
      "width": 1280,
      "height": 720,
      "avg_frame_rate": "0/0"
    }
  ]
}
"""

FRACTION_FPS_JSON = """
{
  "format": {"duration": "1"},
  "streams": [
    {
      "codec_type": "video",
      "codec_name": "h264",
      "width": 16,
      "height": 16,
      "avg_frame_rate": "30000/1001"
    }
  ]
}
"""


class FfprobeParseTests(unittest.TestCase):
    def test_build_cmd_no_double_dash(self) -> None:
        cmd = build_cmd(r"C:\ffmpeg\bin\ffprobe.exe", r"D:\测试 视频.mp4")
        self.assertIsInstance(cmd, list)
        self.assertNotIn("--", cmd)
        self.assertEqual(cmd[-1], r"D:\测试 视频.mp4")
        self.assertEqual(
            cmd[:-1],
            [
                r"C:\ffmpeg\bin\ffprobe.exe",
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
            ],
        )

    def test_parse_complete_json(self) -> None:
        info = parse(COMPLETE_JSON, r"C:\clip.mp4", 12_884_901)
        self.assertEqual(info.filename, "clip.mp4")
        self.assertEqual(info.size_bytes, 12_884_901)
        self.assertAlmostEqual(info.duration_sec or 0, 83.2)
        self.assertEqual(info.width, 1920)
        self.assertEqual(info.height, 1080)
        self.assertEqual(info.video_codec, "h264")
        self.assertEqual(info.audio_codec, "aac")
        self.assertEqual(info.fps, 30.0)
        self.assertEqual(info.bit_rate, 2_100_000)
        self.assertIsNone(info.warning)

    def test_parse_missing_fields(self) -> None:
        info = parse(MISSING_JSON, "a.mp4", 100)
        self.assertIsNone(info.duration_sec)
        self.assertIsNone(info.fps)
        self.assertIsNone(info.bit_rate)
        self.assertIsNone(info.audio_codec)
        self.assertEqual(info.video_codec, "hevc")
        self.assertIsNone(info.warning)

    def test_parse_skips_attached_pic(self) -> None:
        info = parse(COVER_ONLY_JSON, "song.mp3", 10)
        self.assertIsNone(info.video_codec)
        self.assertEqual(info.audio_codec, "mp3")
        self.assertIsNotNone(info.warning)

    def test_parse_no_video_stream(self) -> None:
        info = parse('{"format": {}, "streams": []}', "bad.bin", 3)
        self.assertIsNone(info.width)
        self.assertIsNotNone(info.warning)

    def test_parse_invalid_json(self) -> None:
        info = parse("not-json", "a.mp4", 1)
        self.assertEqual(info.size_bytes, 1)
        self.assertIsNone(info.video_codec)
        self.assertIsNotNone(info.warning)

    def test_fractional_fps(self) -> None:
        info = parse(FRACTION_FPS_JSON, "ntsc.mp4", 1)
        self.assertAlmostEqual(info.fps or 0, 30000 / 1001, places=3)
        self.assertEqual(format_fps(info.fps), "29.97 fps")

    def test_formatters(self) -> None:
        self.assertEqual(format_size(500), "500 B")
        self.assertEqual(format_size(12_884_901), "12.3 MB")
        self.assertEqual(format_duration(83), "00:01:23")
        self.assertEqual(format_duration(None), UNKNOWN)
        self.assertEqual(format_fps(30.0), "30 fps")
        self.assertEqual(format_bit_rate(2_100_000), "2.1 Mbps")


if __name__ == "__main__":
    unittest.main()

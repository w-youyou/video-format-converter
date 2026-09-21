from __future__ import annotations

import unittest

from app.core.ffmpeg_service import (
    MSG_COPY_FAIL,
    MSG_NO_AUDIO,
    build_convert_cmd,
    humanize_ffmpeg_error,
    is_same_media_path,
    replace_output_suffix,
)
from app.core.presets import all_presets, get_preset


class PresetCommandTests(unittest.TestCase):
    def test_four_presets_are_lists_with_paths(self) -> None:
        ffmpeg = r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
        source = r"D:\测试 视频.mp4"
        self.assertEqual(len(all_presets()), 4)
        for preset in all_presets():
            output = rf"D:\out{preset.suffix}"
            cmd = build_convert_cmd(ffmpeg, source, output, preset)
            self.assertIsInstance(cmd, list)
            self.assertTrue(all(isinstance(item, str) for item in cmd))
            self.assertEqual(cmd[0], ffmpeg)
            self.assertIn("-hide_banner", cmd)
            self.assertIn("-i", cmd)
            self.assertEqual(cmd[cmd.index("-i") + 1], source)
            self.assertEqual(cmd[-1], output)
            self.assertNotIn("-y", cmd)
            self.assertFalse(any(" -i " in item for item in cmd))
            self.assertEqual(cmd[1], "-hide_banner")

    def test_copy_mux_maps_and_drops_subs(self) -> None:
        preset = get_preset("copy_mux")
        cmd = build_convert_cmd("ffmpeg", "in.mkv", "out.mp4", preset)
        self.assertIn("-sn", cmd)
        self.assertIn("-map", cmd)
        self.assertIn("0:v:0", cmd)
        self.assertIn("0:a:0?", cmd)
        self.assertIn("-c", cmd)
        self.assertIn("copy", cmd)

    def test_replace_output_suffix_keeps_stem(self) -> None:
        result = replace_output_suffix(r"D:\a\v_转换.mp4", ".mp3")
        self.assertEqual(result, r"D:\a\v_转换.mp3")

    def test_same_media_path_normcase(self) -> None:
        self.assertTrue(
            is_same_media_path(r"C:\Video\A.mp4", r"c:\video\a.mp4")
        )
        self.assertFalse(
            is_same_media_path(r"C:\Video\A.mp4", r"C:\Video\A_转换.mp4")
        )

    def test_humanize_copy_and_mp3(self) -> None:
        self.assertEqual(humanize_ffmpeg_error("anything", "copy_mux"), MSG_COPY_FAIL)
        self.assertEqual(humanize_ffmpeg_error("anything", "mp3_audio"), MSG_NO_AUDIO)
        text = humanize_ffmpeg_error("line1\nError while encoding")
        self.assertIn("Error while encoding", text)
        self.assertIn("详细日志", text)


if __name__ == "__main__":
    unittest.main()

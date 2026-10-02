"""측정 증거의 해시 바인딩·비관찰·실제 미디어 실행 및 계산 검증."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('motion_review', ROOT/'scripts/motion_review_evidence.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MotionEvidenceTests(unittest.TestCase):
    def test_reading_counts_dates_english_and_composed_korean(self):
        self.assertEqual(m.reading_time('가 나!')[0], 2)
        self.assertEqual(m.reading_time('가 나 AI 10/19')[0], 8)
        self.assertAlmostEqual(m.reading_time('가나다라마바사아자차카타')[1], 2.3)

    def test_declared_exposure_size_safe_area_and_event_offset(self):
        data = {'safe_rect': [.1, .1, .9, .8],
                'texts': [{'id': 'date', 'text': '접수 9/30~10/8', 'stable_start': 1., 'stable_end': 1.2,
                           'font_px': 20, 'bbox': [800, 1500, 1000, 1800]}],
                'events': [{'id': 'settle', 'visual_time': 1., 'audio_time': 1.1}]}
        r = m.declared_checks(data, 1080, 1920, 3, 30)
        self.assertGreater(r['texts'][0]['reading_shortfall_seconds'], 0)
        self.assertTrue(r['texts'][0]['size_below_recommendation'])
        self.assertFalse(r['texts'][0]['bbox_inside_selected_safe_rect'])
        self.assertTrue(r['events'][0]['outside_two_frame_target'])
        self.assertEqual(r['provenance'], 'AUTHOR_DECLARED_UNVERIFIED')

    def test_velocity_acceleration_uses_actual_sample_intervals(self):
        r = m.declared_checks({'layer_samples': [{'id': 'title', 'samples': [
            {'t': 0, 'x': 0, 'y': 0}, {'t': 1, 'x': 2, 'y': 0}, {'t': 3, 'x': 10, 'y': 0}]}]},
            1080, 1920, 3, 30)['motion_samples']
        self.assertEqual(r[0]['vx_px_s'], 2)
        self.assertEqual(r[1]['vx_px_s'], 4)
        self.assertAlmostEqual(r[1]['ax_px_s2'], 2/1.5)
        with self.assertRaises(ValueError):
            m.declared_checks({'layer_samples': [{'id': 'bad', 'samples': [
                {'t': 1, 'x': 0, 'y': 0}, {'t': 1, 'x': 1, 'y': 1}]}]}, 100, 100, 3, 30)

    def test_nonfinite_and_invalid_times_are_rejected(self):
        with self.assertRaises(ValueError):
            m.declared_checks({'events': [{'id': 'e', 'visual_time': float('nan'), 'audio_time': 1}]},
                              100, 100, 3, 30)
        with self.assertRaises(ValueError):
            m.declared_checks({'safe_rect': [.9, .1, .1, .8]}, 100, 100, 3, 30)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg needed')
    def test_real_media_is_measured_without_observation_or_input_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); v = p/'input.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=64x96:r=30:d=3',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=3',
                            '-c:v', 'libx264', '-c:a', 'aac', '-t', '3', str(v)], check=True)
            old = m.sha(v); manifest = p/'manifest.json'
            manifest.write_text(json.dumps({'video_sha256': old}))
            out = p/'evidence'; r = m.collect(v, out, manifest)
            self.assertEqual(old, m.sha(v))
            self.assertEqual(r['video_sha256'], old)
            self.assertEqual(r['status'], 'PROXY_EVIDENCE_ONLY')
            self.assertFalse(r['observed_audio']); self.assertFalse(r['observed_video'])
            self.assertEqual(r['loudness']['status'], 'MEASURED')
            for name in ('evidence.json', 'first.png', 'last.png', 'contact-sheet.png', 'waveform.png'):
                self.assertTrue((out/name).stat().st_size > 0)
            before = (out/'evidence.json').read_bytes()
            with self.assertRaises(ValueError): m.collect(v, out)
            self.assertEqual(before, (out/'evidence.json').read_bytes())
            manifest.write_text(json.dumps({'video_sha256': '0'*64}))
            with self.assertRaises(ValueError): m.collect(v, p/'stale', manifest)
            self.assertFalse((p/'stale').exists())

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg needed')
    def test_silent_and_no_audio_are_not_reported_as_listened(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); v = p/'no-audio.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=32x48:r=30:d=1',
                            '-c:v', 'libx264', str(v)], check=True)
            r = m.collect(v, p/'no-audio-review')
            self.assertEqual(r['loudness']['status'], 'NO_AUDIO')
            silent = p/'silent.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(v), '-f', 'lavfi', '-i',
                            'anullsrc=r=48000:cl=mono:d=1', '-c:v', 'copy', '-c:a', 'aac',
                            '-t', '1', str(silent)], check=True)
            r = m.collect(silent, p/'silent-review')
            self.assertEqual(r['loudness']['status'], 'UNMEASURABLE')
            self.assertIsNone(r['loudness']['measurements']['input_i'])
            self.assertFalse(r['observed_audio'])


if __name__ == '__main__':
    unittest.main()

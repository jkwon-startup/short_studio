"""로컬 자동 증거 수집. 실제 시청·청취 및 QA PASS를 수행하지 않는다."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import unicodedata


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('유한한 수치가 필요합니다')
    return value


def reading_time(text):
    # NFC 조합한 한글 음절과 나머지 문자 모두 계산; 날짜/영문을 누락하지 않는다.
    count = sum(1 for c in unicodedata.normalize('NFC', text)
                if not c.isspace() and unicodedata.category(c)[0] not in 'PC')
    return count, max(1.0, count / 6 + 0.3)


def declared_checks(manifest, width, height, duration, fps):
    rect = manifest.get('safe_rect')
    if rect is not None:
        if (not isinstance(rect, list) or len(rect) != 4
                or not 0 <= number(rect[0]) < number(rect[2]) <= 1
                or not 0 <= number(rect[1]) < number(rect[3]) <= 1):
            raise ValueError('safe_rect 오류')
    texts = []
    for row in manifest.get('texts', []):
        start, end = number(row['stable_start']), number(row['stable_end'])
        size = number(row['font_px'])
        box = row['bbox']
        if (not 0 <= start < end <= duration + .001 or size <= 0
                or len(box) != 4 or not number(box[0]) < number(box[2])
                or not number(box[1]) < number(box[3])):
            raise ValueError('텍스트 노출/크기/bbox 오류')
        count, minimum = reading_time(row['text'])
        target_ratio = {'headline': .04, 'secondary': .022}.get(row.get('role'), .028)
        inside = (box[0] >= 0 and box[1] >= 0 and box[2] <= width and box[3] <= height)
        safe = (inside and box[0] >= rect[0] * width and box[1] >= rect[1] * height
                and box[2] <= rect[2] * width and box[3] <= rect[3] * height) if rect else None
        texts.append({**row, 'count': count, 'recommended_seconds': round(minimum, 4),
                      'declared_stable_seconds': end-start,
                      'reading_shortfall_seconds': max(0, minimum-(end-start)),
                      'font_height_ratio': size/height, 'recommended_min_ratio': target_ratio,
                      'size_below_recommendation': size/height < target_ratio,
                      'bbox_inside_frame': inside, 'bbox_inside_selected_safe_rect': safe})
    motion = []
    for layer in manifest.get('layer_samples', []):
        samples = layer['samples']
        previous = None
        velocity = None
        for s in samples:
            t, x, y = (number(s[k]) for k in ('t', 'x', 'y'))
            if not 0 <= t <= duration + .001 or previous and t <= previous[0]:
                raise ValueError('레이어 샘플 시간 오류')
            if previous:
                dt = t-previous[0]
                vx, vy = (x-previous[1])/dt, (y-previous[2])/dt
                mid = (t+previous[0])/2
                ax = (vx-velocity[1])/(mid-velocity[0]) if velocity else None
                ay = (vy-velocity[2])/(mid-velocity[0]) if velocity else None
                motion.append({'layer': layer['id'], 'interval_start': previous[0], 'interval_end': t,
                               'midpoint': mid, 'vx_px_s': vx, 'vy_px_s': vy,
                               'speed_px_s': math.hypot(vx, vy), 'ax_px_s2': ax, 'ay_px_s2': ay})
                velocity = (mid, vx, vy)
            previous = (t, x, y)
    events = []
    for e in manifest.get('events', []):
        vt, at = number(e['visual_time']), number(e['audio_time'])
        if not 0 <= vt <= duration + .001 or not 0 <= at <= duration + .001:
            raise ValueError('이벤트 시간 오류')
        events.append({**e, 'audio_minus_visual_seconds': at-vt,
                       'audio_minus_visual_frames': (at-vt)*fps,
                       'outside_two_frame_target': abs(at-vt)*fps > 2})
    return {'provenance': 'AUTHOR_DECLARED_UNVERIFIED', 'text_inventory_completeness': 'NOT_VERIFIED',
            'texts': texts, 'motion_samples': motion, 'events': events,
            'missing': [k for k in ('texts', 'layer_samples', 'events') if not manifest.get(k)],
            'safe_zone_status': 'DECLARED_NOT_PLATFORM_VERIFIED' if rect else 'NOT_PROVIDED'}


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise ValueError('로컬 도구 실패: ' + result.stderr[-1600:])
    return result


def collect(video, output, manifest_path=None):
    video, output = Path(video).resolve(), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('새 출력 폴더가 필요합니다. 기존 증거를 덮어쓰지 않습니다')
    input_sha = sha(video)
    manifest_sha = sha(manifest_path) if manifest_path else None
    manifest = json.loads(Path(manifest_path).read_text()) if manifest_path else {}
    if manifest_path and manifest.get('video_sha256') != input_sha:
        raise ValueError('manifest 영상 SHA가 현재 파일과 다릅니다')
    probe = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                            '-of', 'json', str(video)]).stdout)
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    duration = float(probe['format']['duration'])
    n, d = stream['avg_frame_rate'].split('/')
    fps = float(n)/float(d)
    if not 0 < duration <= 180 or fps <= 0:
        raise ValueError('검수 입력은 유효한 0~180초 영상이어야 합니다')
    checks = declared_checks(manifest, stream['width'], stream['height'], duration, fps)
    output.mkdir(parents=True, exist_ok=False)
    # 실패해도 이 폴더/도구 로그를 보존한다. 성공 패킷은 마지막에만 쓴다.
    (output/'probe.json').write_text(json.dumps(probe, ensure_ascii=False, indent=2)+'\n')
    commands = []
    def execute(args, name):
        cmd = ['ffmpeg', '-hide_banner', '-nostdin', '-n'] + args
        commands.append(cmd)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        (output/(name+'.log')).write_text(result.stderr)
        if result.returncode:
            raise ValueError('증거 수집 실패: '+name+'; 로그 보존: '+str(output))
        return result
    execute(['-v', 'error', '-i', str(video), '-f', 'null', '-'], 'decode')
    step = max(1.0, duration/24)
    count = min(24, max(1, math.ceil(duration/step)))
    execute(['-v', 'error', '-i', str(video), '-vf',
             f'fps=1/{step}:start_time=0:round=down,scale=240:-2,tile=6x4',
             '-frames:v', '1', str(output/'contact-sheet.png')], 'contact-sheet')
    execute(['-v', 'error', '-i', str(video), '-vf', 'scale=480:-2', '-frames:v', '1',
             str(output/'first.png')], 'first')
    execute(['-v', 'error', '-sseof', str(-min(.2, duration)), '-i', str(video), '-vf',
             'reverse,scale=480:-2', '-frames:v', '1', str(output/'last.png')], 'last')
    audio = any(s['codec_type'] == 'audio' for s in probe['streams'])
    loudness = {'status': 'NO_AUDIO'}
    if audio:
        execute(['-v', 'error', '-i', str(video), '-filter_complex',
                 '[0:a:0]aformat=channel_layouts=mono,showwavespic=s=1200x200:colors=white[v]',
                 '-map', '[v]', '-frames:v', '1', str(output/'waveform.png')], 'waveform')
        result = execute(['-i', str(video), '-map', '0:a:0', '-af',
                          'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
                          '-f', 'null', '-'], 'loudness')
        pos = result.stderr.rfind('{')
        data = json.loads(result.stderr[pos:result.stderr.rfind('}')+1])
        measured = {}
        for field in ('input_i', 'input_tp', 'input_lra', 'input_thresh'):
            value = float(data[field])
            measured[field] = value if math.isfinite(value) else None
        loudness = {'status': 'MEASURED' if measured['input_i'] is not None else 'UNMEASURABLE',
                    'measurements': measured, 'raw': data,
                    'note': '입력 측정값만 기록. 원본/음성을 변경하지 않으며 목표 달성·청취 판정이 아니다.'}
    if sha(video) != input_sha or manifest_path and sha(manifest_path) != manifest_sha:
        raise ValueError('수집 중 입력 변경: 증거 STALE; 재실행 필요')
    if checks['motion_samples']:
        with (output/'motion-velocity-acceleration.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(checks['motion_samples'][0]))
            writer.writeheader(); writer.writerows(checks['motion_samples'])
    evidence = {'status': 'PROXY_EVIDENCE_ONLY', 'video': str(video), 'video_sha256': input_sha,
                'manifest_sha256': manifest_sha, 'observed_video': False, 'observed_audio': False,
                'ffmpeg_version': run(['ffmpeg', '-version']).stdout.splitlines()[0],
                'decode': 'SUCCESS', 'duration': duration, 'fps': fps,
                'contact_sheet_nominal_times': [round(i*step, 6) for i in range(count)],
                'sample_note': '약 1초 간격, 최대 24칸. fps 필터 양자화가 있으며 전수 프레임 검사가 아님.',
                'loudness': loudness, 'declared_checks': checks,
                'not_implemented': ['OCR/실제 텍스트 가독성', '자동 오디오 사건 인식', '전수 광과민성 검출',
                                    '플랫폼 실제 UI 가림', '정상 속도 시청/청취·무음 이해·재미 판정'],
                'commands': commands}
    (output/'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    try:
        result = collect(args.video, args.output_dir, args.manifest)
        print(json.dumps({'status': result['status'], 'evidence': str(args.output_dir/'evidence.json')}, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, StopIteration, subprocess.TimeoutExpired) as exc:
        parser.exit(2, 'BLOCKED: '+str(exc)+'\n')


if __name__ == '__main__':
    main()

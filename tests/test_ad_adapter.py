"""기존 Claude 어댑터의 실제 BGM·시제품 추출과 광고 방향 검증."""
from pathlib import Path
import subprocess, unittest

PY=Path('/Library/Frameworks/Python.framework/Versions/3.11/bin/python3')
ROOT=Path(__file__).resolve().parents[1]

CASE=r'''
from pathlib import Path
import array, importlib.util, json, tempfile, sys, wave
root=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location('ad_adapter',root/'scripts/claude_adapters/autopilot.py')
ap=importlib.util.module_from_spec(spec);spec.loader.exec_module(ap)

def blocked(action):
    try:action()
    except ap.Blocked:return
    raise AssertionError('Expected affected stage BLOCKED')

blocked(lambda:ap.voice_fit_factor(35,30))
blocked(lambda:ap.voice_fit_factor(31,30,{'atempo':1.1}))
assert ap.voice_fit_factor(31,30,{'atempo':1.1,'reason':'명시된 호흡/시간 조정'})==1.1
assert ap.voice_fit_factor(23,30)==1.0
blocked(lambda:ap.creative_direction(
    {'creative_direction':{'mode':'motion_graphics','selection_source':'USER_REQUEST'}},
    {'creative_direction':{'mode':'photoreal_ad','selection_source':'DEFAULT'}}))
blocked(lambda:ap.endcard_options({'brand':'ExampleBrand'},{}))
custom={'bg':'#FFFFFF','accent':'#042A24','wordmark_text':'ExampleBrand','slogan':''}
assert ap.endcard_options({'brand':'ExampleBrand'},{'endcard':custom})['wordmark_text']=='ExampleBrand'

with tempfile.TemporaryDirectory(prefix='ad-adapter-technical-test-') as tmp:
    t=Path(tmp);ap.ROOT=t
    w=t/'work/claude-test';w.mkdir(parents=True)
    (w/'brief.json').write_text(json.dumps({'duration':30,'brand':'ExampleBrand','voice_id':'TEST_VOICE_ID'}))
    (w/'plan.json').write_text(json.dumps({'creative_direction':{'mode':'motion_graphics'}}))
    blocked(lambda:ap.Renderer('claude-test'))
    original_sh=ap.sh
    ap.sh=lambda *a,**k: (_ for _ in ()).throw(AssertionError('External call before unsupported-render check'))
    blocked(lambda:ap.cmd_assets('claude-test'))
    ap.sh=original_sh
    # TTS/ASR mock verifies cache identity and preservation; it is not voice quality QA.
    vdir=w/'voice';vdir.mkdir();(vdir/'voice_raw.mp3').write_bytes(b'legacy unbound voice')
    script=w/'script.json';script.write_text(json.dumps({'tts_text':'첫 번째 대본','script_id':'s1'}))
    calls=[]
    def fake_sh(cmd,**kwargs):
        if len(cmd)>1 and str(cmd[1]).endswith('elevenlabs_tts.py'):
            out=Path(cmd[cmd.index('--out')+1]);text=Path(cmd[cmd.index('--text-file')+1]).read_bytes()
            out.write_bytes(b'TTS MOCK:'+text);calls.append(str(out))
        elif cmd[0]=='ffmpeg':
            source=Path(cmd[cmd.index('-i')+1]);Path(cmd[-1]).write_bytes(source.read_bytes())
        elif cmd[0]==ap.WHISPER:
            out=Path(cmd[cmd.index('--output-dir')+1]);out.mkdir(parents=True,exist_ok=True)
            (out/(Path(cmd[1]).stem+'.json')).write_text(json.dumps({'segments':[{'start':0,'end':1,'text':'ASR MOCK'}]}))
        else:raise AssertionError('Unexpected mock operation: '+str(cmd))
        return ''
    original_duration=ap.duration;ap.sh=fake_sh;ap.duration=lambda _:1
    ap.cmd_voice('claude-test');first=(vdir/'voice.mp3').read_bytes()
    ap.cmd_voice('claude-test');assert len(calls)==1
    script.write_text(json.dumps({'tts_text':'수정한 두 번째 대본','script_id':'s2'}))
    ap.cmd_voice('claude-test');assert len(calls)==2
    assert (vdir/'voice.mp3').read_bytes()!=first
    assert any(p.read_bytes()==first for p in (vdir/'selected-history').glob('*/voice.mp3'))
    assert len(list((vdir/'generations').glob('*/voice_raw.mp3')))==2
    assert (vdir/'voice_raw.mp3').read_bytes()==b'legacy unbound voice'
    ap.sh=original_sh;ap.duration=original_duration
    voice=t/'voice.wav';bgm=t/'music.wav'
    ap.sh(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=48000:cl=mono:d=1','-c:a','pcm_s16le',str(voice)])
    ap.sh(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=1','-c:a','pcm_s16le',str(bgm)])
    plain=t/'plain';music=t/'music';plain.mkdir();music.mkdir()
    a=ap.build_audio(plain,voice,[],1)
    b=ap.build_audio(music,voice,[],1,bgm=bgm,bgm_gain_db=-12)
    def energy(path):
        with wave.open(str(path),'rb') as f:
            assert f.getframerate()==48000
            return sum(abs(x) for x in array.array('h',f.readframes(f.getnframes())))
    assert energy(a)==0
    assert energy(b)>0
    assert (music/'audio/bgm_stem.wav').exists()
    assert (music/'audio/voice_stem.wav').exists()
    assert (music/'audio/sfx_stem.wav').exists()
    assert abs(ap.duration(b)-1)<.01
    r=w/'render';r.mkdir()
    video=r/'claude-test_draft.mp4'
    ap.sh(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=16x16:r=30:d=9',
           '-f','lavfi','-i','anullsrc=r=48000:cl=mono:d=9','-c:v','libx264','-c:a','aac','-t','9',str(video)])
    files=ap.cmd_previews('claude-test')
    assert [round(ap.duration(Path(p)),2) for p in files]==[3,8]
print('VOICE_FIT_BRAND_MOTION_BGM_PREVIEWS_OK')
'''

class AdAdapterTests(unittest.TestCase):
    @unittest.skipUnless(PY.is_file(),'Claude adapter Python runtime not installed')
    def test_actual_music_mix_preview_lengths_and_direction_guards(self):
        result=subprocess.run([str(PY),'-c',CASE,str(ROOT)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('VOICE_FIT_BRAND_MOTION_BGM_PREVIEWS_OK',result.stdout)

if __name__=='__main__':unittest.main()

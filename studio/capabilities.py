"""버전·자원 점검. 자격증명·기기 고유 식별자는 수집하지 않는다."""
import importlib.util, json, platform, shutil, subprocess
from pathlib import Path

def inspect(root):
    result={"platform":platform.platform(),"tools":{},"disk_free_bytes":shutil.disk_usage(root).free,"adapters":{}}
    for name,args in {"python3":["--version"],"node":["--version"],"ffmpeg":["-version"],"ffprobe":["-version"],"blender":["--version"],"codex":["--version"]}.items():
        p=shutil.which(name)
        if p:
            x=subprocess.run([p,*args],capture_output=True,text=True,timeout=20)
            result["tools"][name]={"path":p,"version":x.stdout.splitlines()[0] if x.stdout else x.stderr.splitlines()[0],"exit_code":x.returncode}
        else: result["tools"][name]={"status":"BLOCKED"}
    voices=subprocess.run(["say","-v","?"],capture_output=True,text=True,timeout=20)
    result["korean_voices"]=[x.split("#")[0].strip() for x in voices.stdout.splitlines() if "ko_KR" in x]
    gpu=subprocess.run(["system_profiler","SPDisplaysDataType","-json"],capture_output=True,text=True,timeout=30)
    try:
        displays=json.loads(gpu.stdout).get("SPDisplaysDataType",[])
        result["gpu"]=[{k:v for k,v in x.items() if k in ("sppci_model","sppci_cores","spdisplays_metal") } for x in displays]
    except ValueError: result["gpu"]="점검 실패"
    memory=subprocess.run(["sysctl","-n","hw.memsize"],capture_output=True,text=True,timeout=10)
    result["memory_bytes"]=memory.stdout.strip()
    result["remotion_global"]=Path('/opt/homebrew/lib/node_modules/remotion').exists()
    result["python_tts_packages"]={k:importlib.util.find_spec(k) is not None for k in ("TTS","kokoro","piper","edge_tts")}
    result["adapters"]={"ffmpeg":"CONNECTED_LOCAL", "blender":"CONNECTED_LOCAL", "macos_say":"CONNECTED_TECHNICAL_ONLY_LICENSE_PENDING", "remotion":"UNCONNECTED", "image_generation":"INTERACTIVE_ONLY_NO_HEADLESS_ADAPTER", "cloud_tts":"UNCONNECTED_NO_COST_APPROVAL", "codex":"NATIVE_RESEARCH_CALL_VERIFIED_GPT56SOL_PERSISTENT_20261002", "viewer_qa":"HUMAN_OBSERVATION_REQUIRED"}
    return result

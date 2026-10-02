"""공간·가림·카메라·실제 물체 이동 기술시험. 완성 콘텐츠 아님."""
import bpy, math, sys, json
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:];out=Path(args[0]);frames=int(args[1])
if out.exists() and any(p.name != ".fixture.json" for p in out.iterdir()): raise RuntimeError("기존 Blender 결과 덮어쓰기 금지")
if not 1 <= frames <= 360: raise RuntimeError("기술시험 프레임은 1~360")
out.mkdir(parents=True,exist_ok=True)
(out/".fixture.json").write_text(json.dumps({"fixture":True,"quality":"NOT_REVIEWED"}))
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=180;scene.render.resolution_y=320;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.fps=12;scene.frame_start=1;scene.frame_end=frames
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.background_type='WORLD'
scene.world.color=(0.04,0.08,0.07)
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-1));floor=bpy.context.object;floor.name='BACKGROUND';floor.color=(0.05,0.15,0.12,1)
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0));occluder=bpy.context.object;occluder.name='MIDGROUND_OCCLUDER';occluder.scale=(0.3,0.8,2);occluder.color=(0.8,0.8,0.7,1)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5,location=(-2,1,0));ball=bpy.context.object;ball.name='SUBJECT';ball.color=(0.7,0.03,0.04,1)
ball.keyframe_insert(data_path='location',frame=1);ball.location.x=2;ball.keyframe_insert(data_path='location',frame=max(frames,36))
bpy.ops.object.camera_add(location=(5,-8,5));cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=28;scene.camera=cam
cam.keyframe_insert(data_path='location',frame=1);cam.location.x=4;cam.keyframe_insert(data_path='location',frame=max(frames,36))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fixture.blend'))
scene.render.filepath=str(out/'frame-');bpy.ops.render.render(animation=True)

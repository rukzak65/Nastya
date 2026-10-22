"""ПРИКОЛ: лупа ищет на синем фоне, 4K, 6.6 с, 10 поз в секунду.

В Blender: открыть этот текст и запустить. Создаётся отдельная сцена.
Существующие сцены не удаляются. PNG, шрифты и освещение не нужны.
В обычном Python этот файл рендерит MP4 из векторных контуров.
"""
from pathlib import Path
import math
import json
import sys

WIDTH, HEIGHT, FPS, POSE_FPS = 3840, 2160, 30, 10
DURATION, FRAME_COUNT = 6.6, 198
BACKGROUND, FOREGROUND = '0F4AFB', 'FFFEEF'
SCALE = 1.28
ROOT = Path(__file__).resolve().parent if '__file__' in globals() else Path.home()

# Centre of the circular lens. Coordinates reproduce the supplied artwork.
OUTER_RADIUS, INNER_RADIUS = 223, 198
HANDLE = [(66,226),(125,202),(162,340),(132,353)]
DOT = (166,392,31)
# Seconds, centre X, centre Y, clockwise tilt in degrees.
WAYPOINTS = [
    (0.0,-700,1120,-15),(.2,-700,1120,-15),
    (.9,800,990,7),(1.2,900,930,13),(1.4,900,930,6),
    (1.95,1400,650,-12),(2.2,1440,630,-17),(2.4,1440,630,-9),
    (3.0,1920,1190,10),(3.25,1960,1210,17),(3.45,1960,1210,7),
    (4.0,2470,790,-10),(4.25,2510,760,-17),(4.45,2510,760,-8),
    (5.0,3040,1130,8),(5.25,3090,1100,14),(5.4,3090,1100,5),
    (6.0,4500,940,-13),(6.6,4500,940,-13),
]

def pose(seconds):
    for a,b in zip(WAYPOINTS,WAYPOINTS[1:]):
        if a[0]<=seconds<=b[0]:
            p=(seconds-a[0])/(b[0]-a[0])
            p=p*p*(3-2*p)
            return tuple(a[j]+(b[j]-a[j])*p for j in (1,2,3))
    return WAYPOINTS[-1][1:]

def outline_points(radius, count=256, center=(0,0)):
    return [(center[0]+radius*math.cos(2*math.pi*i/count),
             center[1]+radius*math.sin(2*math.pi*i/count)) for i in range(count)]

def build_blender():
    import bpy
    scene=bpy.data.scenes.new('ПРИКОЛ — Лупа ищет')
    bpy.context.window.scene=scene
    engines={item.identifier for item in scene.render.bl_rna.properties['engine'].enum_items}
    scene.render.engine=next(name for name in ('BLENDER_EEVEE_NEXT','BLENDER_EEVEE','CYCLES') if name in engines)
    scene.render.resolution_x=WIDTH;scene.render.resolution_y=HEIGHT
    scene.render.resolution_percentage=100
    scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=FRAME_COUNT
    scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard'
    scene.view_settings.look='None'
    scene.view_settings.exposure=0;scene.view_settings.gamma=1
    if hasattr(scene.render,'use_motion_blur'):scene.render.use_motion_blur=False
    def rgb(value):
        srgb=[int(value[i:i+2],16)/255 for i in (0,2,4)]
        return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in srgb)+(1,)
    def material(name,value):
        mat=bpy.data.materials.new(name);mat.diffuse_color=rgb(value);mat.use_nodes=True
        nodes=mat.node_tree.nodes;nodes.clear()
        em=nodes.new('ShaderNodeEmission');em.inputs['Color'].default_value=rgb(value)
        out=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(em.outputs[0],out.inputs[0])
        return mat
    blue=material('Синий — 0F4AFB',BACKGROUND)
    cream=material('Белый — FFFEEF',FOREGROUND)
    def mesh(name,points,faces,mat,parent=None):
        data=bpy.data.meshes.new(name);data.from_pydata(points,[],faces);data.update()
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
        obj.data.materials.append(mat);obj.parent=parent
        return obj
    mesh('Прямоугольник — фон',[(-30,-20,-.1),(30,-20,-.1),(30,20,-.1),(-30,20,-.1)],[(0,1,2,3)],blue)
    controller=bpy.data.objects.new('Лупа — движение',None);scene.collection.objects.link(controller)
    def local(points):return [(x*SCALE/100,-y*SCALE/100,0) for x,y in points]
    count=256
    points=outline_points(OUTER_RADIUS,count)+outline_points(INNER_RADIUS,count)
    faces=[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    mesh('Окружность',local(points),faces,cream,controller)
    mesh('Четырёхугольник — ручка',local(HANDLE),[(0,1,2,3)],cream,controller)
    mesh('Круг — точка',local(outline_points(DOT[2],128,DOT[:2])),[tuple(range(128))],cream,controller)
    for index in range(FRAME_COUNT//3):
        x,y,angle=pose(index/POSE_FPS)
        controller.location=((x-WIDTH/2)/100,(HEIGHT/2-y)/100,0)
        controller.rotation_euler=(0,0,-math.radians(angle))
        for prop in ('location','rotation_euler'):controller.keyframe_insert(data_path=prop,frame=index*3+1)
    ad=controller.animation_data
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    bag=action_get_channelbag_for_slot(ad.action,ad.action_slot)
    for curve in bag.fcurves:
        for key in curve.keyframe_points:key.interpolation='CONSTANT'
    data=bpy.data.cameras.new('Камера');camera=bpy.data.objects.new('Камера',data)
    scene.collection.objects.link(camera);camera.location=(0,0,30);camera.rotation_euler=(0,0,0)
    data.type='ORTHO';data.ortho_scale=WIDTH/100;scene.camera=camera
    scene.render.image_settings.media_type='VIDEO'
    scene.render.image_settings.file_format='FFMPEG'
    scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
    scene.render.ffmpeg.constant_rate_factor='HIGH'
    scene.render.filepath='//prikol_magnifier_intro_4k.mp4'
    scene['background_hex']=BACKGROUND;scene['pose_fps']=POSE_FPS
    scene.frame_set(1)
    if '--save-blend' in sys.argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'prikol_magnifier_intro.blend'),compress=True)
    print('BLENDER_SCENE_READY',flush=True)

def render_video():
    import subprocess
    sys.path.insert(0,'/tmp/prikol-logo-lib')
    import aggdraw
    from PIL import Image
    ROOT.mkdir(exist_ok=True,parents=True)
    def render(index):
        ss=2
        im=Image.new('RGB',(WIDTH*ss,HEIGHT*ss),'#'+BACKGROUND)
        x,y,angle=pose(index/POSE_FPS)
        c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
        def polygon(points):
            path=aggdraw.Path()
            for j,(px,py) in enumerate(points):
                tx=(x+SCALE*(c*px-s*py))*ss
                ty=(y+SCALE*(s*px+c*py))*ss
                (path.moveto if j==0 else path.lineto)(tx,ty)
            path.close();return path
        draw=aggdraw.Draw(im)
        # Exact circles, with cubic Bezier edges, rotated rigidly as one symbol.
        def ellipse(cx,cy,r,color):
            k=.5522847498307936
            raw=[('M',cx+r,cy),('C',cx+r,cy+k*r,cx+k*r,cy+r,cx,cy+r),
                 ('C',cx-k*r,cy+r,cx-r,cy+k*r,cx-r,cy),
                 ('C',cx-r,cy-k*r,cx-k*r,cy-r,cx,cy-r),
                 ('C',cx+k*r,cy-r,cx+r,cy-k*r,cx+r,cy)]
            path=aggdraw.Path()
            for cmd in raw:
                pts=[]
                for j in range(1,len(cmd),2):
                    px,py=cmd[j:j+2]
                    pts.extend(((x+SCALE*(c*px-s*py))*ss,(y+SCALE*(s*px+c*py))*ss))
                (path.moveto if cmd[0]=='M' else path.curveto)(*pts)
            path.close();draw.path(path,aggdraw.Brush('#'+color))
        ellipse(0,0,OUTER_RADIUS,FOREGROUND)
        ellipse(0,0,INNER_RADIUS,BACKGROUND)
        draw.path(polygon(HANDLE),aggdraw.Brush('#'+FOREGROUND))
        ellipse(*DOT,FOREGROUND)
        draw.flush()
        return im.resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
    output=ROOT/'prikol_magnifier_intro_4k.mp4'
    command=['ffmpeg','-hide_banner','-loglevel','warning','-y','-f','rawvideo',
             '-pixel_format','rgb24','-video_size',f'{WIDTH}x{HEIGHT}','-framerate',str(FPS),'-i','-','-an',
             '-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709,setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709',
             '-c:v','libx264','-threads','2','-preset','slow','-crf','10','-pix_fmt','yuv420p','-profile:v','high',
             '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv',
             '-movflags','+faststart',str(output)]
    poses=[];contact=Image.new('RGB',(1920,1620))
    with (ROOT/'encode.log').open('w') as log:
        proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        try:
            for index in range(FRAME_COUNT//3):
                im=render(index)
                if index in (0,9,22,32,42,63):
                    im.save(ROOT/f'pose_{index:03d}.png')
                    j=(0,9,22,32,42,63).index(index)
                    contact.paste(im.resize((960,540),Image.Resampling.LANCZOS),((j%2)*960,(j//2)*540))
                data=im.tobytes()
                for _ in range(3):proc.stdin.write(data)
                poses.append({'frame':index*3+1,'pose':list(pose(index/POSE_FPS))})
                if index%10==0:print('POSE',index+1,'/',FRAME_COUNT//3,flush=True)
        finally:proc.stdin.close()
        if proc.wait():raise RuntimeError((ROOT/'encode.log').read_text())
    contact.save(ROOT/'contact_sheet.png')
    (ROOT/'timing.json').write_text(json.dumps({'width':WIDTH,'height':HEIGHT,'fps':FPS,'pose_fps':POSE_FPS,
        'duration':DURATION,'frames':FRAME_COUNT,'background':BACKGROUND,'foreground':FOREGROUND,'poses':poses},indent=2))
    print('VIDEO_CREATED',output.stat().st_size,flush=True)

if __name__=='__main__':
    try:import bpy
    except ImportError:render_video()
    else:build_blender()

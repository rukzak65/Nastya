"""Черепаха-брелок: реконструкция по двум скриншотам.
Blender: Скриптинг → Создать → вставить код → Alt/Option + P.
Создаёт отдельную сцену; фотографии и сторонние библиотеки не нужны.
"""
import bpy
import bmesh
import math
import os
import random
from mathutils import Vector


def build_turtle():
    scene=bpy.data.scenes.new('Черепаха — реконструкция по референсу')
    if bpy.context.window:
        bpy.context.window.scene=scene
    collection=bpy.data.collections.new('Черепаха — все детали')
    scene.collection.children.link(collection)
    root=bpy.data.objects.new('Черепаха — модель',None)
    collection.objects.link(root)
    rng=random.Random(37)
    model=[]

    def rgba(hex_color):
        c=[int(hex_color[i:i+2],16)/255 for i in (0,2,4)]
        return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)+(1,)

    def material(name,color,metal=.75,rough=.46):
        mat=bpy.data.materials.new(name)
        mat.diffuse_color=rgba(color)
        mat.use_nodes=True
        nt=mat.node_tree;nt.nodes.clear()
        shader=nt.nodes.new('ShaderNodeBsdfPrincipled')
        shader.inputs['Base Color'].default_value=rgba(color)
        shader.inputs['Metallic'].default_value=metal
        shader.inputs['Roughness'].default_value=rough
        out=nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(shader.outputs['BSDF'],out.inputs['Surface'])
        return mat

    silver=material('Серый металл','858C96',.72,.46)
    dark=material('Тёмный боковой металл','474A4C',.65,.49)
    edge=material('Светлая грань металла','A0A3A5',.72,.40)
    facets=[silver,material('Холодная грань','78828E',.72,.46),edge]
    teal=[material('Бирюза','369D96',.10,.50),
          material('Бирюза — тёмная грань','318F8B',.10,.51),
          material('Бирюза — светлая грань','41AAA0',.10,.48)]

    def mesh(name,verts,faces,mats,part=None,indices=None):
        data=bpy.data.meshes.new(name+' — сетка')
        data.from_pydata(verts,[],faces);data.update()
        for mat in mats:data.materials.append(mat)
        if indices:
            for poly,idx in zip(data.polygons,indices):poly.material_index=idx
        bm=bmesh.new();bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(data);bm.free();data.update()
        obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
        if part:
            obj.parent=root;obj['turtle_part']=part;model.append(obj)
        return obj

    def bezier(segments,steps=10):
        pts=[]
        for a,b,c,d in segments:
            for i in range(steps):
                t=i/steps;u=1-t
                pts.append((u*u*u*a[0]+3*u*u*t*b[0]+3*u*t*t*c[0]+t*t*t*d[0],
                            u*u*u*a[1]+3*u*u*t*b[1]+3*u*t*t*c[1]+t*t*t*d[1]))
        return pts

    def area(poly):
        return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))/2

    def ccw(poly):
        return poly if area(poly)>0 else list(reversed(poly))

    def loft(name,outline,levels,part,center=None,facet_top=False):
        outline=ccw(list(outline));n=len(outline)
        cx,cy=center or (sum(p[0] for p in outline)/n,sum(p[1] for p in outline)/n)
        verts=[(cx+(x-cx)*s,cy+(y-cy)*s,z) for s,z in levels for x,y in outline]
        faces=[tuple(reversed(range(n)))];ids=[1]
        for k in range(len(levels)-1):
            for i in range(n):
                j=(i+1)%n
                faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
                ids.append(1 if k==0 else (2 if k==1 else 0))
        last=(len(levels)-1)*n
        if facet_top:
            center_id=len(verts);verts.append((cx,cy,levels[-1][1]+.015))
            for i in range(n):
                faces.append((last+i,last+(i+1)%n,center_id));ids.append(rng.choice((0,0,3,4)))
        else:
            faces.append(tuple(last+i for i in range(n)));ids.append(0)
        return mesh(name,verts,faces,[silver,dark,edge,facets[1],facets[2]],part,ids)

    outline=ccw(bezier([
        ((0,1.43),(.55,1.46),(.91,1.10),(.89,.63)),
        ((.89,.63),(.91,-.12),(.45,-1.22),(0,-1.43)),
        ((0,-1.43),(-.45,-1.22),(-.91,-.12),(-.89,.63)),
        ((-.89,.63),(-.91,1.10),(-.55,1.46),(0,1.43)),
    ],12))
    n=len(outline)
    # Выпуклый гранёный корпус с тёмной нижней стенкой.
    radii=(1,.94,.84,.72,.58,.42,.24)
    profile=((0,.70),(.24,.68),(.42,.64),(.58,.58),(.72,.51),(.84,.44),(.94,.35),(1,.23))

    def height_r(r):
        r=max(0,min(1,r))
        for (a,za),(b,zb) in zip(profile,profile[1:]):
            if r<=b:return za+(zb-za)*(r-a)/(b-a)
        return .23

    def gauge(x,y):
        result=0
        for a,b in zip(outline,outline[1:]+outline[:1]):
            nx,ny=b[1]-a[1],a[0]-b[0]
            d=nx*a[0]+ny*a[1]
            if d>1e-9:result=max(result,(nx*x+ny*y)/d)
        return result

    def z_surface(x,y):return height_r(gauge(x,y))

    verts=[(x,y,.035) for x,y in outline]
    verts += [(x*r,y*r,height_r(r)) for r in radii for x,y in outline]
    faces=[tuple(reversed(range(n)))];ids=[1]
    for k in range(len(radii)):
        for i in range(n):
            j=(i+1)%n
            faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i));ids.append(1 if k==0 else 0)
    center_id=len(verts);verts.append((0,0,height_r(0)))
    last=len(radii)*n
    for i in range(n):faces.append((last+i,last+(i+1)%n,center_id));ids.append(0)
    mesh('Панцирь — сужение к хвосту',verts,faces,[silver,dark],'shell',ids)

    # Каждая бирюзовая вставка — отдельный закрытый гранёный камень.
    domain=ccw([(x*.70,y*.81) for x,y in outline])

    def clip(poly,boundary):
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):
            source=poly;poly=[]
            if not source:break
            def side(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
            previous=source[-1];dp=side(previous)
            for current in source:
                dc=side(current)
                if (dc>=-1e-9)!=(dp>=-1e-9):
                    t=dp/(dp-dc)
                    poly.append((previous[0]+t*(current[0]-previous[0]),previous[1]+t*(current[1]-previous[1])))
                if dc>=-1e-9:poly.append(current)
                previous,dp=current,dc
        clean=[]
        for p in poly:
            if not clean or math.dist(p,clean[-1])>1e-6:clean.append(p)
        if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-6:clean.pop()
        return ccw(clean) if len(clean)>2 else []

    h=.32-.075/math.sqrt(2)
    count=0
    for i in range(-5,6):
        for j in range(-5,6):
            x,y=(i+j)*.32,(i-j)*.32+.04
            diamond=ccw([(x,y+h),(x+h,y),(x,y-h),(x-h,y)])
            poly=clip(domain,diamond)
            if len(poly)<3 or abs(area(poly))<.008:continue
            count+=1;m=len(poly)
            cx=sum(p[0] for p in poly)/m;cy=sum(p[1] for p in poly)/m
            vs=[(px,py,z_surface(px,py)-.012) for px,py in poly]
            vs += [(px,py,z_surface(px,py)+.018) for px,py in poly]
            vs += [(cx+(px-cx)*.61,cy+(py-cy)*.61,
                    z_surface(cx+(px-cx)*.61,cy+(py-cy)*.61)+.045) for px,py in poly]
            fs=[tuple(reversed(range(m)))];mi=[0]
            for k in (0,1):
                for t in range(m):
                    u=(t+1)%m;fs.append((k*m+t,k*m+u,(k+1)*m+u,(k+1)*m+t));mi.append(rng.randrange(3))
            center=len(vs);vs.append((cx,cy,z_surface(cx,cy)+.055))
            for t in range(m):fs.append((2*m+t,2*m+(t+1)%m,center));mi.append(rng.choice((0,0,1,2)))
            mesh('Бирюзовая вставка %02d'%count,vs,fs,teal,'inlay',mi)

    front=bezier([
        ((-.76,.85),(-1.00,1.26),(-1.37,1.53),(-1.69,1.36)),
        ((-1.69,1.36),(-1.87,1.27),(-1.98,.96),(-1.84,.86)),
        ((-1.84,.86),(-1.65,.85),(-1.42,1.01),(-.76,.85)),
    ],6)
    rear=bezier([
        ((-.32,-1.08),(-.60,-.82),(-1.05,-.85),(-1.15,-1.11)),
        ((-1.15,-1.11),(-1.25,-1.32),(-1.11,-1.61),(-.98,-1.40)),
        ((-.98,-1.40),(-.85,-1.21),(-.64,-1.18),(-.32,-1.08)),
    ],6)
    for label,shape in (('Передний',front),('Задний',rear)):
        for sign,side in ((1,'левый'),(-1,'правый')):
            shape2=[(x*sign,y) for x,y in shape]
            loft(label+' '+side+' ласт',shape2,[(1,.035),(1,.16),(.96,.205),(.72,.30)],'flipper',facet_top=True)

    neck=[(-.33,1.27),(.33,1.27),(.33,1.72),(-.33,1.72)]
    loft('Шея — соединительная перемычка',neck,[(1,.09),(1,.24)],'neck')
    head=bezier([
        ((0,2.64),(.20,2.49),(.49,2.25),(.48,2.03)),
        ((.48,2.03),(.47,1.77),(.24,1.65),(0,1.65)),
        ((0,1.65),(-.24,1.65),(-.47,1.77),(-.48,2.03)),
        ((-.48,2.03),(-.49,2.25),(-.20,2.49),(0,2.64)),
    ],7)
    loft('Голова — каплевидная',head,[(1,.10),(1,.27),(.91,.40),(.78,.48)],'head',center=(0,2.08))

    def ico(name,center,scale,part,mat=teal[0]):
        bm=bmesh.new();bmesh.ops.create_icosphere(bm,subdivisions=2,radius=1)
        for v in bm.verts:v.co=Vector((v.co.x*scale[0]+center[0],v.co.y*scale[1]+center[1],v.co.z*scale[2]+center[2]))
        data=bpy.data.meshes.new(name+' — сетка');bm.to_mesh(data);bm.free()
        data.materials.append(mat)
        obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
        obj.parent=root;obj['turtle_part']=part;model.append(obj)
        return obj

    for sign,side in ((-1,'Левый'),(1,'Правый')):
        ico(side+' бирюзовый глаз',(sign*.49,2.17,.29),(.105,.115,.13),'eye')

    def torus(name,center,radius,tube,part,vertical=False):
        verts=[];faces=[];nu,nv=32,8
        for i in range(nu):
            a=2*math.pi*i/nu
            for j in range(nv):
                b=2*math.pi*j/nv
                x=(radius+tube*math.cos(b))*math.cos(a)
                y=(radius+tube*math.cos(b))*math.sin(a)
                z=tube*math.sin(b)
                if vertical:x,z=z,-x
                verts.append((x+center[0],y+center[1],z+center[2]))
        for i in range(nu):
            for j in range(nv):
                faces.append((i*nv+j,((i+1)%nu)*nv+j,((i+1)%nu)*nv+(j+1)%nv,i*nv+(j+1)%nv))
        return mesh(name,verts,faces,[silver],part)

    torus('Нижнее звено — горизонтальное',(0,2.91,.28),.275,.057,'chain')
    torus('Верхнее звено — вертикальное',(0,3.32,.28),.275,.057,'chain',True)
    # Плоская металлическая шайба, а не круглый в сечении тор.
    profile_ring=[(.59,.27),(.59,.09),(.63,.045),(.95,.045),
                  (1,.10),(1,.27),(.95,.34),(.63,.34)]
    verts=[];faces=[];ids=[];segments=48
    for r,z in profile_ring:
        for i in range(segments):
            a=2*math.pi*i/segments;verts.append((r*math.cos(a),4.56+r*math.sin(a),z))
    for k in range(len(profile_ring)):
        for i in range(segments):
            j=(i+1)%segments;l=(k+1)%len(profile_ring)
            faces.append((k*segments+i,k*segments+j,l*segments+j,l*segments+i));ids.append(1 if k in (0,1,2,3,4) else 0)
    mesh('Большое кольцо — шайба с отверстием',verts,faces,[silver,dark],'washer',ids)
    for i in range(20):
        a=2*math.pi*i/20
        ico('Бирюзовая бусина %02d'%(i+1),(1.0*math.cos(a),4.56+1.0*math.sin(a),.18),(.105,.105,.105),'bead')

    floor=material('Фон студии','363A3E',0,.82)
    mesh('Фон студии',[(-100,-100,-.025),(100,-100,-.025),(100,100,-.025),(-100,100,-.025)],[(0,1,2,3)],[floor])
    world=bpy.data.worlds.new('Нейтральное студийное окружение');world.use_nodes=True
    nt=world.node_tree;nt.nodes.clear()
    background=nt.nodes.new('ShaderNodeBackground');background.inputs[0].default_value=(.34,.37,.42,1);background.inputs[1].default_value=.60
    output=nt.nodes.new('ShaderNodeOutputWorld');nt.links.new(background.outputs[0],output.inputs[0]);scene.world=world

    def look(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    for name,pos,power,size,color in (
        ('Большой мягкий свет',(-3,2,8),650,5,(.91,.95,1)),
        ('Заполняющий свет',(5,-1,5),420,4,(1,.96,.89)),
        ('Свет над кольцом',(1,7,6),450,4,(.93,1,1)),
    ):
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.location=pos;look(obj,(0,1.9,.2))

    scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    bpy.context.view_layer.update()
    def camera(name,pos,top=False):
        data=bpy.data.cameras.new(name);data.type='ORTHO';data.clip_start=.01;data.clip_end=300
        obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.location=pos
        look(obj,(0,2.0,.25))
        bpy.context.view_layer.update()
        local=[obj.matrix_world.inverted()@(o.matrix_world@Vector(corner)) for o in model for corner in o.bound_box]
        x0,x1=min(v.x for v in local),max(v.x for v in local)
        y0,y1=min(v.y for v in local),max(v.y for v in local)
        q=obj.rotation_euler.to_quaternion()
        obj.location += q@Vector(((x0+x1)/2,(y0+y1)/2,0))
        data.ortho_scale=max(x1-x0,(y1-y0)*1.6)*1.12
        return obj
    angle=camera('Камера — объёмный ракурс',(-7.6,-8.7,10))
    top=camera('Камера — вид сверху',(0,2.0,15))
    scene.camera=angle;scene['camera_angle']=angle.name;scene['camera_top']=top.name
    scene.render.engine='CYCLES';scene.cycles.samples=64
    scene.cycles.use_denoising=False;scene.cycles.use_preview_denoising=False
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    scene.view_settings.exposure=0;scene.view_settings.gamma=1
    scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG'
    if hasattr(scene.render.image_settings,'media_type'):scene.render.image_settings.media_type='IMAGE'
    scene.render.image_settings.color_mode='RGB'
    scene.render.filepath=os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.path.expanduser('~/Desktop'),'turtle_reference.png')
    if hasattr(scene.render,'use_motion_blur'):scene.render.use_motion_blur=False
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type=='VIEW_3D':
                    space.shading.type='MATERIAL';space.shading.use_scene_world=False;space.shading.use_scene_lights=False
                    space.use_local_camera=False;space.camera=angle;space.region_3d.view_perspective='CAMERA'
    bpy.context.view_layer.update()
    print('Черепаха создана. Камеры: объёмный ракурс и вид сверху. Бирюзовых вставок:',count)
    return scene


if __name__=='__main__':
    build_turtle()

"""Run in the supplied box .blend. Creates a separate, self-contained promo scene."""
import bpy
import math
from mathutils import Vector

WIDTH, HEIGHT, FPS, POSE_FPS = 3840, 2160, 30, 10
DURATION = 8


def rgba(value):
    c = [int(value[i:i+2], 16)/255 for i in (0, 2, 4)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in c)+(1,)


def constant_keys(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    if hasattr(ad.action, 'fcurves'):
        curves = ad.action.fcurves
    else:
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
        bag = action_get_channelbag_for_slot(ad.action, ad.action_slot)
        curves = bag.fcurves if bag else []
    for curve in curves:
        for key in curve.keyframe_points:
            key.interpolation = 'CONSTANT'


def build(top_down=False):
    source = next((s for s in bpy.data.scenes if any(
        o.type == 'MESH' and o.name.startswith('ПРИКОЛ — 10.png')
        for o in s.objects)), None)
    if source is None:
        raise RuntimeError('Открой присланный файл с коробкой и картами.')
    panels = [o for o in source.objects if o.type == 'MESH'
              and o.data.uv_layers.get('OutsideUV')]
    source_cards = [o for o in source.objects if o.type == 'MESH'
                    and o.data.uv_layers.get('FrontUV')]
    assert len(panels) == 14 and len(source_cards) >= 2

    scene = bpy.data.scenes.new('ПРИКОЛ — '+('строго сверху' if top_down else 'наклонный ракурс')+' — картон')
    scene['top_down'] = top_down
    for workspace in bpy.data.workspaces:
        workspace.use_pin_scene = False
    for window in bpy.context.window_manager.windows:
        window.scene = scene
    scene['source_scene'] = source.name
    scene['pose_fps'] = POSE_FPS
    collection = bpy.data.collections.new('Коробка и карты')
    scene.collection.children.link(collection)

    def object(name, data=None):
        o = bpy.data.objects.new(name, data)
        collection.objects.link(o)
        return o

    move = object('Коробка — въезд по дуге')
    move.empty_display_size = .02
    old_hinges = {p.parent for p in panels if p.parent and
                  p.parent.name.startswith('Открывание')}
    copied = {}
    for old in [*old_hinges, *panels]:
        new = old.copy()
        if old.type == 'MESH':
            new.data = old.data.copy()
        new.animation_data_clear()
        collection.objects.link(new)
        copied[old] = new
    for old, new in copied.items():
        new.parent = copied.get(old.parent, move)
        if new.type == 'EMPTY':
            new.rotation_euler = (0, 0, 0)

    def hinge(prefix):
        return copied[next(p for p in panels if p.name.startswith(prefix))].parent

    lid, left, right = hinge('Крышка.'), hinge('Левая створка.'), hinge('Правая створка.')
    lid_panel = copied[next(p for p in panels if p.name.startswith('Крышка.'))]

    # Preserve the supplied UV artwork, while reducing lighting washout.
    materials = {}
    def copy_material(original):
        if original not in materials:
            m = original.copy()
            materials[original] = m
            m.name = original.name + ' — промо правил'
            if m.node_tree:
                nt = m.node_tree
                shader = next((n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'),None)
                if shader:
                    color = shader.inputs['Base Color']
                    base = color.links[0].from_socket if color.is_linked else None
                    # Deterministic, mild face shading keeps the artwork saturated
                    # and avoids grain or denoising blur on the small rules text.
                    geometry = nt.nodes.new('ShaderNodeNewGeometry')
                    dot = nt.nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT'
                    nt.links.new(geometry.outputs['Normal'],dot.inputs[0])
                    nt.links.new(geometry.outputs['Incoming'],dot.inputs[1])
                    absolute = nt.nodes.new('ShaderNodeMath');absolute.operation='ABSOLUTE'
                    nt.links.new(dot.outputs['Value'],absolute.inputs[0])
                    shade = nt.nodes.new('ShaderNodeMath');shade.operation='MULTIPLY_ADD'
                    shade.inputs[1].default_value=.20;shade.inputs[2].default_value=.80
                    nt.links.new(absolute.outputs[0],shade.inputs[0])
                    multiply = nt.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY'
                    multiply.inputs[0].default_value=1
                    if base:nt.links.new(base,multiply.inputs[1])
                    else:multiply.inputs[1].default_value=color.default_value
                    nt.links.new(shade.outputs[0],multiply.inputs[2])
                    emission = nt.nodes.new('ShaderNodeEmission')
                    nt.links.new(multiply.outputs[0],emission.inputs['Color'])
                    output = next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
                    nt.links.new(emission.outputs[0],output.inputs['Surface'])
        return materials[original]

    for panel in copied.values():
        if panel.type == 'MESH':
            for slot in panel.material_slots:
                slot.material = copy_material(slot.material)

    # A real 30-card stack remains inside the box throughout the shot.
    backs = [next(c for c in source_cards if c.name.startswith(prefix))
             for prefix in ('ПРИКОЛ — 10.png', 'БРИФ — 20.png')]
    for i in range(30):
        original = backs[0 if i == 29 else i % 2]
        card = original.copy()
        card.data = original.data.copy()
        card.animation_data_clear()
        card.name = 'Карта в стопке %02d' % (i+1)
        collection.objects.link(card)
        card.parent = move
        card.location = (.042, .062, .0009+i*.00045)
        card.rotation_euler = (0, 0, 0)
        card.hide_render = False
        card['inside_stack'] = True
        for slot in card.material_slots:
            slot.material = copy_material(slot.material)

    def emission_material(name, color):
        m = bpy.data.materials.new(name)
        m.diffuse_color = rgba(color)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        e = nt.nodes.new('ShaderNodeEmission')
        e.inputs['Color'].default_value = rgba(color)
        output = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(e.outputs[0], output.inputs['Surface'])
        return m

    def plane(name, x0, x1, y0, y1, z, mat):
        data = bpy.data.meshes.new(name)
        data.from_pydata([(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)],[],[(0,1,2,3)])
        data.materials.append(mat)
        data.update()
        return object(name, data)

    floor = plane('Фон FFFEEF', -10, 10, -10, 10, -.001,
                  emission_material('Фон — FFFEEF', 'FFFEEF'))
    shadow_mat = emission_material('Мягкая контактная тень', 'FFFEEF')
    nt = shadow_mat.node_tree
    tex = nt.nodes.new('ShaderNodeTexCoord')
    distance = nt.nodes.new('ShaderNodeVectorMath')
    distance.operation = 'DISTANCE'
    distance.inputs[1].default_value = (.5,.5,0)
    nt.links.new(tex.outputs['UV'],distance.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .10
    ramp.color_ramp.elements[0].color = tuple(v*.88 for v in rgba('FFFEEF')[:3])+(1,)
    ramp.color_ramp.elements[1].position = .49
    ramp.color_ramp.elements[1].color = rgba('FFFEEF')
    ramp.color_ramp.interpolation = 'EASE'
    nt.links.new(distance.outputs['Value'],ramp.inputs[0])
    nt.links.new(ramp.outputs['Color'],next(n for n in nt.nodes if n.type=='EMISSION').inputs['Color'])
    shadow = plane('Контактная тень', .042-.105,.042+.105,.062-.125,.062+.125,-.0008,shadow_mat)
    shadow.parent = move
    uv = shadow.data.uv_layers.new(name='UVMap')
    for loop, coord in zip(uv.data,((0,0),(1,0),(1,1),(0,1))):
        loop.uv = coord

    world = bpy.data.worlds.new('Нейтральный студийный свет')
    world.use_nodes = True
    world.node_tree.nodes.clear()
    background = world.node_tree.nodes.new('ShaderNodeBackground')
    background.inputs[0].default_value = (1,1,1,1)
    background.inputs[1].default_value = .15
    output = world.node_tree.nodes.new('ShaderNodeOutputWorld')
    world.node_tree.links.new(background.outputs[0],output.inputs[0])
    scene.world = world

    def look(o, point):
        o.rotation_euler = (Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()

    for name, position, power, size in (
        ('Свет сверху',(-.16,.12,.55),5,.40),
        ('Мягкий заполняющий свет',(.22,-.12,.38),2,.35),
    ):
        data = bpy.data.lights.new(name,'AREA')
        data.energy, data.size = power, size
        light = object(name,data)
        light.location = position
        look(light,(0,0,.03))

    data = bpy.data.cameras.new('Камера — приближение к правилам')
    data.type = 'ORTHO' if top_down else 'PERSP'
    data.lens = 50
    data.clip_start, data.clip_end = .001, 100
    data.dof.use_dof = False
    camera = object(data.name,data)
    scene.camera = camera
    start_target = Vector((0,0,.012))
    start_position = Vector((0,0,.6)) if top_down else Vector((.20,.27,.32))
    start_offset = start_position-start_target
    camera.location = start_position
    if top_down:camera.rotation_euler=(0,0,math.pi)
    else:look(camera,start_target)
    q = camera.rotation_euler.to_quaternion()
    screen_right = q@Vector((1,0,0))
    ground_up = q@Vector((0,1,0))
    ground_up.z = 0
    ground_up.normalize()
    softbox = object('Скользящий софтбокс — отражение ламинации')
    softbox.empty_display_size = .015

    def ease(t):
        t = max(0,min(1,t))
        return t*t*(3-2*t)

    for pose in range(DURATION*POSE_FPS+1):
        t = pose/POSE_FPS
        entry = ease(t/1.6)
        arc = entry*math.pi/2
        offset = screen_right*(-.28+.28*math.sin(arc)) + ground_up*(-.18*math.cos(arc))
        move.location = Vector((-.042,-.062,0))+offset
        move.rotation_euler = (0,0,math.radians(-28*(1-entry)))
        # The lid clears 90 degrees before either inner flap starts moving.
        # Its remaining opening continues during the main camera push-in.
        angle = (95*ease((t-2)/1.2) if t<=3.2
                 else 95+(85 if top_down else 20)*ease((t-3.2)/1.4))
        lid.rotation_euler = (math.radians(angle),0,0)
        # The upper flap lifts first; the lower one follows after it clears.
        left.rotation_euler = (0,math.radians(-185)*ease((t-3.2)/.6),0)
        right.rotation_euler = (0,math.radians(185)*ease((t-3.5)/.6),0)
        bpy.context.view_layer.update()
        lid_center = lid_panel.matrix_world@Vector((.042,.062,0))
        zoom = (.35*ease((t-2)/1.8) if t<=3.8
                else .35+.65*ease((t-3.8)/1.2))
        target = start_target.lerp(lid_center,zoom)
        if top_down:
            camera.location=(target.x,target.y,.6)
            camera.rotation_euler=(0,0,math.pi)
            data.ortho_scale=.43+(.25-.43)*zoom
            data.keyframe_insert(data_path='ortho_scale',frame=1+pose*(FPS//POSE_FPS))
        else:
            end_normal = Vector((0,math.sin(math.radians(115)),-math.cos(math.radians(115))))
            camera.location = target+start_offset.lerp(end_normal*.355,zoom)
            look(camera,target)
        # A reflected strip light follows the lid. Its reflection travels across
        # the print during the move and settles before the final reading hold.
        normal = (lid_panel.matrix_world.to_3x3() @ Vector((0,0,1))).normalized()
        view = (camera.location-lid_center).normalized()
        if normal.dot(view)<0: normal.negate()
        reflected = 2*normal.dot(view)*normal-view
        tangent = (lid_panel.matrix_world.to_3x3() @ Vector((1,0,0))).normalized()
        scan = .065*math.cos(2*math.pi*min(t,5)/3)*(1-.7*ease((t-4)/1))
        softbox.location = lid_center + reflected*.22 + tangent*scan
        frame = 1+pose*(FPS//POSE_FPS)
        for o in (move,lid,left,right,camera,softbox):
            o.keyframe_insert(data_path='location',frame=frame)
            o.keyframe_insert(data_path='rotation_euler',frame=frame)
    for o in (move,lid,left,right,camera,softbox):
        constant_keys(o)
    if top_down:constant_keys(data)

    # Printed coated paperboard: two scales of pulp grain, shallow paper relief,
    # warm exposed edges, and a distinct elongated softbox reflection. All print
    # UVs and source pixels are preserved. The deterministic reflection does not
    # need stochastic glossy rays or text-blurring denoising.
    for original, mat in materials.items():
        if original.name not in ('Наружный дизайн','Внутренний дизайн','Торцы картона'):
            continue
        nt=mat.node_tree
        emission=next(n for n in nt.nodes if n.type=='EMISSION')
        output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
        def math_node(operation, a=None, b=None, c=None, label=''):
            node=nt.nodes.new('ShaderNodeMath');node.operation=operation;node.label=label
            for i,value in enumerate((a,b,c)):
                if value is None:continue
                if isinstance(value,(float,int)):node.inputs[i].default_value=value
                else:nt.links.new(value,node.inputs[i])
            return node.outputs[0]
        def vector_node(operation, a=None, b=None):
            node=nt.nodes.new('ShaderNodeVectorMath');node.operation=operation
            for i,value in enumerate((a,b)):
                if value is None:continue
                if isinstance(value,tuple):node.inputs[i].default_value=value
                else:nt.links.new(value,node.inputs[i])
            return node.outputs['Value'] if operation=='DOT_PRODUCT' else node.outputs['Vector']
        coordinates=nt.nodes.new('ShaderNodeTexCoord')
        noise=nt.nodes.new('ShaderNodeTexNoise');noise.label='Мелкое бумажное зерно'
        noise.inputs['Scale'].default_value=1700
        noise.inputs['Detail'].default_value=2
        noise.inputs['Roughness'].default_value=.68
        nt.links.new(coordinates.outputs['Object'],noise.inputs['Vector'])
        stretched=vector_node('MULTIPLY',coordinates.outputs['Object'],(1,5,1))
        fibers=nt.nodes.new('ShaderNodeTexNoise');fibers.label='Короткие волокна картона'
        fibers.inputs['Scale'].default_value=420
        fibers.inputs['Detail'].default_value=2
        nt.links.new(stretched,fibers.inputs['Vector'])
        pulp=math_node('ADD',math_node('MULTIPLY',noise.outputs['Fac'],.65),
                       math_node('MULTIPLY',fibers.outputs['Fac'],.35))
        grain=math_node('MULTIPLY_ADD',pulp,.28,.80,label='Фактура печатного картона')
        multiply=nt.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY'
        multiply.inputs[0].default_value=1
        if original.name=='Торцы картона':
            multiply.inputs[1].default_value=rgba('B7A78C')
        else:
            nt.links.new(emission.inputs['Color'].links[0].from_socket,multiply.inputs[1])
        nt.links.new(grain,multiply.inputs[2])
        nt.links.new(multiply.outputs[0],emission.inputs['Color'])
        if original.name=='Торцы картона':continue
        bump=nt.nodes.new('ShaderNodeBump')
        bump.label='Неглубокий рельеф волокон под ламинацией'
        bump.inputs['Strength'].default_value=.28
        bump.inputs['Distance'].default_value=.000075
        nt.links.new(pulp,bump.inputs['Height'])
        geometry=nt.nodes.new('ShaderNodeNewGeometry')
        relative=nt.nodes.new('ShaderNodeTexCoord');relative.object=softbox
        light_direction=vector_node('NORMALIZE',vector_node('MULTIPLY',relative.outputs['Object'],(-1,-1,-1)))
        half_direction=vector_node('NORMALIZE',vector_node('ADD',light_direction,geometry.outputs['Incoming']))
        sign=math_node('SIGN',vector_node('DOT_PRODUCT',geometry.outputs['Normal'],geometry.outputs['Incoming']))
        oriented=nt.nodes.new('ShaderNodeVectorMath');oriented.operation='SCALE'
        nt.links.new(bump.outputs['Normal'],oriented.inputs[0]);nt.links.new(sign,oriented.inputs['Scale'])
        tangent=nt.nodes.new('ShaderNodeTangent');tangent.direction_type='UV_MAP';tangent.uv_map='OutsideUV'
        # Project the tangent onto the bumped surface, so the fibres actually
        # modulate the narrow direction of the reflected strip as well.
        tangent_dot=vector_node('DOT_PRODUCT',oriented.outputs[0],tangent.outputs[0])
        projection=nt.nodes.new('ShaderNodeVectorMath');projection.operation='SCALE'
        nt.links.new(oriented.outputs[0],projection.inputs[0]);nt.links.new(tangent_dot,projection.inputs['Scale'])
        paper_tangent=vector_node('NORMALIZE',vector_node('SUBTRACT',tangent.outputs[0],projection.outputs[0]))
        bitangent=vector_node('NORMALIZE',vector_node('CROSS_PRODUCT',oriented.outputs[0],paper_tangent))
        across=vector_node('DOT_PRODUCT',half_direction,paper_tangent)
        along=vector_node('DOT_PRODUCT',half_direction,bitangent)
        width=math_node('MULTIPLY',math_node('MULTIPLY',across,across),260)
        length=math_node('MULTIPLY',math_node('MULTIPLY',along,along),9)
        exponent=math_node('MULTIPLY',math_node('ADD',width,length),-1)
        lobe=math_node('POWER',math.e,exponent,label='Продолговатый блик софтбокса')
        front=math_node('GREATER_THAN',vector_node('DOT_PRODUCT',oriented.outputs[0],half_direction),.01)
        strength=math_node('MULTIPLY',math_node('MULTIPLY',lobe,front),.16,label='Глянцевая ламинация')
        glossy=nt.nodes.new('ShaderNodeEmission')
        glossy.label='Отражение на покрытии'
        glossy.inputs['Color'].default_value=(1,1,1,1)
        nt.links.new(strength,glossy.inputs['Strength'])
        addition=nt.nodes.new('ShaderNodeAddShader')
        nt.links.new(emission.outputs[0],addition.inputs[0])
        nt.links.new(glossy.outputs[0],addition.inputs[1])
        nt.links.new(addition.outputs[0],output.inputs['Surface'])

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 17
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.dither_intensity = 0
    scene.render.use_persistent_data = True
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, DURATION*FPS
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 15
    scene.render.filepath = '//box_rules_frames/'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    if hasattr(scene.render,'use_motion_blur'):
        scene.render.use_motion_blur = False
    for image in bpy.data.images:
        if image.source == 'FILE' and image.size[0] and not image.packed_file:
            image.pack()
    scene.frame_set(151)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.use_local_camera = False
                space.camera = camera
                space.region_3d.view_perspective = 'CAMERA'
    print('Built box-rules promo:',len(scene.objects),'objects; 30 cards; 8 seconds')
    return scene


if __name__ == '__main__':
    build(False)
    build(True)

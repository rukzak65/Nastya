"""ПРИКОЛ: отдельная сцена заставки, без PNG и сторонних библиотек.

В Blender: новый текст → вставить весь код → Option/Alt + P.
Старые сцены остаются в проекте. Рендер → Рендер анимации.
"""
import math
import os
import sys

WIDTH, HEIGHT, FPS = 3840, 2160, 30
DURATION = 3.6
POSE_FPS = 10
BACKGROUND = "0F4AFB"
CREAM = "FFFFEF"
UNIT = .01
CENTER = (266, 178.5)
VIEW_WIDTH = 532


def polygon(*points):
    return [("M", *points[0])] + [("L", *p) for p in points[1:]] + [("Z",)]


def ellipse(x, y, rx, ry):
    k = .5522847498307936
    return [
        ("M", x + rx, y),
        ("C", x + rx, y + k*ry, x + k*rx, y + ry, x, y + ry),
        ("C", x - k*rx, y + ry, x - rx, y + k*ry, x - rx, y),
        ("C", x - rx, y - k*ry, x - k*rx, y - ry, x, y - ry),
        ("C", x + k*rx, y - ry, x + rx, y - k*ry, x + rx, y),
        ("Z",),
    ]


def reflected(path):
    return [(cmd[0], *[774-v if i % 2 == 0 else v
                      for i, v in enumerate(cmd[1:])]) for cmd in path]


LEFT_ARM = [
    ("M", 368, 213), ("C", 362, 212, 359, 210, 361, 209),
    ("C", 366, 209, 368, 205, 365, 201),
    ("C", 361, 196, 355, 198, 352, 202),
    ("C", 347, 210, 353, 217, 366, 219), ("Z",),
]

# Векторные контуры элементов логотипа. Текстовые шрифты не нужны.
# Контроллер, цвет, контур. Синие элементы — глаза и просвет буквы Р.
SHAPES = [
    ("P", CREAM, polygon((110, 80), (204, 80), (204, 277),
                         (163, 277), (163, 144), (151, 144),
                         (151, 277), (110, 277))),
    ("R", CREAM, [
        ("M", 216, 80), ("L", 242, 80),
        ("C", 268, 80, 284, 91, 284, 110),
        ("C", 284, 129, 269, 138, 245, 138),
        ("L", 245, 172), ("L", 216, 172), ("Z",),
    ]),
    ("R", BACKGROUND, ellipse(252, 110, 8, 7.2)),
    ("I", CREAM, polygon((216, 184), (245, 184), (245, 214),
                         (284, 184), (284, 264), (255, 264),
                         (255, 246), (216, 277))),
    ("K", CREAM, polygon((294, 80), (315.3, 80), (315.3, 136),
                         (325, 80), (348, 80), (329.5, 186),
                         (350, 277), (294, 277))),
    ("left_leg", CREAM, polygon((368.9, 226), (386, 226),
                                (386, 254), (378, 277), (356, 277))),
    ("right_leg", CREAM, polygon((386, 226), (405.8, 226),
                                 (416, 277), (393, 277), (386, 254))),
    ("body", CREAM, polygon((379, 184), (397, 184), (405.8, 226),
                            (407.8, 236), (366.3705882, 236), (368.9, 226))),
    ("left_arm", CREAM, LEFT_ARM),
    ("right_arm", CREAM, reflected(LEFT_ARM)),
    ("head", CREAM, ellipse(387, 126, 29, 46)),
    ("head", BACKGROUND, ellipse(375, 125, 5, 7.5)),
    ("head", BACKGROUND, ellipse(398, 125, 5, 7.5)),
    ("head", BACKGROUND, [
        ("M", 378, 144), ("L", 396, 144),
        ("C", 396, 158, 378, 158, 378, 144), ("Z",),
    ]),
]

ROOTS = {
    "P": (157, 178.5), "R": (250, 126), "I": (250, 230.5),
    "K": (322, 178.5), "mascot": (387, 277),
}
PARTS = {
    "left_leg": (386, 226), "right_leg": (386, 226),
    "body": (386, 226), "left_arm": (363, 208),
    "right_arm": (411, 208), "head": (387, 126),
}
NAMES = {
    "P": "Буква П", "R": "Буква Р", "I": "Буква И", "K": "Буква К",
    "mascot": "Человечек — приход справа", "left_leg": "Левая нога",
    "right_leg": "Правая нога", "body": "Тело", "left_arm": "Левая рука",
    "right_arm": "Правая рука", "head": "Голова и улыбка",
}
NEUTRAL = (True, 0, 0, 0, 1, 1)


def pose_at(seconds):
    """Десять отдельных поз в секунду; между ними нет плавных переходов."""
    t = math.floor(max(0, seconds)*POSE_FPS + 1e-6) / POSE_FPS
    pose = {key: NEUTRAL for key in (*ROOTS, *PARTS)}
    for i, key in enumerate(("P", "R", "I", "K")):
        age = round(t - (.2 + i*.3), 5)
        sign = (-1 if i % 2 == 0 else 1)
        if age < 0:
            pose[key] = (False, 0, 0, 0, 1, 1)
        elif age < .1:
            pose[key] = (True, sign*3, 4, sign*7, .93, 1.04)
        elif age < .2:
            pose[key] = (True, -sign, -2, -sign*2.5, 1.025, .985)
        elif age < .3:
            pose[key] = (True, 0, 1, sign*.8, .995, 1.005)

    if t < .6:
        pose["mascot"] = (True, 200, 0, 0, 1, 1)
    elif t < 2.4:
        n = round((t-.6)*POSE_FPS)
        phase = n*math.pi/2
        swing = math.sin(phase)
        pose["mascot"] = (True, 200*(1-n/18),
                          -3*abs(swing), swing*2.1, 1, 1)
        pose["left_leg"] = (True, 0, 0, swing*16, 1, 1-.12*max(-swing, 0))
        pose["right_leg"] = (True, 0, 0, -swing*16, 1, 1-.12*max(swing, 0))
        pose["left_arm"] = (True, 0, 0, -swing*14, 1, 1)
        pose["right_arm"] = (True, 0, 0, swing*14, 1, 1)
        pose["head"] = (True, 0, -.5*abs(swing), -swing*1.5, 1, 1)
    elif t < 2.5:
        pose["mascot"] = (True, -1.5, 0, -1, 1.02, .985)
    elif t < 2.6:
        pose["mascot"] = (True, .5, -1, .5, .995, 1.005)
    return pose


def points_of(path):
    """Аппроксимация кривых с достаточной детализацией для 4K."""
    result = []
    current = (0, 0)
    for cmd in path:
        if cmd[0] in ("M", "L"):
            current = cmd[1:3]
            result.append(current)
        elif cmd[0] == "C":
            p0, p1, p2, p3 = current, cmd[1:3], cmd[3:5], cmd[5:7]
            for i in range(1, 49):
                t, u = i/48, 1-i/48
                result.append(tuple(u**3*p0[j] + 3*u*u*t*p1[j] +
                                    3*u*t*t*p2[j] + t**3*p3[j]
                                    for j in (0, 1)))
            current = p3
    # У замкнутых эллипсов последний узел совпадает с первым.
    if len(result) > 2 and math.dist(result[0], result[-1]) < 1e-7:
        result.pop()
    return result


def curves_of(data):
    ad = data.animation_data
    if not ad or not ad.action:
        return []
    if hasattr(ad.action, "fcurves"):
        return ad.action.fcurves
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    bag = action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return bag.fcurves if bag else []


def build_scene():
    import bpy
    scene = bpy.data.scenes.new("ПРИКОЛ — НАЧАЛО ПРОМО")
    scene["prikol_logo_intro"] = True
    scene["pose_fps"] = POSE_FPS
    collection = bpy.data.collections.new("Логотип и анимация шагов")
    scene.collection.children.link(collection)

    def make(data, name):
        o = bpy.data.objects.new(name, data)
        collection.objects.link(o)
        return o

    def linear(hex_color):
        c = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
        return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4
                     for v in c) + (1,)

    materials = {}
    for color in (BACKGROUND, CREAM):
        mat = bpy.data.materials.new("Цвет #" + color)
        mat.use_nodes = True
        mat.diffuse_color = linear(color)
        nt = mat.node_tree
        nt.nodes.clear()
        emission = nt.nodes.new("ShaderNodeEmission")
        emission.inputs[0].default_value = linear(color)
        output = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(emission.outputs[0], output.inputs["Surface"])
        materials[color] = mat

    controls = {}
    for key, (x, y) in ROOTS.items():
        obj = make(None, NAMES[key])
        obj.location = ((x-CENTER[0])*UNIT, (CENTER[1]-y)*UNIT, .05)
        obj["intro_control"] = key
        controls[key] = obj
    for key, (x, y) in PARTS.items():
        obj = make(None, NAMES[key])
        obj.parent = controls["mascot"]
        obj.location = ((x-387)*UNIT, (277-y)*UNIT, 0)
        obj["intro_control"] = key
        controls[key] = obj

    for i, (key, color, path) in enumerate(SHAPES):
        anchor = ROOTS.get(key, PARTS.get(key))
        vertices = [((x-anchor[0])*UNIT, (anchor[1]-y)*UNIT, i*.0001)
                    for x, y in points_of(path)]
        mesh = bpy.data.meshes.new(NAMES[key] + " — контур")
        mesh.from_pydata(vertices, [], [tuple(range(len(vertices)))])
        mesh.materials.append(materials[color])
        obj = make(mesh, NAMES[key] + " — графика")
        obj.parent = controls[key]

    # Плоский синий фон: одинаковый цвет при любом освещении.
    mesh = bpy.data.meshes.new("Однотонный фон")
    mesh.from_pydata([(-20, -20, 0), (20, -20, 0),
                      (20, 20, 0), (-20, 20, 0)], [], [(0, 1, 2, 3)])
    mesh.materials.append(materials[BACKGROUND])
    make(mesh, "Фон #" + BACKGROUND)

    for frame in range(1, round(DURATION*FPS)+1, FPS//POSE_FPS):
        poses = pose_at((frame-1)/FPS)
        for key, o in controls.items():
            visible, dx, dy, angle, sx, sy = poses[key]
            x, y = ROOTS.get(key, PARTS.get(key))
            if key in ROOTS:
                o.location = ((x+dx-CENTER[0])*UNIT,
                              (CENTER[1]-y-dy)*UNIT, .05)
            else:
                o.location = ((x+dx-387)*UNIT, (277-y-dy)*UNIT, 0)
            o.rotation_euler = (0, 0, -math.radians(angle))
            o.scale = (sx, sy, 1) if visible else (0, 0, 0)
            for prop in ("location", "rotation_euler", "scale"):
                o.keyframe_insert(data_path=prop, frame=frame)
    for o in controls.values():
        for fc in curves_of(o):
            for point in fc.keyframe_points:
                point.interpolation = "CONSTANT"

    data = bpy.data.cameras.new("Статичная камера — 16:9")
    camera = make(data, "Статичная камера — 16:9")
    camera.location = (0, 0, 10)
    camera.rotation_euler = (0, 0, 0)
    data.type = "ORTHO"
    data.ortho_scale = VIEW_WIDTH*UNIT
    data.dof.use_dof = False
    scene.camera = camera
    world = bpy.data.worlds.new("Окружение заставки")
    world.color = (0, 0, 0)
    scene.world = world

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.preview_samples = 8
    scene.cycles.use_denoising = False
    scene.cycles.use_preview_denoising = False
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 17
    scene.cycles.filter_width = 1
    if sys.platform == "darwin":
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.refresh_devices()
            if any(d.type == "METAL" for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == "METAL"
                scene.cycles.device = "GPU"
        except (AttributeError, TypeError, RuntimeError):
            pass

    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, round(DURATION*FPS)
    scene.render.film_transparent = False
    scene.render.dither_intensity = 0
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    if hasattr(scene.render, "use_motion_blur"):
        scene.render.use_motion_blur = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure, scene.view_settings.gamma = 0, 1
    settings = scene.render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "VIDEO"
    settings.file_format = "FFMPEG"
    settings.color_mode = "RGB"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    folder = (os.path.dirname(bpy.data.filepath) if bpy.data.filepath
              else os.path.expanduser("~/Desktop"))
    scene.render.filepath = os.path.join(folder, "prikol_logo_intro_4k.mp4")

    for t, label in ((0, "НАЧАЛО"), (.2, "П"), (.5, "Р"), (.8, "И"),
                     (1.1, "К"), (.6, "ЧЕЛОВЕЧЕК ИДЁТ СПРАВА"),
                     (2.6, "ЛОГОТИП СОБРАН")):
        scene.timeline_markers.new(label, frame=1+round(t*FPS))
    for workspace in bpy.data.workspaces:
        workspace.use_pin_scene = False
    if bpy.context.window:
        bpy.context.window.scene = scene
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.type = "MATERIAL"
                    space.shading.use_scene_world = True
                    space.shading.use_scene_lights = True
                    space.use_local_camera = False
                    space.camera = camera
                    space.region_3d.view_perspective = "CAMERA"
    scene.frame_set(82)  # При открытии виден собранный логотип.
    bpy.context.view_layer.update()
    print("Заставка готова: 4K, 30 кадров/с, 3,6 с. Кадр 82 — просмотр. Рендер → Рендер анимации.")
    return scene


if __name__ == "__main__":
    build_scene()

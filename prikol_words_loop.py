"""ПРИКОЛ: ИГРАЙ → ПРИДУМЫВАЙ → ШУТИ. Зацикленная заставка 4K.

В Blender: новый текст → вставить весь код → Option/Alt + P.
Создаётся отдельная сцена. Все слова заданы векторными контурами.
"""
import math
import os
import sys

WIDTH, HEIGHT, FPS = 3840, 2160, 30
DURATION, POSE_FPS = 6.0, 10
BACKGROUND, BLUE = "FFFEEF", "0F4AFB"
ORDER = ("играй", "придумывай", "шути")
OUTPUT_STEM = "prikol_words_loop_4k"
CANVAS_W, CANVAS_H = 1920, 1080
WORD_WIDTH = 1612.8
UNIT = .005


def polygon(*points):
    return [("M", *points[0])] + [("L", *p) for p in points[1:]] + [("Z",)]


def oval(x, y, rx, ry):
    k = .5522847498307936
    return [("M", x+rx, y),
            ("C", x+rx, y+k*ry, x+k*rx, y+ry, x, y+ry),
            ("C", x-k*rx, y+ry, x-rx, y+k*ry, x-rx, y),
            ("C", x-rx, y-k*ry, x-k*rx, y-ry, x, y-ry),
            ("C", x+k*rx, y-ry, x+rx, y-k*ry, x+rx, y), ("Z",)]


def letter_i(x):
    return polygon((x, 220), (x+80.5, 220), (x+80.5, 337.5),
                   (x+190, 202), (x+190, 578), (x+109.5, 578),
                   (x+109.5, 457), (x, 578))


WORDS = {
    "играй": {
        "bounds": (124, 142, 1268, 578),
        "paths": [
            (BLUE, letter_i(124)),
            (BLUE, polygon((368, 174), (667, 174), (656, 237),
                           (433, 237), (433, 493), (368, 495))),
            (BLUE, [("M", 486, 322), ("L", 550, 322),
                    ("C", 626, 322, 676, 347, 676, 395),
                    ("C", 676, 440, 622, 469, 547, 469),
                    ("L", 547, 578), ("L", 486, 578), ("Z",)]),
            (BACKGROUND, [("M", 590, 383),
                          ("C", 580, 382, 576, 386, 577, 398),
                          ("C", 577, 409, 585, 412, 596, 408),
                          ("C", 611, 403, 607, 386, 590, 383), ("Z",)]),
            (BLUE, polygon((840, 174), (1052, 578), (890, 578),
                           (873, 541), (801, 541), (784, 578), (628, 578))),
            (BACKGROUND, [("M", 840, 420),
                          ("C", 826, 420, 814, 434, 815, 455),
                          ("C", 815, 473, 817, 478, 839, 478),
                          ("C", 860, 478, 864, 474, 864, 458),
                          ("C", 864, 438, 854, 420, 840, 420), ("Z",)]),
            (BLUE, letter_i(1078)),
            (BLUE, polygon((1104, 142), (1244, 142),
                           (1234, 202), (1104, 202))),
        ],
    },
    "придумывай": {
        "bounds": (53, 48, 1982, 428),
        "paths": [
            (BLUE, polygon((53, 147), (247, 147), (247, 428),
                           (163, 428), (163, 239), (137, 239),
                           (137, 428), (53, 428))),
            (BLUE, [("M", 272, 147), ("L", 348, 147),
                    ("C", 425, 147, 478, 174, 478, 225),
                    ("C", 478, 270, 436, 307, 365, 307),
                    ("L", 338, 307), ("L", 338, 425),
                    ("L", 272, 425), ("Z",)]),
            (BACKGROUND, [("M", 386, 213),
                          ("C", 377, 213, 371, 216, 371, 227),
                          ("C", 371, 238, 375, 243, 385, 243),
                          ("C", 394, 243, 403, 237, 403, 229),
                          ("C", 403, 219, 396, 213, 386, 213), ("Z",)]),
            (BLUE, polygon((362, 325), (404, 325), (404, 365),
                           (478, 325), (478, 425), (435, 425),
                           (435, 387), (362, 425))),
            (BLUE, polygon((619, 142), (704, 330), (742, 330),
                           (705, 425), (534, 425), (498, 330), (535, 330))),
            (BACKGROUND, [("M", 625, 301),
                          ("C", 615, 301, 607, 309, 608, 320),
                          ("C", 608, 330, 615, 332, 625, 332),
                          ("C", 640, 332, 643, 329, 642, 319),
                          ("C", 641, 310, 634, 301, 625, 301), ("Z",)]),
            (BLUE, polygon((713, 147), (926, 147), (810, 425),
                           (732, 425), (769, 330))),
            (BLUE, polygon((963, 147), (1054, 272), (1138, 147),
                           (1239, 424), (1123, 424), (1102, 353),
                           (1051, 424), (996, 359), (975, 424), (863, 424))),
            (BLUE, [("M", 1258, 144), ("L", 1319, 144),
                    ("L", 1320, 334), ("C", 1366, 334, 1390, 349, 1390, 378),
                    ("C", 1390, 407, 1357, 425, 1319, 425),
                    ("L", 1258, 425), ("Z",)]),
            (BACKGROUND, oval(1315, 378, 11, 10.5)),
            (BLUE, [("M", 1400, 144), ("L", 1440, 144),
                    ("C", 1487, 144, 1523, 161, 1523, 191),
                    ("C", 1523, 213, 1495, 224, 1485, 225),
                    ("C", 1512, 227, 1540, 244, 1540, 270),
                    ("C", 1540, 299, 1499, 309, 1453, 309),
                    ("L", 1453, 425), ("L", 1400, 425), ("Z",)]),
            (BACKGROUND, [("M", 1453, 170),
                          ("C", 1470, 172, 1486, 181, 1486, 193),
                          ("C", 1486, 206, 1473, 215, 1453, 217), ("Z",)]),
            (BACKGROUND, [("M", 1453, 241),
                          ("C", 1478, 241, 1498, 249, 1498, 262),
                          ("C", 1498, 275, 1479, 282, 1453, 282), ("Z",)]),
            (BLUE, polygon((1639, 144), (1805, 425), (1679, 425),
                           (1666, 400), (1608, 400), (1595, 425), (1473, 425))),
            (BACKGROUND, [("M", 1652, 315),
                          ("C", 1639, 315, 1633, 323, 1633, 337),
                          ("C", 1633, 353, 1636, 356, 1652, 356),
                          ("C", 1668, 356, 1672, 353, 1671, 337),
                          ("C", 1670, 324, 1664, 315, 1652, 315), ("Z",)]),
            (BLUE, polygon((1716, 180), (1771, 149), (1816, 230),
                           (1840, 96), (1982, 353), (1927, 383),
                           (1881, 302), (1853, 425))),
            (BLUE, polygon((1709, 102), (1804, 48), (1821, 93), (1732, 143))),
        ],
    },
    "шути": {
        "bounds": (180, 188, 1266, 546),
        "paths": [
            (BLUE, polygon((180, 188), (248, 188), (248, 485),
                           (305, 485), (365, 188), (436, 188),
                           (376, 485), (479, 485), (479, 188),
                           (548, 188), (548, 546), (180, 546))),
            (BLUE, polygon((629, 188), (876, 188), (729, 542),
                           (608, 542), (687, 443))),
            (BLUE, polygon((848, 306), (1042, 304), (1028, 362),
                           (987, 362), (987, 538), (917, 542),
                           (917, 362), (848, 360))),
            (BLUE, polygon((1066, 188), (1138, 188), (1138, 331),
                           (1266, 188), (1266, 542), (1193, 542),
                           (1193, 409), (1066, 542))),
        ],
    },
}


def geometry(word):
    x0, y0, x1, y1 = WORDS[word]["bounds"]
    return ((x0+x1)/2, (y0+y1)/2), WORD_WIDTH/(x1-x0)


def pose_at(seconds):
    """Один цикл — 60 отдельных поз; начало и конец совпадают."""
    tick = math.floor(max(0, seconds)*POSE_FPS+1e-6) % 60
    index, local = divmod(tick, 20)
    current, following = ORDER[index], ORDER[(index+1) % 3]
    hidden = (False, 0, 0, 0, 1, 0)
    neutral = (True, 0, 0, 0, 1, 0)
    pose = {word: hidden for word in ORDER}
    pose[current] = neutral
    outgoing = {
        10: (0, 0, -2, 1.025), 11: (0, 0, -6, 1.06),
        12: (0, 0, -10, 1.08), 13: (-120, -10, -16, 1.08),
        14: (-300, -30, -22, 1.04), 15: (-620, -70, -28, .98),
        16: (-1000, -100, -36, .90), 17: (-1450, -160, -44, .84),
        18: (-1900, -220, -52, .75),
    }
    incoming = {
        13: (1750, 160, 14, .96), 14: (1120, 90, 9, 1),
        15: (650, 30, -6, 1.025), 16: (260, -20, -3, 1.04),
        17: (60, -10, 1.5, 1.02), 18: (-10, 0, -.8, .995),
    }
    if local in outgoing:
        pose[current] = (True, *outgoing[local], 0)
    if local in incoming:
        pose[following] = (True, *incoming[local], 1)
    if local == 19:
        pose[current], pose[following] = hidden, neutral
    return pose


def points_of(path):
    points, current = [], (0, 0)
    for command in path:
        if command[0] in ("M", "L"):
            current = command[1:3]
            points.append(current)
        elif command[0] == "C":
            a, b, c, d = current, command[1:3], command[3:5], command[5:7]
            for i in range(1, 49):
                t, u = i/48, 1-i/48
                points.append(tuple(u**3*a[j] + 3*u*u*t*b[j] +
                                    3*u*t*t*c[j] + t**3*d[j] for j in (0, 1)))
            current = d
    if len(points)>2 and math.dist(points[0], points[-1])<1e-7:
        points.pop()
    return points


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
    scene = bpy.data.scenes.new("ПРИКОЛ — ИГРАЙ ПРИДУМЫВАЙ ШУТИ — ЦИКЛ")
    scene["prikol_words_loop"] = True
    collection = bpy.data.collections.new("Три слова — векторные контуры")
    scene.collection.children.link(collection)

    def make(data, name):
        obj = bpy.data.objects.new(name, data)
        collection.objects.link(obj)
        return obj

    materials = {}
    for color in (BACKGROUND, BLUE):
        channels = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
        rgba = tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
                     for v in channels) + (1,)
        mat = bpy.data.materials.new("Цвет #"+color)
        mat.use_nodes = True
        mat.diffuse_color = rgba
        nt = mat.node_tree
        nt.nodes.clear()
        emission = nt.nodes.new("ShaderNodeEmission")
        emission.inputs[0].default_value = rgba
        output = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(emission.outputs[0], output.inputs["Surface"])
        materials[color] = mat

    controls = {}
    for word in ORDER:
        controller = make(None, word.upper()+" — движение целиком")
        controller["word"] = word
        controls[word] = controller
        (cx, cy), scale = geometry(word)
        for i, (color, path) in enumerate(WORDS[word]["paths"]):
            vertices = [((x-cx)*scale*UNIT, (cy-y)*scale*UNIT, i*.00001)
                        for x, y in points_of(path)]
            mesh = bpy.data.meshes.new(word+" — контур "+str(i+1))
            mesh.from_pydata(vertices, [], [tuple(range(len(vertices)))])
            mesh.materials.append(materials[color])
            shape = make(mesh, word+" — графика "+str(i+1))
            shape.parent = controller

    mesh = bpy.data.meshes.new("Сплошной фон #"+BACKGROUND)
    mesh.from_pydata([(-30, -30, 0), (30, -30, 0),
                      (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    mesh.materials.append(materials[BACKGROUND])
    make(mesh, "Фон #"+BACKGROUND)
    for frame in range(1, round(DURATION*FPS)+1, FPS//POSE_FPS):
        for word, state in pose_at((frame-1)/FPS).items():
            visible, dx, dy, angle, scale, depth = state
            obj = controls[word]
            obj.location = (dx*UNIT, -dy*UNIT, .05+depth*.01)
            obj.rotation_euler = (0, 0, -math.radians(angle))
            obj.scale = (scale, scale, 1) if visible else (0, 0, 0)
            for prop in ("location", "rotation_euler", "scale"):
                obj.keyframe_insert(data_path=prop, frame=frame)
    for obj in controls.values():
        for fc in curves_of(obj):
            for key in fc.keyframe_points:
                key.interpolation = "CONSTANT"

    data = bpy.data.cameras.new("Статичная камера 16:9")
    camera = make(data, "Статичная камера 16:9")
    camera.location = (0, 0, 10)
    camera.rotation_euler = (0, 0, 0)
    data.type, data.ortho_scale = "ORTHO", CANVAS_W*UNIT
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
                for device in prefs.devices:
                    device.use = device.type == "METAL"
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
    scene.render.filepath = os.path.join(folder, OUTPUT_STEM+".mp4")
    for t, label in ((0, "ИГРАЙ"), (2, "ПРИДУМЫВАЙ"), (4, "ШУТИ"),
                     (5.9, "ВОЗВРАТ К НАЧАЛУ")):
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
    scene.frame_set(61)
    bpy.context.view_layer.update()
    print("Готово: 3840×2160, 30 кадров/с, цикл 6 секунд. Рендер → Рендер анимации.")
    return scene


if __name__ == "__main__":
    build_scene()

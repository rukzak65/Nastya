import bpy
import math
import os
import random
import sys

# 4K, горизонтальный кадр; сами карты — вертикальные.
WIDTH, HEIGHT = 3840, 2160
FPS, END_FRAME = 30, 178                 # 5,933 секунды
ROWS, COLS = 4, 7                     # 28 мест; открываются 8 разных карт.
CW, CH, THICKNESS = 0.080, 0.120, 0.00045
PITCH_X, PITCH_Y = 0.095, 0.125
BACKGROUND = "FF3916"

# Можно оставить пустыми: откроются четыре подписанных окна.
PRIKOL_BACK = ""                         # Одна рубашка ПРИКОЛ.
BRIF_BACK = ""                           # Одна рубашка БРИФ.
PRIKOL_FACES = []                        # 10 лицевых ПРИКОЛ: шутки текстом.
BRIF_FACES = []                          # 14 лицевых БРИФ, можно выбрать все 20.
_PICKS = [[], [], [], []]
FEATURED = ((2, 2), (1, 6), (3, 6), (3, 2), (0, 4), (2, 4), (2, 6), (1, 2))


def rgba(value):
    c = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c) + (1,)


def normalized(path):
    return os.path.realpath(os.path.expanduser(bpy.path.abspath(path)))


def frame_at(seconds):
    return 1 + round(seconds * FPS)


def hold_keys(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    if hasattr(ad.action, "fcurves"):
        curves = ad.action.fcurves
    else:
        from bpy_extras.anim_utils import action_get_channelbag_for_slot
        bag = action_get_channelbag_for_slot(ad.action, ad.action_slot)
        curves = bag.fcurves if bag else []
    for curve in curves:
        for key in curve.keyframe_points:
            key.interpolation = "CONSTANT"


def build_scene(prikol_back, brif_back, prikol_faces, brif_faces):
    prikol_faces = sorted(set(normalized(p) for p in prikol_faces))
    brif_faces = sorted(set(normalized(p) for p in brif_faces))
    if len(prikol_faces) < 10 or len(brif_faces) < 14:
        raise RuntimeError("Выбери 10 разных лицевых ПРИКОЛ и минимум 14 разных лицевых БРИФ.")
    prikol_faces, brif_faces = prikol_faces[:10], brif_faces[:14]
    prikol_back, brif_back = normalized(prikol_back), normalized(brif_back)
    images = {}
    for path in [prikol_back, brif_back] + prikol_faces + brif_faces:
        if path in images:
            continue
        if not os.path.isfile(path) or not os.path.getsize(path):
            raise RuntimeError("Файл не найден или пуст: " + path)
        image = bpy.data.images.load(path, check_existing=False)
        image.reload()
        if min(image.size) == 0:
            raise RuntimeError("Не читается PNG: " + os.path.basename(path))
        image.colorspace_settings.name = "sRGB"
        image.pack()
        images[path] = image

    scene = bpy.data.scenes.new("ПРИКОЛ — ШАХМАТНАЯ РАСКЛАДКА")
    scene["prikol_chess"] = True
    collection = bpy.data.collections.new("Карты и фон")
    scene.collection.children.link(collection)

    def obj(data, name):
        result = bpy.data.objects.new(name, data)
        collection.objects.link(result)
        return result

    # Материалы сохраняют исходные цвета PNG и не дают бликов.
    def emission(name, color):
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        material.diffuse_color = color
        nt = material.node_tree
        nt.nodes.clear()
        shader = nt.nodes.new("ShaderNodeEmission")
        shader.inputs[0].default_value = color
        shader.inputs[1].default_value = 1
        output = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(shader.outputs[0], output.inputs["Surface"])
        return material, shader

    printed = {}

    def printed_material(path):
        if path not in printed:
            material, shader = emission(os.path.basename(path), rgba("FFFFEF"))
            nt = material.node_tree
            texture = nt.nodes.new("ShaderNodeTexImage")
            texture.image = images[path]
            texture.interpolation = "Linear"
            texture.extension = "EXTEND"
            uv = nt.nodes.new("ShaderNodeUVMap")
            uv.uv_map = "CardUV"
            nt.links.new(uv.outputs["UV"], texture.inputs["Vector"])
            nt.links.new(texture.outputs["Color"], shader.inputs[0])
            printed[path] = material
        return printed[path]

    edge, _ = emission("Тонкий торец картона", rgba("E6E3D5"))
    ground_material, _ = emission("Фон FF3916", rgba(BACKGROUND))

    # Мягкие плоские тени: стабильны между кадрами, без шума.
    shadow_material = bpy.data.materials.new("Мягкая тень карты")
    shadow_material.use_nodes = True
    if hasattr(shadow_material, "surface_render_method"):
        shadow_material.surface_render_method = "BLENDED"
    else:
        shadow_material.blend_method = "BLEND"
    nt = shadow_material.node_tree
    nt.nodes.clear()

    def calc(operation, a, b=None):
        node = nt.nodes.new("ShaderNodeMath")
        node.operation = operation
        for index, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                node.inputs[index].default_value = value
            else:
                nt.links.new(value, node.inputs[index])
        return node.outputs[0]

    uv = nt.nodes.new("ShaderNodeTexCoord")
    separate = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], separate.inputs[0])
    dx = calc("SUBTRACT", calc("ABSOLUTE", calc("SUBTRACT", separate.outputs["X"], .5)), .345)
    dy = calc("SUBTRACT", calc("ABSOLUTE", calc("SUBTRACT", separate.outputs["Y"], .5)), .397)
    distance = calc("MAXIMUM", dx, dy)
    fade = nt.nodes.new("ShaderNodeMapRange")
    fade.interpolation_type = "SMOOTHERSTEP"
    fade.clamp = True
    nt.links.new(distance, fade.inputs["Value"])
    for name, value in (("From Min", -.04), ("From Max", .055), ("To Min", .22), ("To Max", 0)):
        fade.inputs[name].default_value = value
    info = nt.nodes.new("ShaderNodeObjectInfo")
    opacity = calc("MULTIPLY", fade.outputs["Result"], info.outputs["Color"])
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    black = nt.nodes.new("ShaderNodeEmission")
    black.inputs[0].default_value = (0, 0, 0, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(opacity, mix.inputs[0])
    nt.links.new(transparent.outputs[0], mix.inputs[1])
    nt.links.new(black.outputs[0], mix.inputs[2])
    output = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], output.inputs["Surface"])

    def plane(name, material):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)], [], [(0, 1, 2, 3)])
        mesh.materials.append(material)
        layer = mesh.uv_layers.new(name="UVMap")
        for loop in mesh.loops:
            v = mesh.vertices[loop.vertex_index].co
            layer.data[loop.index].uv = (v.x + .5, v.y + .5)
        return obj(mesh, name)

    ground = plane("Фон FF3916", ground_material)
    ground.scale = (4, 4, 1)
    ground.location.z = -.0003

    cards, shadows = {}, {}
    rest = {}
    rng = random.Random(42)
    assigned = {}
    all_cells = [(r, c) for r in range(ROWS) for c in range(COLS)]
    ordered_cells = list(FEATURED) + [key for key in all_cells if key not in FEATURED]
    for parity, faces in ((0, prikol_faces), (1, brif_faces)):
        cells = [key for key in ordered_cells if sum(key) % 2 == parity]
        for index, key in enumerate(cells):
            # Повторные скрытые лица — только у фоновых ПРИКОЛ.
            # Все открываемые карты получают разные PNG.
            assigned[key] = faces[index % len(faces)]

    for row in range(ROWS):
        for column in range(COLS):
            category = "ПРИКОЛ" if (row + column) % 2 == 0 else "БРИФ"
            front = assigned[(row, column)]
            back = prikol_back if category == "ПРИКОЛ" else brif_back
            vertices = []
            radius = .0045
            for cx, cy, start in ((CW / 2 - radius, CH / 2 - radius, 0),
                                  (-CW / 2 + radius, CH / 2 - radius, 90),
                                  (-CW / 2 + radius, -CH / 2 + radius, 180),
                                  (CW / 2 - radius, -CH / 2 + radius, 270)):
                for i in range(8):
                    a = math.radians(start + i * 90 / 7)
                    vertices.append((cx + radius * math.cos(a), cy + radius * math.sin(a), THICKNESS / 2))
            n = len(vertices)
            vertices += [(x, y, -z) for x, y, z in vertices[:n]]
            polygons = [list(range(n)), list(reversed(range(n, 2 * n)))]
            polygons += [(i, i + n, (i + 1) % n + n, (i + 1) % n) for i in range(n)]
            name = f"{category} — ряд {row + 1}, место {column + 1}"
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(vertices, [], polygons)
            mesh.update()
            for material in (printed_material(front), printed_material(back), edge):
                mesh.materials.append(material)
            layer = mesh.uv_layers.new(name="CardUV")
            for poly in mesh.polygons:
                poly.material_index = poly.index if poly.index < 2 else 2
                for li in poly.loop_indices:
                    x, y, z = vertices[mesh.loops[li].vertex_index]
                    layer.data[li].uv = (.5 + (-x if poly.index == 1 else x) / CW, .5 + y / CH)
            card = obj(mesh, name)
            card["kind"] = "card"
            card["category"], card["row"], card["column"] = category, row, column
            card["front_path"], card["back_path"] = front, back
            key = row, column
            cards[key] = card
            shadow = plane("Тень — " + name, shadow_material)
            shadow["kind"] = "shadow"
            shadows[key] = shadow
            x = (column - (COLS - 1) / 2) * PITCH_X + rng.uniform(-.00025, .00025)
            y = ((ROWS - 1) / 2 - row) * PITCH_Y + rng.uniform(-.00025, .00025)
            rest[key] = x, y, rng.uniform(-.55, .55)

    def pose(key, frame, x, y, z, turn, angle):
        card, shadow = cards[key], shadows[key]
        card.location = (x, y, z)
        card.rotation_euler = (0, math.radians(turn), math.radians(angle))
        card.keyframe_insert(data_path="location", frame=frame)
        card.keyframe_insert(data_path="rotation_euler", frame=frame)
        spread = 1 + min(.35, z * 7)
        shadow.location = (x + .0008, y - .0013, -.0002)
        shadow.rotation_euler = (0, 0, math.radians(angle))
        shadow.scale = (CW * 1.45 * spread * (.28 + .72 * abs(math.cos(math.radians(turn)))), CH * 1.26 * spread, 1)
        opacity = .85 / (1 + max(0, z) * 12)
        shadow.color = (opacity, opacity, opacity, 1)
        for prop in ("location", "rotation_euler", "scale", "color"):
            shadow.keyframe_insert(data_path=prop, frame=frame)

    flat_z = THICKNESS / 2 + .00008
    for key, (x, y, angle) in rest.items():
        pose(key, 1, x, y, flat_z, 180, angle)

    def flip(key, seconds, show_front):
        x, y, angle = rest[key]
        f = frame_at(seconds)
        before, after = (180, 0) if show_front else (0, 180)
        pose(key, f, x, y, flat_z, before, angle)
        pose(key, f + 1, x + .001, y, .043, 95, angle - 1.4)
        pose(key, f + 3, x, y, .0011, after, angle + .9)
        pose(key, f + 6, x, y, flat_z, after, angle)

    # Порядок открытий и возвратов по присланному референсу.
    events = [
        (FEATURED[0], .067, True), (FEATURED[1], .233, True),
        (FEATURED[0], .433, False), (FEATURED[1], .700, False),
        (FEATURED[2], .900, True), (FEATURED[2], 1.267, False),
        (FEATURED[3], 1.400, True), (FEATURED[4], 1.633, True),
        (FEATURED[4], 1.933, False), (FEATURED[3], 2.100, False),
        (FEATURED[5], 2.300, True), (FEATURED[6], 2.500, True),
        (FEATURED[5], 2.667, False), (FEATURED[6], 2.867, False),
        (FEATURED[2], 3.000, True), (FEATURED[2], 3.333, False),
        (FEATURED[7], 3.600, True), (FEATURED[6], 3.900, True),
    ]
    for key, seconds, front in events:
        flip(key, seconds, front)

    # В конце две карты сходятся и ложатся одной стопкой.
    a, b = FEATURED[7], FEATURED[6]
    ax, ay, aa = rest[a]
    bx, by, ba = rest[b]
    gathering = [
        (4.20, 0, 0, 0, 0),
        (4.33, .08, -12, 9, .018),
        (4.50, .28, -20, 16, .025),
        (4.67, .52, -11, 24, .022),
        (4.83, .78, 4, 28, .016),
        (5.00, .95, -4, 13, .009),
        (5.17, 1, -2, 5, .003),
        (5.33, 1, 0, 1.8, 0),
        (5.50, 1, 0, 0, 0),
    ]
    for seconds, t, ra, rb, lift in gathering:
        f = frame_at(seconds)
        xa, ya = ax * (1 - t) - .004 * t, ay * (1 - t) + .030 * t
        xb, yb = bx * (1 - t) + .003 * t, by * (1 - t) + .027 * t
        pose(a, f, xa, ya, max(flat_z, .0012 * t) + lift, 0, aa * (1 - t) + ra)
        pose(b, f, xb, yb, max(flat_z, .0019 * t) + lift * 1.3, 0, ba * (1 - t) + rb)
    for card in list(cards.values()) + list(shadows.values()):
        hold_keys(card)

    data = bpy.data.cameras.new("Неподвижная камера сверху")
    camera = obj(data, "Неподвижная камера сверху")
    camera.location = (0, 0, 1)
    camera.rotation_euler = (0, 0, 0)
    data.type, data.ortho_scale, data.clip_start = "ORTHO", .630, .001
    data.dof.use_dof = False
    scene.camera = camera
    world = bpy.data.worlds.new("Однотонное окружение")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = rgba(BACKGROUND)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])
    scene.world = world
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.preview_samples = 16
    scene.cycles.use_denoising = False
    scene.cycles.use_preview_denoising = False
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 17
    scene.cycles.filter_width = 1.0
    scene.cycles.transparent_max_bounces = 16
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
    scene.frame_start, scene.frame_end = 1, END_FRAME
    scene.render.film_transparent = False
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
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.path.expanduser("~/Desktop")
    scene.render.filepath = os.path.join(base_dir, "PRIKOL_CHESS", "prikol_chess.mp4")
    for seconds, name in ((0, "РУБАШКИ"), (.067, "ПЕРВОЕ ОТКРЫТИЕ"),
                           (2.3, "СЛЕДУЮЩИЕ КАРТЫ"), (3.6, "ФИНАЛЬНАЯ ПАРА"),
                           (4.2, "КАРТЫ СХОДЯТСЯ"), (5.5, "СТОПКА")):
        scene.timeline_markers.new(name, frame=frame_at(seconds))
    for workspace in bpy.data.workspaces:
        workspace.use_pin_scene = False
    if bpy.context.window:
        bpy.context.window.scene = scene
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                space.shading.type = "MATERIAL"
                space.shading.use_scene_world = True
                space.shading.use_scene_lights = True
                if hasattr(space.shading, "use_compositor"):
                    space.shading.use_compositor = "DISABLED"
                space.use_local_camera = False
                space.camera = camera
                space.region_3d.view_perspective = "CAMERA"
    scene.frame_set(1)
    bpy.context.view_layer.update()
    print("Готово: 4K, 178 кадров, 5,93 с. Кадр 124 — проверка лицевых. Рендер → Рендер анимации.")
    return scene


TITLES = (
    "1/4 — РУБАШКА ПРИКОЛ: один PNG",
    "2/4 — РУБАШКА БРИФ: один PNG",
    "3/4 — 10 ЛИЦЕВЫХ ПРИКОЛ: шутки текстом",
    "4/4 — 14 ЛИЦЕВЫХ БРИФ: можно выбрать все 20",
)


def picker_class(stage):
    class Picker(bpy.types.Operator):
        bl_idname = "prikol.chess_png_" + str(stage)
        bl_label = TITLES[stage]
        filepath: bpy.props.StringProperty(subtype="FILE_PATH")
        directory: bpy.props.StringProperty(subtype="DIR_PATH")
        files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
        filter_glob: bpy.props.StringProperty(default="*.png;*.PNG", options={"HIDDEN"})

        def draw(self, context):
            box = self.layout.box()
            box.label(text=TITLES[stage])
            if stage < 2:
                box.label(text="Выбери только ОДНУ рубашку этой категории.")
            else:
                box.label(text="Выделяй несколько PNG с Shift / Cmd.")
                box.label(text="ПРИКОЛ = шутки текстом; БРИФ = графика и эмоции.")
                box.label(text="Лица открываемых карт не повторяются.")
                if stage == 3:
                    box.label(text="Можно выбрать 20 БРИФ — используются 14.")

        def invoke(self, context, event):
            context.window_manager.fileselect_add(self)
            return {"RUNNING_MODAL"}

        def execute(self, context):
            directory = self.directory or os.path.dirname(self.filepath)
            paths = [os.path.join(directory, f.name) for f in self.files]
            paths = [normalized(p) for p in paths if os.path.isfile(p)]
            if not paths and os.path.isfile(self.filepath):
                paths = [normalized(self.filepath)]
            paths = list(dict.fromkeys(paths))
            if not paths or (stage < 2 and len(paths) != 1):
                self.report({"ERROR"}, "Рубашка: один PNG. Лицевые: 10 ПРИКОЛ или 14 БРИФ.")
                return {"CANCELLED"}
            minimum = (1, 1, 10, 14)[stage]
            if len(paths) < minimum:
                self.report({"ERROR"}, "Выбери минимум " + str(minimum) + " разных PNG этой категории.")
                return {"CANCELLED"}
            _PICKS[stage] = paths
            if stage < 3:
                def next_picker():
                    getattr(bpy.ops.prikol, "chess_png_" + str(stage + 1))("INVOKE_DEFAULT")
                    return None
                bpy.app.timers.register(next_picker, first_interval=.2)
            else:
                try:
                    build_scene(_PICKS[0][0], _PICKS[1][0], _PICKS[2], _PICKS[3])
                except Exception as error:
                    self.report({"ERROR"}, str(error))
                    return {"CANCELLED"}
                self.report({"INFO"}, "Готово! Рендер → Рендер анимации. Видео настроено автоматически.")
            return {"FINISHED"}

    Picker.__name__ = "PRIKOL_OT_chess_png_" + str(stage)
    return Picker


if __name__ == "__main__":
    if PRIKOL_BACK and BRIF_BACK and PRIKOL_FACES and BRIF_FACES:
        build_scene(PRIKOL_BACK, BRIF_BACK, PRIKOL_FACES, BRIF_FACES)
    else:
        _PICKS = [[], [], [], []]
        for stage in range(4):
            old = bpy.types.Operator.bl_rna_get_subclass_py("PRIKOL_OT_chess_png_" + str(stage))
            if old:
                bpy.utils.unregister_class(old)
            bpy.utils.register_class(picker_class(stage))
        bpy.ops.prikol.chess_png_0("INVOKE_DEFAULT")

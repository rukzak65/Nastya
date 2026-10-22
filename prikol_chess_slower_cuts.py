import bpy
import os

# Дополнительный блок. Основной код удалять не нужно.
SLOWDOWN = 1.5                 # 1.5 = примерно 8,9 секунды.


def curves_of(data):
    ad = data.animation_data
    if not ad or not ad.action:
        return []
    if hasattr(ad.action, "fcurves"):
        return ad.action.fcurves
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    bag = action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return bag.fcurves if bag else []


def stepped(data):
    for curve in curves_of(data):
        for point in curve.keyframe_points:
            point.interpolation = "CONSTANT"


def make_slower_cuts(source, slowdown=SLOWDOWN):
    while source.get("prikol_chess_base_scene"):
        original = bpy.data.scenes.get(source["prikol_chess_base_scene"])
        if original is None:
            raise RuntimeError("Открой исходную сцену с шахматной раскладкой.")
        source = original
    if not source.get("prikol_chess"):
        raise RuntimeError("Сначала запусти основной код с раскладкой 4 × 7.")
    originals = {(o["row"], o["column"]): o for o in source.objects
                 if o.get("kind") == "card"}
    if len(originals) != 28:
        raise RuntimeError("Нужна готовая шахматная раскладка 4 × 7.")
    if slowdown < 1:
        raise RuntimeError("SLOWDOWN должен быть не меньше 1.")
    fps = source.render.fps / source.render.fps_base
    def at(seconds):
        return 1 + round(round(seconds * fps) * slowdown)

    previous_frame = source.frame_current
    source.frame_set(1)
    rest = {key: (o.location.copy(), o.rotation_euler.z) for key, o in originals.items()}
    shadows = [o for o in source.objects if o.get("kind") == "shadow"]
    shadow_for = {
        key: min(shadows, key=lambda o: (o.location.xy - rest[key][0].xy).length_squared)
        for key in originals
    } if shadows else {}
    scene = source.copy()
    scene.name = "ПРИКОЛ — МЕДЛЕННО, БЕЗ ПЕРЕВОРОТОВ"
    scene["prikol_chess_base_scene"] = source.name
    scene["prikol_chess_slowdown"] = slowdown

    # Отдельная сцена и отдельные объекты; исходная сохраняется.
    for child in list(scene.collection.children):
        scene.collection.children.unlink(child)
    for old in list(scene.collection.objects):
        scene.collection.objects.unlink(old)
    collection = bpy.data.collections.new("Карты — мгновенная смена лиц")
    scene.collection.children.link(collection)
    copies = {}
    for old in source.objects:
        new = old.copy()
        new.animation_data_clear()
        if old.type == "CAMERA":
            new.data = old.data.copy()
        collection.objects.link(new)
        copies[old] = new
    for old, new in copies.items():
        new.parent = copies.get(old.parent)
    scene.camera = copies[source.camera]
    cards = {key: copies[o] for key, o in originals.items()}

    def image_from(material):
        return next(n.image for n in material.node_tree.nodes
                    if n.type == "TEX_IMAGE" and n.image)

    # Смена картинки вместо вращения: 0 = рубашка, 1 = лицо.
    switches = {}
    for key, old in originals.items():
        card = cards[key]
        front = image_from(old.material_slots[0].material)
        back = image_from(old.material_slots[1].material)
        material = bpy.data.materials.new("Склейка — " + old.name)
        material.use_nodes = True
        tree = material.node_tree
        tree.nodes.clear()
        uv = tree.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "CardUV"
        mix = tree.nodes.new("ShaderNodeMixRGB")
        for socket, image in ((1, back), (2, front)):
            texture = tree.nodes.new("ShaderNodeTexImage")
            texture.image = image
            texture.interpolation = "Linear"
            texture.extension = "EXTEND"
            tree.links.new(uv.outputs["UV"], texture.inputs["Vector"])
            tree.links.new(texture.outputs["Color"], mix.inputs[socket])
        emission = tree.nodes.new("ShaderNodeEmission")
        tree.links.new(mix.outputs[0], emission.inputs[0])
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        tree.links.new(emission.outputs[0], output.inputs["Surface"])
        # Материал меняется только у новой копии объекта.
        card.material_slots[0].link = "OBJECT"
        card.material_slots[0].material = material
        card.location, angle = rest[key]
        card.rotation_euler = (0, 0, angle)
        mix.inputs[0].default_value = 0
        mix.inputs[0].keyframe_insert(data_path="default_value", frame=1)
        switches[key] = mix.inputs[0], tree

    featured = ((2, 2), (1, 6), (3, 6), (3, 2), (0, 4), (2, 4), (2, 6), (1, 2))
    events = [
        (0, .067, 1), (1, .233, 1), (0, .433, 0), (1, .700, 0),
        (2, .900, 1), (2, 1.267, 0), (3, 1.400, 1), (4, 1.633, 1),
        (4, 1.933, 0), (3, 2.100, 0), (5, 2.300, 1), (6, 2.500, 1),
        (5, 2.667, 0), (6, 2.867, 0), (2, 3.000, 1), (2, 3.333, 0),
        (7, 3.600, 1), (6, 3.900, 1),
    ]
    for index, seconds, value in events:
        socket, tree = switches[featured[index]]
        socket.default_value = value
        socket.keyframe_insert(data_path="default_value", frame=at(seconds))
    for socket, tree in switches.values():
        stepped(tree)

    # Сохраняем движение финальной пары, растягивая его по времени.
    final_keys = (featured[7], featured[6])
    moving = [originals[key] for key in final_keys]
    moving += [shadow_for[key] for key in final_keys if key in shadow_for]
    for old in moving:
        new = copies[old]
        for seconds in (0, 4.20, 4.33, 4.50, 4.67, 4.83, 5.00, 5.17, 5.33, 5.50):
            source.frame_set(1 + round(seconds * fps))
            new.location = old.location.copy()
            new.rotation_euler = (0, 0, old.rotation_euler.z)
            new.keyframe_insert(data_path="location", frame=at(seconds))
            new.keyframe_insert(data_path="rotation_euler", frame=at(seconds))
            if old.get("kind") == "shadow":
                new.scale, new.color = old.scale.copy(), tuple(old.color)
                new.keyframe_insert(data_path="scale", frame=at(seconds))
                new.keyframe_insert(data_path="color", frame=at(seconds))
        stepped(new)
    source.frame_set(previous_frame)
    scene.frame_start = 1
    scene.frame_end = round((source.frame_end - source.frame_start + 1) * slowdown)
    for marker in scene.timeline_markers:
        marker.frame = 1 + round((marker.frame - 1) * slowdown)
    stem, extension = os.path.splitext(source.render.filepath)
    scene.render.filepath = stem + "_slow_cuts" + (extension or ".mp4")
    if hasattr(scene.render, "use_motion_blur"):
        scene.render.use_motion_blur = False
    if bpy.context.window:
        bpy.context.window.scene = scene
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.camera = scene.camera
                    space.use_local_camera = False
                    space.region_3d.view_perspective = "CAMERA"
    scene.frame_set(1)
    bpy.context.view_layer.update()
    print("Готово: мгновенная смена лиц, без переворотов. Длительность:",
          round(scene.frame_end / fps, 2), "с. Файл:", scene.render.filepath)
    return scene


if __name__ == "__main__":
    source = bpy.context.scene
    if not source.get("prikol_chess"):
        sources = [s for s in bpy.data.scenes if s.get("prikol_chess")
                   and not s.get("prikol_chess_base_scene")]
        if not sources:
            raise RuntimeError("Сначала создай раскладку основным скриптом.")
        source = sources[-1]
    make_slower_cuts(source)

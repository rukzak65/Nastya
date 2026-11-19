"""Build a self-contained, editable Blender 4.3+ turntable.

In Blender, open this file in the Text Editor and choose Run Script.
From a terminal:
    blender -b --factory-startup --python build_turntable.py -- --output turntable.blend
All construction dimensions in this script are millimetres.
"""
import argparse
import math
import sys
from pathlib import Path

import _cycles
import bmesh
import bpy
from mathutils import Vector

MM = 0.001
TAU = math.tau
DECK_TOP = 46.3
PLATTER = (-51, 0)
PIVOT = (156, 107)


def metres(values):
    return tuple(v * MM for v in values)


def srgb(hex_color):
    values = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (*[v / 12.92 if v < 0.04045 else ((v + 0.055) / 1.055) ** 2.4
              for v in values], 1)


def group(name, owner):
    collection = bpy.data.collections.new(name)
    owner.children.link(collection)
    return collection


def surface(name, color, roughness, metal=0, coat=0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = srgb(color)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    for key, value in {
        "Base Color": srgb(color), "Metallic": metal, "Roughness": roughness,
        "Coat Weight": coat, "Coat Roughness": 0.28,
    }.items():
        bsdf.inputs[key].default_value = value
    return material, bsdf


def noise(material, vector, scale, location, detail=2):
    nodes, links = material.node_tree.nodes, material.node_tree.links
    texture = nodes.new("ShaderNodeTexNoise")
    texture.location = location
    texture.inputs["Scale"].default_value = scale
    texture.inputs["Detail"].default_value = detail
    links.new(vector, texture.inputs["Vector"])
    return texture.outputs["Fac"]


def coords(material):
    node = material.node_tree.nodes.new("ShaderNodeTexCoord")
    node.location = (-1000, 140)
    return node.outputs["Object"]


def ramp(material, factor, dark, light, location):
    node = material.node_tree.nodes.new("ShaderNodeValToRGB")
    node.location = location
    for stop, color in zip(node.color_ramp.elements, (dark, light)):
        stop.color = srgb(color)
    material.node_tree.links.new(factor, node.inputs["Fac"])
    return node.outputs["Color"]


def bump(material, bsdf, height, distance_mm, strength, location, normal=None):
    node = material.node_tree.nodes.new("ShaderNodeBump")
    node.location = location
    node.inputs["Distance"].default_value = distance_mm * MM
    node.inputs["Strength"].default_value = strength
    links = material.node_tree.links
    links.new(height, node.inputs["Height"])
    if normal:
        links.new(normal, node.inputs["Normal"])
    links.new(node.outputs["Normal"], bsdf.inputs["Normal"])
    return node.outputs["Normal"]


def grain(name, base, dark, light, roughness, scale, height, *, metal=0, coat=0):
    material, bsdf = surface(name, base, roughness, metal, coat)
    vector = coords(material)
    variation = noise(material, vector, 64, (-750, 250), 3)
    pores = noise(material, vector, scale, (-750, -60), 2)
    material.node_tree.links.new(
        ramp(material, variation, dark, light, (-440, 250)), bsdf.inputs["Base Color"]
    )
    bump(material, bsdf, pores, height, 0.45, (-220, -60))
    return material


def brushed_gold(name, radial):
    material, bsdf = surface(name, "D8AA69", 0.35, 1, 0.10)
    if "Anisotropic IOR Level" in bsdf.inputs:
        bsdf.inputs["Anisotropic IOR Level"].default_value = 0.32
    vector = coords(material)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    mapping = nodes.new("ShaderNodeVectorMath")
    mapping.operation = 'MULTIPLY'
    mapping.location = (-790, 120)
    mapping.inputs[1].default_value = (1, 1, 0) if radial else (9000, 9000, 420)
    links.new(vector, mapping.inputs[0])
    sample = mapping.outputs["Vector"]
    if radial:
        radius = nodes.new("ShaderNodeVectorMath")
        radius.operation = 'LENGTH'
        radius.location = (-610, 150)
        links.new(sample, radius.inputs[0])
        sample = radius.outputs["Value"]
        tangent = nodes.new("ShaderNodeTangent")
        tangent.direction_type = 'RADIAL'
        tangent.axis = 'Z'
        tangent.location = (-210, -280)
        links.new(tangent.outputs["Tangent"], bsdf.inputs["Tangent"])
    brush = noise(material, sample, 9200 if radial else 1.0, (-430, 80), 2)
    links.new(ramp(material, brush, "BD8F51", "E4BB7D", (-220, 220)), bsdf.inputs["Base Color"])
    bump(material, bsdf, brush, 0.007, 0.20, (-200, -45))
    return material


def walnut_veneer():
    material, bsdf = surface("Dark walnut | satin veneer", "462215", 0.38, coat=0.18)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    p = coords(material)
    p.node.location = (-1250, 180)
    bsdf.location = (570, 200)
    nodes.get("Material Output").location = (900, 200)

    def vector_math(operation, a, b, label, location):
        node = nodes.new("ShaderNodeVectorMath")
        node.operation = operation
        node.label = label
        node.location = location
        links.new(a, node.inputs[0])
        if hasattr(b, "is_output"):
            links.new(b, node.inputs[1])
        else:
            node.inputs[1].default_value = b
        return node.outputs["Vector"]

    # Offset the trunk axis from the veneer cut for broad, nearly horizontal figure.
    distortion = noise(material, p, 10.5, (-1040, 590), detail=3)
    drift = vector_math('MULTIPLY', distortion, (0, 0.019, -0.022),
                        "Subtle irregularity in the cut", (-820, 590))
    warped = vector_math('ADD', p, drift, "Warped trunk coordinates", (-610, 590))
    cross_section = vector_math('MULTIPLY', warped, (0, 1, 1),
                                "Trunk axis along the chassis", (-405, 590))
    center = vector_math('ADD', cross_section, (0, 0.245, 0.105),
                         "Off-centre veneer slice", (-200, 625))
    radius = nodes.new("ShaderNodeVectorMath")
    radius.operation = 'LENGTH'
    radius.location = (0, 610)
    links.new(center, radius.inputs[0])
    growth = noise(material, radius.outputs["Value"], 260, (195, 610), detail=2)
    fiber_domain = vector_math('MULTIPLY', warped, (13, 770, 660),
                               "Longitudinal wood fibres", (-415, 155))
    fibers = noise(material, fiber_domain, 1.0, (-185, 155), detail=3)
    figure = nodes.new("ShaderNodeMixRGB")
    figure.label = "Growth figure and strands"
    figure.location = (180, 270)
    figure.inputs[0].default_value = 0.52
    links.new(growth, figure.inputs[1])
    links.new(fibers, figure.inputs[2])
    color = ramp(material, figure.outputs["Color"], "221009", "713923", (370, 440))
    color.node.label = "Warm walnut heartwood"
    colors = color.node.color_ramp
    for position, color_hex in ((0.25, "2D170F"), (0.47, "452215"), (0.68, "60311F")):
        colors.elements.new(position).color = srgb(color_hex)
    links.new(color, bsdf.inputs["Base Color"])

    pore_domain = vector_math('MULTIPLY', p, (205, 4970, 4230),
                              "Fine pores under satin finish", (-610, -230))
    pores = noise(material, pore_domain, 1.0, (-380, -230), detail=2)
    relief = bump(material, bsdf, fibers, 0.024, 0.20, (35, -105))
    bump(material, bsdf, pores, 0.012, 0.27, (300, -105), normal=relief)
    roughness = nodes.new("ShaderNodeMapRange")
    roughness.label = "Satin roughness"
    roughness.location = (70, -430)
    roughness.inputs["To Min"].default_value = 0.32
    roughness.inputs["To Max"].default_value = 0.45
    links.new(fibers, roughness.inputs["Value"])
    links.new(roughness.outputs["Result"], bsdf.inputs["Roughness"])
    return material


def make_materials():
    colors = {
        'plinth': walnut_veneer(),
        'rim': brushed_gold("Matte gold | circular brush", True),
        'tube': brushed_gold("Matte gold | satin tube", False),
        'edge': surface("Champagne gold | machined edges", "E3B87D", 0.24, 0.95)[0],
        'ink': surface("Blackened bronze | lettering on gold", "211712", 0.57, 0.16)[0],
        'legend': surface("Champagne | embossed legends", "E2C58F", 0.43, 0.40)[0],
        'black': grain("Graphite anodized aluminum", "202124", "1A1B1D", "28292B", 0.38, 4400, 0.012, metal=0.53),
        'steel': surface("Dark machined steel", "46474B", 0.28, 0.81)[0],
        'rubber': grain("Molded rubber", "151417", "111114", "222125", 0.63, 3600, 0.022),
        'felt': grain("Black felt", "28282A", "202023", "343437", 0.88, 4700, 0.072),
        'floor': grain("Charcoal studio surface", "252326", "212024", "28272A", 0.86, 3100, 0.04),
        'void': surface("Recess | carbon black", "0D0C0E", 0.75)[0],
        'acrylic': surface("Clear acrylic", "F6F7F8", 0.105)[0],
    }
    felt = colors['felt']
    felt.node_tree.nodes.get("Principled BSDF").inputs["Sheen Weight"].default_value = 0.14
    acrylic = colors['acrylic'].node_tree.nodes.get("Principled BSDF")
    acrylic.inputs["Transmission Weight"].default_value = 1.0
    acrylic.inputs["IOR"].default_value = 1.49
    return colors


def mesh(name, vertices, faces, collection, material, *, origin=(0, 0, 0), smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata([metres(v) for v in vertices], [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    data.update()
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = metres(origin)
    if material:
        data.materials.append(material)
    for face in data.polygons:
        face.use_smooth = smooth
    return obj


def bevel(obj, width, segments=3):
    modifier = obj.modifiers.new("Machined edge radii", 'BEVEL')
    modifier.width = width * MM
    modifier.segments = segments
    modifier.harden_normals = True
    normals = obj.modifiers.new("Face-weighted normals", 'WEIGHTED_NORMAL')
    normals.keep_sharp = True
    return obj


def box(name, size, center, c, material, radius=0.45, angle=0):
    x, y, z = (s / 2 for s in size)
    verts = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
             (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
    obj = mesh(name, verts, faces, c, material, origin=center)
    obj.rotation_euler.z = angle
    return bevel(obj, radius) if radius else obj


def rounded_rect(width, depth, radius, z, center_y=0):
    points = []
    for sx, sy, start in [(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)]:
        cx, cy = sx * (width / 2 - radius), sy * (depth / 2 - radius) + center_y
        for step in range(13):
            t = math.radians(start + 90 * step / 12)
            points.append((cx + radius * math.cos(t), cy + radius * math.sin(t), z))
    return points


def loft(name, rings, c, material, *, origin=(0, 0, 0), cap=True, cyclic=False, smooth=True):
    n = len(rings[0])
    faces = []
    connections = len(rings) if cyclic else len(rings) - 1
    for i in range(connections):
        a, b = i * n, ((i + 1) % len(rings)) * n
        for j in range(n):
            k = (j + 1) % n
            faces.append((a + j, a + k, b + k, b + j))
    if cap:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    obj = mesh(name, [v for ring in rings for v in ring], faces, c, material,
               origin=origin, smooth=smooth)
    if cap:
        obj.data.polygons[-1].use_smooth = False
        obj.data.polygons[-2].use_smooth = False
    return obj


def lathe(name, profile, origin, c, material, *, steps=96, hollow=False):
    ring = [(math.cos(TAU * i / steps), math.sin(TAU * i / steps)) for i in range(steps)]
    points = [[(r * x, r * y, z) for x, y in ring] for r, z in profile]
    return loft(name, points, c, material, origin=origin, cap=not hollow, cyclic=hollow)


def disc(name, radius, height, center, c, material, *, edge=0.35, steps=72):
    z = height / 2
    edge = min(edge, height * 0.28)
    return lathe(name, [(radius - edge, -z), (radius, -z + edge), (radius, z - edge),
                        (radius - edge, z)], center, c, material, steps=steps)


def ring(name, outer, inner, height, center, c, material, *, steps=96):
    return lathe(name, [(outer - 0.20, -height / 2), (outer, -height / 2 + 0.22),
                        (outer, height / 2 - 0.22), (outer - 0.20, height / 2),
                        (inner + 0.18, height / 2), (inner, height / 2 - 0.18),
                        (inner, -height / 2 + 0.18), (inner + 0.18, -height / 2)],
                 center, c, material, steps=steps, hollow=True)


def rod(name, a, b, radius, c, material, *, steps=56):
    start, end = Vector(a), Vector(b)
    obj = disc(name, radius, (end - start).length, (start + end) / 2, c, material, steps=steps)
    obj.rotation_euler = (end - start).to_track_quat('Z', 'Y').to_euler()
    return obj


def path(name, points, radius, c, material, *, smooth=False):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 20
    data.bevel_depth = radius * MM
    data.bevel_resolution = 6
    data.use_fill_caps = True
    spline = data.splines.new('BEZIER' if smooth else 'POLY')
    if smooth:
        spline.bezier_points.add(len(points) - 1)
        for point, value in zip(spline.bezier_points, points):
            point.co = metres(value)
            point.handle_left_type = point.handle_right_type = 'AUTO'
    else:
        spline.points.add(len(points) - 1)
        for point, value in zip(spline.points, points):
            point.co = (*metres(value), 1)
    obj = bpy.data.objects.new(name, data)
    c.objects.link(obj)
    data.materials.append(material)
    return obj


def relief(text, size, center, c, material):
    letters = bpy.data.curves.new(f"Relief | {text}", 'FONT')
    letters.body = text
    letters.align_x = letters.align_y = 'CENTER'
    letters.size = size * MM
    letters.extrude = 0.078 * MM
    letters.bevel_depth = 0.023 * MM
    letters.bevel_resolution = 2
    mesh_text = bpy.data.objects.new(letters.name, letters)
    mesh_text.location = metres(center)
    c.objects.link(mesh_text)
    letters.materials.append(material)
    return mesh_text


def boolean_difference(obj, cutter, label):
    modifier = obj.modifiers.new(label, 'BOOLEAN')
    modifier.operation = 'DIFFERENCE'
    modifier.solver = 'EXACT'
    modifier.object = cutter
    cutter.hide_render = True
    cutter.hide_set(True)
    cutter.display_type = 'WIRE'


def screw(name, center, radius, c, cutters, material, index):
    head = disc(name, radius, 1.8, center, c, material, edge=0.35, steps=32)
    x, y, z = center
    slot = box(f"Slot cutter | {name}", (radius * 1.75, radius * 0.33, 1.1),
               (x, y, z + 0.83), cutters, None, radius=0, angle=index * 0.73 + 0.28)
    boolean_difference(head, slot, "Recessed screw slot")
    return head


def make_body(c, feet, rear, hinges, cutters, m):
    # Lower chassis and cast upper shell are separated by a physical gasket line.
    for name, profiles, material in [
        ("Stamped lower chassis", [(448, 343, 6, 14), (452, 347, 7, 15.1),
                                  (454, 349, 8, 17.1)], m['black']),
        ("Perimeter gasket", [(453, 348, 8, 16.9), (453.5, 348.5, 8, 17.5)], m['rubber']),
        ("Burgundy die-cast plinth", [(453.2, 348.2, 7.3, 17.3), (454.4, 349.4, 7.7, 18.1),
                                    (455, 350, 8, 19.2), (455, 350, 8, 43.9),
                                    (454.5, 349.5, 7.8, 45.0), (453, 348, 7.1, 46.05),
                                    (451.6, 346.6, 6.5, DECK_TOP)], m['plinth']),
    ]:
        obj = loft(name, [rounded_rect(*profile) for profile in profiles], c, material)
        normal = obj.modifiers.new("Face-weighted normals", 'WEIGHTED_NORMAL')
        normal.keep_sharp = True
    box("Recessed bottom access panel", (371, 258, 2), (0, 3, 13.5), c, m['black'], 3)
    for i, (x, y) in enumerate(((-191, -148), (191, -148), (-191, 148), (191, 148)), 1):
        disc(f"Foot {i} | threaded mount", 18.5, 2.4, (x, y, 13.6), feet, m['steel'])
        lathe(f"Isolation foot {i}", [(19.8, 2.2), (21.5, 2.8), (22, 3.8), (22, 9.2),
                                    (21.4, 10.2), (18.5, 11.8), (17.7, 12.8)],
              (x, y, 0), feet, m['black'])
        disc(f"Foot {i} | nitrile isolation pad", 20.4, 2.4, (x, y, 1.2), feet, m['rubber'])
        for z in (4.6, 6.2, 7.8):
            ring(f"Foot {i} | damped tread {z:.1f}", 22.16, 21.65, 0.54,
                 (x, y, z), feet, m['rubber'])
    for x in (-151, 151):
        label = "L" if x < 0 else "R"
        box(f"{label} hinge | plate", (53, 19, 8), (x, 178.5, 43.8), hinges, m['black'], 1.5)
        box(f"{label} hinge | body", (26, 17, 11), (x, 181, 49), hinges, m['black'], 1.7)
        rod(f"{label} hinge | pin", (x - 13.8, 182, 51.5), (x + 13.8, 182, 51.5),
            3.4, hinges, m['steel'])
        box(f"{label} hinge | lid clip", (25, 7.5, 14), (x, 182.4, 57.4), hinges, m['black'], 1.5)
        for i, offset in enumerate((-19, 19)):
            screw(f"{label} hinge screw {i + 1}", (x + offset, 179, 47.9),
                  2.1, hinges, cutters, m['steel'], i)
    box("Rear terminal bracket", (118, 2, 19), (84, 174.4, 29), rear, m['black'], 0.7)
    for x, name, material in [(48, 'Left RCA', m['legend']), (64, 'Right RCA', m['rim']),
                               (86, 'Earth post', m['steel']), (125, 'DC barrel', m['black'])]:
        outer = rod(name + " | outer socket", (x, 174.4, 28), (x, 179.1, 28), 4.3, rear, material)
        bore = rod(name + " | bore cutter", (x, 175.6, 28), (x, 180, 28), 2.6, cutters, None)
        boolean_difference(outer, bore, "Bored socket")
        rod(name + " | insulator", (x, 175, 28), (x, 176.4, 28), 2.55, rear, m['void'])


def make_platter(c, m):
    x, y = PLATTER
    disc("Platter | motor bearing seat", 121, 2.1, (x, y, 47.4), c, m['black'], steps=160)
    lathe("Platter | drive hub", [(139, 0), (153, 0.8), (157, 2), (157, 8.5), (154, 9.4)],
          (x, y, 48.5), c, m['black'], steps=192)
    lathe("Platter | machined gold outer rim", [(157, 0), (158.5, 0.5), (159, 1.2),
          (159, 8.2), (158.6, 9.1), (157.9, 9.6), (156.5, 9.9),
          (154.7, 9.9), (154.7, 8.6), (155.4, 8.2), (155.4, 0.6)],
          (x, y, 48.4), c, m['rim'], steps=240, hollow=True)
    ring("Platter | lower edge line", 159.02, 158.75, 0.52, (x, y, 51.15), c, m['edge'], steps=240)
    ring("Platter | gold top lip", 157.7, 155.35, 0.58, (x, y, 58.15), c, m['edge'], steps=240)
    disc("Platter | charcoal felt slipmat", 156.0, 2.0, (x, y, 58.6),
         c, m['felt'], edge=0.43, steps=240)
    disc("Center puck | felt gasket", 18.7, 0.95, (x, y, 59.92), c, m['rubber'])
    lathe("Center puck | brushed face", [(18.5, 0), (19.1, 0.42), (19.1, 2.8),
                                       (18.9, 3.36), (18.35, 3.75)],
          (x, y, 60.3), c, m['rim'], steps=128)
    lathe("Center spindle", [(3.25, 0), (3.25, 3), (3.10, 4.35), (2.65, 5.05),
                           (1.85, 5.6), (0.35, 5.9)],
          (x, y, 64.05), c, m['edge'], steps=72)


def make_controls(c, m):
    for text, x in [('OFF', -207), ('ON', -185)]:
        y = -106
        disc("Power " + text + " | sleeve", 7.1, 1.25, (x, y, 46.8), c, m['black'])
        lathe("Power " + text + " | domed cap", [(5.95, 0), (6.6, 0.55), (6.6, 2),
              (6.2, 2.8), (5.5, 3.41), (4.8, 3.68), (4.25, 3.80)],
              (x, y, 47.1), c, m['rim'])
        relief(text, 4.5, (x, y, 50.95), c, m['ink'])
    x, y = -196, -137
    disc("Speed selector | rubber collar", 14.8, 1.4, (x, y, 46.8), c, m['black'])
    lathe("Speed selector | gold knob", [(13.7, 0), (14.25, 0.55), (14.25, 7.3),
          (13.99, 8.15), (13.35, 8.85), (11.8, 9.13)],
          (x, y, 47.4), c, m['rim'], steps=128)
    box("Speed selector | embossed index", (0.60, 2.1, 0.23), (x, y - 10.5, 56.51),
        c, m['ink'], 0.07)
    arc = [math.radians(225 + 90 * i / 90) for i in range(91)]
    path("Speed selector | embossed scale arc",
         [(x + 19.8 * math.cos(t), y + 19.8 * math.sin(t), DECK_TOP + 0.06) for t in arc],
         0.17, c, m['legend'])
    for label, angle in [('33', 227), ('45', 270), ('78', 313)]:
        t = math.radians(angle)
        dx, dy = math.cos(t), math.sin(t)
        path(f"Speed selector | embossed {label} tick",
             [(x + r * dx, y + r * dy, DECK_TOP + 0.09) for r in (18.0, 21.8)],
             0.24, c, m['legend'])
        relief(label, 6.8, (x + 26 * dx, y + 26.5 * dy, DECK_TOP + 0.08), c, m['legend'])


def make_tonearm(fixed, moving, cutters, m):
    px, py = PIVOT
    disc("Tonearm pedestal | gasket", 34.6, 1.65, (px, py, 47.0), fixed, m['rubber'])
    lathe("Tonearm pedestal | spun base", [(32.8, 0), (34.0, 0.7), (34.0, 3.3),
          (33.5, 4.2), (30.9, 5.6), (29.5, 6.1)], (px, py, 47.8), fixed, m['black'])
    ring("Tonearm pedestal | face collar", 29.1, 23.7, 1.4, (px, py, 54.5), fixed, m['steel'])
    disc("Tonearm swivel | bearing well", 23.65, 2.2, (px, py, 54.6), fixed, m['void'])
    lathe("Tonearm swivel | vertical spindle", [(14.5, 0), (15.2, 0.7), (15.2, 7),
                    (13.3, 10), (11.0, 15.0)], (px, py + 2, 55), moving, m['steel'])
    for i, (dx, dy) in enumerate(((-21, -17), (18, -19), (20, 19))):
        screw(f"Tonearm mounting screw {i + 1}", (px + dx, py + dy, 53.6),
              2.05, fixed, cutters, m['steel'], i)
    disc("Anti-skate | mount", 10.6, 4.0, (187, 102, 56.4), fixed, m['black'])
    lathe("Anti-skate | unmarked dial", [(9.25, 0), (9.8, 0.7), (9.8, 5),
          (9.3, 6.1), (8.5, 6.6)], (187, 102, 58.2), fixed, m['steel'])
    # The bracket, damping cylinder and cue lever have independently editable geometry.
    rod("Cue damper | piston", (172, 79, 52.7), (172, 79, 69.9), 4.8, fixed, m['steel'])
    box("Cue damper | arc saddle", (18, 5.1, 2.3), (171, 79, 70.9), fixed, m['rubber'], 0.6, -0.13)
    rod("Cue lever | shaft", (177.8, 71.5, 60.3), (186, 52, 65.9), 1.5, fixed, m['steel'])
    box("Cue lever | rounded grip", (4.4, 18, 4.1), (187.6, 47, 66.2), fixed, m['black'], 1.45, 0.23)
    box("Arm rest | post", (7, 7, 19), (172, 63, 57.4), fixed, m['black'], 1.1)
    rod("Arm rest | clamp pin", (168, 63, 68.6), (177, 63, 68.6), 1.65, fixed, m['steel'])
    box("Arm rest | clip", (10.5, 5, 2.7), (172, 63, 70.5), fixed, m['black'], 0.7)

    rod("Gimbal | side axle", (137, 105, 76.8), (175, 105, 76.8), 3.2, moving, m['steel'])
    for x in (139, 173):
        rod(f"Gimbal | bearing housing {x}", (x - 2.8, 105, 76.8),
            (x + 2.8, 105, 76.8), 7.6, moving, m['black'])
    box("Gimbal | upper bridge", (55, 13, 6.3), (159, 101, 83.9),
        moving, m['black'], 1.55, -0.54)
    rod("Counterweight | threaded shank", (px, 110, 80), (px, 163, 80), 4.4, moving, m['steel'])
    counter = lathe("Counterweight | matte gold cylinder", [(11.7, -13.8), (12.4, -12.8),
                    (12.8, -10), (12.8, 9.9), (12.45, 12.0), (11.8, 13.0)],
                    (px, 146.6, 80), moving, m['rim'], steps=112)
    counter.rotation_euler.x = math.pi / 2
    knob_ridges = [(1.0, 0.0), (0.994, 0.002), (0.994, 0.005), (1.0, 0.007)]
    teeth = [(r * math.cos(TAU * i / 72 + d), r * math.sin(TAU * i / 72 + d))
             for i in range(72) for r, d in knob_ridges]
    knurl = loft("Counterweight | knurled calibration ring",
                 [[(x * r, y * r, z) for x, y in teeth]
                  for r, z in ((12.55, -2.4), (13.05, -1.9), (13.05, 1.9), (12.55, 2.4))],
                 moving, m['rim'], origin=(px, 134.8, 80), smooth=False)
    knurl.rotation_euler.x = math.pi / 2
    rod("Counterweight | rear end plug", (px, 159.7, 80), (px, 162.4, 80),
        10.4, moving, m['black'])
    rod("Tonearm | black pivot barrel", (px, 115, 80), (px, 80, 78.6), 5.2, moving, m['black'])
    points = [(156, 86, 79), (159, 71, 78.4), (166, 47, 77.6), (177, 14, 76.2),
              (188, -23, 75), (189, -48, 74.5), (181, -73, 73.2),
              (169, -94, 71.1), (156, -112, 69.9)]
    path("Tonearm | continuous S-bend tube", points, 3.7, moving, m['tube'], smooth=True)
    for a, b, radius, label in [
        ((157, 73, 78.5), (159.6, 64.5, 78.1), 4.2, "Pivot ferrule"),
        ((169, -94, 71.1), (164.2, -100.65, 70.64), 4.35, "Knurled bayonet sleeve"),
        ((163.5, -101.5, 70.55), (156, -112, 69.9), 4.05, "Bayonet tapered nose"),
    ]:
        rod(f"Tonearm | {label}", a, b, radius, moving, m['rim'])
    a, b = Vector((169, -94, 71.1)), Vector((164.2, -100.65, 70.64))
    for i in range(7):
        t = a.lerp(b, (i + 1) / 8)
        e = (b - a).normalized() * 0.14
        rod(f"Bayonet | fine knurl ring {i + 1}", t - e, t + e, 4.46, moving, m['edge'], steps=48)
    make_headshell(moving, cutters, m)

    # Parent all moving pieces to one vertical axis. The parked pose remains the default.
    root = bpy.data.objects.new("Arm swivel axis | rotate around Z", None)
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = 0.015
    root.location = metres((px, py, 76.8))
    moving.objects.link(root)
    from mathutils import Matrix
    inverse = Matrix.Translation(-root.location)
    for obj in list(moving.objects):
        if obj != root:
            obj.parent = root
            obj.matrix_parent_inverse = inverse
    # Cutters must follow the component when the arm rotates.
    for obj in cutters.objects:
        if obj.name.startswith(("Headshell |", "Slot cutter | Cartridge screw")):
            obj.parent = root
            obj.matrix_parent_inverse = inverse


def make_headshell(c, cutters, m):
    origin = Vector((156, -112))
    forward = Vector((-0.586, -0.810)).normalized()
    across = Vector((-forward.y, forward.x))
    angle = math.atan2(across.y, across.x)

    def here(x, y, z):
        loc = origin + across * x + forward * y
        return loc.x, loc.y, z

    outline = [(-7.4, -2), (7.4, -2), (8.9, 7), (8.9, 31), (10.6, 38),
               (10.6, 49), (8.8, 52.2), (-8.8, 52.2), (-10.6, 49), (-10.6, 38),
               (-8.9, 31), (-8.9, 7)]
    body = loft("Headshell | pierced graphite shell",
                [[here(x, y, z) for x, y in outline] for z in (66.9, 70.8)], c, m['black'], smooth=False)
    for i, y in enumerate((8, 18, 28), 1):
        hole = lathe(f"Headshell | oval opening cutter {i}", [(3.25, -5), (3.25, 5)],
                     here(0, y, 69.1), cutters, None, steps=40)
        hole.scale.y = 1.30
        hole.rotation_euler.z = angle
        boolean_difference(body, hole, f"Open ventilation slot {i}")
    for i, x in enumerate((-5.45, 5.45), 1):
        hole = disc(f"Headshell | countersink cutter {i}", 3.25, 3.9, here(x, 43, 70.4),
                    cutters, None, edge=0.35, steps=40)
        boolean_difference(body, hole, f"Recessed mounting hole {i}")
        screw(f"Cartridge screw {i}", here(x, 43, 69.63), 2.65, c, cutters, m['edge'], i)
    bevel(body, 0.38)
    box("Cartridge | lower body", (16.7, 19.8, 10.6), here(0, 40.15, 62.5),
        c, m['black'], 1.1, angle)
    box("Cartridge | stylus throat", (10.2, 7.8, 3.1), here(0, 47, 56.4),
        c, m['void'], 0.7, angle)
    rod("Stylus | cantilever", here(0, 46, 56.1), here(0, 52.3, 53.6), 0.42, c, m['steel'], steps=24)
    lathe("Stylus | diamond tip", [(0.08, 0), (0.40, 0.66), (0.28, 1.03)],
          here(0, 52.3, 52.7), c, m['steel'], steps=16)
    path("Headshell | matte gold finger lift", [here(8.7, 24, 69.3), here(15, 24, 69.6),
         here(21, 23.2, 70.0), here(25, 22.2, 70.4)], 1.04, c, m['tube'], smooth=True)
    box("Headshell | finger lift grip", (9.0, 2.3, 1.2), here(21.5, 22.9, 70.1),
        c, m['rim'], 0.42, angle - 0.14)


def make_cover(c, m):
    # Molded acrylic shell. Outer face and inner cavity share the beveled lower rim.
    profile = [
        (455.5, 351, 7.4, 2.0), (457, 352.5, 8.1, 3.0),
        (459.5, 355, 9.4, 47.7), (458.8, 354.3, 8.7, 49.0), (457.0, 352.5, 7.9, 49.8),
        (451.2, 346.7, 5.3, 2.0), (452.0, 347.5, 5.8, 3.1),
        (454.6, 350.1, 7.5, 46.5), (453.5, 349, 6.9, 47.35),
    ]
    loops = [rounded_rect(*parameters, center_y=-174.0) for parameters in profile]
    n = len(loops[0])
    faces = []
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8), (0, 5)):
        for i in range(n):
            j = (i + 1) % n
            faces.append((a * n + i, a * n + j, b * n + j, b * n + i))
    faces += [tuple(range(4 * n, 5 * n)), tuple(reversed(range(8 * n, 9 * n)))]
    cover = mesh("Molded acrylic cover", [v for loop in loops for v in loop], faces, c, m['acrylic'],
                 origin=(0, 179, 53), smooth=True)
    cover.data.polygons[-1].use_smooth = cover.data.polygons[-2].use_smooth = False
    cover.rotation_euler.x = math.radians(-67)
    cover["Closed rotation X (degrees)"] = 0.0
    cover["Acrylic thickness (mm)"] = 2.45
    return cover


def point_at(obj, target):
    obj.rotation_euler = (Vector(metres(target)) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def area(name, position, target, energy, size, color, c, size_y=None):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.color = color
    if size_y:
        light.shape = 'RECTANGLE'
        light.size_y = size_y * MM
    else:
        light.shape = 'DISK'
    light.size = size * MM
    obj = bpy.data.objects.new(name, light)
    c.objects.link(obj)
    obj.location = metres(position)
    point_at(obj, target)


def make_shot(scene, material, overhead):
    c = group("Studio | camera, lights and floor", scene.collection)
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene.render.engine = 'CYCLES'
    has_cpu_denoiser = bool(getattr(_cycles, "with_openimagedenoise", False))
    scene.cycles.samples = 96 if has_cpu_denoiser else 160
    scene.cycles.adaptive_threshold = 0.018
    scene.cycles.use_denoising = has_cpu_denoiser
    scene.cycles.max_bounces = 10
    scene.cycles.transmission_bounces = 8
    scene.render.resolution_x, scene.render.resolution_y = (2600, 2080) if overhead else (2200, 1850)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = "//top.png" if overhead else "//three-quarter.png"
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -2.5
    world = bpy.data.worlds.new(f"{scene.name} | studio bounce")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.29, 0.33, 0.40, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.15
    scene.world = world
    box("Charcoal seamless floor", (30000, 30000, 8), (0, 0, -4.08),
        c, material, radius=0)

    name = "Camera | orthographic overhead" if overhead else "Camera | three-quarter inspection"
    data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, data)
    c.objects.link(camera)
    scene.camera = camera
    data.clip_start = 0.005
    data.clip_end = 50
    if overhead:
        camera.location = metres((0, 7, 850))
        data.type = 'ORTHO'
        data.ortho_scale = 0.540
    else:
        camera.location = metres((532, -865, 410))
        data.type = 'PERSP'
        data.lens = 53
        point_at(camera, (0, 7, 141))
    area("Key | warm window from upper left", (-420, 310, 545), (-50, 0, 34),
         45 if overhead else 40, 385, (1.0, 0.86, 0.72), c, size_y=540)
    area("Fill | cool bounced card", (400, -210, 500), (65, -20, 30),
         8 if overhead else 11, 470, (0.77, 0.85, 1.0), c)
    area("Edge | long softbox", (294, 430, 290), (38, 30, 49), 11, 290,
         (1.0, 0.89, 0.74), c, size_y=490)
    if overhead:
        area("Overhead bounce | brushed metal", (-73, -46, 365), (-46, -27, 41),
             6, 330, (1.0, 0.94, 0.86), c, size_y=375)
    else:
        area("Front bounce | feet and plinth", (30, -525, 115), (0, -120, 15),
             13, 250, (1.0, 0.93, 0.86), c, size_y=580)


def build():
    original = bpy.context.scene
    top = bpy.data.scenes.new("01 | Top")
    detail = bpy.data.scenes.new("02 | Three-quarter")
    if bpy.context.window:
        bpy.context.window.scene = top

    whole = group("Turntable | wine lacquer and matte gold", top.collection)
    detail.collection.children.link(whole)
    c = group("01 · Plinth and underside", whole)
    feet = group("02 · Isolation feet", whole)
    rear = group("03 · Rear terminals", whole)
    hinges = group("04 · Hinges", whole)
    platter = group("05 · Platter and bearing", whole)
    controls = group("06 · Speed and power controls", whole)
    fixed = group("07 · Tonearm base and cue mechanism", whole)
    moving = group("08 · Tonearm, cartridge and stylus", whole)
    cutters = group("09 · Recess and bore tools", whole)
    cover = group("10 · Hinged acrylic cover", detail.collection)
    m = make_materials()

    make_body(c, feet, rear, hinges, cutters, m)
    make_platter(platter, m)
    make_controls(controls, m)
    make_tonearm(fixed, moving, cutters, m)
    make_cover(cover, m)
    make_shot(top, m['floor'], overhead=True)
    make_shot(detail, m['floor'], overhead=False)

    # Keep Boolean operands available to the depsgraph but out of view in either scene.
    for scene in (top, detail):
        view = scene.view_layers[0]
        view.update()
        for obj in cutters.objects:
            obj.hide_set(True, view_layer=view)
    for screen in bpy.data.screens:
        for region in screen.areas:
            if region.type == 'VIEW_3D':
                viewport = region.spaces.active
                viewport.region_3d.view_perspective = 'CAMERA'
                viewport.overlay.show_overlays = False
                viewport.shading.type = "SOLID"
                viewport.shading.color_type = 'MATERIAL'

    # A fresh default scene has no project content to preserve.
    if original.name == "Scene" and set(original.objects.keys()) <= {"Camera", "Cube", "Light"}:
        bpy.data.scenes.remove(original)
    source = Path(globals().get("__file__", ""))
    if source.is_file() and bpy.data.texts.get("build_turntable.py") is None:
        bpy.data.texts.load(str(source), internal=True)
    if bpy.context.window:
        bpy.context.window.scene = top
    return top, detail


def main():
    cli = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Save the assembled Blender document")
    args = parser.parse_args(cli)
    build()
    if args.output:
        destination = args.output.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)


if __name__ == "__main__":
    main()

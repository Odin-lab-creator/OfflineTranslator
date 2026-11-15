"""Проба Blender: бункер в разрезе, 10 с. Запуск: /home/user/bpyenv/bin/python test_scene.py OUT_DIR [кадры: 1-300]
Рендер Cycles на процессоре в 270×480, потом увеличение ×4 без сглаживания → пиксельный вид 1080×1920."""
import math
import random
import sys

import bpy

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bl_out"
FR = sys.argv[2] if len(sys.argv) > 2 else "1-300"
f0, f1 = (int(x) for x in FR.split("-"))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 300
sc.render.fps = 30


# ---------- материалы ----------
def mat(name, color, rough=0.9, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def noise_mat(name, c1, c2, scale=6.0, stones=None):
    """Земля: шум из двух оттенков + камешки (вороной)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeNewGeometry")   # координаты сцены, а не растянутой коробки
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Position"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.4, 0.65
    ramp.color_ramp.elements[0].color, ramp.color_ramp.elements[1].color = (*c1, 1), (*c2, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    if stones:
        vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 9
        nt.links.new(tc.outputs["Position"], vo.inputs["Vector"])
        st = nt.nodes.new("ShaderNodeValToRGB")
        st.color_ramp.elements[0].position, st.color_ramp.elements[1].position = 0.06, 0.08
        st.color_ramp.elements[0].color, st.color_ramp.elements[1].color = (1, 1, 1, 1), (0, 0, 0, 1)
        nt.links.new(vo.outputs["Distance"], st.inputs["Fac"])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
        nt.links.new(st.outputs["Color"], mix.inputs["Factor"])
        nt.links.new(col, mix.inputs[6])
        mix.inputs[7].default_value = (*stones, 1)
        col = mix.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    return m


def planks_mat(name, c1, c2, vertical=True):
    """Доски: кирпичная текстура, вытянутая в длинные планки."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.85
    tc = nt.nodes.new("ShaderNodeNewGeometry")   # координаты сцены, а не растянутой коробки
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, math.pi / 2 if vertical else 0, 0)
    nt.links.new(tc.outputs["Position"], mp.inputs["Vector"])
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value, br.inputs["Color2"].default_value = (*c1, 1), (*c2, 1)
    br.inputs["Mortar"].default_value = (0.12, 0.07, 0.04, 1)
    br.inputs["Scale"].default_value = 2.2
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Brick Width"].default_value = 2.2
    br.inputs["Row Height"].default_value = 0.22
    nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    return m


M = {
    "earth": noise_mat("earth", (0.34, 0.19, 0.09), (0.24, 0.13, 0.06), 4, stones=(0.42, 0.40, 0.36)),
    "rock": noise_mat("rock", (0.16, 0.16, 0.17), (0.10, 0.10, 0.11), 3, stones=(0.28, 0.28, 0.30)),
    "cave": noise_mat("cave", (0.20, 0.12, 0.07), (0.14, 0.08, 0.05), 6, stones=(0.30, 0.27, 0.24)),
    "grass": mat("grass", (0.10, 0.28, 0.07)),
    "wood": planks_mat("wood", (0.50, 0.30, 0.15), (0.40, 0.23, 0.11)),
    "floor": planks_mat("floor", (0.28, 0.16, 0.08), (0.22, 0.12, 0.06), vertical=False),
    "beam": mat("beam", (0.34, 0.20, 0.10)),
    "crate": mat("crate", (0.22, 0.13, 0.07)),
    "house": planks_mat("house", (0.30, 0.19, 0.11), (0.25, 0.15, 0.09), vertical=False),
    "roof": mat("roof", (0.25, 0.08, 0.06)),
    "pine": mat("pine", (0.05, 0.17, 0.09)),
    "trunk": mat("trunk", (0.18, 0.10, 0.05)),
    "fence": mat("fence", (0.35, 0.24, 0.14)),
    "metal": mat("metal", (0.35, 0.36, 0.38), 0.5),
    "jar": mat("jar", (0.55, 0.12, 0.08), 0.3),
    "mattress": mat("mattress", (0.45, 0.10, 0.08)),
    "pillow": mat("pillow", (0.75, 0.72, 0.65)),
    "moon": mat("moon", (1, 1, 0.9), emit=(1.0, 0.97, 0.85), strength=6),
    "star": mat("star", (1, 1, 1), emit=(0.9, 0.92, 1.0), strength=8),
    "flame": mat("flame", (1, 0.7, 0.3), emit=(1.0, 0.65, 0.25), strength=40),
    "wax": mat("wax", (0.9, 0.88, 0.8)),
    "window": mat("window", (0.05, 0.06, 0.08)),
    # люди
    "skin": mat("skin", (0.80, 0.55, 0.40)), "cap": mat("cap", (0.85, 0.30, 0.04)), "pom": mat("pom", (0.9, 0.9, 0.86)),
    "jacket": mat("jacket", (0.08, 0.22, 0.55)), "jeans": mat("jeans", (0.10, 0.10, 0.14)),
    "boot": mat("boot", (0.12, 0.07, 0.04)), "pack": mat("pack", (0.25, 0.18, 0.10)), "eye": mat("eye", (0.02, 0.02, 0.02)),
    "zskin": mat("zskin", (0.32, 0.45, 0.22)), "zshirt": mat("zshirt", (0.22, 0.20, 0.18)),
    "zpants": mat("zpants", (0.13, 0.14, 0.12)), "zeye": mat("zeye", (1, 0.1, 0.05), emit=(1, 0.08, 0.03), strength=25),
    "blood": mat("blood", (0.25, 0.02, 0.02)),
}


def box(name, size, loc, m, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = size
    o.data.materials.append(M[m])
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


def empty(name, loc, parent=None):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    sc.collection.objects.link(o)
    if parent:
        o.parent = parent
    return o


# ---------- земля в разрезе: блок с вырезанными комнатами (лицевая сторона открыта к камере) ----------
earth = box("earth", (14, 3, 6), (0, 1.5, -3), "earth")
rock = box("rock", (14, 3, 4), (0, 1.5, -8), "rock")
box("grass", (14, 3, 0.12), (0, 1.5, 0.06), "grass")
ROOMS = {"cellar": ((-1.3, 1.6), (-1.7, -0.25)), "shaft": ((-0.25, 0.65), (-2.8, -1.6)), "room": ((-3.6, 2.6), (-4.6, -2.75))}
for nm, ((x0, x1), (z0, z1)) in ROOMS.items():
    cut = box("cut_" + nm, (x1 - x0, 2.2, z1 - z0), ((x0 + x1) / 2, 1.0, (z0 + z1) / 2), "cave")
    cut.hide_render = True
    cut.display_type = "WIRE"
    md = earth.modifiers.new("b_" + nm, "BOOLEAN")
    md.operation, md.object = "DIFFERENCE", cut
    # задняя стенка выемки
    box("back_" + nm, (x1 - x0, 0.05, z1 - z0), ((x0 + x1) / 2, 2.1, (z0 + z1) / 2), "cave")
# комната: доски, пол, балка, стойки
box("roomwall", (6.2, 0.05, 1.85), (-0.5, 2.05, -3.68), "wood")
box("roomfloor", (6.2, 2.2, 0.12), (-0.5, 1.0, -4.54), "floor")
box("beam", (6.2, 0.25, 0.18), (-0.5, 1.9, -2.84), "beam")
for x in (-3.45, 2.45):
    box("post", (0.16, 0.2, 1.85), (x, 1.9, -3.68), "beam")
# погреб: полки с банками
for sx in (-1.0, 0.95):
    box("shelf", (0.5, 0.3, 0.04), (sx, 1.9, -0.95), "beam")
    for k in range(4):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.16, location=(sx - 0.18 + k * 0.12, 1.85, -0.85))
        bpy.context.object.data.materials.append(M["jar"])
# лестница от люка до пола комнаты
for xr in (-0.05, 0.45):
    box("rail", (0.05, 0.05, 4.6), (xr, 1.4, -2.3), "beam")
for i in range(18):
    box("rung", (0.5, 0.04, 0.035), (0.2, 1.4, -4.4 + i * 0.25), "beam")
# люк
box("hatch", (1.0, 1.0, 0.07), (0.2, 1.4, 0.14), "fence")
# матрас, ящик со свечой
box("mattress", (1.6, 1.0, 0.2), (-2.6, 1.3, -4.38), "mattress")
box("pillow", (0.4, 0.6, 0.12), (-3.2, 1.3, -4.22), "pillow")
box("crate", (0.45, 0.45, 0.45), (1.6, 1.4, -4.25), "crate")
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.16, location=(1.6, 1.3, -3.94))
bpy.context.object.data.materials.append(M["wax"])
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=(1.6, 1.3, -3.83))
bpy.context.object.data.materials.append(M["flame"])

# ---------- поверхность: дом, забор, ёлки, небо ----------
box("house", (2.6, 2.4, 2.0), (-4.6, 2.3, 1.0), "house")
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=2.1, depth=1.3, location=(-4.6, 2.3, 2.65), rotation=(0, 0, math.pi / 4))
bpy.context.object.data.materials.append(M["roof"])
box("window", (0.6, 0.05, 0.5), (-4.0, 1.08, 1.2), "window")
box("door", (0.6, 0.05, 1.1), (-5.2, 1.08, 0.55), "beam")
for i in range(9):
    box("fence", (0.12, 0.06, 0.9 - (0.3 if i == 4 else 0)), (-2.9 + i * 0.32, 2.6, 0.45), "fence")
box("fencebar", (2.9, 0.04, 0.08), (-1.6, 2.58, 0.6), "fence")
rnd = random.Random(3)
for i in range(16):
    x = -6.5 + i * 0.95 + rnd.uniform(-0.3, 0.3)
    y = 3.4 + rnd.uniform(0, 3)
    h = rnd.uniform(1.6, 2.6)
    if -5.9 < x < -3.3 and y < 4:
        continue
    box("trunk", (0.15, 0.15, h * 0.3), (x, y, h * 0.15), "trunk")
    for k in range(3):
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=h * (0.36 - k * 0.08), depth=h * 0.45,
                                        location=(x, y, h * (0.35 + k * 0.22)))
        bpy.context.object.data.materials.append(M["pine"])
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, location=(1.5, 14, 4.9))
bpy.context.object.data.materials.append(M["moon"])
for i in range(60):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.03, location=(rnd.uniform(-4, 4), 15, rnd.uniform(2.5, 9)))
    bpy.context.object.data.materials.append(M["star"])

world = bpy.data.worlds.new("night")
sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.04, 0.10, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# ---------- свет ----------
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(-25), 0))
sun = bpy.context.object.data; sun.energy = 0.25; sun.color = (0.6, 0.7, 1.0)
bpy.ops.object.light_add(type="POINT", location=(1.6, 1.0, -3.5))
candle = bpy.context.object; candle.data.color = (1.0, 0.62, 0.28); candle.data.shadow_soft_size = 0.05
for f in range(1, 301, 3):                                     # мерцание свечи
    candle.data.energy = 22 + 5 * math.sin(f * 0.9) + 3 * math.sin(f * 2.3)
    candle.data.keyframe_insert("energy", frame=f)
bpy.ops.object.light_add(type="SPOT", location=(0.2, 1.4, -0.1), rotation=(0, 0, 0))
cel = bpy.context.object.data; cel.energy = 25; cel.color = (0.6, 0.7, 1.0); cel.spot_size = 1.2   # луна сквозь щели люка
bpy.ops.object.light_add(type="AREA", location=(-0.5, -3, -3.5), rotation=(math.pi / 2, 0, 0))
fill = bpy.context.object.data; fill.energy = 60; fill.size = 8; fill.color = (0.55, 0.6, 0.9)        # слабая подсветка разреза


# ---------- человечки из кубиков ----------
def person(kind):
    z = kind == "zombie"
    sk = "zskin" if z else "skin"
    top = "zshirt" if z else "jacket"
    legs = "zpants" if z else "jeans"
    root = empty(kind, (0, 0, 0))
    hip = empty(kind + "_hip", (0, 0, 0.82), root)
    parts = {"root": root}
    for side, y in (("L", 0.11), ("R", -0.11)):
        lp = empty(f"{kind}_leg{side}", (0, y, 0.82), root)
        box("leg", (0.18, 0.16, 0.78), (0, y, 0.43), legs, lp)
        box("boot", (0.28, 0.17, 0.12), (0.05, y, 0.06), "boot", lp)
        parts["leg" + side] = lp
    box("torso", (0.26, 0.42, 0.6), (0, 0, 1.12), top, root)
    if z:
        box("blood", (0.02, 0.12, 0.14), (0.135, -0.05, 1.18), "blood", root)
    else:
        box("pack", (0.18, 0.34, 0.42), (-0.21, 0, 1.15), "pack", root)
    neck = empty(kind + "_neck", (0, 0, 1.42), root)
    box("head", (0.3, 0.3, 0.32), (0.02, 0, 1.6), sk, neck)
    box("eye", (0.02, 0.05, 0.05), (0.17, -0.07, 1.63), "zeye" if z else "eye", neck)
    box("eye2", (0.02, 0.05, 0.05), (0.17, 0.07, 1.63), "zeye" if z else "eye", neck)
    if z:
        box("hair", (0.3, 0.3, 0.06), (0.0, 0, 1.77), "zpants", neck)
        box("jaw", (0.04, 0.12, 0.05), (0.17, 0, 1.5), "blood", neck)
    else:
        box("cap", (0.33, 0.33, 0.17), (0.01, 0, 1.8), "cap", neck)
        box("cuff", (0.34, 0.34, 0.06), (0.01, 0, 1.72), "cap", neck)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0.0, 0, 1.94))
        pom = bpy.context.object; pom.data.materials.append(M["pom"]); pom.parent = neck
    for side, y in (("L", 0.27), ("R", -0.27)):
        ap = empty(f"{kind}_arm{side}", (0, y, 1.38), root)
        box("arm", (0.13, 0.13, 0.58), (0, y, 1.1), top, ap)
        box("hand", (0.12, 0.12, 0.1), (0, y, 0.77), sk, ap)
        parts["arm" + side] = ap
    parts["neck"] = neck
    return parts


def key(o, f, loc=None, rot=None):
    if loc is not None:
        o.location = loc
        o.keyframe_insert("location", frame=f)
    if rot is not None:
        o.rotation_euler = rot
        o.keyframe_insert("rotation_euler", frame=f)


# зомби: идёт к люку, останавливается, нюхает
Z = person("zombie")
for f in range(1, 301, 2):
    t = f / 30
    x = -3.2 + min(t, 3.4) * 0.85
    walking = t < 3.4
    key(Z["root"], f, loc=(x, 1.6, 0.12), rot=(0, 0, 0))
    sw = math.sin(t * 5.5) * 0.45 if walking else 0
    key(Z["legL"], f, rot=(0, sw, 0)); key(Z["legR"], f, rot=(0, -sw, 0))
    reach = -1.45 + math.sin(t * 2.2) * 0.12                         # руки вперёд
    key(Z["armL"], f, rot=(0, reach, 0)); key(Z["armR"], f, rot=(0, reach + 0.15, 0))
    key(Z["neck"], f, rot=(0, 0.25 + (0.25 * math.sin(t * 3) if not walking else 0), 0))

# герой: спускается по лестнице (спиной к камере), потом идёт к свече
H = person("hero")
for f in range(1, 301, 2):
    t = f / 30
    if t < 2.6:                                                       # стоит в погребе, смотрит вверх
        key(H["root"], f, loc=(0.55, 1.15, -1.7), rot=(0, 0, math.pi))
        for nm in ("legL", "legR", "armL", "armR"):
            key(H[nm], f, rot=(0, 0, 0))
        key(H["neck"], f, rot=(0, -0.35, 0))
    elif t < 7.2:                                                     # лезет вниз
        k = (t - 2.6) / 4.6
        key(H["root"], f, loc=(0.2, 1.15, -1.7 - k * 2.85), rot=(0, 0, math.pi / 2))
        c = math.sin(t * 6)
        key(H["armL"], f, rot=(0, -2.3 + 0.5 * c, 0)); key(H["armR"], f, rot=(0, -2.3 - 0.5 * c, 0))
        key(H["legL"], f, rot=(0, -0.5 * max(0, c), 0)); key(H["legR"], f, rot=(0, -0.5 * max(0, -c), 0))
        key(H["neck"], f, rot=(0, 0, 0))
    else:                                                             # идёт к свече
        k = min(1, (t - 7.2) / 2.2)
        key(H["root"], f, loc=(0.2 + k * 0.9, 1.15, -4.55), rot=(0, 0, 0))
        sw = math.sin(t * 7) * 0.5 if k < 1 else 0
        key(H["legL"], f, rot=(0, sw, 0)); key(H["legR"], f, rot=(0, -sw, 0))
        key(H["armL"], f, rot=(0, -sw * 0.7, 0)); key(H["armR"], f, rot=(0, sw * 0.7 - (0.9 if k >= 1 else 0), 0))
        key(H["neck"], f, rot=(0, 0.15, 0))

# ---------- камера: с поверхности плавно под землю ----------
bpy.ops.object.camera_add(rotation=(math.pi / 2, 0, 0))
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.ortho_scale = 9.5
sc.camera = cam
for f in range(1, 301, 5):
    t = f / 300
    e = 0 if t < 0.25 else min(1, (t - 0.25) / 0.6)
    e = e * e * (3 - 2 * e)
    key(cam, f, loc=(-0.2, -20, 1.2 - e * 3.7))

# ---------- рендер ----------
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 20
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.cycles.filter_width = 0.6
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.view_settings.exposure = 0.6
sc.render.resolution_x, sc.render.resolution_y = 270, 480
sc.render.use_freestyle = True
sc.render.line_thickness_mode = "ABSOLUTE"
sc.render.line_thickness = 1.0
fs = bpy.context.view_layer.freestyle_settings
ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("lines")
ls.select_by_visibility = True
ls.select_silhouette, ls.select_border, ls.select_crease = True, True, False
if ls.linestyle is None:
    ls.linestyle = bpy.data.linestyles.new("ink")
ls.linestyle.color = (0.03, 0.02, 0.03)
ls.linestyle.thickness = 1.0
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = OUT.rstrip("/") + "/f_"
sc.frame_start, sc.frame_end = f0, f1
bpy.ops.render.render(animation=True)

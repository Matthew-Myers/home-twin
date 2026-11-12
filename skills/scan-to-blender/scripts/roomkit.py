# roomkit.py — building blocks for detailed single-room models (kitchen, office, ...).
# Coordinates are plan metres from the level's south-west corner, z = 0 at the floor. Cabinet runs use a wall frame: walk the room counter-clockwise,
# so for a run p0 -> p1 the room is on the LEFT; u runs along the wall, v out into the room.
import bpy, math, os
from mathutils import Vector

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "polyhaven")

# ---------------------------------------------------------------- scene
def reset(engine='BLENDER_EEVEE'):
    if bpy.app.background:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    else:
        # live Blender (MCP): clear the scene only; a factory reset would unload the MCP add-on
        for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                     bpy.data.cameras, bpy.data.curves, bpy.data.worlds, bpy.data.images):
            for item in list(coll):
                coll.remove(item)
    s = bpy.context.scene
    s.render.engine = engine
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = 'AgX - Medium High Contrast'
    if hasattr(s.eevee, "use_raytracing"):
        s.eevee.use_raytracing = True
    s.eevee.taa_render_samples = 64
    return s

def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob

GPU_BACKENDS = ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI")   # tried in this order; else CPU

def use_cycles(samples=256, exposure=0.0):
    """final renders: Cycles, denoised, on the best GPU backend found (OptiX, CUDA, HIP, Metal,
    oneAPI), falling back to the CPU. Set RENDER_DEVICE=CPU (or a backend name) to force one."""
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons["cycles"].preferences
    want = os.environ.get("RENDER_DEVICE", "").upper()
    order = (want,) if want and want != "CPU" else (() if want == "CPU" else GPU_BACKENDS)
    backend = None
    for b in order:
        try:
            prefs.compute_device_type = b
        except TypeError:
            continue                                        # backend not built into this Blender
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == b]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == b
            backend = b
            break
    s.cycles.device = 'GPU' if backend else 'CPU'
    print(f"roomkit: Cycles on {backend or 'CPU'}")
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    s.cycles.denoiser = 'OPTIX' if backend == 'OPTIX' else 'OPENIMAGEDENOISE'
    s.cycles.max_bounces = 8
    s.view_settings.exposure = exposure

def hdri_world(asset, strength=1.0, rotation=0.0):
    """sky photo as the world light (seen through the windows)"""
    s = bpy.context.scene
    s.world = bpy.data.worlds.new("hdri")
    nt = s.world.node_tree
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(ASSETS, asset, "sky.hdr"), check_existing=True)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value[2] = math.radians(rotation)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], env.inputs["Vector"])
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = strength
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])

# ---------------------------------------------------------------- materials
_mats = {}

def _bsdf(m):
    return m.node_tree.nodes["Principled BSDF"]

def mat(name, rgb, rough=0.6, metal=0.0, coat=0.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    b = _bsdf(m)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    _mats[name] = m
    return m

def glass(name="glass"):
    if name in _mats:
        return _mats[name]
    m = mat(name, (0.9, 0.95, 1.0), 0.0)
    _bsdf(m).inputs["Transmission Weight"].default_value = 1.0
    _bsdf(m).inputs["IOR"].default_value = 1.45
    return m

def emissive(name, rgb, strength):
    if name in _mats:
        return _mats[name]
    m = mat(name, rgb, 0.5)
    _bsdf(m).inputs["Emission Color"].default_value = (*rgb, 1)
    _bsdf(m).inputs["Emission Strength"].default_value = strength
    return m

def pbr(name, asset, size=1.0, tint=None, rot=0.0, normal=0.6, rough_add=0.0, coat=0.0, wash=None, rot3=None):
    """Poly Haven texture set, box-projected at real size: one texture tile = `size` metres.
    Objects here are built in world coordinates, so object space is plan space.
    tint multiplies the colour; wash=(rgb, amount) blends it toward a flat colour.
    rot3=(rx, ry, rz) degrees rotates the projection in 3D: plank textures (boards along image x) come out
    horizontal on walls; vertical boards need ry=90 on walls along x and rx=90 on walls along y."""
    key = f"{name}_{asset}_{size}_{tint}_{rot}_{wash}_{rot3}"
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = _bsdf(m)
    b.inputs["Coat Weight"].default_value = coat
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / size, 1 / size, 1 / size)
    if rot3:
        mp.inputs["Rotation"].default_value = tuple(math.radians(a) for a in rot3)
    else:
        mp.inputs["Rotation"].default_value[2] = math.radians(rot)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(fname, color):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(ASSETS, asset, fname), check_existing=True)
        if not color:
            n.image.colorspace_settings.name = "Non-Color"
        n.projection = 'BOX'; n.projection_blend = 0.2
        nt.links.new(mp.outputs[0], n.inputs["Vector"])
        return n

    diff = img("diff.jpg", True)
    col = diff.outputs["Color"]
    if tint:
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs[0].default_value = 1.0
        mul.inputs[7].default_value = (*tint, 1)
        nt.links.new(col, mul.inputs[6]); col = mul.outputs[2]
    if wash:
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
        mix.inputs[0].default_value = wash[1]
        mix.inputs[7].default_value = (*wash[0], 1)
        nt.links.new(col, mix.inputs[6]); col = mix.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    rough = img("rough.jpg", False)
    if rough_add:
        add = nt.nodes.new("ShaderNodeMath"); add.operation = 'ADD'; add.use_clamp = True
        add.inputs[1].default_value = rough_add
        nt.links.new(rough.outputs["Color"], add.inputs[0]); nt.links.new(add.outputs[0], b.inputs["Roughness"])
    else:
        nt.links.new(rough.outputs["Color"], b.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = normal
    nt.links.new(img("nor.jpg", False).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    _mats[key] = m
    return m

def _plane_vector(nt, plane):
    """world position -> 2D texture vector on the given plane ('xy', 'xz', 'yz')"""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    com = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    a, b = plane
    nt.links.new(sep.outputs[a.upper()], com.inputs[0])
    nt.links.new(sep.outputs[b.upper()], com.inputs[1])
    return com.outputs[0]

def tile(name, rgb, grout, w, h, plane, rough=0.25, vary=0.06, offset=0.5):
    """running-bond tile / brick / plank pattern in real metres"""
    key = f"{name}_{plane}"
    if key in _mats:
        return _mats[key]
    m = mat(key, rgb, rough)
    nt = m.node_tree
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = offset
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = w
    br.inputs["Row Height"].default_value = h
    br.inputs["Mortar Size"].default_value = 0.0025 if grout else 0.0006
    br.inputs["Color1"].default_value = (*rgb, 1)
    br.inputs["Color2"].default_value = (*[max(0, c * (1 - vary)) for c in rgb], 1)
    br.inputs["Mortar"].default_value = (*(grout or [c * 0.7 for c in rgb]), 1)
    nt.links.new(_plane_vector(nt, plane), br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], _bsdf(m).inputs["Base Color"])
    _mats[key] = m
    return m

def basketweave(name, rgb, grout, L=0.20, rough=0.55, vary=0.15):
    """basketweave brick floor: L x L squares, each two L x L/2 bricks, alternating direction"""
    if name in _mats:
        return _mats[name]
    m = mat(name, rgb, rough)
    nt = m.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    def brick(swap):
        com = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(sep.outputs["Y" if swap else "X"], com.inputs[0])
        nt.links.new(sep.outputs["X" if swap else "Y"], com.inputs[1])
        br = nt.nodes.new("ShaderNodeTexBrick")
        br.offset = 0.0
        br.inputs["Scale"].default_value = 1.0
        br.inputs["Brick Width"].default_value = L
        br.inputs["Row Height"].default_value = L / 2
        br.inputs["Mortar Size"].default_value = 0.004
        br.inputs["Bias"].default_value = 0.0
        br.inputs["Color1"].default_value = (*rgb, 1)
        br.inputs["Color2"].default_value = (*[c * (1 - vary) for c in rgb], 1)
        br.inputs["Mortar"].default_value = (*grout, 1)
        nt.links.new(com.outputs[0], br.inputs["Vector"])
        return br.outputs["Color"]
    # which square: (floor(x/L) + floor(y/L)) mod 2
    def cell(axis):
        d = nt.nodes.new("ShaderNodeMath"); d.operation = 'DIVIDE'; d.inputs[1].default_value = L
        nt.links.new(sep.outputs[axis], d.inputs[0])
        fl = nt.nodes.new("ShaderNodeMath"); fl.operation = 'FLOOR'
        nt.links.new(d.outputs[0], fl.inputs[0])
        return fl.outputs[0]
    add = nt.nodes.new("ShaderNodeMath"); add.operation = 'ADD'
    nt.links.new(cell("X"), add.inputs[0]); nt.links.new(cell("Y"), add.inputs[1])
    mod = nt.nodes.new("ShaderNodeMath"); mod.operation = 'FLOORED_MODULO'; mod.inputs[1].default_value = 2
    nt.links.new(add.outputs[0], mod.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    nt.links.new(mod.outputs[0], mix.inputs[0])
    nt.links.new(brick(False), mix.inputs[6]); nt.links.new(brick(True), mix.inputs[7])
    nt.links.new(mix.outputs[2], _bsdf(m).inputs["Base Color"])
    _mats[name] = m
    return m

def wood(name, light, dark, plane="xy", along="x", rough=0.45, scale=1.0):
    """streaky wood grain running along `along`"""
    key = f"{name}_{plane}_{along}"
    if key in _mats:
        return _mats[key]
    m = mat(key, light, rough)
    nt = m.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping")
    s = [40 * scale] * 3
    s["xyz".index(along)] = 1.5 * scale            # long streaks along the grain
    mp.inputs["Scale"].default_value = s
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Distortion"].default_value = 1.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (*light, 1)
    nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], _bsdf(m).inputs["Base Color"])
    _mats[key] = m
    return m

def plank_floor(name, light, dark, plank_w=0.19, plank_l=1.4):
    """wood plank floor: staggered planks with grain"""
    if name in _mats:
        return _mats[name]
    m = wood(name + "_g", light, dark, along="x", rough=0.35)
    nt = m.node_tree
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.37
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = plank_l
    br.inputs["Row Height"].default_value = plank_w
    br.inputs["Mortar Size"].default_value = 0.0008
    br.inputs["Color1"].default_value = (1, 1, 1, 1)
    br.inputs["Color2"].default_value = (0.82, 0.82, 0.82, 1)
    br.inputs["Mortar"].default_value = (0.35, 0.35, 0.35, 1)
    nt.links.new(_plane_vector(nt, "xy"), br.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
    mul.inputs[0].default_value = 1.0
    ramp_out = _bsdf(m).inputs["Base Color"].links[0].from_socket
    nt.links.new(ramp_out, mul.inputs[6])
    nt.links.new(br.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], _bsdf(m).inputs["Base Color"])
    _mats[name] = m
    return m

def terrazzo(name, base, chips, scale=70):
    """cream base with scattered coloured chips"""
    if name in _mats:
        return _mats[name]
    m = mat(name, base, 0.3)
    nt = m.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = scale
    nt.links.new(geo.outputs["Position"], vor.inputs["Vector"])
    pick = nt.nodes.new("ShaderNodeValToRGB")          # chip colour from the cell's random colour
    pick.color_ramp.interpolation = 'CONSTANT'
    els = pick.color_ramp.elements
    els[0].color = (*chips[0], 1)
    els[1].position = 0.5; els[1].color = (*chips[1 % len(chips)], 1)
    for i, c in enumerate(chips[2:]):
        e = els.new(0.5 + 0.5 * (i + 1) / len(chips)); e.color = (*c, 1)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vor.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[0], pick.inputs["Fac"])
    is_chip = nt.nodes.new("ShaderNodeMath"); is_chip.operation = 'LESS_THAN'
    is_chip.inputs[1].default_value = 0.18
    nt.links.new(vor.outputs["Distance"], is_chip.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = (*base, 1)
    nt.links.new(is_chip.outputs[0], mix.inputs[0])
    nt.links.new(pick.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], _bsdf(m).inputs["Base Color"])
    _mats[name] = m
    return m

# ---------------------------------------------------------------- geometry
def mesh_box(name, corners, m, bevel=0.002):
    """corners: 8 world points in the order of box_corners()"""
    me = bpy.data.meshes.new(name)
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    me.from_pydata([tuple(c) for c in corners], [], faces)
    me.update()
    ob = link(bpy.data.objects.new(name, me))
    if m:
        me.materials.append(m)
    if bevel:
        bv = ob.modifiers.new("bevel", 'BEVEL')
        bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
    return ob

def box(name, x0, y0, z0, x1, y1, z1, m, bevel=0.002):
    return mesh_box(name, [Vector(p) for p in (
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))], m, bevel)

class Frame:
    """wall frame: origin p0, u along the wall toward p1, v into the room (left of p0->p1)"""
    def __init__(self, p0, p1):
        self.o = Vector((*p0, 0))
        d = Vector((p1[0] - p0[0], p1[1] - p0[1], 0))
        self.length = d.length
        self.u = d.normalized()
        self.v = Vector((-self.u.y, self.u.x, 0))
        self.plane = "xz" if abs(self.u.x) > 0.5 else "yz"
        self.along = "x" if abs(self.u.x) > 0.5 else "y"
        self.angle = math.atan2(self.u.y, self.u.x)

    def at(self, u, v, z):
        return self.o + self.u * u + self.v * v + Vector((0, 0, z))

    def box(self, name, u0, u1, v0, v1, z0, z1, m, bevel=0.002):
        c = [self.at(u, v, z) for z in (z0, z1) for (u, v) in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
        return mesh_box(name, c, m, bevel)

    def cyl(self, name, u, v, z0, z1, r, m, axis="z", verts=24):
        depth = z1 - z0
        if axis == "z":
            bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts,
                                                location=self.at(u, v, (z0 + z1) / 2))
        else:   # along u, z0..z1 are u positions
            bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts,
                                                location=self.at((z0 + z1) / 2, u, v),
                                                rotation=(0, math.pi / 2, self.angle))
        ob = bpy.context.object; ob.name = name
        ob.data.materials.append(m)
        return ob

# ---------------------------------------------------------------- room shell
def shell(outline, height, openings, wall_m, floor_m, ceiling_m=None, thick=0.12, base_m=None):
    """walls (with openings), floor and ceiling for a room.
    outline: counter-clockwise interior corners. openings: {edge index: [(s0, s1, z0, z1), ...]}
    measured along each edge from its start corner."""
    n = len(outline)
    def convex(j):
        """True at an outside corner (left turn on a CCW outline): walls extend to close it.
        At inside corners an extension would poke into the room."""
        (ax, ay), (bx, by), (cx, cy) = outline[j - 1], outline[j], outline[(j + 1) % n]
        return (bx - ax) * (cy - by) - (by - ay) * (cx - bx) > 0
    for i in range(n):
        f = Frame(outline[i], outline[(i + 1) % n])
        cuts = sorted(openings.get(i, []))
        # solid spans between openings, and the wall above/below each opening
        edges = [0.0] + [c for s0, s1, _, _ in cuts for c in (s0, s1)] + [f.length]
        ext0 = thick if convex(i) else 0.0
        ext1 = thick if convex((i + 1) % n) else 0.0
        for k in range(0, len(edges), 2):
            if edges[k + 1] - edges[k] > 1e-3:
                a = edges[k] - (ext0 if k == 0 else 0)
                b = edges[k + 1] + (ext1 if k + 2 == len(edges) else 0)
                f.box(f"wall{i}_{k}", a, b, -thick, 0, 0, height, wall_m, 0)
        for j, (s0, s1, z0, z1) in enumerate(cuts):
            if z0 > 0:
                f.box(f"wall{i}_sill{j}", s0, s1, -thick, 0, 0, z0, wall_m, 0)
            f.box(f"wall{i}_head{j}", s0, s1, -thick, 0, z1, height, wall_m, 0)
        if base_m:   # baseboard
            for k in range(0, len(edges), 2):
                if edges[k + 1] - edges[k] > 1e-3:
                    f.box(f"base{i}_{k}", edges[k], edges[k + 1], 0, 0.012, 0, 0.09, base_m, 0.001)
    xs = [p[0] for p in outline]; ys = [p[1] for p in outline]
    me = bpy.data.meshes.new("floor")
    me.from_pydata([(x, y, 0) for x, y in outline], [], [list(range(n))])
    fl = link(bpy.data.objects.new("floor", me)); me.materials.append(floor_m)
    if ceiling_m:
        me2 = bpy.data.meshes.new("ceiling")
        me2.from_pydata([(x, y, height) for x, y in outline], [], [list(reversed(range(n)))])
        cl = link(bpy.data.objects.new("ceiling", me2)); me2.materials.append(ceiling_m)
    # outdoor ground beyond the windows
    box("ground", min(xs) - 30, min(ys) - 30, -0.6, max(xs) + 30, max(ys) + 30, -0.5,
        mat("ground", (0.25, 0.3, 0.18), 1.0), 0)

def window(f, s0, s1, z0, z1, frame_m, mullions=(1, 1)):
    """window in a wall opening: frame, glass, optional grid (cols, rows)"""
    t = 0.05
    f.box("win_l", s0, s0 + t, -0.08, -0.02, z0, z1, frame_m)
    f.box("win_r", s1 - t, s1, -0.08, -0.02, z0, z1, frame_m)
    f.box("win_b", s0, s1, -0.08, -0.02, z0, z0 + t, frame_m)
    f.box("win_t", s0, s1, -0.08, -0.02, z1 - t, z1, frame_m)
    f.box("win_sill", s0 - 0.04, s1 + 0.04, -0.12, 0.04, z0 - 0.02, z0, frame_m)
    f.box("win_glass", s0, s1, -0.055, -0.045, z0, z1, glass(), 0)
    cols, rows = mullions
    for c in range(1, cols):
        u = s0 + (s1 - s0) * c / cols
        f.box("win_mv", u - 0.012, u + 0.012, -0.07, -0.04, z0, z1, frame_m, 0.001)
    for r in range(1, rows):
        z = z0 + (z1 - z0) * r / rows
        f.box("win_mh", s0, s1, -0.07, -0.04, z - 0.012, z + 0.012, frame_m, 0.001)

def door_casing(f, s0, s1, z1, m, w=0.07):
    f.box("case_l", s0 - w, s0, 0, 0.015, 0, z1 + w, m, 0.002)
    f.box("case_r", s1, s1 + w, 0, 0.015, 0, z1 + w, m, 0.002)
    f.box("case_t", s0 - w, s1 + w, 0, 0.015, z1, z1 + w, m, 0.002)

# ---------------------------------------------------------------- cabinetry
class Style:
    """cabinet look: door style 'shaker' | 'slab' | 'raised'; pull 'bar' | 'knob' | 'cutout' | 'wire'"""
    def __init__(self, box_m, door_m, counter_m, pull_m, door="slab", pull="bar",
                 counter_t=0.03, splash_m=None, splash_h=0.45, toe_m=None, upper_door_m=None, faucet_m=None):
        self.box_m, self.door_m, self.counter_m, self.pull_m = box_m, door_m, counter_m, pull_m
        self.faucet_m = faucet_m          # None = chrome
        self.door, self.pull, self.counter_t = door, pull, counter_t
        self.splash_m, self.splash_h = splash_m, splash_h
        self.toe_m = toe_m or box_m
        self.upper_door_m = upper_door_m or door_m

BASE_D, BASE_H, TOE_H, TOE_IN, GAP = 0.60, 0.87, 0.10, 0.06, 0.003

def _door(f, st, name, u0, u1, z0, z1, v, m, pull_at="top", grain=None):
    """one door or drawer front from u0..u1, z0..z1, front face at v"""
    t = 0.019
    face = f.box(name, u0 + GAP, u1 - GAP, v, v + t, z0 + GAP, z1 - GAP, m, 0.0015)
    if st.door == "shaker":       # recessed centre panel: rails and stiles proud of it
        r = min(0.065, (u1 - u0) / 5, (z1 - z0) / 5)
        f.box(name + "_rl", u0 + GAP, u0 + GAP + r, v + t, v + t + 0.006, z0 + GAP, z1 - GAP, m, 0.001)
        f.box(name + "_rr", u1 - GAP - r, u1 - GAP, v + t, v + t + 0.006, z0 + GAP, z1 - GAP, m, 0.001)
        f.box(name + "_rb", u0 + GAP + r, u1 - GAP - r, v + t, v + t + 0.006, z0 + GAP, z0 + GAP + r, m, 0.001)
        f.box(name + "_rt", u0 + GAP + r, u1 - GAP - r, v + t, v + t + 0.006, z1 - GAP - r, z1 - GAP, m, 0.001)
    if st.door == "raised":       # as-is builder-grade: bevelled raised panel
        r = min(0.07, (u1 - u0) / 5, (z1 - z0) / 5)
        f.box(name + "_rp", u0 + r, u1 - r, v + t, v + t + 0.008, z0 + r, z1 - r, m, 0.006)
    fz = v + t + (0.006 if st.door in ("shaker", "raised") else 0)
    pm = st.pull_m
    if pull_at == "none" or st.pull == "none":
        return face
    if st.pull == "cutout":       # finger groove along the top edge
        f.box(name + "_cut", u0 + GAP, u1 - GAP, v + t - 0.004, v + t + 0.001,
              (z1 - 0.025) if pull_at == "top" else z0, (z1 - GAP) if pull_at == "top" else z0 + 0.025,
              mat("shadow", (0.03, 0.03, 0.03), 0.9), 0)
        return face
    zc = (z1 - 0.06) if pull_at == "top" else (z0 + 0.06) if pull_at == "bottom" else (z0 + z1) / 2
    uc = (u0 + u1) / 2
    if st.pull == "knob":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.016, location=f.at(uc, fz + 0.02, zc), segments=16, ring_count=8)
        bpy.context.object.data.materials.append(pm)
    else:                          # bar / wire pull, horizontal
        L = min(0.32, (u1 - u0) * 0.5) if st.pull == "bar" else 0.096
        f.cyl(name + "_pull", fz + 0.025, zc, uc - L / 2, uc + L / 2, 0.006, pm, axis="u", verts=12)
        for e in (uc - L / 2 + 0.01, uc + L / 2 - 0.01):
            f.box(name + "_post", e - 0.004, e + 0.004, fz, fz + 0.025, zc - 0.004, zc + 0.004, pm, 0)
    return face

def base_unit(f, st, u0, u1, kind="doors", depth=BASE_D, h=BASE_H):
    """base cabinet: carcass, toe kick, fronts. kind: doors | drawers | sink | blank"""
    f.box("toe", u0, u1, 0, depth - TOE_IN, 0, TOE_H, st.toe_m, 0)
    f.box("carcass", u0, u1, 0, depth - 0.019, TOE_H, h, st.box_m, 0)
    v = depth - 0.019
    w = u1 - u0
    if kind == "drawers":
        bands = [TOE_H, TOE_H + 0.26, TOE_H + 0.52, h]
        for i in range(3):
            _door(f, st, "drawer", u0, u1, bands[i], bands[i + 1], v, st.door_m, "top")
        return
    top = h - 0.16
    if kind != "sink":
        _door(f, st, "drawer", u0, u1, top, h, v, st.door_m, "middle")
    else:
        _door(f, st, "false", u0, u1, top, h, v, st.door_m, "none" if st.pull == "cutout" else "middle")
    n = 1 if w < 0.55 else 2
    for i in range(n):
        a = u0 + w * i / n; b = u0 + w * (i + 1) / n
        _door(f, st, "door", a, b, TOE_H, top, v, st.door_m, "top")

def tall_unit(f, st, u0, u1, h=2.2, depth=BASE_D, split=0.9):
    f.box("toe", u0, u1, 0, depth - TOE_IN, 0, TOE_H, st.toe_m, 0)
    f.box("carcass", u0, u1, 0, depth - 0.019, TOE_H, h, st.box_m, 0)
    v = depth - 0.019
    n = 1 if (u1 - u0) < 0.55 else 2
    for i in range(n):
        a = u0 + (u1 - u0) * i / n; b = u0 + (u1 - u0) * (i + 1) / n
        _door(f, st, "tall_lo", a, b, TOE_H, split + TOE_H + 0.5, v, st.door_m, "top")
        _door(f, st, "tall_hi", a, b, split + TOE_H + 0.5, h, v, st.door_m, "bottom")

def upper_unit(f, st, u0, u1, z0=1.40, z1=2.20, depth=0.33, pull_at="bottom", open_box=False):
    """wall cabinet; open_box=True leaves it doorless (dark interior, e.g. over a microwave)"""
    if open_box:
        t = 0.018
        for a, b, c, d in ((u0, u0 + t, z0, z1), (u1 - t, u1, z0, z1), (u0, u1, z0, z0 + t), (u0, u1, z1 - t, z1)):
            f.box("upper_open", a, b, 0, depth, c, d, st.box_m, 0)
        f.box("upper_back", u0, u1, 0, 0.005, z0, z1, mat("cab_inside", (0.55, 0.52, 0.47), 0.8), 0)
        return
    f.box("upper", u0, u1, 0, depth - 0.019, z0, z1, st.box_m, 0)
    n = 1 if (u1 - u0) < 0.55 else 2
    for i in range(n):
        a = u0 + (u1 - u0) * i / n; b = u0 + (u1 - u0) * (i + 1) / n
        _door(f, st, "udoor", a, b, z0, z1, depth - 0.019, st.upper_door_m, pull_at)

def glass_upper(f, st, u0, u1, z0, z1, depth=0.34, doors=None, dishes=True):
    """wall cabinet with framed glass doors; shelves and some crockery inside, lit"""
    inside = mat("cab_inside_white", (0.90, 0.89, 0.86), 0.6)
    f.box("gu_back", u0, u1, 0, 0.012, z0, z1, inside, 0)
    for a, b, c, d in ((u0, u0 + 0.018, z0, z1), (u1 - 0.018, u1, z0, z1), (u0, u1, z0, z0 + 0.018), (u0, u1, z1 - 0.018, z1)):
        f.box("gu_case", a, b, 0, depth - 0.02, c, d, st.box_m, 0)
    shelves = [z0 + (z1 - z0) * k / 3 for k in (1, 2)]
    for z in shelves:
        f.box("gu_shelf", u0 + 0.018, u1 - 0.018, 0.012, depth - 0.03, z - 0.009, z + 0.009, glass(), 0)
    if dishes:
        crock = mat("crockery", (0.93, 0.92, 0.88), 0.25)
        for z in [z0 + 0.018] + shelves:
            k = int((u1 - u0) / 0.16)
            for i in range(k):
                u = u0 + 0.08 + i * (u1 - u0 - 0.16) / max(k - 1, 1)
                if i % 3 == 2:      # a stack of plates
                    f.cyl("plates", u, depth * 0.45, z + 0.01, z + 0.07, 0.11, crock, verts=24)
                elif i % 3 == 0:    # a tall jug
                    f.cyl("jug", u, depth * 0.5, z + 0.01, z + 0.2, 0.055, crock, verts=20)
    n = doors or max(1, round((u1 - u0) / 0.45))
    fr = 0.055
    for i in range(n):
        a = u0 + (u1 - u0) * i / n + GAP; b = u0 + (u1 - u0) * (i + 1) / n - GAP
        for c0, c1, d0, d1 in ((a, a + fr, z0, z1), (b - fr, b, z0, z1), (a, b, z0, z0 + fr), (a, b, z1 - fr, z1)):
            f.box("gu_frame", c0, c1, depth - 0.02, depth, d0 + GAP, d1 - GAP, st.upper_door_m, 0.002)
        f.box("gu_glass", a + fr, b - fr, depth - 0.012, depth - 0.008, z0 + fr, z1 - fr, glass(), 0)
        f.box("gu_knob", (a + b) / 2 - 0.012 + ((b - a) / 2 - 0.04) * (1 if i % 2 == 0 else -1),
              (a + b) / 2 + 0.012 + ((b - a) / 2 - 0.04) * (1 if i % 2 == 0 else -1),
              depth, depth + 0.025, z0 + 0.06, z0 + 0.085, st.pull_m, 0.006)
    strip_light(f, u0 + 0.05, u1 - 0.05, depth * 0.5, z1 - 0.03, 6)

def rect_table(x0, y0, x1, y1, h, top_m, base_m, trestle=False):
    box("table_top", x0, y0, h - 0.035, x1, y1, h, top_m, 0.004)
    if trestle:     # two end trestles joined by a stretcher, along the long (y) side
        for y in (y0 + 0.15, y1 - 0.15):
            box("trestle_leg", (x0 + x1) / 2 - 0.04, y - 0.04, 0.05, (x0 + x1) / 2 + 0.04, y + 0.04, h - 0.035, base_m, 0.006)
            box("trestle_foot", x0 + 0.08, y - 0.04, 0, x1 - 0.08, y + 0.04, 0.05, base_m, 0.006)
        box("stretcher", (x0 + x1) / 2 - 0.025, y0 + 0.15, 0.2, (x0 + x1) / 2 + 0.025, y1 - 0.15, 0.26, base_m, 0.004)
    else:
        for x, y in ((x0 + 0.06, y0 + 0.06), (x1 - 0.06, y0 + 0.06), (x0 + 0.06, y1 - 0.06), (x1 - 0.06, y1 - 0.06)):
            box("table_leg", x - 0.025, y - 0.025, 0, x + 0.025, y + 0.025, h - 0.035, base_m, 0.006)

def bench(x0, y0, x1, y1, m, h=0.46):
    """backless bench, long side along y"""
    box("bench_top", x0, y0, h - 0.04, x1, y1, h, m, 0.004)
    for y in (y0 + 0.08, y1 - 0.12):
        box("bench_leg", x0 + 0.03, y, 0, x1 - 0.03, y + 0.04, h - 0.04, m, 0.004)

def beam(x0, y0, x1, y1, ceiling, drop, m):
    """dropped structural beam (e.g. where a load-bearing wall came out)"""
    return box("ceiling_beam", x0, y0, ceiling - drop, x1, y1, ceiling, m, 0.004)   # hidden with the ceiling in cutaways

def open_shelves(f, u0, u1, zs, m, depth=0.26, t=0.04):
    for z in zs:
        f.box("shelf", u0, u1, 0, depth, z, z + t, m, 0.003)

def countertop(f, u0, u1, st, depth=BASE_D + 0.025, h=BASE_H, sinks=(), splash=True, splash_top=None, v0=0.0):
    """counter slab from u0..u1 with sink cut-outs [(u_centre, width)]; v0 < 0 overhangs the back"""
    top = f.box("counter", u0, u1, v0, depth, h, h + st.counter_t, st.counter_m, 0.002)
    if sinks:   # one faucet, centred over the bowl(s)
        uc = sum(c for c, _ in sinks) / len(sinks)
        faucet(f, uc, 0.04, h + st.counter_t, st.faucet_m or mat("chrome", (0.8, 0.8, 0.8), 0.15, 1.0))
    for uc, w in sinks:
        cut = f.box("cut", uc - w / 2, uc + w / 2, 0.08, 0.08 + 0.43, h - 0.3, h + 0.1, None, 0)
        b = top.modifiers.new("sink", 'BOOLEAN'); b.object = cut; b.operation = 'DIFFERENCE'
        cut.hide_render = True; cut.hide_viewport = True
        steel = mat("steel", (0.75, 0.75, 0.76), 0.25, 1.0)
        f.box("basin", uc - w / 2, uc + w / 2, 0.08, 0.51, h - 0.2, h - 0.19, steel, 0)
        for a, b2, c, d in ((uc - w / 2, uc - w / 2 + 0.01, 0.08, 0.51), (uc + w / 2 - 0.01, uc + w / 2, 0.08, 0.51),
                            (uc - w / 2, uc + w / 2, 0.08, 0.09), (uc - w / 2, uc + w / 2, 0.50, 0.51)):
            f.box("basin_w", a, b2, c, d, h - 0.2, h + st.counter_t - 0.002, steel, 0)
    if splash and st.splash_m:
        z1 = splash_top or (h + st.counter_t + st.splash_h)
        f.box("splash", u0, u1, 0, 0.008, h + st.counter_t, z1, st.splash_m, 0)

def faucet(f, u, v, z, m):
    f.cyl("faucet_base", u, v, z, z + 0.03, 0.025, m)
    f.cyl("faucet_neck", u, v, z, z + 0.33, 0.012, m)
    f.box("faucet_spout", u - 0.011, u + 0.011, v, v + 0.22, z + 0.31, z + 0.335, m, 0.004)
    f.box("faucet_tip", u - 0.013, u + 0.013, v + 0.2, v + 0.225, z + 0.25, z + 0.335, m, 0.004)

# ---------------------------------------------------------------- appliances
def range_unit(f, u0, u1, body_m, top_m, style="coil"):
    w = u1 - u0
    f.box("range", u0, u1, 0.02, 0.66, 0, 0.91, body_m, 0.004)
    f.box("range_top", u0, u1, 0.02, 0.66, 0.91, 0.925, top_m, 0.002)
    f.box("oven_win", u0 + 0.09, u1 - 0.09, 0.661, 0.665, 0.32, 0.62, mat("oven_glass", (0.02, 0.02, 0.02), 0.08), 0.002)
    f.box("oven_handle", u0 + 0.06, u1 - 0.06, 0.66, 0.70, 0.74, 0.76, mat("chrome", (0.8, 0.8, 0.8), 0.15, 1.0), 0.005)
    burner = mat("burner", (0.05, 0.05, 0.05), 0.4)
    if style != "glasstop":
        for bu, bv in ((0.25, 0.2), (0.75, 0.2), (0.25, 0.48), (0.75, 0.48)):
            f.cyl("burner", u0 + w * bu, bv + 0.02, 0.925, 0.93, 0.09 if bv < 0.3 else 0.075, burner, verts=32)
    if style == "glasstop":   # smooth black glass top, controls + display on a backguard
        for bu, bv, r in ((0.27, 0.22, 0.10), (0.73, 0.22, 0.09), (0.27, 0.5, 0.08), (0.73, 0.5, 0.10)):
            f.cyl("zone", u0 + w * bu, bv + 0.02, 0.925, 0.9255, r, mat("zone", (0.09, 0.09, 0.09), 0.15), verts=48)
        f.box("backguard", u0, u1, 0.02, 0.10, 0.925, 1.07, body_m, 0.006)
        for uu in (0.1, 0.2, 0.8, 0.9):
            f.box("knob", u0 + w * uu - 0.017, u0 + w * uu + 0.017, 0.10, 0.125, 0.98, 1.015,
                  mat("knob_white", (0.85, 0.85, 0.83), 0.4), 0.012)
        f.box("display", u0 + w * 0.42, u0 + w * 0.58, 0.10, 0.102, 0.99, 1.02, emissive("display", (0.2, 1.0, 0.4), 2.0), 0)
        f.box("oven_drawer", u0 + 0.01, u1 - 0.01, 0.66, 0.67, 0.02, 0.16, body_m, 0.004)
        return
    if style == "coil":   # backguard with knobs
        f.box("backguard", u0, u1, 0.02, 0.09, 0.925, 1.08, body_m, 0.004)
        for i in range(4):
            f.cyl("knob", u0 + w * (0.2 + 0.2 * i), 0.1, 0.99, 1.01, 0.018, burner, axis="z")
    else:                 # pro-style front knobs
        for i in range(5):
            f.box("knob", u0 + w * (0.15 + 0.175 * i) - 0.02, u0 + w * (0.15 + 0.175 * i) + 0.02, 0.66, 0.69, 0.82, 0.86, burner, 0.008)

def fridge(f, u0, u1, body_m, handle_m, depth=0.75, h=1.78, french=True):
    f.box("fridge", u0, u1, 0.0, depth - 0.03, 0, h, body_m, 0.01)
    w = u1 - u0
    if french:
        f.box("fz_door", u0 + 0.004, u1 - 0.004, depth - 0.03, depth, 0.02, 0.66, body_m, 0.008)
        f.box("fl_door", u0 + 0.004, u0 + w / 2 - 0.003, depth - 0.03, depth, 0.68, h - 0.01, body_m, 0.008)
        f.box("fr_door", u0 + w / 2 + 0.003, u1 - 0.004, depth - 0.03, depth, 0.68, h - 0.01, body_m, 0.008)
        for uh in (u0 + w / 2 - 0.05, u0 + w / 2 + 0.05):
            f.box("f_handle", uh - 0.012, uh + 0.012, depth + 0.01, depth + 0.035, 0.85, 1.45, handle_m, 0.006)
        f.box("fz_handle", u0 + 0.15, u1 - 0.15, depth + 0.01, depth + 0.035, 0.58, 0.61, handle_m, 0.006)

def dishwasher(f, u0, u1, front_m, handle_m):
    f.box("dw", u0 + GAP, u1 - GAP, 0.0, 0.6, TOE_H, BASE_H, front_m, 0.004)
    f.box("dw_toe", u0, u1, 0, 0.54, 0, TOE_H, mat("dw_toe", (0.1, 0.1, 0.1), 0.5), 0)
    f.box("dw_handle", u0 + 0.06, u1 - 0.06, 0.6, 0.63, BASE_H - 0.07, BASE_H - 0.05, handle_m, 0.006)

def microwave(f, u0, u1, z0, body_m):
    f.box("mw", u0, u1, 0, 0.38, z0, z0 + 0.42, body_m, 0.006)
    f.box("mw_win", u0 + 0.05, u1 - 0.22, 0.381, 0.384, z0 + 0.07, z0 + 0.33, mat("oven_glass", (0.02, 0.02, 0.02), 0.08), 0.002)

def hood(f, u0, u1, z0, ceiling, m, style="box"):
    if style == "box":       # plaster/panel box hood to the ceiling
        f.box("hood", u0, u1, 0, 0.52, z0, ceiling, m, 0.004)
    else:                    # chimney: canopy + flue
        f.box("hood_canopy", u0, u1, 0, 0.5, z0, z0 + 0.08, m, 0.003)
        w = u1 - u0
        f.box("hood_flue", u0 + w * 0.3, u1 - w * 0.3, 0, 0.28, z0 + 0.08, ceiling, m, 0.003)

# ---------------------------------------------------------------- furniture & lights
def round_table(x, y, d, h, top_m, base_m, pedestal=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=d / 2, depth=0.035, vertices=64, location=(x, y, h - 0.0175))
    bpy.context.object.data.materials.append(top_m)
    if pedestal:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=h - 0.05, vertices=24, location=(x, y, (h - 0.05) / 2 + 0.02))
        bpy.context.object.data.materials.append(base_m)
        bpy.ops.mesh.primitive_cone_add(radius1=0.3, radius2=0.06, depth=0.08, vertices=48, location=(x, y, 0.04))
        bpy.context.object.data.materials.append(base_m)

def _seat_frame(x, y, a, back, half):
    """frame for a seat centred at (x, y) facing angle a: u runs across it, v from the back
    toward the front (the left normal of p0 -> p1 is the facing direction)"""
    fx, fy = math.cos(a), math.sin(a)          # facing
    ux, uy = math.sin(a), -math.cos(a)         # across, so that left(u) = facing
    bx, by = x - fx * back, y - fy * back      # middle of the back edge
    return Frame((bx - ux * half, by - uy * half), (bx + ux * half, by + uy * half))

def chair(x, y, facing, m, style="windsor", seat_h=0.45):
    """facing: angle (deg) the sitter faces"""
    a = math.radians(facing)
    f = _seat_frame(x, y, a, 0.22, 0.22)
    # frame: u across the chair (0..0.44), v from the back toward the front
    f.box("seat", 0, 0.44, 0.0, 0.42, seat_h - 0.03, seat_h, m, 0.006)
    for u, v in ((0.03, 0.03), (0.41, 0.03), (0.03, 0.39), (0.41, 0.39)):
        f.cyl("leg", u, v, 0, seat_h - 0.03, 0.014, m, verts=10)
    if style == "windsor":
        f.box("crest", 0.02, 0.42, 0.0, 0.03, seat_h + 0.38, seat_h + 0.45, m, 0.006)
        for i in range(6):
            f.cyl("spindle", 0.05 + i * 0.068, 0.015, seat_h, seat_h + 0.39, 0.007, m, verts=8)
    elif style == "shell":   # moulded shell back
        f.box("shell", 0.0, 0.44, 0.0, 0.05, seat_h, seat_h + 0.36, m, 0.02)

def banquette(f, u0, u1, seat_m, base_m, depth=0.5, seat_h=0.46, back_h=0.42, drawers=None, channels=0):
    """built-in bench against a wall: base (optionally with drawers: a pull material),
    seat cushion, back cushion (optionally channel-tufted into `channels` vertical rolls)"""
    f.box("bench_base", u0, u1, 0, depth, 0, seat_h - 0.08, base_m, 0.004)
    if drawers:
        n = max(1, round((u1 - u0) / 0.6))
        for i in range(n):
            a = u0 + (u1 - u0) * i / n + 0.03; b = u0 + (u1 - u0) * (i + 1) / n - 0.03
            f.box("bench_drawer", a, b, depth, depth + 0.018, 0.10, seat_h - 0.11, base_m, 0.002)
            f.box("bench_pull", (a + b) / 2 - 0.05, (a + b) / 2 + 0.05, depth + 0.018, depth + 0.03,
                  seat_h - 0.2, seat_h - 0.185, drawers, 0.003)
    f.box("bench_seat", u0 + 0.01, u1 - 0.01, 0.02, depth, seat_h - 0.08, seat_h, seat_m, 0.025)
    if channels:
        w = (u1 - u0 - 0.02) / channels
        for i in range(channels):
            a = u0 + 0.01 + i * w
            f.box("bench_channel", a + 0.004, a + w - 0.004, 0.0, 0.12, seat_h, seat_h + back_h, seat_m, 0.035)
    elif back_h > 0:
        f.box("bench_back", u0 + 0.01, u1 - 0.01, 0.0, 0.12, seat_h, seat_h + back_h, seat_m, 0.03)

def velvet(name, rgb):
    """upholstery velvet: soft sheen at grazing angles"""
    m = mat(name, rgb, 0.75)
    b = _bsdf(m)
    b.inputs["Sheen Weight"].default_value = 1.0
    b.inputs["Sheen Tint"].default_value = (*[min(1, c * 2.2 + 0.1) for c in rgb], 1)
    return m

def office_chair(x, y, facing, seat_m, frame_m):
    """task chair: five-star base, gas column, seat, back; faces `facing` degrees"""
    a = math.radians(facing)
    for i in range(5):
        t = a + i * 2 * math.pi / 5
        bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.32, vertices=8,
                                            location=(x + math.cos(t) * 0.16, y + math.sin(t) * 0.16, 0.06),
                                            rotation=(0, math.pi / 2, t))
        bpy.context.object.data.materials.append(frame_m)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.025, location=(x + math.cos(t) * 0.31, y + math.sin(t) * 0.31, 0.025))
        bpy.context.object.data.materials.append(frame_m)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.38, location=(x, y, 0.25))
    bpy.context.object.data.materials.append(frame_m)
    f = _seat_frame(x, y, a, 0.25, 0.25)
    f.box("seat", 0, 0.5, 0.02, 0.5, 0.44, 0.52, seat_m, 0.03)
    f.box("back", 0.04, 0.46, 0.0, 0.07, 0.58, 1.12, seat_m, 0.035)
    f.box("back_post", 0.22, 0.28, -0.02, 0.02, 0.44, 0.62, frame_m, 0.005)

def lounge_chair(x, y, facing, shell_m, cushion_m, base_m):
    """low mid-century lounge chair with ottoman-free shell"""
    a = math.radians(facing)
    f = _seat_frame(x, y, a, 0.4, 0.42)
    f.box("lc_seat_shell", 0.02, 0.82, 0.05, 0.8, 0.30, 0.36, shell_m, 0.02)
    f.box("lc_seat", 0.06, 0.78, 0.08, 0.78, 0.36, 0.44, cushion_m, 0.04)
    f.box("lc_back_shell", 0.02, 0.82, 0.0, 0.08, 0.36, 0.95, shell_m, 0.02)
    f.box("lc_back", 0.06, 0.78, 0.07, 0.18, 0.42, 0.92, cushion_m, 0.05)
    for u in (0.0, 0.8):
        f.box("lc_arm", u, u + 0.04, 0.1, 0.75, 0.52, 0.56, shell_m, 0.01)
    f.cyl("lc_column", 0.42, 0.42, 0.04, 0.30, 0.03, base_m)
    # five-point star base, approximated by a pentagon plate
    bpy.ops.mesh.primitive_cylinder_add(radius=0.33, depth=0.03, vertices=5, location=(*f.at(0.42, 0.42, 0)[:2], 0.02))
    bpy.context.object.data.materials.append(base_m)

def monitor(f, u, v, z, width, m, screen_m, curved=False):
    """desk monitor centred at u on a desk at height z, screen facing -v (toward the sitter)"""
    f.box("mon_stand", u - 0.12, u + 0.12, v, v + 0.2, z, z + 0.012, m, 0.004)
    f.box("mon_neck", u - 0.025, u + 0.025, v + 0.12, v + 0.15, z, z + 0.32, m, 0.004)
    segs = 5 if curved else 1
    for i in range(segs):
        a0 = -width / 2 + width * i / segs; a1 = a0 + width / segs
        bow = (abs((a0 + a1) / 2) / (width / 2)) ** 2 * 0.06 if curved else 0
        f.box("mon_body", u + a0, u + a1, v + 0.06 - bow, v + 0.1 - bow, z + 0.14, z + 0.52, m, 0.003)
        f.box("mon_screen", u + a0 + 0.004, u + a1 - 0.004, v + 0.058 - bow, v + 0.06 - bow, z + 0.15, z + 0.51, screen_m, 0)

def curved_screen(cx, cy, z0, facing, width, height, body_m, screen_m, radius=1.8, segs=24, stand_m=None):
    """curved monitor: an arc of `width` metres on a circle of `radius`, centred at (cx, cy),
    screen facing angle `facing` (degrees, toward the user), bottom edge at z0"""
    a = math.radians(facing)
    d = Vector((math.cos(a), math.sin(a), 0))          # toward the user
    s = Vector((-d.y, d.x, 0))                          # sideways
    focal = Vector((cx, cy, 0)) + d * radius
    half = width / (2 * radius)
    def strip(name, inset, m, z_lo, z_hi, solid=0.0):
        verts, faces = [], []
        for i in range(segs + 1):
            t = -half + 2 * half * i / segs
            p = focal - d * (radius - inset) * math.cos(t) + s * (radius - inset) * math.sin(t)
            verts += [(p.x, p.y, z_lo), (p.x, p.y, z_hi)]
        for i in range(segs):
            faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
        me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
        ob = link(bpy.data.objects.new(name, me)); me.materials.append(m)
        if solid:
            sol = ob.modifiers.new("t", 'SOLIDIFY'); sol.thickness = solid; sol.offset = 1
        return ob
    strip("monitor_body", 0.0, body_m, z0, z0 + height, solid=0.035)
    strip("monitor_screen", 0.004, screen_m, z0 + 0.01, z0 + height - 0.01)
    # stand: neck behind the middle, flat foot
    back = Vector((cx, cy, 0)) - d * 0.09
    box("monitor_neck", back.x - 0.03, back.y - 0.03, z0 - 0.12, back.x + 0.03, back.y + 0.03, z0 + height * 0.6,
        stand_m or body_m, 0.004)
    foot = Vector((cx, cy, 0)) - d * 0.06
    box("monitor_foot", foot.x - 0.13, foot.y - 0.13, z0 - 0.13, foot.x + 0.13, foot.y + 0.13, z0 - 0.12,
        stand_m or body_m, 0.006)

def pc_tower(f, u0, u1, v0, z0, h, case_m, glow_rgb=(0.15, 0.45, 1.0), depth=0.24):
    """glass-sided PC case on a desk: frame f's -v side faces the user; 3 RGB fan rings on the front
    (the u1 end), lit interior behind the glass side"""
    v1 = v0 + depth
    f.box("pc_case", u0, u1, v0, v1, z0, z0 + h, case_m, 0.004)
    f.box("pc_glass", u0 + 0.02, u1 - 0.02, v0 - 0.003, v0, z0 + 0.03, z0 + h - 0.03, glass(), 0)
    f.box("pc_inside", u0 + 0.03, u1 - 0.03, v0 + 0.03, v0 + 0.035, z0 + 0.05, z0 + h - 0.05,
          emissive("pc_glow", glow_rgb, 1.2), 0)
    ring = emissive("fan_ring", glow_rgb, 6.0)
    for k in range(3):
        z = z0 + h * (0.22 + 0.28 * k)
        c = f.at(u1 + 0.002, (v0 + v1) / 2, z)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.006, location=c,
                                         rotation=(0, math.pi / 2, f.angle))
        bpy.context.object.data.materials.append(ring)

def pc_dual_chamber(f, z0, case_m, glow_rgb=(0.15, 0.45, 1.0), W=0.328, D=0.481, H=0.496):
    """Corsair Vengeance a7500-style dual-chamber case (6500X-class body, ~481 x 328 x 496 mm).
    Frame f runs along the glass face (u across it, 0..W), v goes back into the case (0..D), so the
    viewer stands on the -v side looking through the glass at the motherboard on the back tray.
    The three intake fans sit stacked on the inner side wall at u = W, facing across the case;
    a 240 mm AIO radiator hangs under the top with two fans, an exhaust fan on the u = 0 wall,
    and an RTX 5090 Founders Edition (304 x 137 x 40 mm) lies horizontal across the board."""
    glass_m = glass()
    ring = emissive("fan_ring", glow_rgb, 6.0)
    glow = emissive("pc_glow", glow_rgb, 0.6)
    blades = emissive("fan_blades", glow_rgb, 0.7)
    hub = mat("fan_hub", (0.02, 0.02, 0.022), 0.5)
    gpu_m = mat("gpu_gunmetal", (0.07, 0.07, 0.075), 0.32, 1.0)
    alu = mat("gpu_silver", (0.55, 0.55, 0.57), 0.28, 1.0)
    white = emissive("gpu_logo", (1.0, 1.0, 1.0), 3.0)
    tray = mat("mobo_tray", (0.03, 0.03, 0.033), 0.6)
    pcb = mat("mobo_pcb", (0.05, 0.05, 0.055), 0.45, 0.4)
    ft, t, zb = 0.015, 0.012, z0 + 0.015              # feet, frame bar, body bottom
    zt = z0 + H
    def fan(u, v, z, axis, r=0.058):
        rot = {"u": (0, math.pi / 2, f.angle), "v": (0, math.pi / 2, f.angle + math.pi / 2), "z": (0, 0, f.angle)}[axis]
        # thin lit blade disc inside the ring (RGB fans glow across the blades); kept inside the ring's radius
        bpy.ops.mesh.primitive_cylinder_add(radius=r - 0.012, depth=0.006, vertices=32, location=f.at(u, v, z), rotation=rot)
        bpy.context.object.data.materials.append(blades)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.018, depth=0.008, vertices=24, location=f.at(u, v, z), rotation=rot)
        bpy.context.object.data.materials.append(hub)
        bpy.ops.mesh.primitive_torus_add(major_radius=r - 0.004, minor_radius=0.005, location=f.at(u, v, z), rotation=rot)
        bpy.context.object.data.materials.append(ring)
    # shell: solid top, bottom, back (v = D) and exhaust wall (u = 0); glass on the viewing face and the fan side
    f.box("pc_top", 0, W, 0, D, zt - t, zt, case_m, 0.003)
    f.box("pc_bottom", 0, W, 0, D, zb, zb + t, case_m, 0.002)
    f.box("pc_back", 0, W, D - t, D, zb, zt, case_m, 0.002)
    f.box("pc_rear_wall", 0, t, 0, D, zb, zt, case_m, 0.002)
    f.box("pc_post", W - t, W, 0, t, zb, zt, case_m, 0.002)          # thin corner post between the two glass panes
    f.box("pc_glass_front", t, W - t, -0.002, 0.002, zb + t, zt - t, glass_m, 0)
    f.box("pc_glass_side", W - 0.004, W, t, D - t, zb + t, zt - t, glass_m, 0)
    for u in (0.03, W - 0.05):
        for v in (0.03, D - 0.05):
            f.box("pc_foot", u, u + 0.02, v, v + 0.02, z0, zb, case_m, 0.002)
    # motherboard chamber: tray at the back, board, PSU shroud along the bottom
    tv = D * 0.72                                       # tray plane; cable chamber behind it
    f.box("pc_tray", t, W - t, tv, tv + 0.004, zb + t, zt - t, tray, 0)
    f.box("pc_board", 0.03, 0.274, tv - 0.006, tv, zb + 0.13, zb + 0.435, pcb, 0.001)
    f.box("pc_shroud", t, 0.30, t, tv, zb + t, zb + 0.11, case_m, 0.002)       # PSU shroud: under the board only
    f.box("pc_glow_wall", t + 0.01, 0.29, tv - 0.0065, tv - 0.006, zb + 0.12, zt - 0.09, glow, 0)
    # RTX 5090 FE, horizontal in the top slot, logo edge toward the glass
    gz = zb + 0.24
    f.box("gpu_body", 0.012, 0.296, tv - 0.143, tv - 0.006, gz, gz + 0.04, gpu_m, 0.004)
    for u in (0.012, 0.284):
        f.box("gpu_end", u, u + 0.012, tv - 0.143, tv - 0.006, gz - 0.001, gz + 0.041, alu, 0.002)
    f.box("gpu_logo", 0.06, 0.20, tv - 0.1445, tv - 0.143, gz + 0.016, gz + 0.026, white, 0)
    for u in (0.08, 0.23):                             # flow-through fans on its underside
        fan(u, tv - 0.075, gz - 0.002, "z", r=0.048)
    # CPU block + RAM, 240 mm radiator under the top with two fans, rear exhaust fan
    f.cyl("aio_pump", 0.15, tv - 0.03, zb + 0.34, zb + 0.39, 0.03, gpu_m, axis="z", verts=32)
    f.box("aio_logo", 0.135, 0.165, tv - 0.0305, tv - 0.0295, zb + 0.35, zb + 0.38, white, 0)
    for k in range(4):
        u = 0.205 + k * 0.009
        f.box("ram", u, u + 0.006, tv - 0.04, tv - 0.006, zb + 0.30, zb + 0.43, case_m, 0.001)
        f.box("ram_rgb", u, u + 0.006, tv - 0.04, tv - 0.006, zb + 0.43, zb + 0.44, ring, 0)
    f.box("aio_rad", 0.035, 0.28, 0.10, 0.225, zt - t - 0.03, zt - t, case_m, 0.002)
    for u in (0.095, 0.22):
        fan(u, 0.163, zt - t - 0.045, "z")
    fan(t + 0.012, tv - 0.09, zt - 0.11, "u")
    # three 140 mm intakes stacked on the inner wall (the motherboard tray) beside the board, toward the
    # front: they face the long glass side, so they read face-on through it and edge-on through the front pane
    fu = (0.30 + W - t) / 2
    for z in (zb + 0.115, zb + 0.26, zb + 0.405):
        fan(fu, tv - 0.016, z, "v", r=0.068)

def slat_wall(f, u0, u1, z0, z1, slat_m, felt_m, slat_w=0.027, gap=0.013, depth=0.021, felt_t=0.009):
    """acoustic slat panelling: dark felt backer with vertical wood slats"""
    f.box("slat_felt", u0, u1, 0, felt_t, z0, z1, felt_m, 0)
    n = int((u1 - u0 + gap) / (slat_w + gap))
    start = u0 + ((u1 - u0) - (n * slat_w + (n - 1) * gap)) / 2
    for i in range(n):
        u = start + i * (slat_w + gap)
        f.box("slat", u, u + slat_w, felt_t, felt_t + depth, z0, z1, slat_m, 0.0008)

def place_model(asset, x, y, z, height, rot=0.0):
    """append a Poly Haven model (assets/polyhaven/<asset>/model.blend, from fetch_polyhaven.py),
    scale it to `height` metres and stand it on (x, y, z), turned `rot` degrees"""
    d = os.path.join(ASSETS, asset)
    with bpy.data.libraries.load(os.path.join(d, "model.blend"), link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None]
    for o in objs:
        link(o)
    for img in bpy.data.images:     # appended textures keep library-relative paths: point them home
        if img.filepath and not os.path.exists(bpy.path.abspath(img.filepath)):
            cand = os.path.join(d, "textures", os.path.basename(img.filepath))
            if os.path.exists(cand):
                img.filepath = cand
    bpy.context.view_layer.update()
    meshes = [o for o in objs if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector(map(min, *pts)); hi = Vector(map(max, *pts))
    root = link(bpy.data.objects.new(asset, None))
    root.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)
    bpy.context.view_layer.update()
    for o in objs:
        if o.parent is None:
            o.parent = root
            o.matrix_parent_inverse = root.matrix_world.inverted()
    s = height / max(hi.z - lo.z, 1e-6)
    root.location = (x, y, z); root.scale = (s, s, s); root.rotation_euler = (0, 0, math.radians(rot))
    return root

def trailing_vine(f, u, z, leaf_m, pot_m, drop=0.45, strands=5, seed=1, pot_r=0.055, shelf_d=0.27):
    """pothos-style plant in a small pot at (u, shelf top z) on a wall frame; strands creep to the
    shelf's front edge and hang down `drop` metres, leaves alternating along them"""
    import random
    rnd = random.Random(seed)
    f.cyl("vine_pot", u, 0.13, z, z + 0.10, pot_r, pot_m, verts=32)
    f.cyl("vine_soil", u, 0.13, z + 0.085, z + 0.095, pot_r - 0.006, mat("soil", (0.08, 0.06, 0.04), 0.9), verts=32)
    leaf = bpy.data.meshes.get("leaf_mesh")
    if leaf is None:            # one shared leaf mesh, instanced for every leaf
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=12, ring_count=6)
        tmp = bpy.context.object; leaf = tmp.data; leaf.name = "leaf_mesh"
        bpy.data.objects.remove(tmp)
        leaf.materials.append(leaf_m)
    def add_leaf(p, size):
        ob = link(bpy.data.objects.new("vine_leaf", leaf))
        ob.location = p
        ob.scale = (size, size * 0.75, size * 0.12)
        ob.rotation_euler = (rnd.uniform(-1.2, 1.2), rnd.uniform(-0.6, 0.6), rnd.uniform(0, math.tau))
    # a crown of leaves on the pot
    for i in range(14):
        a = rnd.uniform(0, math.tau)
        add_leaf(f.at(u + math.cos(a) * rnd.uniform(0, 0.06), 0.13 + math.sin(a) * rnd.uniform(0, 0.06),
                      z + 0.10 + rnd.uniform(0.0, 0.07)), rnd.uniform(0.022, 0.032))
    for k in range(strands):
        du = rnd.uniform(-0.12, 0.12)
        length = drop * rnd.uniform(0.5, 1.0)
        # path: across the shelf top to its front edge, then down with a gentle sway
        path = []
        for i in range(8):
            t = i / 7
            path.append(f.at(u + du * t, 0.13 + (shelf_d - 0.13) * t, z + 0.09 - 0.03 * t))
        n = int(length / 0.03)
        for i in range(n):
            t = i / max(n - 1, 1)
            path.append(f.at(u + du + 0.03 * math.sin(t * 5 + k), shelf_d + 0.01 + 0.02 * t, z - t * length))
        for i, p in enumerate(path):
            side = 1 if i % 2 else -1
            add_leaf(p + f.u * side * 0.012, rnd.uniform(0.018, 0.028))

def floor_lamp(x, y, shade_m, base_m, h=1.62, shade_r=0.21, shade_h=0.30, watts=40, color=(1.0, 0.78, 0.52)):
    """standing lamp: weighted disc base, slim stem, drum shade glowing from inside"""
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.025, vertices=48, location=(x, y, 0.0125))
    bpy.context.object.data.materials.append(base_m)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=h - shade_h * 0.5, vertices=16,
                                        location=(x, y, (h - shade_h * 0.5) / 2))
    bpy.context.object.data.materials.append(base_m)
    bpy.ops.mesh.primitive_cylinder_add(radius=shade_r, depth=shade_h, vertices=64, end_fill_type='NOTHING',
                                        location=(x, y, h - shade_h / 2))
    sh = bpy.context.object; sh.data.materials.append(shade_m)
    sol = sh.modifiers.new("t", 'SOLIDIFY'); sol.thickness = 0.004
    ld = bpy.data.lights.new("floor_lamp", 'POINT'); ld.energy = watts * 6; ld.color = color
    ld.shadow_soft_size = 0.05
    lo = link(bpy.data.objects.new("floor_lamp", ld)); lo.location = (x, y, h - shade_h * 0.55)
    return lo

def credenza(f, u0, u1, body_m, front_m, leg_m, depth=0.42, h=0.64, leg_h=0.14, doors=3):
    """low cabinet on slim legs against a wall: slab doors with finger-groove tops"""
    f.box("credenza_body", u0, u1, 0, depth - 0.02, leg_h, h, body_m, 0.003)
    w = (u1 - u0) / doors
    for i in range(doors):
        a = u0 + i * w + 0.003; b = a + w - 0.006
        f.box("credenza_door", a, b, depth - 0.02, depth, leg_h + 0.015, h - 0.035, front_m, 0.002)
        f.box("credenza_groove", a, b, depth - 0.021, depth + 0.001, h - 0.035, h - 0.015,
              mat("shadow", (0.03, 0.03, 0.03), 0.9), 0)
    f.box("credenza_top", u0 - 0.005, u1 + 0.005, 0, depth + 0.005, h - 0.015, h + 0.01, body_m, 0.003)
    for u in (u0 + 0.05, u1 - 0.07):
        for v in (0.05, depth - 0.07):
            f.box("credenza_leg", u, u + 0.02, v, v + 0.02, 0, leg_h, leg_m, 0.002)

def fluted_console(f, u0, u1, body_m, leg_m, depth=0.40, h=0.51, leg_h=0.125, flute_r=0.009, pitch=0.022):
    """media console with rounded (half-round) ends, fluted tambour front wrapping the ends, a slab
    top and four slim round legs. Defaults: a typical 65 x 15.7 x 20.1 in console on 4.9 in legs."""
    r = depth / 2
    ua, ub = u0 + r, u1 - r                         # centres of the two round ends
    top_t = 0.018
    f.box("console_body", ua, ub, 0, depth, leg_h, h - top_t, body_m, 0.002)
    for uc in (ua, ub):
        f.cyl("console_end", uc, r, leg_h, h - top_t, r, body_m, verts=48)
    f.box("console_top", ua, ub, -0.002, depth + 0.004, h - top_t, h, body_m, 0.002)
    for uc in (ua, ub):
        f.cyl("console_top_end", uc, r, h - top_t, h, r + 0.003, body_m, verts=48)
    z0, z1 = leg_h + 0.012, h - top_t - 0.012
    n = int((ub - ua) / pitch)
    for i in range(n + 1):                          # flutes across the flat front
        f.cyl("console_flute", ua + i * (ub - ua) / n, depth - 0.002, z0, z1, flute_r, body_m, verts=12)
    step = pitch / r                                # flutes wrapping each rounded end, front round to the side
    for uc, a0, a1 in ((ua, math.pi / 2, math.pi * 1.45), (ub, -math.pi * 0.45, math.pi / 2)):
        k = int((a1 - a0) / step)
        for i in range(k + 1):
            a = a0 + i * (a1 - a0) / k
            f.cyl("console_flute", uc + (r - 0.002) * math.cos(a), r + (r - 0.002) * math.sin(a), z0, z1,
                  flute_r, body_m, verts=12)
    f.box("console_seam", (u0 + u1) / 2 - 0.002, (u0 + u1) / 2 + 0.002, depth - 0.001, depth + 0.012, z0, z1,
          mat("shadow", (0.01, 0.01, 0.01), 0.9), 0)     # where the two tambour doors meet
    for u in (u0 + 0.16, u1 - 0.16):
        for v in (0.07, depth - 0.07):
            f.cyl("console_leg", u, v, 0, leg_h, 0.014, leg_m, verts=16)

def etagere(f, u0, u1, frame_m, shelf_m, depth=0.34, h=1.90, shelves=5):
    """slim open bookcase: thin metal frame, shelves; stands flat against a wall"""
    for u in (u0, u1 - 0.02):
        for v in (0.0, depth - 0.02):
            f.box("etagere_post", u, u + 0.02, v, v + 0.02, 0, h, frame_m, 0.002)
    zs = [0.06 + (h - 0.08) * k / (shelves - 1) for k in range(shelves)]
    for z in zs:
        f.box("etagere_shelf", u0 + 0.02, u1 - 0.02, 0.0, depth, z, z + 0.022, shelf_m, 0.002)
    return zs

def steel_shelving(f, u0, u1, m, depth=0.61, h=1.83, shelves=5, post=0.04, name="shelving"):
    """heavy-duty boltless steel shelving unit (garage/basement storage, e.g. 48x24x72 in):
    four angle posts, `shelves` decks with a front/back lip; stands against the wall. Returns deck heights."""
    for u in (u0, u1 - post):
        for v in (0.0, depth - post):
            f.box(f"{name}_post", u, u + post, v, v + post, 0, h, m, 0.003)
    zs = [0.10 + (h - 0.13) * k / (shelves - 1) for k in range(shelves)]
    for z in zs:
        f.box(f"{name}_deck", u0 + post, u1 - post, 0.0, depth, z, z + 0.018, m, 0.002)
        for v0 in (0.0, depth - 0.012):     # beam lips front and back
            f.box(f"{name}_beam", u0 + post, u1 - post, v0, v0 + 0.012, z - 0.045, z + 0.018, m, 0.001)
    return zs

def cyl(name, p, axis, r, length, m, verts=24):
    """cylinder centred at world point p along 'x' | 'y' | 'z' (pipes, bars, tanks, plates)"""
    rot = {"x": (0, math.pi / 2, 0), "y": (math.pi / 2, 0, 0), "z": (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, vertices=verts, location=p, rotation=rot)
    o = bpy.context.object; o.name = name
    if m:
        o.data.materials.append(m)
    return o

def tube(name, a, b, m, s=0.05):
    """square tube / post / rail between two world points a and b (any direction)"""
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cube_add(size=1, location=(a + b) / 2)
    o = bpy.context.object; o.name = name
    o.scale = (s, s, d.length)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    if m:
        o.data.materials.append(m)
    return o

def obox(name, c, U, V, W, a, b, t, m, bevel=0.006):
    """oriented box: centre c, half sizes a / b / t along directions U / V / W (angled equipment parts,
    sloped rails, reclined pads)"""
    c, U, V, W = Vector(c), Vector(U).normalized(), Vector(V).normalized(), Vector(W).normalized()
    pts = [c + U * su * a + V * sv * b + W * sw * t
           for sw in (-1, 1) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    return mesh_box(name, pts, m, bevel)

def half_disc(name, wall_x, yc, z, r, depth, m, sx=1.0, toward=1):
    """half-round slab against a wall plane x = wall_x (console tops, demilune tables, wall bowls):
    a cylinder cut at the wall so nothing pokes through. toward=+1: the room is at x > wall_x."""
    import bmesh
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=48, location=(wall_x, yc, z))
    o = bpy.context.object; o.name = name; o.scale = (sx, 1, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0),
                           plane_no=(toward, 0, 0), clear_inner=True)
    bmesh.ops.contextual_create(bm, geom=[e for e in bm.edges if e.is_boundary])
    bm.to_mesh(o.data); bm.free()
    if m:
        o.data.materials.append(m)
    return o

def hole_pattern_mat(name, rgb, length, pitch=0.0508, hole_rgb=(0.01, 0.01, 0.01)):
    """perforated square tube (rack uprights, shelving posts): holes at `pitch` up the centre of every face.
    Procedural on Generated coords; build the tube with tube() so its local z is the length (metres)."""
    m = mat(name, rgb, 0.35, 0.3)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    def op(kind, a, b=None):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = kind
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    zf = op('FRACT', op('MULTIPLY', sep.outputs["Z"], length / pitch))
    along = op('LESS_THAN', op('ABSOLUTE', op('SUBTRACT', zf, 0.5)), 0.24)
    acx = op('LESS_THAN', op('ABSOLUTE', op('SUBTRACT', sep.outputs["X"], 0.5)), 0.16)
    acy = op('LESS_THAN', op('ABSOLUTE', op('SUBTRACT', sep.outputs["Y"], 0.5)), 0.16)
    mask = op('MULTIPLY', along, op('MAXIMUM', acx, acy))
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = (*rgb, 1); mix.inputs[7].default_value = (*hole_rgb, 1)
    nt.links.new(mask, mix.inputs[0])
    nt.links.new(mix.outputs[2], _bsdf(m).inputs["Base Color"])
    return m

def totes(f, u0, u1, zs, depth, mats, per_shelf=2, h=0.30, seed=0):
    """plain lidded storage totes on a shelving unit's decks (user: 'simplify the totes')"""
    import random
    rnd = random.Random(seed)
    w = (u1 - u0 - 0.06) / per_shelf
    for k, z in enumerate(zs[:-1]):
        room = zs[k + 1] - z - 0.04
        th = min(h, room)
        for j in range(per_shelf):
            if rnd.random() < 0.15:
                continue                       # a gap here and there
            m = mats[rnd.randrange(len(mats))]
            a = u0 + 0.03 + j * w + 0.01
            f.box(f"tote_{k}_{j}", a, a + w - 0.02, 0.04, depth - 0.04, z + 0.02, z + 0.02 + th - 0.03, m, 0.01)
            f.box(f"tote_lid_{k}_{j}", a - 0.005, a + w - 0.015, 0.035, depth - 0.035, z + th - 0.01, z + th + 0.005,
                  m, 0.004)

def rug(x0, y0, x1, y1, m):
    return box("rug", x0, y0, 0, x1, y1, 0.012, m, 0.004)

def stool(x, y, seat_m, leg_m, seat_h=0.64, r=0.18):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=0.05, vertices=40, location=(x, y, seat_h - 0.025))
    bpy.context.object.data.materials.append(seat_m)
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=seat_h, vertices=10,
                                            location=(x + math.cos(a) * r * 0.65, y + math.sin(a) * r * 0.65, seat_h / 2),
                                            rotation=(math.sin(a) * 0.12, -math.cos(a) * 0.12, 0))
        bpy.context.object.data.materials.append(leg_m)
    bpy.ops.mesh.primitive_torus_add(major_radius=r * 0.62, minor_radius=0.008, location=(x, y, 0.25))
    bpy.context.object.data.materials.append(leg_m)

def pendant(x, y, z, kind, shade_m, watts=40, color=(1.0, 0.8, 0.6), drop=0.6, ceiling=2.48):
    """kind: 'cone' | 'globe' | 'dome'; z = bottom of the shade"""
    before = set(bpy.data.objects)
    cord = mat("cord", (0.05, 0.05, 0.05), 0.5)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.004, depth=ceiling - z, location=(x, y, (ceiling + z) / 2))
    bpy.context.object.data.materials.append(cord)
    glow = emissive(f"bulb_{kind}", color, 8.0)
    if kind == "lantern":       # faceted paper lantern
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.24, location=(x, y, z + 0.22), segments=8, ring_count=5)
        ob = bpy.context.object; ob.scale = (1, 1, 0.92)
        ob.data.materials.append(emissive("paper", (1.0, 0.94, 0.84), 1.5))
        lz = z + 0.22
    elif kind == "globe":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(x, y, z + 0.15), segments=32, ring_count=16)
        bpy.context.object.data.materials.append(emissive("globe_glass", (1.0, 0.92, 0.8), 3.0))
        lz = z + 0.15
    else:
        r1, r2, h = (0.17, 0.05, 0.22) if kind == "cone" else (0.22, 0.06, 0.16)
        bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, vertices=48, location=(x, y, z + h / 2))
        sh = bpy.context.object; sh.data.materials.append(shade_m)
        sol = sh.modifiers.new("t", 'SOLIDIFY'); sol.thickness = 0.004
        bpy.ops.mesh.primitive_cylinder_add(radius=r1 - 0.01, depth=0.002, vertices=48, location=(x, y, z + 0.003))
        bpy.context.object.data.materials.append(glow)
        lz = z + 0.05
    ld = bpy.data.lights.new("pendant", 'POINT'); ld.energy = watts * 6; ld.color = color
    ld.shadow_soft_size = 0.05
    lo = link(bpy.data.objects.new("pendant", ld)); lo.location = (x, y, lz)
    for o in set(bpy.data.objects) - before:      # name the fitting so top views can hide it
        if o.type == 'MESH':
            o.name = "pendant_fitting"
    return lo

def can_light(x, y, ceiling, watts=12, color=(1.0, 0.85, 0.7)):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.004, vertices=32, location=(x, y, ceiling - 0.002))
    bpy.context.object.name = "can_lens"
    bpy.context.object.data.materials.append(emissive("can_lens", color, 12.0))
    ld = bpy.data.lights.new("can", 'SPOT'); ld.energy = watts * 25; ld.color = color
    ld.spot_size = math.radians(80); ld.spot_blend = 0.6; ld.shadow_soft_size = 0.04
    lo = link(bpy.data.objects.new("can", ld)); lo.location = (x, y, ceiling - 0.01)
    return lo

def flush_light(x, y, ceiling, watts=60, color=(1.0, 0.82, 0.62)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(x, y, ceiling), segments=32, ring_count=16)
    ob = bpy.context.object; ob.scale = (1, 1, 0.3)
    ob.name = "ceiling_flush"          # ceiling_* -> hidden with the ceiling in overhead / cutaway views
    ob.data.materials.append(emissive("flush_glass", (1.0, 0.95, 0.88), 4.0))
    ld = bpy.data.lights.new("flush", 'POINT'); ld.energy = watts * 6; ld.color = color
    lo = link(bpy.data.objects.new("flush", ld)); lo.location = (x, y, ceiling - 0.12)
    return lo

def alabaster_flush(x, y, ceiling, diameter=0.36, watts=60, color=(1.0, 0.82, 0.62)):
    """flush-mount dish of veined alabaster with a slim brass ring, glowing from inside"""
    r = diameter / 2
    if "alabaster" not in _mats:
        m = bpy.data.materials.new("alabaster")
        nt = m.node_tree; b = _bsdf(m)
        b.inputs["Base Color"].default_value = (0.95, 0.90, 0.82, 1)
        b.inputs["Roughness"].default_value = 0.35
        b.inputs["Emission Color"].default_value = (1.0, 0.86, 0.68, 1)
        # stone veining: noise drives a ramp from warm cream to a darker honey vein
        geo = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 9.0; nz.inputs["Detail"].default_value = 8.0
        nz.inputs["Distortion"].default_value = 4.0
        nt.links.new(geo.outputs["Object"], nz.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = (0.75, 0.55, 0.35, 1)
        ramp.color_ramp.elements[1].position = 0.6; ramp.color_ramp.elements[1].color = (1.0, 0.92, 0.80, 1)
        nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        strength = nt.nodes.new("ShaderNodeMath"); strength.operation = 'MULTIPLY'
        strength.inputs[1].default_value = 3.0
        nt.links.new(nz.outputs["Fac"], strength.inputs[0])
        nt.links.new(strength.outputs[0], b.inputs["Emission Strength"])
        _mats["alabaster"] = m
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, ceiling - 0.03), segments=48, ring_count=24)
    dish = bpy.context.object; dish.name = "alabaster_dish"
    dish.scale = (1, 1, 0.42)
    dish.data.materials.append(_mats["alabaster"])
    bpy.ops.mesh.primitive_cylinder_add(radius=r * 1.04, depth=0.03, vertices=64, location=(x, y, ceiling - 0.015))
    bpy.context.object.data.materials.append(mat("brass", (0.80, 0.62, 0.32), 0.3, 1.0))
    ld = bpy.data.lights.new("alabaster", 'POINT'); ld.energy = watts * 6; ld.color = color
    ld.shadow_soft_size = r * 0.8
    lo = link(bpy.data.objects.new("alabaster_light", ld)); lo.location = (x, y, ceiling - 0.12)
    return lo

def alabaster_linear(x, y, ceiling, length=0.60, width=0.145, depth=0.06, along="y", watts=83,
                     color=(1.0, 0.84, 0.67)):
    """linear flush mount: brushed-brass stadium (rounded-end) body with an alabaster panel
    underneath. Defaults are the Latitude Run 1-light alabaster LED flush mount's spec sheet:
    23.62 x 5.71 x 2.36 in, 28 W, 1120 lm, 3000 K (~500 Blender W across three emitters, on the
    same scale as the other fixtures here: ~800 lm bulb = 360 W)."""
    alabaster_flush(-100, -100, -50)            # makes the "alabaster" material (and a throwaway)
    for o in [o for o in bpy.data.objects if o.location.x < -50]:
        bpy.data.objects.remove(o)
    def outline(inset, seg=16):
        r = width / 2 - inset
        half = length / 2 - width / 2
        pts = []
        for a0, cx in ((-math.pi / 2, half), (math.pi / 2, -half)):     # two semicircular ends
            for i in range(seg + 1):
                a = a0 + math.pi * i / seg
                pts.append((cx + r * math.cos(a), r * math.sin(a)))
        return [(x + p[0], y + p[1]) if along == "x" else (x + p[1], y + p[0]) for p in pts]
    def solid(name, pts, z0, z1, m):
        n = len(pts)
        verts = [(px, py, z0) for px, py in pts] + [(px, py, z1) for px, py in pts]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
        ob = link(bpy.data.objects.new(name, me)); me.materials.append(m)
        bv = ob.modifiers.new("bevel", 'BEVEL'); bv.width = 0.002; bv.segments = 2; bv.limit_method = 'ANGLE'
        return ob
    brass = mat("brushed_brass", (0.78, 0.60, 0.33), 0.38, 1.0)
    solid("linear_brass", outline(0), ceiling - depth, ceiling, brass)
    solid("linear_alabaster", outline(0.012), ceiling - depth - 0.002, ceiling - depth + 0.01, _mats["alabaster"])
    lights = []
    for k in (-1, 0, 1):        # three emitters along the panel so the glow spreads like an LED board
        ld = bpy.data.lights.new("linear", 'POINT'); ld.energy = watts * 2; ld.color = color
        ld.shadow_soft_size = 0.08
        lo = link(bpy.data.objects.new("linear_light", ld))
        off = k * (length / 2 - width / 2)
        lo.location = (x + (off if along == "x" else 0), y + (off if along == "y" else 0), ceiling - depth - 0.03)
        lo.visible_glossy = False   # the glowing panel shows in reflections; bare point lights would read as dots
        lights.append(lo)
    return lights

def strip_light(f, u0, u1, v, z, watts=10, color=(1.0, 0.85, 0.65)):
    """under-cabinet LED: area light facing down"""
    ld = bpy.data.lights.new("strip", 'AREA'); ld.shape = 'RECTANGLE'
    ld.size = u1 - u0; ld.size_y = 0.03; ld.energy = watts * 8; ld.color = color
    lo = link(bpy.data.objects.new("strip", ld))
    lo.location = f.at((u0 + u1) / 2, v, z)
    lo.rotation_euler = (0, 0, f.angle)
    return lo

def daylight(sun_dir=(50, 0, 120), sun_strength=3.0, sky=(0.55, 0.7, 1.0), sky_strength=1.0):
    s = bpy.context.scene
    s.world = bpy.data.worlds.new("day")
    bg = s.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*sky, 1)
    bg.inputs["Strength"].default_value = sky_strength
    sd = bpy.data.lights.new("sun", 'SUN'); sd.energy = sun_strength; sd.angle = math.radians(2)
    sd.color = (1.0, 0.95, 0.88)
    so = link(bpy.data.objects.new("sun", sd))
    so.rotation_euler = tuple(math.radians(a) for a in sun_dir)

def window_glow(f, s0, s1, z0, z1, watts=150):
    """area light just inside a window. EEVEE: stands in for skylight through it.
    Cycles: becomes a light portal, guiding the real sky light through the opening."""
    ld = bpy.data.lights.new("winlight", 'AREA'); ld.shape = 'RECTANGLE'
    ld.size = s1 - s0; ld.size_y = z1 - z0; ld.energy = watts; ld.color = (0.9, 0.95, 1.0)
    lo = link(bpy.data.objects.new("winlight", ld))
    lo.location = f.at((s0 + s1) / 2, 0.05, (z0 + z1) / 2)
    # area lights shine along their local -Z: point it into the room (+v)
    lo.rotation_euler = (math.pi / 2, 0, f.angle)
    if bpy.context.scene.render.engine == 'CYCLES':
        ld.cycles.is_portal = True
    return lo

# ---------------------------------------------------------------- cameras
def camera(name, eye, target, lens=16):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.05
    co = link(bpy.data.objects.new(name, cd))
    co.location = eye
    d = Vector(target) - Vector(eye)
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return co

def render(cam, path, res=(1600, 1000)):
    s = bpy.context.scene
    s.camera = cam
    s.render.resolution_x, s.render.resolution_y = res
    s.render.image_settings.file_format = 'JPEG'
    s.render.image_settings.quality = 90
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)

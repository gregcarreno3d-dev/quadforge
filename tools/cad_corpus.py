#!/usr/bin/env python3
"""Builds a corpus of synthetic CAD parts (triangulated STL, millimetres) for ``tools/cad_battery.py``.

    python3 tools/cad_corpus.py OUT_FOLDER

The parts are made with Blender primitives, exact booleans and bevels, so they have what real CAD parts have: planes,
cylinders, cones, spheres, tori, holes, slots, ribs, chamfers and fillets. Needs Blender's Python module (``bpy``).
The corpus is deterministic: the same call always writes the same files.
"""
import math
import os
import sys


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    import bpy

    def fresh():
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def add(kind, **kw):
        getattr(bpy.ops.mesh, "primitive_%s_add" % kind)(**kw)
        o = bpy.context.active_object
        return o

    def box(sx, sy, sz, loc=(0, 0, 0)):
        o = add("cube", size=2, location=loc)
        o.scale = (sx, sy, sz)
        bpy.ops.object.transform_apply(scale=True)
        return o

    def cyl(r, depth, loc=(0, 0, 0), rot=(0, 0, 0), verts=96):
        return add("cylinder", radius=r, depth=depth, vertices=verts, location=loc, rotation=rot)

    def cone(r1, r2, depth, loc=(0, 0, 0), verts=96):
        return add("cone", radius1=r1, radius2=r2, depth=depth, vertices=verts, location=loc)

    def sphere(r, loc=(0, 0, 0)):
        return add("uv_sphere", radius=r, segments=64, ring_count=32, location=loc)

    def torus(R, r, loc=(0, 0, 0)):
        return add("torus", major_radius=R, minor_radius=r, major_segments=96, minor_segments=32, location=loc)

    def boolean(a, b, op="DIFFERENCE"):
        m = a.modifiers.new("b", "BOOLEAN")
        m.operation, m.object, m.solver = op, b, "EXACT"
        bpy.context.view_layer.objects.active = a
        bpy.ops.object.modifier_apply(modifier="b")
        bpy.data.objects.remove(b, do_unlink=True)

    def bevel(o, width, segments=3, angle=35.0):
        m = o.modifiers.new("v", "BEVEL")
        m.width, m.segments, m.limit_method, m.angle_limit = width, segments, "ANGLE", math.radians(angle)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="v")

    def save(o, name):
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        tri = o.modifiers.new("t", "TRIANGULATE")
        tri.min_vertices = 4
        bpy.ops.object.modifier_apply(modifier="t")
        path = os.path.join(out, name + ".stl")
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)
        print("wrote", path)

    def part(name, builder):
        fresh()
        save(builder(), name)

    # 1 plate with a grid of holes
    def plate_grid():
        a = box(40, 25, 3)
        for x in (-25, -8, 8, 25):
            for y in (-12, 12):
                boolean(a, cyl(3.2, 10, (x, y, 0), verts=64))
        bevel(a, 0.6, 2)
        return a
    part("plate_grid", plate_grid)

    # 2 flange with a bolt circle and a raised hub
    def flange():
        a = cyl(30, 6)
        boolean(a, cyl(22, 20))
        h = cyl(26, 10, (0, 0, 8))
        boolean(a, h, "UNION")
        for k in range(6):
            t = k * math.pi / 3
            boolean(a, cyl(3.5, 20, (26 * math.cos(t), 26 * math.sin(t), 0), verts=48))
        bevel(a, 0.7, 2)
        return a
    part("flange", flange)

    # 3 stepped shaft
    def shaft():
        a = cyl(8, 40)
        boolean(a, cyl(12, 14, (0, 0, -14)), "UNION")
        boolean(a, cyl(5, 20, (0, 0, 28)), "UNION")
        boolean(a, box(2, 6, 6, (0, 0, 33)), "DIFFERENCE")
        bevel(a, 0.8, 2)
        return a
    part("shaft", shaft)

    # 4 U channel with slots
    def channel():
        a = box(50, 15, 12)
        boolean(a, box(52, 11, 12, (0, 0, 3)))
        for x in (-30, -10, 10, 30):
            boolean(a, box(3, 1.8, 20, (x, 0, -6)))
        bevel(a, 0.8, 3)
        return a
    part("channel", channel)

    # 5 hex bolt head with a washer face
    def bolt():
        a = cyl(10, 7, verts=6)
        boolean(a, cyl(9, 1, (0, 0, -3.5), verts=96), "UNION")
        boolean(a, cyl(5, 40, (0, 0, -22)), "UNION")
        bevel(a, 0.5, 2)
        return a
    part("bolt", bolt)

    # 6 spur gear with a hub bore
    def gear():
        import bmesh
        me = bpy.data.meshes.new("g")
        bm = bmesh.new()
        n = 20
        ring = []
        for i in range(n * 4):
            phase = i % 4
            r = 22 if phase in (1, 2) else 18
            t = (i + (0.0 if phase in (1, 2) else 0.0)) * 2 * math.pi / (n * 4)
            ring.append(bm.verts.new((r * math.cos(t), r * math.sin(t), -4)))
        f = bm.faces.new(ring)
        res = bmesh.ops.extrude_face_region(bm, geom=[f])
        for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
            v.co.z = 4
        bm.normal_update()
        bm.to_mesh(me)
        a = bpy.data.objects.new("g", me)
        bpy.context.collection.objects.link(a)
        bpy.context.view_layer.objects.active = a
        boolean(a, cyl(6, 20, verts=64))
        boolean(a, box(1.5, 8, 20, (0, 6, 0)))
        return a
    part("gear", gear)

    # 7 pulley (revolution profile with a groove)
    def pulley():
        a = cyl(24, 14)
        boolean(a, torus(26.5, 5, (0, 0, 0)))
        boolean(a, cyl(7, 30, verts=64))
        bevel(a, 0.8, 3)
        return a
    part("pulley", pulley)

    # 8 cone adapter (tube to cone)
    def adapter():
        a = cone(20, 10, 30)
        boolean(a, cone(17, 7, 32))
        boolean(a, cyl(20, 6, (0, 0, -18)), "UNION")
        boolean(a, cyl(17, 8, (0, 0, -18)))
        bevel(a, 0.6, 2)
        return a
    part("adapter", adapter)

    # 9 enclosure box with a cut-out and standoffs
    def enclosure():
        a = box(40, 28, 12)
        boolean(a, box(37, 25, 11, (0, 0, 2)))
        for x in (-30, 30):
            for y in (-18, 18):
                boolean(a, cyl(3.5, 11, (x, y, -3), verts=48), "UNION")
                boolean(a, cyl(1.3, 12, (x, y, -3), verts=32))
        boolean(a, box(7, 4, 8, (-40, 0, 0)))
        bevel(a, 0.8, 3)
        return a
    part("enclosure", enclosure)

    # 10 heat sink with fins
    def heatsink():
        a = box(30, 25, 3, (0, 0, -9))
        for k in range(9):
            boolean(a, box(1.2, 24, 9, (-26 + k * 6.5, 0, -3)), "UNION")
        bevel(a, 0.35, 2)
        return a
    part("heatsink", heatsink)

    # 11 knob with a sphere top and a flat
    def knob():
        a = cyl(16, 18)
        boolean(a, sphere(20, (0, 0, 9)), "INTERSECT")
        boolean(a, cyl(3, 30, verts=48))
        boolean(a, box(10, 1.5, 6, (0, 4.5, -6)))
        bevel(a, 0.6, 3)
        return a
    part("knob", knob)

    # 12 bracket with ribs (L shape + gusset)
    def bracket():
        a = box(30, 15, 3)
        boolean(a, box(3, 15, 22, (-27, 0, 19)), "UNION")
        for y in (-8, 8):
            boolean(a, box(1.5, 1.5, 1.5, (0, y, 0)), "UNION")
        g = box(1.5, 15, 12, (-24.5, 0, 9))
        g.rotation_euler = (0, math.radians(-38), 0)
        bpy.context.view_layer.objects.active = g
        bpy.ops.object.transform_apply(rotation=True)
        boolean(a, g, "UNION")
        boolean(a, cyl(4, 10, (12, 0, 0), verts=64))
        boolean(a, cyl(3.3, 10, (-27, 0, 25), (0, math.pi / 2, 0), verts=64))
        bevel(a, 0.9, 3)
        return a
    part("bracket", bracket)

    # 13 cup / vase (revolution with a rounded bottom)
    def cup():
        a = cyl(18, 30)
        boolean(a, torus(14, 4, (0, 0, -15)), "UNION")
        boolean(a, cyl(15, 29, (0, 0, 2.5)))
        bevel(a, 1.0, 4)
        return a
    part("cup", cup)

    # 14 T-slot profile extrusion
    def tslot():
        a = box(10, 10, 30)
        boolean(a, box(3, 12, 32, (0, 0, 0)))
        boolean(a, box(6, 4, 32, (0, 6, 0)))
        boolean(a, cyl(2.2, 40, verts=48))
        bevel(a, 0.5, 2)
        return a
    part("tslot", tslot)

    # 15 handle (a torus segment with two bosses)
    def handle():
        a = torus(25, 5)
        boolean(a, box(60, 30, 30, (0, 30, 0)))
        for x in (-25, 25):
            boolean(a, cyl(7, 8, (x, 0, 0), (math.pi / 2, 0, 0), verts=64), "UNION")
            boolean(a, cyl(2.5, 20, (x, 0, 0), (math.pi / 2, 0, 0), verts=48))
        return a
    part("handle", handle)

    # 16 bearing housing: block with a bore, a counterbore and two bolt holes
    def housing():
        a = box(25, 20, 12)
        boolean(a, cyl(10, 30, verts=96))
        boolean(a, cyl(13, 6, (0, 0, 6)))
        for x in (-19, 19):
            boolean(a, cyl(2.8, 30, (x, 0, 0), verts=48))
        bevel(a, 0.9, 3)
        return a
    part("housing", housing)

    # 17 countersunk plate
    def countersunk():
        a = box(35, 20, 3)
        for x in (-22, 0, 22):
            boolean(a, cone(3, 6, 3, (x, 0, 0), verts=64))
            boolean(a, cyl(3, 10, (x, 0, 0), verts=64))
        bevel(a, 0.5, 2)
        return a
    part("countersunk", countersunk)

    # 18 tube with a slot and a cross hole
    def tube():
        a = cyl(12, 50)
        boolean(a, cyl(9, 52))
        boolean(a, box(1.5, 20, 12, (0, 0, 14)))
        boolean(a, cyl(3, 40, (0, 0, -12), (0, math.pi / 2, 0), verts=48))
        bevel(a, 0.6, 2)
        return a
    part("tube", tube)

    # 19 ball joint (sphere on a post)
    def balljoint():
        a = cyl(5, 30, (0, 0, -10))
        boolean(a, sphere(12, (0, 0, 8)), "UNION")
        boolean(a, cyl(4, 30, (0, 0, 12)))
        bevel(a, 0.6, 3)
        return a
    part("balljoint", balljoint)

    # 20 ratchet wheel (a polygon with notches and a flat)
    def ratchet():
        a = cyl(26, 6, verts=12)
        for k in range(12):
            t = k * math.pi / 6
            c = cyl(2.5, 10, (26 * math.cos(t), 26 * math.sin(t), 0), verts=24)
            boolean(a, c)
        boolean(a, cyl(8, 10, verts=64))
        bevel(a, 0.6, 2)
        return a
    part("ratchet", ratchet)


if __name__ == "__main__":
    main()

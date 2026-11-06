import bpy, sys
p = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=p)
for im in bpy.data.images:
    if im.filepath and not im.packed_file: im.pack()
print("packed", [im.name for im in bpy.data.images if im.packed_file])
bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)

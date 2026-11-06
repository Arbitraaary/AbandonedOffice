import bpy

def mat_new(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); o.location = (1200, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (900, 0)
    nt.links.new(b.outputs[0], o.inputs[0])
    return m, nt, b

class G:
    """tiny node-graph helper"""
    def __init__(s, nt): s.nt = nt; s.x = -1600; s.y = 0
    def n(s, t, **kw):
        nd = s.nt.nodes.new(t); nd.location = (s.x, s.y); s.y -= 180
        if s.y < -2400: s.y = 0; s.x += 220
        for k, v in kw.items():
            if k in nd.inputs: nd.inputs[k].default_value = v
            else: setattr(nd, k, v)
        return nd
    def L(s, a, b): s.nt.links.new(a, b)
    def val(s, x, sock):
        if isinstance(x, bpy.types.NodeSocket): s.L(x, sock)
        else: sock.default_value = x
    def math(s, op, a, b=0.0, clamp=False):
        m = s.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        s.val(a, m.inputs[0]); s.val(b, m.inputs[1]); return m.outputs[0]
    def rng(s, src, a, b):
        r = s.n("ShaderNodeMapRange"); r.inputs[1].default_value = a; r.inputs[2].default_value = b
        s.L(src, r.inputs[0]); return r.outputs[0]
    def mixc(s, fac, a, b, blend='MIX'):
        m = s.n("ShaderNodeMix", data_type='RGBA', blend_type=blend)
        s.val(fac, m.inputs[0]); s.val(a, m.inputs[6]); s.val(b, m.inputs[7]); return m.outputs[2]
    def mixf(s, fac, a, b):
        m = s.n("ShaderNodeMix", data_type='FLOAT')
        s.val(fac, m.inputs[0]); s.val(a, m.inputs[2]); s.val(b, m.inputs[3]); return m.outputs[0]
    def noise(s, vec, scale, detail=6.0, rough=0.6, mapping_scale=None):
        if mapping_scale:
            mp = s.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = mapping_scale
            s.L(vec, mp.inputs[0]); vec = mp.outputs[0]
        nz = s.n("ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=rough)
        s.L(vec, nz.inputs[0]); return nz.outputs[0]


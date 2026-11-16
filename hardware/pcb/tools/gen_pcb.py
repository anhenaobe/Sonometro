"""Build pcb.kicad_pcb (placement only, no routing) from the KiCad netlist of pcb.kicad_sch.

Run with KiCad's python:  "C:/Program Files/KiCad/10.0/bin/python.exe" gen_pcb.py <out_dir>
  <out_dir> must contain check.xml (kicad-cli sch export netlist --format kicadxml) and lib/.
Board: 90 x 64 mm, 2 layers, no mounting holes. Origin of the outline at (100, 100) mm.
"""
import os
import sys
import math
import xml.etree.ElementTree as ET
import pcbnew

OUT = sys.argv[1]
KFP = r'C:/Program Files/KiCad/10.0/share/kicad/footprints'
BX0, BY0, BW, BH = 100.0, 100.0, 90.0, 64.0
MM = pcbnew.FromMM

# ------------------------------------------------------------------ netlist
root = ET.parse(os.path.join(OUT, 'check.xml')).getroot()
comps = {}
for c in root.iter('comp'):
    fields = {f.get('name'): (f.text or '') for f in c.iter('field')}
    comps[c.get('ref')] = dict(value=c.findtext('value'), fp=c.findtext('footprint'),
                               tstamp=c.findtext('tstamps').split()[0], fields=fields)
padnet = {}
netnames = []
for n in root.iter('net'):
    name = n.get('name')
    if name.startswith(('unconnected-(', 'Net-(')):      # KiCad escapes '/' of pin names in these
        name = name.replace('/', '{slash}')
    netnames.append(name)
    for nd in n.iter('node'):
        padnet[(nd.get('ref'), nd.get('pin'))] = name

board = pcbnew.NewBoard(os.path.join(OUT, 'pcb.kicad_pcb'))
board.SetCopperLayerCount(2)
nets = {}
for name in netnames:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    nets[name] = ni

# ------------------------------------------------------------------ outline
def edge(x1, y1, x2, y2):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    board.Add(s)


edge(BX0, BY0, BX0 + BW, BY0)
edge(BX0 + BW, BY0, BX0 + BW, BY0 + BH)
edge(BX0 + BW, BY0 + BH, BX0, BY0 + BH)
edge(BX0, BY0 + BH, BX0, BY0)

# ---------------------------------------------------------------- footprints
fps = {}


def load(ref):
    c = comps[ref]
    lib, name = c['fp'].split(':')
    path = os.path.join(OUT, 'lib', 'Sonometro.pretty') if lib == 'Sonometro' else os.path.join(KFP, lib + '.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit('cannot load ' + c['fp'])
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(c['value'])
    fp.SetPath(pcbnew.KIID_PATH('/' + c['tstamp']))
    fp.SetSheetname('/')
    fp.SetSheetfile('pcb.kicad_sch')
    for fname in [k for k in c['fields'] if k not in ('Footprint', 'Reference', 'Value')]:
        if True:
            fp.SetField(fname, c['fields'][fname])
            f = fp.GetField(fname)
            if f is not None:
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
    for pad in fp.Pads():
        n = padnet.get((ref, pad.GetNumber()))
        if n:
            pad.SetNet(nets[n])
    board.Add(fp)
    fps[ref] = fp
    return fp


geo = {}   # ref -> dict(pads=[(net, lx, ly)], box=(x1, y1, x2, y2)) in footprint-local mm, rot 0


def local_geo(ref):
    if ref in geo:
        return geo[ref]
    fp = fps.get(ref) or load(ref)
    fp.SetOrientationDegrees(0)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    pads = [(p.GetNetname(), pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y),
             pcbnew.ToMM(p.GetSize(pcbnew.F_Cu).x) / 2, pcbnew.ToMM(p.GetSize(pcbnew.F_Cu).y) / 2)
            for p in fp.Pads()]
    xs, ys = [], []
    for it in fp.GraphicalItems():
        if it.GetLayer() != pcbnew.F_CrtYd:
            continue
        st = it.GetShape()
        if st in (pcbnew.SHAPE_T_SEGMENT, pcbnew.SHAPE_T_RECTANGLE):
            for v in (it.GetStart(), it.GetEnd()):
                xs.append(pcbnew.ToMM(v.x)); ys.append(pcbnew.ToMM(v.y))
        elif st == pcbnew.SHAPE_T_POLY:
            for v in it.GetCorners():
                xs.append(pcbnew.ToMM(v.x)); ys.append(pcbnew.ToMM(v.y))
        elif st in (pcbnew.SHAPE_T_CIRCLE, pcbnew.SHAPE_T_ARC):
            c = it.GetCenter(); r = pcbnew.ToMM(it.GetRadius())
            xs += [pcbnew.ToMM(c.x) - r, pcbnew.ToMM(c.x) + r]; ys += [pcbnew.ToMM(c.y) - r, pcbnew.ToMM(c.y) + r]
    if not xs:   # no courtyard: pads + 0.5 mm
        for n, x, y, hw, hh in pads:
            xs += [x - hw - 0.5, x + hw + 0.5]; ys += [y - hh - 0.5, y + hh + 0.5]
    geo[ref] = dict(pads=[(n, x, y) for n, x, y, _, _ in pads], box=(min(xs), min(ys), max(xs), max(ys)))
    return geo[ref]


def rotp(x, y, rot):
    """KiCad footprint rotation (degrees, CCW on screen, Y down)."""
    t = math.radians(rot)
    c, s = round(math.cos(t), 9), round(math.sin(t), 9)
    return x * c + y * s, -x * s + y * c


def rel_box(ref, rot):
    x1, y1, x2, y2 = local_geo(ref)['box']
    pts = [rotp(x, y, rot) for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2))]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def abs_pads(ref, x, y, rot):
    return [(n, x + px, y + py) for n, lx, ly in local_geo(ref)['pads'] for px, py in [rotp(lx, ly, rot)]]


placed = {}   # ref -> (x1, y1, x2, y2) absolute courtyard box
where = {}    # ref -> (x, y, rot)
CLR = 0.35


def put(ref, x, y, rot=0):
    fp = fps.get(ref) or load(ref)
    local_geo(ref)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    r = rel_box(ref, rot)
    placed[ref] = (x + r[0], y + r[1], x + r[2], y + r[3])
    if ref == 'A1':          # NUCLEO socket: only the two header rows block parts (low parts may go under it)
        assert rot == 0
        placed['A1'] = (x - 1.55, y - 1.55, x + 1.55, y + 37.11)
        placed['A1#CN4'] = (x + 13.69, y - 1.55, x + 16.79, y + 37.11)
    where[ref] = (x, y, rot)
    return fp


def free(b, region):
    x1, y1, x2, y2 = b
    rx1, ry1, rx2, ry2 = region
    if x1 < rx1 or y1 < ry1 or x2 > rx2 or y2 > ry2:
        return False
    if x1 < BX0 + 0.3 or y1 < BY0 + 0.3 or x2 > BX0 + BW - 0.3 or y2 > BY0 + BH - 0.3:
        return False
    for a1, b1, a2, b2 in placed.values():
        if x1 < a2 + CLR and x2 > a1 - CLR and y1 < b2 + CLR and y2 > b1 - CLR:
            return False
    return True


SKIP_TARGET = {'GND'}


def placed_pads(ref):
    x, y, rot = where[ref]
    return abs_pads(ref, x, y, rot)


def autoplace(refs, region, anchors):
    """Place small parts near the pads (of anchors / already placed group members) they share a net with."""
    group = list(anchors)

    def nets_of(ref):
        return {n for n, _, _ in local_geo(ref)['pads']} - SKIP_TARGET - {''}

    def score(ref):
        my = nets_of(ref)
        return -sum(1 for a in group for n, _, _ in placed_pads(a) if n in my)
    todo = sorted(refs, key=score)
    for ref in todo:
        my = nets_of(ref)
        tgt = [(x, y, n) for a in group for n, x, y in placed_pads(a) if n in my]
        if tgt:
            tx = sum(t[0] for t in tgt) / len(tgt)
            ty = sum(t[1] for t in tgt) / len(tgt)
        else:
            tx, ty = (region[0] + region[2]) / 2, (region[1] + region[3]) / 2
        rels = {rot: rel_box(ref, rot) for rot in (0, 90, 180, 270)}
        best = None
        step = 0.25
        first_ring = None
        for ring in range(0, 160):
            if ring == 0:
                cands = [(tx, ty)]
            else:
                cands = [(tx + i * step, ty + j * step) for i in range(-ring, ring + 1) for j in (-ring, ring)]
                cands += [(tx + i * step, ty + j * step) for i in (-ring, ring) for j in range(-ring + 1, ring)]
            for (cx, cy) in cands:
                for rot, r in rels.items():
                    b = (cx + r[0], cy + r[1], cx + r[2], cy + r[3])
                    if not free(b, region):
                        continue
                    cost = 0.0
                    for n, px, py in abs_pads(ref, cx, cy, rot):
                        d = [math.hypot(px - x, py - y) for x, y, nn in tgt if nn == n]
                        if d:
                            cost += min(d)
                    if best is None or cost < best[0] - 1e-9:
                        best = (cost, cx, cy, rot)
                        if first_ring is None:
                            first_ring = ring
            if first_ring is not None and ring >= first_ring + 6:
                break
        if best is None:
            raise SystemExit(f'no room for {ref} in region {region}')
        put(ref, best[1], best[2], best[3])
        group.append(ref)


def rng(prefix, a, b):
    return [f'{prefix}{i}' for i in range(a, b + 1)]


# ---------------------------------------------------------- fixed parts
# Terminal blocks: wire entry = footprint +Y side; rot 270 -> entry faces -X (left edge).
for ref, py in (('J5', 103.6), ('J1', 115.6), ('J7', 127.6)):
    put(ref, 104.5, py, 270)
# BNCs on the bottom edge: the body front (footprint y = +10.02) sits on the board edge, barrel outside.
BNC_Y = BY0 + BH - 10.02
put('J2', 117.5, BNC_Y, 0)
put('J8', 133.5, BNC_Y, 0)
# NUCLEO-L432KC socket on the right edge, USB end at the top edge (UM1956 fig. 5: pin 1 is 8.9 mm
# from the USB edge, rows 15.24 mm apart, board 18.54 mm wide).
put('A1', BX0 + BW - 16.89, BY0 + 9.1, 0)


def buck_ti(u, l, cin, chf, cout, ox, oy):
    """LMR36015 placement after TI SNVSB49D fig. 12-2: inductor above SW (pin 12) with Cout on both
    sides, Cin + Chf against the VIN/PGND pairs (pins 2/1 left, 10/11 right)."""
    put(u, ox, oy, 0)
    put(l, ox, oy - 5.3, 90)                       # pad 1 (SW) toward pin 12, pad 2 (VOUT) away
    put(chf[0], ox - 2.85, oy - 0.8, 90)           # pad 2 (GND) up at pin 1, pad 1 (VIN) down at pin 2
    put(chf[1], ox + 2.85, oy - 0.8, 90)           # same at pins 11/10
    put(cin[0], ox - 7.2, oy + 0.6, 90)
    put(cin[1], ox + 7.2, oy + 0.6, 90)
    for dx, c in zip((-8.0, -4.4, 4.4, 8.0), cout):
        put(c, ox + dx, oy - 5.8, 270)             # pad 1 (VOUT) up, pad 2 (GND) down


buck_ti('U6', 'L1', ['C27', 'C28'], ['C29', 'C30'], ['C31', 'C32', 'C33', 'C34'], 129.0, 108.8)
buck_ti('U7', 'L2', ['C37', 'C38'], ['C39', 'C40'], ['C41', 'C42', 'C43', 'C44'], 150.6, 108.8)
autoplace(['C35', 'C36', 'R29', 'R30'], (118.6, 100.3, 139.8, 117.4), ['U6', 'L1'])
autoplace(['C45', 'C46', 'R31', 'R32'], (139.8, 100.3, 161.0, 117.4), ['U7', 'L2'])
autoplace(['R33', 'C47'], (160.6, 100.3, 171.2, 117.4), ['L2'])
autoplace(['D1', 'D2'], (109.2, 100.3, 118.6, 122.0), ['J5'])

# IEPE current sources above their BNCs (with the current-step jumper and test points)
put('U1', 117.0, 131.0, 0)
autoplace(['R1', 'C2', 'C3', 'R4', 'R5', 'R6', 'C1', 'R2', 'R3', 'R47', 'JP1', 'TP1', 'TP5'],
          (109.2, 117.6, 125.4, 149.2), ['U1', 'J1', 'J2'])
put('U8', 133.5, 131.0, 0)
autoplace(['R36', 'C49', 'C50', 'R34', 'C48', 'R35', 'R48', 'JP2', 'TP3', 'TP6'],
          (125.4, 117.6, 141.6, 149.2), ['U8', 'J7', 'J8'])

# AFE + DAC per channel
put('U3', 150.0, 123.5, 0)
put('U2', 145.5, 129.5, 0)
autoplace(['C7', 'R13', 'R14', 'R16', 'R18', 'R7', 'R8', 'R12', 'C4', 'C5', 'C6', 'R9', 'R10', 'R11',
           'R15', 'R17', 'C8', 'TP2'], (141.6, 117.6, 157.4, 141.0), ['U3', 'U2'])
put('U9', 150.0, 146.0, 0)
put('U10', 145.5, 152.0, 0)
autoplace(['C54', 'R38', 'R39', 'R40', 'R41', 'R42', 'R43', 'R37', 'C51', 'C52', 'C53', 'R46',
           'R44', 'R45', 'C55', 'TP4'], (141.6, 141.0, 157.4, 163.7), ['U9', 'U10'])

# ADC next to the NUCLEO CN3 row (I2S/I2C side): analog end of the PCM1808 toward the AFE,
# digital end toward the NUCLEO.
put('U4', 164.0, 129.0, 90)
_p6 = fps['U4'].FindPadByNumber('6').GetPosition()
x6, y6 = pcbnew.ToMM(_p6.x), pcbnew.ToMM(_p6.y)
put('Y1', x6 + 0.5, y6 + 4.2, 0)                   # oscillator right at SCKI (pin 6)
autoplace(['C15', 'C16', 'C17', 'C18', 'C11', 'C12', 'C13', 'C10', 'C19', 'R19', 'R20', 'C9', 'C14',
           'C20', 'R21', 'R22', 'R23', 'R24', 'R49', 'R50', 'R51', 'TP7'],
          (157.4, 117.6, 171.3, 163.7), ['U4', 'Y1'])

missing = sorted(set(comps) - set(fps))
if missing:
    raise SystemExit('not placed: %r' % missing)

pcbnew.SaveBoard(os.path.join(OUT, 'pcb.kicad_pcb'), board)
print('placed', len(fps), 'footprints; nets', len(nets))

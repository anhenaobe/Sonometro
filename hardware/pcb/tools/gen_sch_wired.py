"""Generate pcb.kicad_sch (single A3 sheet) with real wiring inside each functional block.

* Inside a block every connection is a visible wire (junction dots added automatically).
* Global labels are used only for signals that leave a block; rails use power symbols.
* A geometric self-check aborts if a wire touches a pin/wire/label of another net, if a pin is
  left unconnected, or if the drawn connectivity differs from design.py.
Usage: python gen_sch_wired.py <out_dir>   (needs <out_dir>/lib/Sonometro.kicad_sym)
"""
import os
import sys
import copy
import uuid
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import get_symbol, pins as lib_pins, dump, find, find1, Sym  # noqa: E402
import design  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out')
ROOT_UUID = '5af46bdc-3756-44a4-963b-7cd4ccc2d036'
PROJECT = 'pcb'
NS = uuid.UUID('6f1d7c2a-5b8e-4c3d-9a10-50a0e7e7a003')
LOCAL_LIB = os.path.join(OUT, 'lib', 'Sonometro.kicad_sym')
parts = design.parts
RAILS = set(design.RAILS)
RAIL_SYM = {'GND': 'power:GND', '3V3': 'power:+3V3', '5V': 'power:+5V', '5V_A': 'power:+5VA',
            '24V_PROT': 'power:+24V'}
TWO_PIN = ('Device:R', 'Device:C', 'Device:L')
# (dx, dy, justify) relative to the symbol origin, used instead of the library field position
VAL_POS = {'U2': (2.54, 10.16, 'left'), 'U10': (2.54, 10.16, 'left'), 'U5': (2.54, 29.21, 'left'),
           'U4': (-20.32, 12.7, 'right'), 'U6': (5.08, 17.78, 'left'), 'U7': (5.08, 17.78, 'left'),
           'Y1': (3.81, 10.16, 'right'), 'U1': (2.54, -3.81, 'left'), 'U8': (2.54, -3.81, 'left'),
           'D2': (2.54, 1.27, 'left'), 'J2': (-2.54, -3.81, 'left'), 'J8': (-2.54, -3.81, 'left'),
           'JP1': (-2.54, 1.27, 'right'), 'JP2': (-2.54, 1.27, 'right')}
REF_POS = {'U1': (2.54, -6.35, 'left'), 'U8': (2.54, -6.35, 'left'), 'D2': (2.54, -1.27, 'left'),
           'J2': (-2.54, -6.35, 'left'), 'J8': (-2.54, -6.35, 'left'),
           'JP1': (-2.54, -1.27, 'right'), 'JP2': (-2.54, -1.27, 'right')}
CONN_ABOVE = set()


def U(key):
    return str(uuid.uuid5(NS, key))


def r4(v):
    return round(v + 0.0, 4)


def pt(x, y):
    return (r4(x), r4(y))


# ------------------------------------------------------------------ symbols
libsyms = {}


def libsym(lib_id):
    if lib_id not in libsyms:
        lib, name = lib_id.split(':')
        s = get_symbol(LOCAL_LIB if lib == 'Sonometro' else lib, name)
        s[1] = lib_id
        libsyms[lib_id] = s
    return libsyms[lib_id]


def xform(px, py, rot, mirror=None):
    x, y = px, -py
    if rot == 90:
        x, y = y, -x
    elif rot == 180:
        x, y = -x, -y
    elif rot == 270:
        x, y = -y, x
    if mirror == 'y':
        x = -x
    elif mirror == 'x':
        y = -y
    return x, y


DIRS = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}

# ------------------------------------------------------------------ drawing state
placed = {}        # (ref, unit) -> (x, y, rot, mirror)
pin_at = {}        # 'REF.NUM' -> point
pin_list = []      # (point, ref, num, net, hidden_nc)
segs = []          # [p1, p2, net]
psyms = []         # (net, point, dir)
labels = []        # (kind, net, point, dir, shape)
ncs = []           # point
flags = []         # point
texts = []
rects = []


def place(ref, x, y, rot=0, unit=1, mirror=None):
    p = parts[ref]
    placed[(ref, unit)] = (r4(x), r4(y), rot, mirror)
    for lp in lib_pins(libsym(p['sym'])):
        if lp['unit'] not in (0, unit):
            continue
        ox, oy = xform(lp['x'], lp['y'], rot, mirror)
        q = pt(x + ox, y + oy)
        key = f'{ref}.{lp["num"]}'
        pin_at[key] = q
        pin_list.append((q, ref, lp['num'], p['pins'].get(lp['num']),
                         lp['hidden'] and lp['type'] == 'no_connect'))


def P(s):
    if isinstance(s, str):
        return pin_at[s]
    return pt(*s)


def W(net, *pts_):
    q = [P(s) for s in pts_]
    for a, b in zip(q, q[1:]):
        if a != b:
            if a[0] != b[0] and a[1] != b[1]:
                raise SystemExit(f'non-orthogonal wire {a}->{b} ({net})')
            segs.append([a, b, net])


def pwr(net, s, d):
    psyms.append((net, P(s), d))


def gl(net, s, d, shape='passive'):
    labels.append(('global', net, P(s), d, shape))


def ll(net, s, d):
    labels.append(('local', net, P(s), d, None))


def nc(s):
    ncs.append(P(s))


def flag(s, d='up'):
    flags.append((P(s), d))


def gnd_flag(x, y):
    flag((x, y))
    W('GND', (x, y), (x, y + 2.54))
    pwr('GND', (x, y + 2.54), 'down')


def hang(ref, top, toppin='1'):
    """2-pin part, vertical, with pin `toppin` at point `top`."""
    x, y = P(top)
    place(ref, x, y + 3.81, 0 if toppin == '1' else 180)


def hor(ref, left, leftpin='1'):
    """2-pin part, horizontal, with pin `leftpin` at point `left`."""
    x, y = P(left)
    place(ref, x + 3.81, y, 90 if leftpin == '1' else 270)


def block(x1, y1, x2, y2, title):
    rects.append((x1, y1, x2, y2))
    texts.append((x1 + 2.54, y1 + 5.08, title, 2.0, True))


def note(x, y, t, size=1.27):
    texts.append((x, y, t, size, False))


# ================================================================== BLOCK A: power
def buck(ox, oy, u, l, cin, cboot, cvcc, cout, rtop, rbot, rail, first):
    place(u, ox, oy)
    yr = oy - 7.62
    W('24V_PROT', f'{u}.2', (ox - 71.12, yr))
    for x, c in zip((-55.88, -45.72, -35.56, -25.4), cin):
        hang(c, (ox + x, yr), '1')
        pwr('GND', (ox + x, yr + 7.62), 'down')
    W('24V_PROT', (ox - 15.24, yr), (ox - 15.24, oy - 2.54), f'{u}.9')
    W('24V_PROT', f'{u}.10', (ox - 15.24, oy - 5.08))
    nc(f'{u}.8')
    W('VCC', f'{u}.5', (ox - 20.32, oy + 7.62))
    hang(cvcc, (ox - 20.32, oy + 7.62), '1')
    pwr('GND', (ox - 20.32, oy + 15.24), 'down')
    for x, pn in ((-2.54, '1'), (0, '11'), (2.54, '6')):
        W('GND', f'{u}.{pn}', (ox + x, oy + 15.24))
    W('GND', (ox - 2.54, oy + 15.24), (ox + 2.54, oy + 15.24))
    pwr('GND', (ox, oy + 15.24), 'down')
    # switch node, bootstrap, inductor
    W('BOOT', f'{u}.4', (ox + 17.78, oy - 7.62), (ox + 17.78, oy - 12.7), (ox + 20.32, oy - 12.7))
    hang(cboot, (ox + 20.32, oy - 12.7), '1')
    W('SW', f'{u}.12', (ox + 29.21, oy - 5.08))
    W('SW', f'{u}.3', (ox + 15.24, oy - 2.54), (ox + 15.24, oy - 5.08))
    hor(l, (ox + 29.21, oy - 5.08), '1')
    ll('SW_' + ('3' if rail == '3V3' else '5'), (ox + 15.24, oy - 2.54), 'down')
    # output rail + caps + feedback divider
    yo = oy - 5.08
    end = ox + 86.36
    W(rail, f'{l}.2', (end, yo))
    for x, c in zip((40.64, 50.8, 60.96, 71.12), cout):
        hang(c, (ox + x, yo), '1')
        pwr('GND', (ox + x, oy + 2.54), 'down')
    hang(rtop, (ox + 81.28, yo), '1')
    hang(rbot, (ox + 81.28, oy + 2.54), '1')
    pwr('GND', (ox + 81.28, oy + 10.16), 'down')
    W('FB', f'{u}.7', (ox + 15.24, oy + 7.62), (ox + 15.24, oy + 10.16), (ox + 78.74, oy + 10.16),
      (ox + 78.74, oy + 2.54), (ox + 81.28, oy + 2.54))
    pwr(rail, (end, yo), 'up')
    flag((ox + 76.2, yo))
    note(ox + 36.83, oy + 21.59, f'Vout = 1 V x (1 + {rtop}/{rbot})')


def power_block(ox, oy1, oy2):
    buck(ox, oy1, 'U6', 'L1', ['C27', 'C28', 'C29', 'C30'], 'C35', 'C36', ['C31', 'C32', 'C33', 'C34'],
         'R29', 'R30', '3V3', True)
    buck(ox, oy2, 'U7', 'L2', ['C37', 'C38', 'C39', 'C40'], 'C45', 'C46', ['C41', 'C42', 'C43', 'C44'],
         'R31', 'R32', '5V', False)
    y1, y2 = oy1 - 7.62, oy2 - 7.62
    ym = oy1 + 22.86                         # input stage sits between the two bucks
    bus = ox - 71.12
    W('24V_PROT', (bus, y1), (bus, y2))      # 24V_PROT bus feeding both buck input rails
    place('J5', ox - 86.36, ym, 0, mirror='y')
    W('24V_IN', 'J5.1', (ox - 78.74, ym))
    place('D1', ox - 74.93, ym, 180)         # SS34: anode (pin 2) left, cathode (pin 1) on the bus
    W('GND', 'J5.2', (ox - 78.74, ym + 2.54))
    pwr('GND', (ox - 78.74, ym + 2.54), 'down')
    W('24V_PROT', (bus, ym), (ox - 66.04, ym))
    place('D2', ox - 66.04, ym + 3.81, 270)  # SMBJ26A: cathode on 24V_PROT, anode to GND
    pwr('GND', 'D2.2', 'down')
    pwr('24V_PROT', (ox - 60.96, y1), 'up')
    flag((ox - 50.8, y1))
    gnd_flag(ox - 86.36, ym + 22.86)
    note(ox - 88.9, ym + 13.97, 'J5: 24 V de laboratorio')
    note(ox - 88.9, ym + 17.78, 'D1 polaridad, D2 TVS')
    # 5V -> R33 -> 5V_A
    yo = oy2 - 5.08
    hor('R33', (ox + 91.44, yo), '1')
    W('5V', (ox + 86.36, yo), 'R33.1')
    W('5V_A', 'R33.2', (ox + 109.22, yo))
    hang('C47', (ox + 104.14, yo), '1')
    pwr('GND', (ox + 104.14, oy2 + 2.54), 'down')
    pwr('5V_A', (ox + 109.22, yo), 'up')
    flag((ox + 101.6, yo))


# ================================================================== BLOCK B/C: IEPE sources
def iepe_block(bx, by, u, rfeed, csup, jen, jmic, ch2):
    place(u, bx, by)
    sup = 'IEPE_SUP_SV' if ch2 else 'IEPE_SUP'
    feed = 'IEPE_FEED_SV' if ch2 else 'IEPE_FEED'
    out = 'IEPE_SV' if ch2 else 'IEPE'
    W(sup, f'{u}.7', (bx, by - 10.16))
    hor(rfeed, (bx - 29.21, by - 10.16), '1')
    W(sup, f'{rfeed}.2', (bx, by - 10.16))
    for x, c in zip((-17.78, -7.62), csup):
        hang(c, (bx + x, by - 10.16), '1')
        pwr('GND', (bx + x, by - 2.54), 'down')
    ll(sup, (bx - 5.08, by - 10.16), 'right')
    place(jen, bx - 43.18, by - 12.7, 0, mirror='y')
    W(feed, f'{jen}.2', f'{rfeed}.1')
    W('24V_PROT', f'{jen}.1', (bx - 35.56, by - 12.7))
    pwr('24V_PROT', (bx - 35.56, by - 12.7), 'up')
    # current-setting network, output resistor and the current-step branch (resistor + jumper)
    yo = by + 25.4
    if not ch2:
        W('SET', f'{u}.5', (bx + 20.32, by))
        hang('R4', (bx + 10.16, by), '2')
        hang('R5', (bx + 10.16, by + 7.62), '2')
        hang('R6', (bx + 10.16, by + 15.24), '1')
        W(out, 'R6.2', (bx + 10.16, yo))
        hang('C1', (bx + 20.32, by), '1')
        W(out, 'C1.2', (bx + 20.32, yo))
        W('OUT', f'{u}.2', (bx, by + 7.62))
        W('OUT', (bx - 20.32, by + 7.62), (bx, by + 7.62))
        hang('R2', (bx, by + 7.62), '2')
        hang('R3', (bx - 10.16, by + 7.62), '2')
        W(out, 'R2.1', (bx, yo))
        W(out, 'R3.1', (bx - 10.16, yo))
        hang('R47', (bx - 20.32, by + 7.62), '1')
        place('JP1', bx - 20.32, by + 20.32, 270)        # pin 1 (STEP1) top, pin 2 on IEPE
        tp_x, tp, tpg = bx - 5.08, 'TP1', 'TP5'
    else:
        W('SET', f'{u}.5', (bx + 20.32, by))
        hang('R34', (bx + 10.16, by), '1')
        W(out, 'R34.2', (bx + 10.16, yo))
        hang('C48', (bx + 20.32, by), '1')
        W(out, 'C48.2', (bx + 20.32, yo))
        hang('R35', f'{u}.2', '1')
        W(out, 'R35.2', (bx, yo))
        W('OUT', f'{u}.2', (bx - 10.16, by + 5.08))
        hang('R48', (bx - 10.16, by + 5.08), '1')
        place('JP2', bx - 10.16, by + 17.78, 270)        # pin 1 (STEP2) top, pin 2 toward IEPE_SV
        W(out, 'JP2.2', (bx - 10.16, yo))
        tp_x, tp, tpg = bx + 5.08, 'TP3', 'TP6'
    W(out, (bx - 22.86, yo), (bx + 25.4, yo))
    gl(out, (bx - 22.86, yo), 'left', 'output')
    place(tp, tp_x, yo)                                  # oscilloscope test point on the sensor node
    place(jmic, bx + 30.48, yo, 0)                       # BNC: centre = signal + IEPE bias, shell = GND
    pwr('GND', f'{jmic}.2', 'down')
    place(tpg, bx + 36.83, yo + 10.16)                   # GND test point next to the BNC
    pwr('GND', (bx + 36.83, yo + 10.16), 'down')


# ================================================================== BLOCK D/E: AFE + DAC
def afe_block(dx, dy, m, ch2):
    """m maps CH1 refs -> refs of this channel."""
    g = lambda r: m.get(r, r)  # noqa: E731
    sfx = '_SV' if ch2 else ''
    udac, uop = g('U2'), g('U3')
    place(udac, dx - 40.64, dy - 22.86)
    place(uop, dx, dy, unit=1)
    place(uop, dx, dy - 20.32, unit=2)
    place(uop, dx + 45.72, dy - 20.32, unit=3)
    vdd = '3V3_DAC' + sfx
    W(vdd, f'{udac}.3', (dx - 40.64, dy - 40.64), (dx - 13.97, dy - 40.64))
    for x, c in ((-30.48, 'C5'), (-20.32, 'C6')):
        hang(g(c), (dx + x, dy - 40.64), '1')
        pwr('GND', (dx + x, dy - 33.02), 'down')
    hor(g('R9'), (dx - 13.97, dy - 40.64), '1')
    pwr('3V3', f'{g("R9")}.2', 'up')
    flag((dx - 17.78, dy - 40.64))
    ll(vdd, (dx - 38.1, dy - 40.64), 'right')
    pwr('GND', f'{udac}.2', 'down')
    if not ch2:
        W('I2C_SCL', f'{udac}.5', (dx - 63.5, dy - 25.4))
        gl('I2C_SCL', (dx - 63.5, dy - 25.4), 'left', 'bidirectional')
        hang('R10', (dx - 55.88, dy - 33.02), '2')
        pwr('3V3', (dx - 55.88, dy - 33.02), 'up')
        W('I2C_SDA', f'{udac}.4', (dx - 88.9, dy - 22.86))
        gl('I2C_SDA', (dx - 88.9, dy - 22.86), 'left', 'bidirectional')
        hang('R11', (dx - 81.28, dy - 30.48), '2')
        pwr('3V3', (dx - 81.28, dy - 30.48), 'up')
        W('GND', f'{udac}.6', (dx - 53.34, dy - 20.32))
        pwr('GND', (dx - 53.34, dy - 20.32), 'down')
    else:
        W('I2C_SCL', f'{udac}.5', (dx - 58.42, dy - 25.4))
        gl('I2C_SCL', (dx - 58.42, dy - 25.4), 'left', 'bidirectional')
        W('I2C_SDA', f'{udac}.4', (dx - 58.42, dy - 22.86))
        gl('I2C_SDA', (dx - 58.42, dy - 22.86), 'left', 'bidirectional')
        W(vdd, f'{udac}.6', (dx - 53.34, dy - 20.32), (dx - 53.34, dy - 15.24))
        ll(vdd, (dx - 53.34, dy - 15.24), 'left')
        note(dx - 80, dy - 5.08, 'A0 = 1 -> direccion I2C 0x61')
    # DAC -> RC -> buffer (VSHIFT)
    W('DAC_RAW', f'{udac}.1', (dx - 27.94, dy - 22.86))
    hor(g('R12'), (dx - 27.94, dy - 22.86), '1')
    W('DAC_F', f'{g("R12")}.2', f'{uop}.5')
    hang(g('C4'), (dx - 15.24, dy - 22.86), '1')
    pwr('GND', (dx - 15.24, dy - 15.24), 'down')
    W('VSHIFT', f'{uop}.7', (dx + 10.16, dy - 20.32), (dx + 10.16, dy - 12.7), (dx - 10.16, dy - 12.7),
      (dx - 10.16, dy - 17.78), f'{uop}.6')
    W('VSHIFT', (dx - 10.16, dy - 12.7), (dx - 10.16, dy - 2.54), f'{uop}.3')
    # input divider chain (1M = 390k + 365k + 191k + 54k9) into the summing node
    hor(g('R18'), (dx - 19.05, dy + 2.54), '2')
    hor(g('R16'), (dx - 26.67, dy + 2.54), '2')
    hor(g('R14'), (dx - 34.29, dy + 2.54), '2')
    hor(g('R13'), (dx - 41.91, dy + 2.54), '2')
    iepe = 'IEPE' + sfx
    W(iepe, f'{g("R13")}.2', (dx - 45.72, dy + 2.54))
    gl(iepe, (dx - 45.72, dy + 2.54), 'left', 'input')
    W('SUM', f'{g("R18")}.1', f'{uop}.2')
    W('SUM', (dx - 10.16, dy + 2.54), (dx - 10.16, dy + 10.16), (dx - 7.62, dy + 10.16))
    hor(g('R7'), (dx - 7.62, dy + 10.16), '1')
    hor(g('R8'), (dx, dy + 10.16), '2')
    rest = 'REST_SV' if ch2 else 'REST_OUT'
    W(rest, f'{g("R8")}.1', (dx + 10.16, dy + 10.16), (dx + 10.16, dy))
    W(rest, f'{uop}.1', (dx + 27.94, dy))
    # C16: CF = 10 pF C0G en paralelo con R7+R8 (sin él el sumador queda con 3-6° de margen de fase)
    W('SUM', (dx - 10.16, dy + 10.16), (dx - 10.16, dy + 15.24), (dx - 7.62, dy + 15.24))
    hor(g('C56'), (dx - 7.62, dy + 15.24), '1')
    W(rest, (dx, dy + 15.24), (dx + 10.16, dy + 15.24), (dx + 10.16, dy + 10.16))
    gl(rest, (dx + 27.94, dy), 'right', 'output')
    place('TP4' if ch2 else 'TP2', dx + 22.86, dy)      # oscilloscope test point on REST

    # DC monitor divider
    hang(g('R15'), (dx + 17.78, dy), '2')
    mon = 'DC_MON2' if ch2 else 'DC_MON'
    W(mon, f'{g("R15")}.1', (dx + 40.64, dy + 7.62))
    gl(mon, (dx + 40.64, dy + 7.62), 'right', 'output')
    hang(g('R17'), (dx + 25.4, dy + 7.62), '2')
    pwr('GND', (dx + 25.4, dy + 15.24), 'down')
    hang(g('C8'), (dx + 35.56, dy + 7.62), '1')
    pwr('GND', (dx + 35.56, dy + 15.24), 'down')
    # op-amp supply
    W('5V_A', f'{uop}.8', (dx + 43.18, dy - 30.48), (dx + 53.34, dy - 30.48), (dx + 53.34, dy - 24.13))
    hang(g('C7'), (dx + 53.34, dy - 24.13), '2')
    pwr('5V_A', (dx + 48.26, dy - 30.48), 'up')
    W('GND', f'{uop}.4', (dx + 43.18, dy - 10.16), (dx + 53.34, dy - 10.16), (dx + 53.34, dy - 16.51))
    pwr('GND', (dx + 48.26, dy - 10.16), 'down')


# ================================================================== BLOCK F: ADC + clock
def adc_block(fx, fy):
    place('U4', fx, fy)
    # left channel: REST_OUT -> C9 -> R19 -> VINL (C10 to GND)
    W('ADC_INL', 'U4.13', (fx - 15.24, fy - 7.62), (fx - 15.24, fy - 17.78), (fx - 24.13, fy - 17.78))
    hang('C10', (fx - 20.32, fy - 17.78), '1')
    pwr('GND', (fx - 20.32, fy - 10.16), 'down')
    hor('R19', (fx - 31.75, fy - 17.78), '1')
    hor('C9', (fx - 39.37, fy - 17.78), '1')
    W('REST_OUT', 'C9.1', (fx - 45.72, fy - 17.78))
    gl('REST_OUT', (fx - 45.72, fy - 17.78), 'left', 'input')
    # right channel: REST_SV -> C14 -> R20 -> VINR (C19 to GND)
    W('ADC_INR', 'U4.14', (fx - 24.13, fy - 2.54))
    hang('C19', (fx - 20.32, fy - 2.54), '1')
    pwr('GND', (fx - 20.32, fy + 5.08), 'down')
    hor('R20', (fx - 31.75, fy - 2.54), '1')
    hor('C14', (fx - 39.37, fy - 2.54), '1')
    W('REST_SV', 'C14.1', (fx - 45.72, fy - 2.54))
    gl('REST_SV', (fx - 45.72, fy - 2.54), 'left', 'input')
    # supplies
    W('5V_A', 'U4.3', (fx - 2.54, fy - 35.56), (fx - 27.94, fy - 35.56))
    for x, c in ((-12.7, 'C17'), (-22.86, 'C18')):
        hang(c, (fx + x, fy - 35.56), '1')
        pwr('GND', (fx + x, fy - 27.94), 'down')
    pwr('5V_A', (fx - 27.94, fy - 35.56), 'up')
    W('3V3', 'U4.4', (fx + 2.54, fy - 35.56), (fx + 33.02, fy - 35.56))
    for x, c in ((7.62, 'C11'), (17.78, 'C12'), (27.94, 'C13')):
        hang(c, (fx + x, fy - 35.56), '1')
        pwr('GND', (fx + x, fy - 27.94), 'down')
    pwr('3V3', (fx + 33.02, fy - 35.56), 'up')
    # VREF, grounds, mode pins (MD1=0, FMT=0, MD0=1: master 512 fs, I2S)
    W('PCM_VREF', 'U4.1', (fx - 7.62, fy + 20.32), (fx - 22.86, fy + 20.32))
    for x, c in ((-12.7, 'C15'), (-22.86, 'C16')):
        hang(c, (fx + x, fy + 20.32), '1')
        pwr('GND', (fx + x, fy + 27.94), 'down')
    for pn, x in (('2', -5.08), ('5', -2.54)):
        W('GND', f'U4.{pn}', (fx + x, fy + 17.78))
    W('GND', (fx - 5.08, fy + 17.78), (fx - 2.54, fy + 17.78))
    pwr('GND', (fx - 2.54, fy + 17.78), 'down')
    # mode pins through 10k (SLES177B 8.2.2.1): MD1 = 0, FMT = 0 (I2S), MD0 = 1 -> master 512 fs
    W('MD1', 'U4.11', (fx, fy + 30.48))
    hor('R50', (fx, fy + 30.48), '1')
    pwr('GND', 'R50.2', 'down')
    W('FMT', 'U4.12', (fx + 2.54, fy + 22.86))
    hor('R51', (fx + 2.54, fy + 22.86), '1')
    pwr('GND', 'R51.2', 'down')
    W('MD0', 'U4.10', (fx + 7.62, fy + 17.78), (fx + 12.7, fy + 17.78))
    hor('R49', (fx + 12.7, fy + 17.78), '2')
    pwr('3V3', 'R49.1', 'up')
    # clock: Y1 -> R21 -> SCKI
    W('PCM_MCLK', 'U4.6', (fx + 15.24, fy - 7.62), (fx + 15.24, fy - 20.32), (fx + 19.05, fy - 20.32))
    hor('R21', (fx + 19.05, fy - 20.32), '2')
    place('Y1', fx + 38.1, fy - 20.32, 0, mirror='y')
    W('MCLK_SOURCE', 'R21.1', 'Y1.3')
    pwr('3V3', 'Y1.4', 'up')
    pwr('GND', 'Y1.2', 'down')
    W('3V3', 'Y1.1', (fx + 48.26, fy - 20.32))
    pwr('3V3', (fx + 48.26, fy - 20.32), 'up')
    hang('C20', (fx + 58.42, fy - 24.13), '1')
    pwr('3V3', (fx + 58.42, fy - 24.13), 'up')
    pwr('GND', (fx + 58.42, fy - 16.51), 'down')
    # I2S lines with series resistors to the MCU
    W('PCM_LRCK', 'U4.7', (fx + 24.13, fy - 5.08))
    hor('R23', (fx + 24.13, fy - 5.08), '2')
    W('SAI_FS', 'R23.1', (fx + 35.56, fy - 5.08))
    gl('SAI_FS', (fx + 35.56, fy - 5.08), 'right', 'output')
    W('PCM_BCK', 'U4.8', (fx + 17.78, fy - 2.54), (fx + 17.78, fy + 2.54), (fx + 24.13, fy + 2.54))
    hor('R22', (fx + 24.13, fy + 2.54), '2')
    W('SAI_SCK', 'R22.1', (fx + 35.56, fy + 2.54))
    gl('SAI_SCK', (fx + 35.56, fy + 2.54), 'right', 'output')
    W('PCM_DOUT', 'U4.9', (fx + 15.24, fy), (fx + 15.24, fy + 10.16), (fx + 24.13, fy + 10.16))
    hor('R24', (fx + 24.13, fy + 10.16), '2')
    W('SAI_SD', 'R24.1', (fx + 35.56, fy + 10.16))
    gl('SAI_SD', (fx + 35.56, fy + 10.16), 'right', 'output')


# ================================================================== BLOCK G: NUCLEO-L432KC
NUC_LEFT = {1: ('SAI_FS', 'input'), 2: ('SAI_SD', 'input'), 7: ('I2C_SDA', 'bidirectional'),
            8: ('I2C_SCL', 'bidirectional'), 12: ('SAI_SCK', 'input')}
NUC_RIGHT = {26: ('DC_MON2', 'input'), 27: ('DC_MON', 'input')}


def nucleo_block(gx, gy):
    """A1 = socket for the NUCLEO-L432KC (UM1956 Rev 6 table 16). Only GND and signals are used."""
    place('A1', gx, gy)
    for pn, (net, shape) in NUC_LEFT.items():
        x, y = P(f'A1.{pn}')
        W(net, f'A1.{pn}', (x - 5.08, y))
        gl(net, (x - 5.08, y), 'left', shape)
    for pn, (net, shape) in NUC_RIGHT.items():
        x, y = P(f'A1.{pn}')
        W(net, f'A1.{pn}', (x + 5.08, y))
        gl(net, (x + 5.08, y), 'right', shape)
    x, y = P('A1.4')                                   # CN3-4 GND
    W('GND', 'A1.4', (x - 2.54, y))
    pwr('GND', (x - 2.54, y), 'left')
    x, y = P('A1.17')                                  # CN4-2 GND
    W('GND', 'A1.17', (x + 2.54, y))
    pwr('GND', (x + 2.54, y), 'right')
    for pn in range(1, 31):
        if pn not in NUC_LEFT and pn not in NUC_RIGHT and pn not in (4, 17):
            nc(f'A1.{pn}')
    place('TP7', gx + 30.48, gy + 27.94)               # extra GND test point
    pwr('GND', (gx + 30.48, gy + 27.94), 'down')
    for i, t in enumerate(['Zocalo 2x 1x15 hembra; la NUCLEO se enchufa con el USB hacia el borde.',
                           'NO conectar +3V3, +5V ni VIN: la NUCLEO va por su USB.',
                           'CN4-7/CN4-8 (A5/A4) libres: SB16/SB18 los unen a PB6/PB7.',
                           'Firmware: PA5 y PA6 como entradas flotantes (UM1956 tabla 8).',
                           'Pines del simbolo: 1-15 = CN3-1..15 (izq.), 16-30 = CN4-1..15 (der.).']):
        note(gx - 36, gy + 24.13 + i * 3.81, t)


# ================================================================== sheet layout (A3)
DV = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
frames = []


def mark():
    return (len(pin_list), len(segs), len(psyms), len(labels), len(texts), len(flags), len(placed))


def close(m, title, pad=2.5):
    xs, ys = [], []

    def add(x, y):
        xs.append(x)
        ys.append(y)
    for q, *_ in pin_list[m[0]:]:
        add(*q)
    for a_, b_, _ in segs[m[1]:]:
        add(*a_)
        add(*b_)
    for net, q, d in psyms[m[2]:]:
        dx_, dy_ = DV[d]
        add(q[0] + dx_ * 5.5, q[1] + dy_ * 5.5)
        add(q[0] - 2, q[1])
        add(q[0] + 2, q[1])
    for kind, net, q, d, shape in labels[m[3]:]:
        L = len(net) * 1.05 + (3.5 if kind == 'global' else 0.5)
        dx_, dy_ = DV[d]
        add(q[0] + dx_ * L, q[1] + dy_ * L)
        add(q[0], q[1] - 1.8)
    for (x, y, t, size, bold) in texts[m[4]:]:
        add(x, y - size)
        add(x + len(t) * size * 0.8, y)
    for q, d in flags[m[5]:]:
        dx_, dy_ = DV[d]
        add(q[0] + dx_ * 4, q[1] + dy_ * 4)
    for (ref, unit), (x, y, rot, mirror) in list(placed.items())[m[6]:]:
        if parts[ref]['sym'].startswith(('Connector_Generic:', 'Sonometro:Conn_')):
            ys_ = [q[1] for q, r_, *_ in pin_list if r_ == ref]
            add(x - 1.27, min(ys_) - (6.4 if ref in CONN_ABOVE else 3.9))
            add(x - 1.27 + 1.1 * len(parts[ref]['value']), max(ys_) + 3.2)
        if parts[ref]['sym'] in TWO_PIN:
            if rot in (0, 180):
                add(x + 2.54 + 1.1 * max(len(ref), len(parts[ref]['value'])), y)
            else:
                add(x, y - 3.8)
                add(x, y + 3.8)
    x1, y1, x2, y2 = min(xs) - pad, min(ys) - pad - 6.5, max(xs) + pad, max(ys) + pad
    rects.append((r4(x1), r4(y1), r4(x2), r4(y2)))
    texts.append((r4(x1 + 2.54), r4(y1 + 5.6), title, 2.0, True))
    frames.append((title, x1, y1, x2, y2))


def blk(title, fn, *args, notes=()):
    m = mark()
    fn(*args)
    for (x, y, t) in notes:
        note(x, y, t)
    close(m, title)


OX, OY1 = 104.14, 34.29
blk('ALIMENTACION: 24 V -> 3V3 / 5V (2x LMR36015) y 5V_A (RC)', power_block, OX, OY1, OY1 + 45.72)
BX, BY = 266.7, 39.37
blk('FUENTE IEPE CH1 - ROGA RG-50 (2.8 mA)', iepe_block, BX, BY, 'U1', 'R1', ['C2', 'C3'], 'J1', 'J2', False,
    notes=[(BX - 44, BY + 39.37, 'I = 10uA(1 + 21k/75R) = 2.81 mA;  con JP1: 21k/52.9R -> 3.98 mA'),
           (BX - 44, BY + 43.18, 'J1 en serie: ahi va el amperimetro. Nunca > 30 V ni phantom 48 V')])
CX, CY = 360.68, 52.07
blk('FUENTE IEPE CH2 - SVANTEK SV 12L (1.5 mA)', iepe_block, CX, CY, 'U8', 'R36', ['C49', 'C50'], 'J7', 'J8', True,
    notes=[(CX - 44, CY + 39.37, 'I = 10uA(1 + 15k/100R) = 1.51 mA;  con JP2: 15k/60R -> 2.51 mA'),
           (CX - 44, CY + 43.18, 'SV 12L (TNC) con adaptador BNC-TNC. J7 en serie: amperimetro')])
DX, DY = 114.3, 161.29
blk('AFE CH1 + DAC (MCP4725 @0x60): resta del bias IEPE, k = 0.1', afe_block, DX, DY, {}, False,
    notes=[(DX - 98, DY + 22.86, 'REST_OUT = VSHIFT - 0.1 (IEPE - VSHIFT);  1M = 390k+365k+191k+54k9;  Rf = 2 x 49k9')])
EX, EY = 262.89, 161.29
blk('AFE CH2 + DAC (MCP4725 @0x61): espejo del CH1', afe_block, EX, EY,
    {'U2': 'U10', 'U3': 'U9', 'R12': 'R37', 'R13': 'R38', 'R14': 'R39', 'R16': 'R40', 'R18': 'R41', 'R7': 'R42',
     'R8': 'R43', 'R15': 'R44', 'R17': 'R45', 'R9': 'R46', 'C4': 'C51', 'C5': 'C52', 'C6': 'C53', 'C7': 'C54',
     'C8': 'C55', 'C56': 'C57'}, True)
GX, GY = 365.76, 138.43
blk('NUCLEO-L432KC (enchufada)', nucleo_block, GX, GY)
FX, FY = 73.66, 240.03
blk('ADC PCM1808 + RELOJ 24.576 MHz (maestro 512 fs = 48 kHz, I2S 24 bit)', adc_block, FX, FY)
m = mark()
for i, t in enumerate([
        'Base: Altium Sonometro_2CH (refs, valores, MPN y LCSC conservados) + docs/connection_matrix.md',
        '(alimentacion y canal 2; el AFE del CH2 es espejo exacto del CH1).',
        'Rev B: cambios C1-C12 (ver guia PDF): NUCLEO enchufada, oscilador 24.576 MHz, D1/D2 en la',
        'entrada, sin J6, filtros del lazo de DC a 100 nF, 100 nF X7R, BNC, escalon de corriente',
        '(JP1/JP2), puntos de prueba TP1-TP7 y R49-R51 en los pines de modo del PCM1808.',
        'Cables dentro de cada bloque; etiquetas globales entre bloques. I2C: U2 = 0x60, U10 = 0x61.',
        'Lazo de DC (firmware): DC_MON -> nuevo VSHIFT = VSHIFT - error/1.1 -> DAC; quieto al medir.']):
    note(152, 200 + i * 4.6, t, 1.3)
close(m, 'NOTAS')
for t, x1, y1, x2, y2 in frames:
    print(f'  frame {t[:28]:28} x {x1:6.1f}..{x2:6.1f}  y {y1:6.1f}..{y2:6.1f}')
    if x1 < 12 or y1 < 12 or x2 > 408 or y2 > 285:
        print('    !! outside the A3 drawing area')
for i, (t, *a1) in enumerate(frames):
    for t2, *a2 in frames[i + 1:]:
        if a1[0] < a2[2] and a2[0] < a1[2] and a1[1] < a2[3] and a2[1] < a1[3]:
            print(f'    !! overlap: {t[:20]} / {t2[:20]}')


# ================================================================== connectivity check
class UF:
    def __init__(s):
        s.p = {}

    def f(s, a):
        s.p.setdefault(a, a)
        while s.p[a] != a:
            s.p[a] = s.p[s.p[a]]
            a = s.p[a]
        return a

    def u(s, a, b):
        s.p[s.f(a)] = s.f(b)


def on_inner(q, a, b):
    if q == a or q == b:
        return False
    if a[0] == b[0] == q[0]:
        return min(a[1], b[1]) < q[1] < max(a[1], b[1])
    if a[1] == b[1] == q[1]:
        return min(a[0], b[0]) < q[0] < max(a[0], b[0])
    return False


errors = []
anchor_pts = [q for q, *_ in pin_list] + [q for _, q, _ in psyms] + [l[2] for l in labels] + ncs + [f[0] for f in flags]
# split wires at any connection point lying inside them
changed = True
while changed:
    changed = False
    ends = {q for s in segs for q in s[:2]}
    cands = set(anchor_pts) | ends
    for i, (a, b, net) in enumerate(segs):
        hit = [q for q in cands if on_inner(q, a, b)]
        if hit:
            q = sorted(hit)[0]
            segs[i] = [a, q, net]
            segs.append([q, b, net])
            changed = True
            break
# collinear overlap check
for i, (a, b, n1) in enumerate(segs):
    for c, d, n2 in segs[i + 1:]:
        if {a, b} == {c, d}:
            errors.append(f'duplicate wire {a}-{b}')
uf = UF()
for a, b, net in segs:
    uf.u(('P',) + a, ('P',) + b)
nets_at = collections.defaultdict(set)
for q, ref, num, net, hid in pin_list:
    if hid:
        continue
    uf.u(('PIN', ref, num), ('P',) + q)
for net, q, d in psyms:
    uf.u(('NET', net), ('P',) + q)
for kind, net, q, d, shape in labels:
    uf.u(('NET', net), ('P',) + q)
for net in design.parts and []:
    pass
comp_nets = collections.defaultdict(set)
comp_pins = collections.defaultdict(set)
for q, ref, num, net, hid in pin_list:
    if hid:
        continue
    r = uf.f(('PIN', ref, num))
    comp_pins[r].add(f'{ref}.{num}')
    if net:
        comp_nets[r].add(net)
for key in list(uf.p):
    if key[0] == 'NET':
        comp_nets[uf.f(key)].add('@' + key[1])
# expected membership
target = collections.defaultdict(set)
for ref, p in parts.items():
    for num, net in p['pins'].items():
        if net:
            target[net].add(f'{ref}.{num}')
for r, pins_ in comp_pins.items():
    named = {n for n in comp_nets[r] if not n.startswith('@')}
    labelled = {n[1:] for n in comp_nets[r] if n.startswith('@')}
    if len(named) > 1:
        errors.append(f'SHORT between nets {sorted(named)}: {sorted(pins_)}')
        continue
    if labelled and named and labelled != named:
        errors.append(f'label/power {sorted(labelled)} on net {sorted(named)}')
    if named:
        n = next(iter(named))
        if pins_ != target[n]:
            # nets split in several drawn pieces are merged by labels; check via label groups below
            pass
# union by label name, then compare memberships
groups = collections.defaultdict(set)
for r, pins_ in comp_pins.items():
    named = {n for n in comp_nets[r] if not n.startswith('@')}
    key = next(iter(named)) if len(named) == 1 else None
    if key:
        groups[key] |= pins_
for net, mem in target.items():
    if groups.get(net, set()) != mem:
        errors.append(f'net {net}: drawn {sorted(groups.get(net, set()))} != target {sorted(mem)}')
# every pin must touch something; nets split into pieces must be joined by labels/power
touch = collections.Counter()
for a, b, net in segs:
    touch[a] += 1
    touch[b] += 1
for _, q, _ in psyms:
    touch[q] += 1
for l in labels:
    touch[l[2]] += 1
for q in ncs:
    touch[q] += 1
for q, d in flags:
    touch[q] += 1
pieces = collections.defaultdict(list)
for r, pins_ in comp_pins.items():
    named = {n for n in comp_nets[r] if not n.startswith('@')}
    if len(named) == 1:
        pieces[next(iter(named))].append(r)
for net, rs in pieces.items():
    if len(rs) > 1:
        for r in rs:
            if not any(n.startswith('@') for n in comp_nets[r]):
                errors.append(f'net {net} drawn in {len(rs)} pieces; piece {sorted(comp_pins[r])} has no label')
pin_count = collections.Counter(q for q, *_ , hid in pin_list if not hid)
for q, ref, num, net, hid in pin_list:
    if hid:
        continue
    if net is None:
        if q not in ncs:
            errors.append(f'{ref}.{num} should have a no-connect flag')
    elif touch[q] == 0 and pin_count[q] < 2:
        errors.append(f'{ref}.{num} ({net}) is not connected to anything')
for q in ncs:
    if touch[q] != 1 or pin_count[q] != 1:
        errors.append(f'no-connect at {q} touches something else')
missing = [(r, u) for r, p in parts.items()
           for u in sorted({lp['unit'] for lp in lib_pins(libsym(p['sym']))} - {0}) if (r, u) not in placed]
if missing:
    errors.append(f'not placed: {missing}')
if errors:
    for e in errors[:60]:
        print('ERROR', e)
    raise SystemExit(f'{len(errors)} drawing errors')

# junctions: 3+ wire ends / pins at a point
deg = collections.Counter()
for a, b, net in segs:
    deg[a] += 1
    deg[b] += 1
for q, *_ in pin_list:
    deg[q] += 1
junctions = sorted(q for q, n in deg.items() if n >= 3)

# ================================================================== emit
items = []
counter = collections.Counter()


def prop(name, val, x, y, ang=0, hide=False, justify=None, size=1.27):
    e = [Sym('effects'), [Sym('font'), [Sym('size'), size, size]]]
    if justify:
        e.append([Sym('justify')] + [Sym(j) for j in justify])
    p = [Sym('property'), name, val, [Sym('at'), r4(x), r4(y), ang]]
    if hide:
        p.append([Sym('hide'), Sym('yes')])
    return p + [[Sym('show_name'), Sym('no')], [Sym('do_not_autoplace'), Sym('no')], e]


def emit_symbol(lib_id, ref, value, x, y, rot, unit=1, mirror=None, fields=(), fp='', in_bom=True,
                power=False, key=None):
    sdef = libsym(lib_id)
    key = key or f'{ref}/{unit}'
    s = [Sym('symbol'), [Sym('lib_id'), lib_id], [Sym('at'), x, y, rot]]
    if mirror:
        s.append([Sym('mirror'), Sym(mirror)])
    s += [[Sym('unit'), unit], [Sym('body_style'), 1], [Sym('exclude_from_sim'), Sym('no')],
          [Sym('in_bom'), Sym('yes' if in_bom else 'no')], [Sym('on_board'), Sym('yes')],
          [Sym('in_pos_files'), Sym('yes' if in_bom else 'no')], [Sym('dnp'), Sym('no')],
          [Sym('uuid'), U('sym' + key)]]
    if lib_id in TWO_PIN and not power:
        if rot in (90, 270):
            s.append(prop('Reference', ref, x, y - 2.54, 90))
            s.append(prop('Value', value, x, y + 2.54, 90))
        else:
            j = ['left'] if rot == 0 else ['right']
            s.append(prop('Reference', ref, x + 2.54, y - 1.27, 0, justify=j))
            s.append(prop('Value', value, x + 2.54, y + 1.27, 0, justify=j))
    elif lib_id.startswith(('Connector_Generic:', 'Sonometro:Conn_')):   # Sonometro:Conn_01x02 = copia local (bloque 10)
        bb = [xform(p_['x'], p_['y'], rot, mirror) for p_ in lib_pins(sdef)]
        miny, maxy = min(b[1] for b in bb), max(b[1] for b in bb)
        j = ['right'] if mirror else ['left']     # a mirrored symbol flips field justification
        if ref in CONN_ABOVE:
            s.append(prop('Reference', ref, x - 1.27, y + miny - 5.08, justify=j))
            s.append(prop('Value', value, x - 1.27, y + miny - 2.54, justify=j))
        else:
            s.append(prop('Reference', ref, x - 1.27, y + miny - 2.54, justify=j))
            s.append(prop('Value', value, x - 1.27, y + maxy + 2.54, justify=j))
    else:
        for fname, fval in (('Reference', ref), ('Value', value)):
            lp = [p_ for p_ in find(sdef, 'property') if p_[1] == fname][0]
            at = find1(lp, 'at')
            ox, oy = xform(float(at[1]), float(at[2]), rot, mirror)
            ang = int((float(at[3]) - rot) % 180)
            eff = copy.deepcopy(find1(lp, 'effects'))
            if mirror:
                eff = [e for e in eff if not (isinstance(e, list) and e and e[0] == 'justify')]
            over = (VAL_POS if fname == 'Value' else REF_POS).get(ref) if unit == 1 else None
            if over:                                   # offsets are in sheet coordinates
                ox, oy, ang = over[0], over[1], int((0 - rot) % 180)
                eff = [Sym('effects'), [Sym('font'), [Sym('size'), 1.27, 1.27]], [Sym('justify'), Sym(over[2])]]
            f = [Sym('property'), fname, fval, [Sym('at'), r4(x + ox), r4(y + oy), ang]]
            if (power and fname == 'Reference') or (lib_id == 'Connector:TestPoint' and fname == 'Value'):
                f.append([Sym('hide'), Sym('yes')])
            f += [[Sym('show_name'), Sym('no')], [Sym('do_not_autoplace'), Sym('no')], eff]
            s.append(f)
    s.append(prop('Footprint', fp, x, y, hide=True))
    for nm in ('Datasheet', 'Description'):
        d = [p_ for p_ in find(sdef, 'property') if p_[1] == nm]
        s.append(prop(nm, d[0][2] if d else '', x, y, hide=True))
    for fname, fval in fields:
        s.append(prop(fname, fval, x, y, hide=True))
    for pn in sorted({p_['num'] for p_ in lib_pins(sdef) if p_['unit'] in (0, unit)}, key=lambda n: (len(n), n)):
        s.append([Sym('pin'), pn, [Sym('uuid'), U(f'pin{key}/{pn}')]])
    s.append([Sym('instances'), [Sym('project'), PROJECT,
             [Sym('path'), '/' + ROOT_UUID, [Sym('reference'), ref], [Sym('unit'), unit]]]])
    items.append(s)


for (ref, unit), (x, y, rot, mirror) in placed.items():
    p = parts[ref]
    fields = [('MPN', p['mpn'] or '')]
    if p['lcsc']:
        fields.append(('LCSC', p['lcsc']))
    if p.get('volt'):
        fields.append(('Tension', p['volt']))
    if p['desc']:
        fields.append(('Nota', p['desc']))
    fields.append(('Origen', p['src']))
    emit_symbol(p['sym'], ref, p['value'], x, y, rot, unit, mirror, fields, p['fp'],
                in_bom=p.get('mount') != 'Ninguno')

SUPPLY_ROT = {'up': 0, 'down': 180, 'left': 90, 'right': 270}
GND_ROT = {'down': 0, 'up': 180, 'left': 270, 'right': 90}
for i, (net, q, d) in enumerate(psyms):
    rot = GND_ROT[d] if net == 'GND' else SUPPLY_ROT[d]
    emit_symbol(RAIL_SYM[net], '#PWR%03d' % (i + 1), net, q[0], q[1], rot, in_bom=False, power=True,
                key=f'pwr{q}{net}')
for i, (q, d) in enumerate(flags):
    emit_symbol('power:PWR_FLAG', '#FLG%02d' % (i + 1), 'PWR_FLAG', q[0], q[1], SUPPLY_ROT[d], in_bom=False,
                power=True, key=f'flg{q}')
for a, b, net in segs:
    items.append([Sym('wire'), [Sym('pts'), [Sym('xy'), a[0], a[1]], [Sym('xy'), b[0], b[1]]],
                  [Sym('stroke'), [Sym('width'), 0], [Sym('type'), Sym('default')]],
                  [Sym('uuid'), U(f'w{a}{b}')]])
for q in junctions:
    items.append([Sym('junction'), [Sym('at'), q[0], q[1]], [Sym('diameter'), 0],
                  [Sym('color'), 0, 0, 0, 0], [Sym('uuid'), U(f'j{q}')]])
for q in ncs:
    items.append([Sym('no_connect'), [Sym('at'), q[0], q[1]], [Sym('uuid'), U(f'nc{q}')]])
ANG = {'right': 0, 'up': 90, 'left': 180, 'down': 270}
for kind, net, q, d, shape in labels:
    ang = ANG[d]
    just = 'left' if ang in (0, 90) else 'right'
    if kind == 'local':
        items.append([Sym('label'), net, [Sym('at'), q[0], q[1], ang],
                      [Sym('effects'), [Sym('font'), [Sym('size'), 1.27, 1.27]],
                       [Sym('justify'), Sym(just), Sym('bottom')]],
                      [Sym('uuid'), U(f'l{q}{net}')]])
    else:
        items.append([Sym('global_label'), net, [Sym('shape'), Sym(shape)], [Sym('at'), q[0], q[1], ang],
                      [Sym('fields_autoplaced'), Sym('yes')],
                      [Sym('effects'), [Sym('font'), [Sym('size'), 1.27, 1.27]], [Sym('justify'), Sym(just)]],
                      [Sym('uuid'), U(f'g{q}{net}')],
                      [Sym('property'), 'Intersheetrefs', '${INTERSHEET_REFS}', [Sym('at'), q[0], q[1], 0],
                       [Sym('effects'), [Sym('font'), [Sym('size'), 1.27, 1.27]], [Sym('hide'), Sym('yes')]]]])
for (x1, y1, x2, y2) in rects:
    items.append([Sym('rectangle'), [Sym('start'), x1, y1], [Sym('end'), x2, y2],
                  [Sym('stroke'), [Sym('width'), 0.3], [Sym('type'), Sym('dash')]],
                  [Sym('fill'), [Sym('type'), Sym('none')]], [Sym('uuid'), U(f'rect{x1},{y1}')]])
for (x, y, t, size, bold) in texts:
    font = [Sym('font'), [Sym('size'), size, size]]
    if bold:
        font += [[Sym('thickness'), 0.4], [Sym('bold'), Sym('yes')]]
    items.append([Sym('text'), t, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), x, y, 0],
                  [Sym('effects'), font, [Sym('justify'), Sym('left'), Sym('bottom')]],
                  [Sym('uuid'), U(f'txt{x},{y},{t}')]])

sch = [Sym('kicad_sch'), [Sym('version'), 20260306], [Sym('generator'), 'eeschema'],
       [Sym('generator_version'), '10.0'], [Sym('uuid'), ROOT_UUID], [Sym('paper'), 'A3'],
       [Sym('title_block'), [Sym('title'), 'Sonometro IEPE de 2 canales'], [Sym('date'), '2026-11-15'],
        [Sym('rev'), 'B'], [Sym('company'), 'Universidad Nacional de Colombia - Manizales'],
        [Sym('comment'), 1, 'Altium Sonometro_2CH + docs/connection_matrix.md, rehecho en KiCad'],
        [Sym('comment'), 2, 'Cables dentro de cada bloque; etiquetas globales entre bloques']],
       [Sym('lib_symbols')] + list(libsyms.values())]
sch += items
sch += [[Sym('sheet_instances'), [Sym('path'), '/', [Sym('page'), '1']]], [Sym('embedded_fonts'), Sym('no')]]
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'pcb.kicad_sch'), 'w', encoding='utf-8').write(dump(sch) + '\n')
print(f'wired schematic: {len(placed)} units, {len(segs)} wires, {len(junctions)} junctions, '
      f'{len(labels)} labels, {len(psyms)} power symbols')

"""Builds the project-local KiCad library: lib/Sonometro.kicad_sym + lib/Sonometro.pretty.

Sources:
  * PCM1808PWR pinout: TI SLES177 (pin table), same numbering as the Altium symbol (U4).
  * LMR36015FBRNXR pinout: TI SNVSB49D fig. 7-1 / pin table (page 4).
  * RNX0012A land pattern: TI SNVSB49D page 45 ("EXAMPLE BOARD LAYOUT", 4222858/A).
  * NUCLEO-L432KC socket + symbol: ST UM1956 Rev 6 (fig. 5 mechanics, table 16 pinout).
  * Oscillator YXC O322524576MEEA4SC (C27869) and BNC Kinghelm KH-BNC75-3511 (C2837588):
    footprints from EasyEDA/JLC (easyeda2kicad), stored in vendor_fp.pretty.
"""
import os
import sys
import uuid
import shutil

OUT = sys.argv[1] if len(sys.argv) > 1 else 'lib'
os.makedirs(os.path.join(OUT, 'Sonometro.pretty'), exist_ok=True)
NS = uuid.UUID('6f1d7c2a-5b8e-4c3d-9a10-50a0e7e7a001')


def U(key):
    return str(uuid.uuid5(NS, key))


def font(size=1.27):
    return f'(effects (font (size {size} {size})))'


def prop(name, val, x, y, hide=False):
    h = ' (hide yes)' if hide else ''
    return (f'\t\t(property "{name}" "{val}" (at {x} {y} 0) (show_name no) (do_not_autoplace no){h}\n'
            f'\t\t\t{font()})\n')


def pin(num, name, typ, x, y, ang, hide=False, length=2.54):
    h = ' (hide yes)' if hide else ''
    return (f'\t\t\t(pin {typ} line (at {x} {y} {ang}) (length {length}){h}\n'
            f'\t\t\t\t(name "{name}" {font()})\n'
            f'\t\t\t\t(number "{num}" {font()}))\n')


def symbol(name, ref, value, fp, ds, desc, kw, rect, pins, hide_names=False):
    x1, y1, x2, y2 = rect
    s = f'\t(symbol "{name}"\n'
    if hide_names:
        s += '\t\t(pin_names (offset 1.016) (hide yes))\n'
    s += ('\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes)\n'
          '\t\t(duplicate_pin_numbers_are_jumpers no)\n')
    s += prop('Reference', ref, x1, y1 + 1.27)
    s += prop('Value', value, x1, y2 - 1.27)
    s += prop('Footprint', fp, 0, 0, True)
    s += prop('Datasheet', ds, 0, 0, True)
    s += prop('Description', desc, 0, 0, True)
    s += prop('ki_keywords', kw, 0, 0, True)
    s += (f'\t\t(symbol "{name}_0_1"\n\t\t\t(rectangle (start {x1} {y1}) (end {x2} {y2})\n'
          f'\t\t\t\t(stroke (width 0.254) (type default)) (fill (type background))))\n')
    s += f'\t\t(symbol "{name}_1_1"\n'
    for p in pins:
        s += pin(*p)
    s += '\t\t)\n\t\t(embedded_fonts no)\n\t)\n'
    return s


lib = '(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "sonometro_gen")\n\t(generator_version "10.0")\n'

lib += symbol(
    'PCM1808PWR', 'U', 'PCM1808PWR', 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
    'https://www.ti.com/lit/ds/symlink/pcm1808.pdf',
    'TI PCM1808 24-bit 96 kHz stereo audio ADC, single-ended input, TSSOP-14 (LCSC C55513)',
    'audio adc i2s',
    (-10.16, 10.16, 10.16, -12.7),
    [
        ('13', 'VINL', 'input', -12.7, 7.62, 0),
        ('14', 'VINR', 'input', -12.7, 2.54, 0),
        ('6', 'SCKI', 'input', 12.7, 7.62, 180),
        ('7', 'LRCK', 'bidirectional', 12.7, 5.08, 180),
        ('8', 'BCK', 'bidirectional', 12.7, 2.54, 180),
        ('9', 'DOUT', 'output', 12.7, 0, 180),
        ('3', 'VCC', 'power_in', -2.54, 12.7, 270),
        ('4', 'VDD', 'power_in', 2.54, 12.7, 270),
        ('1', 'VREF', 'passive', -7.62, -15.24, 90),
        ('2', 'AGND', 'power_in', -5.08, -15.24, 90),
        ('5', 'DGND', 'power_in', -2.54, -15.24, 90),
        ('11', 'MD1', 'input', 0, -15.24, 90),
        ('12', 'FMT', 'input', 2.54, -15.24, 90),
        ('10', 'MD0', 'input', 7.62, -15.24, 90),
    ])

lib += symbol(
    'LMR36015FBRNXR', 'U', 'LMR36015FBRNXR', 'Sonometro:Texas_RNX0012A_VQFN-HR-12_2x3mm_P0.5mm',
    'https://www.ti.com/lit/ds/symlink/lmr36015.pdf',
    'TI LMR36015 60 V 1.5 A sync buck, 1 MHz FPWM, VQFN-HR-12 RNX (LCSC C1850339). Pin 3 (NC) must be tied to SW.',
    'buck regulator simple switcher',
    (-10.16, 10.16, 10.16, -10.16),
    [
        ('2', 'VIN', 'power_in', -12.7, 7.62, 0),
        ('10', 'VIN', 'power_in', -12.7, 5.08, 0),
        ('9', 'EN', 'input', -12.7, 2.54, 0),
        ('8', 'PG', 'open_collector', -12.7, -5.08, 0),
        ('5', 'VCC', 'power_out', -12.7, -7.62, 0),
        ('4', 'BOOT', 'passive', 12.7, 7.62, 180),
        ('12', 'SW', 'power_out', 12.7, 5.08, 180),
        ('3', 'NC(SW)', 'passive', 12.7, 2.54, 180),
        ('7', 'FB', 'input', 12.7, -7.62, 180),
        ('1', 'PGND', 'power_in', -2.54, -12.7, 90),
        ('11', 'PGND', 'power_in', 0, -12.7, 90),
        ('6', 'AGND', 'power_in', 2.54, -12.7, 90),
    ])

lib += symbol(
    'O322524576MEEA4SC', 'Y', 'O322524576MEEA4SC', 'Sonometro:Oscillator_YXC_SMD3225-4Pin_3.2x2.5mm',
    'https://www.lcsc.com/product-detail/C27869.html',
    'YXC YSO321SR 24.576 MHz CMOS oscillator, 3.3 V, +-25 ppm, SMD3225 (LCSC C27869). Pin 1 = OE (high = on).',
    'oscillator xo clock 24.576MHz',
    (-5.08, 5.08, 5.08, -5.08),
    [
        ('1', 'OE', 'input', -7.62, 0, 0),
        ('3', 'OUT', 'output', 7.62, 0, 180),
        ('4', 'VDD', 'power_in', 0, 7.62, 270),
        ('2', 'GND', 'power_in', 0, -7.62, 90),
    ])

# NUCLEO-L432KC: UM1956 Rev 6 table 16. Top view: CN3 left, CN4 right, pin 1 at the USB end.
CN3 = ['D1/PA9', 'D0/PA10', 'NRST', 'GND', 'D2/PA12', 'D3/PB0', 'D4/PB7', 'D5/PB6', 'D6/PB1',
       'D7/PC14', 'D8/PC15', 'D9/PA8', 'D10/PA11', 'D11/PB5', 'D12/PB4']
CN4 = ['VIN', 'GND', 'NRST', '+5V', 'A7/PA2', 'A6/PA7', 'A5/PA6', 'A4/PA5', 'A3/PA4', 'A2/PA3',
       'A1/PA1', 'A0/PA0', 'AREF', '+3V3', 'D13/PB3']
nuc_pins = [(str(i + 1), n, 'passive', -15.24, 17.78 - 2.54 * i, 0) for i, n in enumerate(CN3)]
nuc_pins += [(str(i + 16), n, 'passive', 15.24, 17.78 - 2.54 * i, 180)
             for i, n in enumerate(CN4)]
lib += symbol(
    'NUCLEO-L432KC', 'A', 'NUCLEO-L432KC', 'Sonometro:NUCLEO-32_Socket_2x15_P2.54mm_Row15.24mm',
    'https://www.st.com/resource/en/user_manual/um1956-stm32-nucleo32-boards-mb1180-stmicroelectronics.pdf',
    'Socket for NUCLEO-L432KC (Nucleo-32, Arduino Nano pinout). Pins 1-15 = CN3-1..15, 16-30 = CN4-1..15 '
    '(UM1956 Rev 6 table 16).',
    'nucleo stm32 module socket',
    (-12.7, 20.32, 12.7, -20.32), nuc_pins)

lib += symbol(
    'BNC', 'J', 'BNC', 'Sonometro:BNC_Kinghelm_KH-BNC75-3511_Horizontal',
    'https://www.lcsc.com/product-detail/C2837588.html',
    'BNC jack, right angle PCB mount (Kinghelm KH-BNC75-3511, LCSC C2837588). 1 = center, 2-4 = shell.',
    'bnc coaxial connector',
    (-2.54, 2.54, 2.54, -2.54),
    [
        ('1', 'SIG', 'passive', -5.08, 0, 0),
        ('2', 'SHIELD', 'passive', 0, -5.08, 90),
        ('3', 'SHIELD', 'passive', 0, -5.08, 90, True),
        ('4', 'SHIELD', 'passive', 0, -5.08, 90, True),
    ], hide_names=True)
# Copias locales de símbolos genéricos de KiCad 10 con el filtro de footprint que corresponde al footprint real de la
# placa (bloque 10): así ni el ERC (footprint_filter, lib_symbol_mismatch) ni la paridad del DRC
# (footprint_filters_mismatch) avisan. Mismo dibujo, pines y campos que en la biblioteca de KiCad.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import get_symbol, dump, find  # noqa: E402
COPIAS = [
    ('Connector_Generic', 'Conn_01x02', 'Connector*:*_1x??_* Sonometro:TerminalBlock*'),
    ('Jumper', 'Jumper_2_Open', 'Jumper* TestPoint*2Pads* TestPoint*Bridge* PinHeader_1x02*'),
    ('Amplifier_Operational', 'TLV9062', 'SOIC*3.9x4.9mm*P1.27mm* TSSOP*4.4x3mm*P0.65mm* VSSOP*3x3mm*P0.5mm* TSOT?23*'),
]
for _lib, _name, _filt in COPIAS:
    _s = get_symbol(_lib, _name)
    for _p in find(_s, 'property'):
        if _p[1] == 'ki_fp_filters':
            _p[2] = _filt
    lib += '\t' + dump(_s) + '\n'
lib += ')\n'
open(os.path.join(OUT, 'Sonometro.kicad_sym'), 'w', encoding='utf-8').write(lib)


# ---------------------------------------------------------------- footprints
def fp_text(kind, txt, x, y, layer, hide=False):
    h = ' (hide yes)' if hide else ''
    return (f'\t(property "{kind}" "{txt}" (at {x} {y} 0) (layer "{layer}"){h} (uuid "{U(kind + txt + layer)}")\n'
            f'\t\t(effects (font (size 1 1) (thickness 0.15))))\n')


def line(x1, y1, x2, y2, layer, w):
    return (f'\t(fp_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width {w}) (type solid)) '
            f'(layer "{layer}") (uuid "{U(f"{x1}{y1}{x2}{y2}{layer}")}"))\n')


def rect(x1, y1, x2, y2, layer, w):
    return (line(x1, y1, x2, y1, layer, w) + line(x2, y1, x2, y2, layer, w) +
            line(x2, y2, x1, y2, layer, w) + line(x1, y2, x1, y1, layer, w))


def circle(cx, cy, r, layer, w, fill='no'):
    return (f'\t(fp_circle (center {cx} {cy}) (end {cx + r} {cy}) (stroke (width {w}) (type solid)) '
            f'(fill {fill}) (layer "{layer}") (uuid "{U(f"c{cx}{cy}{layer}")}"))\n')


def smd(num, x, y, w, h, shape='roundrect', rr=0.2):
    extra = f' (roundrect_rratio {rr})' if shape == 'roundrect' else ''
    return (f'\t(pad "{num}" smd {shape} (at {x} {y}) (size {w} {h}) '
            f'(layers "F.Cu" "F.Mask" "F.Paste"){extra} (uuid "{U("pad" + num + str(x) + str(y))}"))\n')


def footprint(name, descr, tags, body, pads, crt, silk, ref_y, model=None):
    s = (f'(footprint "{name}"\n\t(version 20260206)\n\t(generator "sonometro_gen")\n\t(generator_version "10.0")\n'
         f'\t(layer "F.Cu")\n\t(descr "{descr}")\n\t(tags "{tags}")\n')
    s += fp_text('Reference', 'REF**', 0, -ref_y, 'F.SilkS')
    s += fp_text('Value', name, 0, ref_y, 'F.Fab')
    s += fp_text('Datasheet', '', 0, 0, 'F.Fab', True)
    s += fp_text('Description', descr, 0, 0, 'F.Fab', True)
    s += '\t(attr smd)\n'
    s += rect(*body, 'F.Fab', 0.1)
    s += rect(*crt, 'F.CrtYd', 0.05)
    s += silk
    s += f'\t(fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") (uuid "{U(name + "fabref")}")\n' \
         f'\t\t(effects (font (size 0.4 0.4) (thickness 0.06))))\n'
    s += ''.join(pads)
    s += '\t(embedded_fonts no)\n)\n'
    open(os.path.join(OUT, 'Sonometro.pretty', name + '.kicad_mod'), 'w', encoding='utf-8').write(s)


# RNX0012A, TI land pattern (top view, KiCad Y down). Side pads 0.6 x 0.25, R0.05.
rnx = []
for num, y in (('1', -1.125), ('2', -0.475), ('3', 0.175), ('4', 0.675)):
    rnx.append(smd(num, -0.9, y, 0.6, 0.25))
for num, y in (('11', -1.125), ('10', -0.475), ('9', 0.175), ('8', 0.675)):
    rnx.append(smd(num, 0.9, y, 0.6, 0.25))
for num, x in (('5', -0.5), ('6', 0.0), ('7', 0.5)):
    rnx.append(smd(num, x, 1.4, 0.25, 0.6))
rnx.append(smd('12', 0.0, -0.7875, 0.25, 1.825))
silk = circle(-1.45, -1.55, 0.1, 'F.SilkS', 0.2)
silk += line(-1.0, -1.6, -0.35, -1.6, 'F.SilkS', 0.12) + line(0.35, -1.6, 1.0, -1.6, 'F.SilkS', 0.12)
footprint('Texas_RNX0012A_VQFN-HR-12_2x3mm_P0.5mm',
          'TI RNX0012A VQFN-HR 12 pin 2x3 mm (LMR36015 RNX). Land pattern from SNVSB49D p.45 (4222858/A). VERIFY against the current TI drawing before ordering.',
          'Texas VQFN-HR RNX0012A LMR36015',
          (-1.0, -1.5, 1.0, 1.5), rnx, (-1.45, -1.95, 1.45, 1.95), silk, 2.6)

# NUCLEO-32 socket: two 1x15 female headers, 2.54 mm pitch, rows 15.24 mm apart (UM1956 Rev 6
# fig. 5). Origin = CN3 pin 1. Pads 1-15 = CN3-1..15 (x = 0), 16-30 = CN4-1..15 (x = 15.24).
# Board outline 18.54 x 50.29 mm drawn on F.Fab (pin-1 offset from the USB edge measured on fig. 5,
# +-0.3 mm). Courtyard only around the header rows: low SMD parts may sit under the module.
def tht(num, x, y, shape):
    return (f'\t(pad "{num}" thru_hole {shape} (at {x} {y}) (size 1.7 1.7) (drill 1.0) '
            f'(layers "*.Cu" "*.Mask") (uuid "{U("tht" + num)}"))\n')


name = 'NUCLEO-32_Socket_2x15_P2.54mm_Row15.24mm'
X0, X1, Y0, Y1 = -1.65, 16.89, -8.9, 41.39
s = (f'(footprint "{name}"\n\t(version 20260206)\n\t(generator "sonometro_gen")\n\t(generator_version "10.0")\n'
     '\t(layer "F.Cu")\n\t(descr "Socket for ST NUCLEO-32 (NUCLEO-L432KC): 2x 1x15 female header 2.54 mm, rows 15.24 mm '
     'apart. UM1956 Rev 6 fig. 5 / table 16. USB end at the top (pin 1 side).")\n\t(tags "nucleo nucleo-32 socket")\n')
s += fp_text('Reference', 'REF**', 7.62, -10.5, 'F.SilkS')
s += fp_text('Value', name, 7.62, 17.78, 'F.Fab')
s += fp_text('Datasheet', '', 0, 0, 'F.Fab', True)
s += fp_text('Description', 'NUCLEO-32 socket', 0, 0, 'F.Fab', True)
s += '\t(attr through_hole)\n'
s += rect(X0, Y0, X1, Y1, 'F.Fab', 0.1)
s += rect(5.12, Y0, 10.12, Y0 + 2.0, 'F.Fab', 0.1)                       # micro-USB
# Serigrafía (REGLAS.md §7): nada debajo del módulo enchufado ni a menos de 0.5 mm del borde. Solo el
# contorno de cada tira hembra (CN4 sin su lado derecho: no hay lugar hasta el borde), marca de pin 1 y "USB"
# fuera del módulo. El contorno de la NUCLEO y los rótulos CN3/CN4 quedan en F.Fab.
s += line(-1.4, -1.4, 1.4, -1.4, 'F.SilkS', 0.15) + line(1.4, -1.4, 1.4, 37.0, 'F.SilkS', 0.15)
s += line(1.4, 37.0, -1.4, 37.0, 'F.SilkS', 0.15) + line(-1.4, 37.0, -1.4, -1.4, 'F.SilkS', 0.15)
s += line(13.84, -1.4, 16.4, -1.4, 'F.SilkS', 0.15) + line(13.84, -1.4, 13.84, 37.0, 'F.SilkS', 0.15)
s += line(13.84, 37.0, 16.4, 37.0, 'F.SilkS', 0.15)
s += (f'\t(fp_poly (pts (xy -2.25 -0.35) (xy -1.65 0) (xy -2.25 0.35)) (stroke (width 0.15) (type solid)) '
      f'(fill yes) (layer "F.SilkS") (uuid "{U("pin1mark")}"))\n')                 # marca de pin 1 (CN3-1)
s += (f'\t(fp_text user "USB" (at -3.05 -4.6 90) (layer "F.SilkS") (uuid "{U("txtUSB")}")\n'
      f'\t\t(effects (font (size 1 1) (thickness 0.15))))\n')
s += (f'\t(fp_poly (pts (xy -3.05 -7.1) (xy -3.45 -6.4) (xy -2.65 -6.4)) (stroke (width 0.15) (type solid)) '
      f'(fill yes) (layer "F.SilkS") (uuid "{U("usbarrow")}"))\n')               # flecha hacia el USB
s += rect(-1.55, -1.55, 1.55, 37.11, 'F.CrtYd', 0.05)
s += rect(13.69, -1.55, 16.79, 37.11, 'F.CrtYd', 0.05)
for t_, x_, y_ in (('USB', 7.62, -5.9), ('CN3', 0, -3.0), ('CN4', 15.24, -3.0), ('NUCLEO-L432KC', 7.62, 39.6)):
    s += (f'\t(fp_text user "{t_}" (at {x_} {y_} 0) (layer "F.Fab") (uuid "{U("txt" + t_)}")\n'
          f'\t\t(effects (font (size 1 1) (thickness 0.15))))\n')
for i in range(15):
    s += tht(str(i + 1), 0, round(2.54 * i, 2), 'rect' if i == 0 else 'circle')
    s += tht(str(i + 16), 15.24, round(2.54 * i, 2), 'rect' if i == 0 else 'circle')
s += '\t(embedded_fonts no)\n)\n'
open(os.path.join(OUT, 'Sonometro.pretty', name + '.kicad_mod'), 'w', encoding='utf-8').write(s)

# Vendor footprints (EasyEDA/JLC via easyeda2kicad, converted to KiCad 10 format): copied as-is.
VEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor_fp.pretty')
for f in os.listdir(VEND):
    if f.endswith('.kicad_mod'):
        shutil.copy(os.path.join(VEND, f), os.path.join(OUT, 'Sonometro.pretty', f))
print('library written to', OUT)

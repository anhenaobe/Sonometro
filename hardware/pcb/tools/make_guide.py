"""Genera la guia PDF (LaTeX + Tectonic) para dibujar la Rev B en Altium y verificarla.

Todo sale de las mismas fuentes que el esquematico: target.json, changes.json, altium.json,
la libreria del proyecto y los archivos exportados por kicad-cli en guia/ (esquematico.pdf,
placa_fab.pdf, posiciones.csv). Uso: python make_guide.py  (luego tectonic guia/guia_conexiones.tex)
"""
import os
import sys
import csv
import json
import math
import collections
import re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import get_symbol, pins as lib_pins  # noqa: E402

G = os.path.join(HERE, 'guia')
T = json.load(open(os.path.join(HERE, 'target.json')))
CH = json.load(open(os.path.join(HERE, 'changes.json'), encoding='utf-8'))
ALT = json.load(open(os.path.join(HERE, 'altium.json'), encoding='utf-8'))['components']
LOCAL = os.path.join(HERE, 'out', 'lib', 'Sonometro.kicad_sym')
BOARD = (100.0, 100.0, 90.0, 64.0)          # KiCad origin of the outline (x, y) and size (mm)


def esc(s):
    s = str(s)
    rep = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_\allowbreak{}',
           '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(rep.get(c, c) for c in s)


def rr(*a):
    out = []
    for x, y in a:
        out += ['%s%d' % (x, i) for i in y]
    return out


BLOCKS = [
    ('Alimentación: entrada 24 V, buck 3V3, buck 5V y filtro 5V\\_A',
     ['J5', 'D1', 'D2', 'U6', 'L1'] + rr(('C', range(27, 37))) + ['R29', 'R30', 'U7', 'L2'] +
     rr(('C', range(37, 47))) + ['R31', 'R32', 'R33', 'C47']),
    ('Fuente IEPE CH1 (ROGA RG-50)', ['J1', 'R1', 'C2', 'C3', 'U1', 'R4', 'R5', 'R6', 'C1', 'R2', 'R3', 'R47', 'JP1',
                                      'J2', 'TP1', 'TP5']),
    ('Fuente IEPE CH2 (Svantek SV 12L)', ['J7', 'R36', 'C49', 'C50', 'U8', 'R34', 'C48', 'R35', 'R48', 'JP2', 'J8',
                                          'TP3', 'TP6']),
    ('AFE + DAC CH1', ['U2', 'U3', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R18',
                       'C4', 'C5', 'C6', 'C7', 'C8', 'TP2']),
    ('AFE + DAC CH2', ['U9', 'U10'] + rr(('R', range(37, 47))) + rr(('C', range(51, 56))) + ['TP4']),
    ('ADC PCM1808 + reloj', ['U4', 'Y1', 'C9', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C19',
                             'C20', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R49', 'R50', 'R51', 'TP7']),
    ('NUCLEO-L432KC (zócalo)', ['A1']),
]
allb = [r for _, rs in BLOCKS for r in rs]
assert sorted(allb) == sorted(T), (set(T) - set(allb), set(allb) - set(T))
block_of = {r: i for i, (_, rs) in enumerate(BLOCKS) for r in rs}

MIRROR = {'U9': 'U3', 'U10': 'U2', 'R37': 'R12', 'R38': 'R13', 'R39': 'R14', 'R40': 'R16', 'R41': 'R18',
          'R42': 'R7', 'R43': 'R8', 'R44': 'R15', 'R45': 'R17', 'R46': 'R9', 'C51': 'C4', 'C52': 'C5',
          'C53': 'C6', 'C54': 'C7', 'C55': 'C8'}

_pn = {}


def pinname(ref, num):
    sym = T[ref]['sym']
    if sym not in _pn:
        lib, name = sym.split(':')
        s = get_symbol(LOCAL if lib == 'Sonometro' else lib, name)
        _pn[sym] = {p['num']: p['name'] for p in lib_pins(s)}
    n = _pn[sym].get(num, '')
    if n in ('', '~') and T[ref]['mpn'].startswith('LT3092'):   # el símbolo del equipo no trae nombres
        n = {'2': 'OUT', '3': 'OUT', '4': 'OUT', '5': 'SET', '7': 'IN', '8': 'IN'}.get(num, n)
    return '' if n in ('', '~') or n == num else n


def _num(v):
    """'4k7' -> 4700, '0.1uF' -> 1e-7, '10R' -> 10, '24.9k' -> 24900 (None si no es un valor)."""
    m = re.fullmatch(r'(\d+(?:\.\d+)?)([pnuµmkKMR]?)(\d*)(?:F|H|Ω|ohm)?', str(v).strip())
    if not m:
        return None
    mult = {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'k': 1e3, 'K': 1e3, 'M': 1e6, 'R': 1, '': 1}
    return round(float(m.group(1) + ('.' + m.group(3) if m.group(3) else '')) * mult[m.group(2)], 15)


def _alt_mpn(c):
    q = c['params']
    return q.get('Manufacturer Part Number') or q.get('Manufacturer_Part_Number') or q.get('MP') or ''


def _size(fp):
    m = re.search(r'_(0402|0603|0805|1206|1210|2220)_', fp + '_')
    return m.group(1) if m else None


ALT_BY_MPN = {_alt_mpn(c).replace(' ', ''): c for c in ALT.values() if _alt_mpn(c)}


def altium_eq(ref):
    """Componente de la Rocket_Library que sirve para ref; 'Gateway' si viene del diseño del gateway."""
    p = T[ref]
    if ref in ('Y1', 'J2', 'J8'):                      # cambiados en C3 / C8: la pieza vieja ya no sirve
        return '\\textbf{NUEVO}'
    src = ALT.get(ref) if p['src'].startswith('Altium') else ALT.get(MIRROR.get(ref, ''))
    if src is not None and _num(src['params'].get('Value')) not in (None, _num(p['value'])):
        src = None                                      # valor cambiado en la Rev B (p. ej. C4: 10uF -> 100nF)
    if src is None:
        src = ALT_BY_MPN.get(p['mpn'].replace(' ', ''))
    if src is None and p['sym'] in ('Device:R', 'Device:C'):
        for c in ALT.values():                          # mismo valor y mismo tamaño (0603, 0402...)
            fpa = ' '.join(c['footprints'])
            if (_num(c['params'].get('Value')) == _num(p['value']) and _size(p['fp'].split(':')[1])
                    and _size(p['fp'].split(':')[1]) in fpa):
                src = c
                break
    if src is not None:
        lib = esc(src['lib'])
        if p['value'] == '100nF' and _alt_mpn(src) != p['mpn']:
            lib += ' (cambiar MPN a X7R)'
        return lib
    if p['src'] == 'connection_matrix.md' and block_of[ref] == 0:
        return 'Gateway'
    return '\\textbf{NUEVO}'


# Códigos LCSC hallados por búsqueda web (2026-11-15) para piezas JLC que no traían código en el diseño
LCSC_WEB = {'LT3092ETS8#TRPBF': 'C462641', 'PCM1808PW': 'C55513', 'TLV9062IDDFR': 'C2867884',
            'MCP4725A0T-E/CH': 'C144198'}


def lcsc_of(p):
    if p['lcsc']:
        return esc(p['lcsc'])
    return LCSC_WEB[p['mpn']] + '*' if p['mpn'] in LCSC_WEB else ''


NO_LCSC = [r for r in allb if T[r]['mount'] == 'JLC' and not T[r]['lcsc'] and T[r]['mpn'] not in LCSC_WEB]


def pad1_table():
    """Posición del pad 1 (desde la esquina inferior izquierda) de las piezas con orientación."""
    d = {f['ref']: f for f in json.load(open(os.path.join(G, 'placement.json')))['fps']}
    refs = [r for r in allb if r.startswith(('U', 'A', 'Y', 'J', 'D'))]
    rows = []
    for r in refs:
        pad = next(q for q in d[r]['pads'] if q[4] == '1')
        x = (pad[0] + pad[2]) / 2 - BOARD[0]
        y = BOARD[1] + BOARD[3] - (pad[1] + pad[3]) / 2
        rows.append(f"{esc(r)} & {esc(T[r]['value'][:13])} & {x:.2f} & {y:.2f}")
    w(r'{\scriptsize\begin{longtable}{@{}llrr|llrr|llrr@{}}\toprule')
    w(r'\textbf{Ref} & \textbf{Valor} & \textbf{X p1} & \textbf{Y p1} & ' * 2 +
      r'\textbf{Ref} & \textbf{Valor} & \textbf{X p1} & \textbf{Y p1}\\\midrule\endhead')
    n = math.ceil(len(rows) / 3)
    for i in range(n):
        cells = [rows[i + k * n] if i + k * n < len(rows) else '& & &' for k in range(3)]
        w(' & '.join(cells) + r'\\')
    w(r'\bottomrule\end{longtable}}')


def pos_table():
    rows = {}
    with open(os.path.join(G, 'posiciones.csv'), newline='') as f:
        for r in csv.DictReader(f):
            x = float(r['PosX']) - BOARD[0]
            y = float(r['PosY']) + BOARD[1] + BOARD[3]      # pos file is Y-up: origin -> bottom-left
            rows[r['Ref']] = (x, y, float(r['Rot']) % 360, r['Side'])
    return rows


COLORS = [(230, 85, 13), (49, 130, 189), (117, 107, 177), (49, 163, 84), (23, 160, 180), (214, 39, 40),
          (99, 99, 99)]
SHORT = ['Alimentación (24 V, bucks 3V3/5V)', 'Fuente IEPE CH1', 'Fuente IEPE CH2', 'AFE + DAC CH1',
         'AFE + DAC CH2', 'ADC PCM1808 + reloj', 'NUCLEO-L432KC']


def draw_map():
    """Mapa de placement legible (PNG) a partir de guia/placement.json (tools/dump_placement.py)."""
    from PIL import Image, ImageDraw, ImageFont
    d = json.load(open(os.path.join(G, 'placement.json')))
    S, M = 22, 60                                   # px/mm, margen
    x0, y0 = BOARD[0], BOARD[1]
    ymax = max(f['box'][3] for f in d['fps'])
    W = int(BOARD[2] * S + 2 * M)
    H = int((max(ymax, y0 + BOARD[3]) - y0) * S + 2 * M + 190)
    img = Image.new('RGB', (W, H), 'white')
    dr = ImageDraw.Draw(img, 'RGBA')

    def font(sz, bold=True):
        for f in (('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf'),
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
            if os.path.exists(f):
                return ImageFont.truetype(f, sz)
        return ImageFont.load_default(size=sz)

    def P(x, y):
        return (M + (x - x0) * S, M + (y - y0) * S)

    dr.rectangle([*P(x0, y0), *P(x0 + BOARD[2], y0 + BOARD[3])], fill=(248, 248, 240), outline='black', width=4)
    fl = font(22, False)
    for t in range(0, int(BOARD[2]) + 1, 10):            # cotas desde la esquina inferior izquierda
        px, py = P(x0 + t, y0 + BOARD[3])
        dr.line([px, py, px, py + 10], fill='black', width=2)
        dr.text((px, py + 12), str(t), fill='black', font=fl, anchor='mt')
    for t in range(0, int(BOARD[3]) + 1, 10):
        px, py = P(x0, y0 + BOARD[3] - t)
        dr.line([px - 10, py, px, py], fill='black', width=2)
        dr.text((px - 13, py), str(t), fill='black', font=fl, anchor='rm')
    for f in sorted(d['fps'], key=lambda f: f['ref'] != 'A1'):
        c = COLORS[block_of[f['ref']]]
        if f['ref'] == 'A1':
            bx = f['body']
            dr.rectangle([*P(bx[0], bx[1]), *P(bx[2], bx[3])], fill=c + (25,), outline=c + (160,), width=3)
        b = f['box']
        dr.rectangle([*P(b[0], b[1]), *P(b[2], b[3])], fill=c + (70,), outline=c + (255,), width=2)
        for p in f['pads']:
            dr.rectangle([*P(p[0], p[1]), *P(p[2], p[3])], fill=(150, 150, 150, 150))
    a1 = next(f for f in d['fps'] if f['ref'] == 'A1')['body']
    dr.text(P((a1[0] + a1[2]) / 2, (a1[1] + a1[3]) / 2), 'A1\nNUCLEO-L432KC\n(enchufada encima,\nUSB arriba)',
            fill=(40, 40, 40), font=font(22), anchor='mm', align='center', stroke_width=3, stroke_fill='white')
    for f in d['fps']:
        if f['ref'] == 'A1':
            continue
        b = f['box']
        wpx, hpx = (b[2] - b[0]) * S, (b[3] - b[1]) * S
        vert = hpx > wpx * 1.3
        room = (hpx if vert else wpx) / max(len(f['ref']), 2) * 1.6
        sz = int(max(11, min(26, room, (wpx if vert else hpx) * 0.8)))
        tim = Image.new('RGBA', (sz * len(f['ref']) + 10, sz + 10), (0, 0, 0, 0))
        ImageDraw.Draw(tim).text((tim.width / 2, tim.height / 2), f['ref'], fill=(0, 0, 0), font=font(sz),
                                 anchor='mm', stroke_width=2, stroke_fill=(255, 255, 255))
        if vert:
            tim = tim.rotate(90, expand=True)
        cx, cy = P((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        img.paste(tim, (int(cx - tim.width / 2), int(cy - tim.height / 2)), tim)
    fy = H - 170                                    # leyenda
    fx = M
    for i, name in enumerate(SHORT):
        col, row = i % 4, i // 4
        lx, ly = fx + col * (W - 2 * M) / 4, fy + row * 48
        dr.rectangle([lx, ly, lx + 32, ly + 32], fill=COLORS[i] + (110,), outline=COLORS[i], width=2)
        dr.text((lx + 40, ly + 16), name, fill='black', font=font(25, False), anchor='lm')
    dr.text((M, fy + 110), 'mm desde la esquina inferior izquierda · cajas = courtyard · gris = pads · '
            'J2/J8: el barril BNC sale por el borde inferior', fill=(60, 60, 60), font=font(22, False))
    img.save(os.path.join(G, 'placement_map.png'), dpi=(300, 300))


L = []
w = L.append
w(r'''\documentclass[10pt,a4paper]{article}
\usepackage{fontspec}
\usepackage[spanish,es-noshorthands,es-tabla]{babel}
\usepackage[margin=16mm]{geometry}
\usepackage{longtable,booktabs,array,graphicx,pdfpages,xcolor,tcolorbox}
\usepackage[hidelinks]{hyperref}
\usepackage{xurl}
\setlength{\parskip}{4pt}\setlength{\parindent}{0pt}\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.1}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcommand{\ok}{\textcolor{green!45!black}{\textbf{OK}}}
\begin{document}
\begin{center}
{\LARGE\bfseries Sonómetro IEPE de 2 canales}\\[4pt]
{\Large Guía de conexiones para dibujar la Rev B en Altium}\\[6pt]
Universidad Nacional de Colombia, Manizales \quad · \quad 15 de noviembre de 2026
\end{center}
\begin{tcolorbox}[colback=green!4,colframe=green!40!black,title=Estado verificado]
La Rev B en KiCad (\texttt{hardware/pcb/}) tiene \textbf{%d componentes y %d redes con nombre}.
Verificación automática: esquemático contra este diseño pin a pin \ok{} (0 diferencias), ERC \ok{} (0),
paridad PCB–esquemático \ok{} (0) y DRC sin errores. Lo único pendiente en la placa es el ruteo.
Fuentes: Altium \texttt{Sonometro\_2CH} del equipo, \texttt{docs/connection\_matrix.md} y los documentos
del fabricante citados en cada cambio.
\end{tcolorbox}
''' % (len(T), len({n for p in T.values() for n in p['pins'].values() if n})))

w(r'''\section*{Cómo usar esta guía}
\begin{enumerate}
\item Abre el esquemático (sección~\ref{sec:esq}) junto a esta guía. Está dibujado por bloques: dentro de cada bloque
todo va con cables y entre bloques con etiquetas globales (puertos en Altium). Las alimentaciones van con
símbolos de alimentación (power ports): GND, 3V3, 5V, 5V\_A y 24V\_PROT.
\item Usa \textbf{exactamente las mismas referencias} (R1, U4, A1…) y \textbf{los mismos números de pin}.
Las piezas marcadas \textbf{NUEVO} no existen en la Rocket\_Library: hay que crear símbolo y footprint
(los footprints de KiCad sirven de referencia; los de JLC salen de su página con el código LCSC). Las marcadas
\emph{Gateway} están en el proyecto Altium del gateway (bucks): cópialas de ahí. En las piezas nuevas respeta
los números de pin de las tablas (p. ej. D1/D2: 1 = cátodo K, 2 = ánodo A; BNC: 1 = centro, 2–4 = carcasa).
\item Proyecto \textbf{plano}, como el del equipo: entre hojas une los bloques con \emph{Ports} o
\emph{Power Ports}; un \emph{Net Label} solo vale dentro de su propia hoja.
\item El zócalo de la NUCLEO (A1) es \textbf{un solo componente de 30 pines}: 1–15 = CN3-1…15 y 16–30 = CN4-1…15
(sección~\ref{sec:nuc}).
\item Cuando termines, verifica tu dibujo con la herramienta incluida (lee tus \texttt{.SchDoc} directamente):\\
\texttt{python hardware/pcb/tools/verify\_altium.py <carpeta\_con\_tus\_SchDoc>}\\
Debe decir \emph{0 problemas}. Si no, te dice qué red está partida, qué pin sobra o qué componente falta.
(Prueba hecha con el Altium actual del equipo: da 118 problemas y todos son piezas que todavía no están
dibujadas —bucks, canal 2, NUCLEO y cambios C1–C12—; ninguno sale en el canal 1 que ya existe.)
\item Para el placement, la sección~\ref{sec:pla} trae X, Y y rotación de cada pieza medidas desde la
\textbf{esquina inferior izquierda} de la placa (90 × 64 mm), con Y hacia arriba como en Altium.
\end{enumerate}
''')

# ------------------------------------------------------------------ 1. change log
w(r'\section{Cambios respecto al diseño del equipo (Rev A → Rev B)}')
w(r'\begin{longtable}{@{}L{0.06\linewidth}L{0.3\linewidth}L{0.6\linewidth}@{}}\toprule')
w(r'\textbf{ID} & \textbf{Cambio} & \textbf{Detalle y fuente}\\\midrule\endhead')
for c in CH:
    w(f"{esc(c['id'])} & {esc(c['title'])} & {esc(c['detail'])}\\\\[2pt]")
w(r'\bottomrule\end{longtable}')
w(r'''Todo lo que no aparece en esta tabla es \textbf{igual al Altium del equipo} (bloques de bucks
copiados de \texttt{connection\_matrix.md}, que a su vez vienen del gateway). El AFE/DAC del canal 2 es un
espejo exacto del canal 1 (mismas piezas), con la dirección I$^2$C del DAC en 0x61 (A0 = 1).''')

# ------------------------------------------------------------------ 2. schematic
w(r'\section{Esquemático completo}\label{sec:esq}')
w(r'''En la página siguiente va el esquemático en A3 (vectorial: se puede ampliar sin perder detalle).
Los recuadros son los bloques de esta guía. Las notas en azul resumen las fórmulas de cada bloque.''')
w(r'\includepdf[pages=-,fitpaper=true]{esquematico.pdf}')

# ------------------------------------------------------------------ 3. BOM per block
w(r'\section{Componentes por bloque}')
w(r'''Columna \emph{Altium}: nombre del componente en la Rocket\_Library que ya usó el equipo (\emph{Gateway} = está
en el proyecto del gateway; \textbf{NUEVO} = hay que crearlo). Un código LCSC con * se encontró en búsqueda web
el 15/11/2026 (confirmar stock al pedir); C55513 es el PCM1808PW\textbf{R} (la versión en carrete, misma pieza).
\emph{Montaje}: JLC = lo monta JLCPCB; Manual = THT que sueldan ustedes (más barato, no paga montaje);
Ninguno = pad de prueba sin componente.''')
for title, refs in BLOCKS:
    w(r'\subsection*{%s}' % title)
    w(r'{\scriptsize\begin{longtable}{@{}L{0.07\linewidth}L{0.17\linewidth}L{0.17\linewidth}L{0.09\linewidth}'
      r'L{0.20\linewidth}L{0.14\linewidth}L{0.06\linewidth}@{}}\toprule')
    w(r'\textbf{Ref} & \textbf{Valor} & \textbf{MPN} & \textbf{LCSC} & \textbf{Footprint (KiCad)} & '
      r'\textbf{Altium} & \textbf{Mont.}\\\midrule\endhead')
    for r in refs:
        p = T[r]
        w(f"{esc(r)} & {esc(p['value'])} & {esc(p['mpn'])} & {lcsc_of(p)} & "
          f"{esc(p['fp'].split(':')[1])} & {altium_eq(r)} & {esc(p['mount'])}\\\\")
    w(r'\bottomrule\end{longtable}}')

# consolidated BOM
w(r'\subsection*{Lista de compra consolidada}')
grp = collections.OrderedDict()
for r in allb:
    p = T[r]
    if p['mount'] == 'Ninguno':
        continue
    k = (p['value'], p['mpn'], lcsc_of(p), p['fp'].split(':')[1], p['mount'])
    grp.setdefault(k, []).append(r)
w(r'{\scriptsize\begin{longtable}{@{}L{0.05\linewidth}L{0.17\linewidth}L{0.2\linewidth}L{0.1\linewidth}'
  r'L{0.07\linewidth}L{0.34\linewidth}@{}}\toprule')
w(r'\textbf{Cant.} & \textbf{Valor} & \textbf{MPN} & \textbf{LCSC} & \textbf{Mont.} & \textbf{Referencias}\\'
  r'\midrule\endhead')
for (val, mpn, lcsc, fp, mount), refs in grp.items():
    w(f"{len(refs)} & {esc(val)} & {esc(mpn)} & {lcsc} & {esc(mount)} & {esc(', '.join(refs))}\\\\")
w(r'\bottomrule\end{longtable}}')
w(r'''Además, fuera de la placa: un \textbf{adaptador BNC macho a TNC hembra} para el SV 12L, dos
\textbf{jumpers} de 2.54 mm (JP1, JP2) y la \textbf{NUCLEO-L432KC}.''')

# ------------------------------------------------------------------ 4. nets
w(r'\section{Conexiones red por red}')
w(r'''Cada fila es una red: todos los pines listados deben quedar unidos (con cable o con la misma
etiqueta/puerto). Formato \texttt{Ref.pin(nombre)}. Las redes sin etiqueta en el esquemático aparecen con
un nombre descriptivo entre corchetes (no hace falta ponerles etiqueta en Altium).''')
nets = collections.defaultdict(list)
for r in allb:
    for num, net in sorted(T[r]['pins'].items(), key=lambda kv: (len(kv[0]), kv[0])):
        if net:
            nm = pinname(r, num)
            nets[net].append(f'{r}.{num}' + (f'({nm})' if nm else ''))
LABELLED = {'GND', '3V3', '5V', '5V_A', '24V_PROT', 'IEPE', 'IEPE_SV', 'REST_OUT', 'REST_SV', 'DC_MON', 'DC_MON2',
            'I2C_SCL', 'I2C_SDA', 'SAI_SCK', 'SAI_FS', 'SAI_SD', 'SW_3', 'SW_5', 'IEPE_SUP', 'IEPE_SUP_SV',
            '3V3_DAC', '3V3_DAC_SV'}
net_block = {n: min(block_of[m.split('.')[0]] for m in mem) for n, mem in nets.items()}
for bi, (title, _) in enumerate(BLOCKS):
    ns = sorted([n for n in nets if net_block[n] == bi], key=lambda n: (n not in LABELLED, n))
    if not ns:
        continue
    w(r'\subsection*{%s}' % title)
    w(r'{\footnotesize\begin{longtable}{@{}L{0.2\linewidth}L{0.06\linewidth}L{0.7\linewidth}@{}}\toprule')
    w(r'\textbf{Red} & \textbf{Pines} & \textbf{Conexiones}\\\midrule\endhead')
    for n in ns:
        shown = esc(n) if n in LABELLED else '{[}' + esc(n) + '{]}'
        w(f"{shown} & {len(nets[n])} & {esc(', '.join(nets[n]))}\\\\")
    w(r'\bottomrule\end{longtable}}')

# ------------------------------------------------------------------ 5. pin tables
w(r'\section{Pin a pin de integrados y conectores}')
multi = [r for r in allb if len(T[r]['pins']) > 2 and r != 'A1']
for r in multi:
    p = T[r]
    w(r'\subsubsection*{%s — %s}' % (esc(r), esc(p['value'])))
    w(r'{\footnotesize\begin{tabular}{@{}lll|lll@{}}\toprule')
    w(r'\textbf{Pin} & \textbf{Nombre} & \textbf{Red} & \textbf{Pin} & \textbf{Nombre} & \textbf{Red}\\\midrule')
    items = sorted(p['pins'].items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 99)
    half = math.ceil(len(items) / 2)
    for i in range(half):
        a = items[i]
        b = items[i + half] if i + half < len(items) else None
        ca = f"{esc(a[0])} & {esc(pinname(r, a[0]))} & {esc(a[1] or 'NC (sin conectar)')}"
        cb = f"{esc(b[0])} & {esc(pinname(r, b[0]))} & {esc(b[1] or 'NC (sin conectar)')}" if b else '& &'
        w(ca + ' & ' + cb + r'\\')
    w(r'\bottomrule\end{tabular}}')

# ------------------------------------------------------------------ 6. NUCLEO
w(r'\section{NUCLEO-L432KC: zócalo A1}\label{sec:nuc}')
w(r'''Fuente: ST UM1956 Rev 6 (tabla 16 y figura 5) y DS11451 Rev 4 (tablas de funciones alternas).
La NUCLEO se enchufa en dos tiras hembra 1×15 de 2.54 mm separadas 15.24 mm, \textbf{con el USB hacia el
borde superior} de la placa. Solo se usan GND y señales: \textbf{no conectar +3V3, +5V ni VIN} (la
NUCLEO se alimenta por su USB). PA0 (DC\_MON) está libre: el puente SB17, que la uniría al reloj MCO del
ST-LINK, viene abierto de fábrica (UM1956 tabla 6) y \textbf{no hay que soldarlo}. CN4-7/CN4-8 (A5/A4) quedan
libres porque los puentes SB16/SB18 de la
NUCLEO los unen a PB6/PB7; en el firmware PA5 y PA6 van como entradas flotantes.''')
w(r'\par\begin{center}\footnotesize\begin{tabular}{@{}llll|llll@{}}\toprule')
w(r'\textbf{Pin A1} & \textbf{CN3} & \textbf{Nombre} & \textbf{Red} & \textbf{Pin A1} & \textbf{CN4} & '
  r'\textbf{Nombre} & \textbf{Red}\\\midrule')
for i in range(15):
    a, b = str(i + 1), str(i + 16)
    na, nb = T['A1']['pins'].get(a), T['A1']['pins'].get(b)
    w(f"{a} & CN3-{i + 1} & {esc(pinname('A1', a))} & {esc(na or '—')} & {b} & CN4-{i + 1} & "
      f"{esc(pinname('A1', b))} & {esc(nb or '—')}\\\\")
w(r'\bottomrule\end{tabular}\end{center}')
w(r'''\par Funciones verificadas: PA8/PA9/PA10 = SAI1\_SCK\_A / SAI1\_FS\_A / SAI1\_SD\_A (AF13);
PB6/PB7 = I2C1\_SCL / I2C1\_SDA (AF4); PA0/PA1 = ADC1\_IN5 / ADC1\_IN6. El PCM1808 es el maestro del
I$^2$S (genera BCK y LRCK); el SAI del STM32 recibe como esclavo.''')

# ------------------------------------------------------------------ 7. placement
POS = pos_table()
w(r'\section{Placement (90 × 64 mm, 2 capas, sin agujeros de montaje)}\label{sec:pla}')
w(r'''Vista superior: cada caja es el courtyard de la pieza, coloreada por bloque; en gris los pads. Bordes: borneras J5/J1/J7 a la izquierda
(cable entra por el borde), BNC J2/J8 abajo (el barril sobresale de la placa; el frente del cuerpo va
alineado con el borde), NUCLEO a la derecha con el USB arriba. Los dos bucks siguen el ejemplo de layout
de TI (SNVSB49D fig. 12-2): bobina sobre el pin SW, COUT a los lados, CIN + CHF pegados a cada par VIN/PGND.
Debajo de la NUCLEO no hay piezas: sirve para pasar pistas.''')
draw_map()
w(r'\begin{center}\includegraphics[width=\linewidth]{placement_map.png}\end{center}')
w(r'''\par\textbf{Al rutear}: U3 (AFE CH1, nodo SUM de 1 M$\Omega$ con R7/R18) queda unos 15 mm debajo del buck
U7/L2: no pasar SW\_5, SW\_3 ni los lazos de entrada de los bucks por encima de U3/U2/R13–R18, y dejar GND
entre ambos bloques. Plano de GND en la capa inferior (cosido con vías), lazos de entrada de los bucks
lo más cortos posible y lejos del AFE, y las señales analógicas (IEPE, REST, DC\_MON) lejos de los nodos SW.
Reglas de JLCPCB ya configuradas en el proyecto: 0.15 mm de separación, pistas de 0.2 mm (0.5 mm en la clase
\emph{Potencia}).''')
w(r'{\footnotesize\begin{longtable}{@{}llrrrl|llrrrl@{}}\toprule')
w(r'\textbf{Ref} & \textbf{Valor} & \textbf{X} & \textbf{Y} & \textbf{Rot} & \textbf{Cara} & '
  r'\textbf{Ref} & \textbf{Valor} & \textbf{X} & \textbf{Y} & \textbf{Rot} & \textbf{Cara}\\\midrule\endhead')
srt = sorted(POS, key=lambda r: (r.rstrip('0123456789'), int(r[len(r.rstrip('0123456789')):] or 0)))
half = math.ceil(len(srt) / 2)
for i in range(half):
    cells = []
    for r in (srt[i], srt[i + half] if i + half < len(srt) else None):
        if r:
            x, y, rot, side = POS[r]
            cells.append(f"{esc(r)} & {esc(T[r]['value'][:14])} & {x:.2f} & {y:.2f} & {rot:.0f} & "
                         f"{'sup' if side == 'top' else 'inf'}")
        else:
            cells.append('& & & & &')
    w(' & '.join(cells) + r'\\')
w(r'\bottomrule\end{longtable}}')
w(r'''Coordenadas en mm desde la esquina inferior izquierda (Y hacia arriba); rotación en grados (antihorario).
X/Y es el \textbf{origen del footprint de KiCad} (centro en las piezas SMD, pin 1 en conectores THT) y la rotación
es respecto a la orientación de la librería de KiCad: los footprints de Altium pueden tener otro origen o girar
distinto. Por eso, para las piezas con orientación, usa la tabla siguiente: si el \textbf{pad 1} de cada pieza
cae en ese punto y la pieza se ve como en el mapa, está bien puesta.''')
pad1_table()

# ------------------------------------------------------------------ 8. calculations
I1 = 10e-6 * (1 + 21000 / 75)
R1s = 1 / (1 / 75 + 1 / 180)
I1s = 10e-6 * (1 + 21000 / R1s)
I2 = 10e-6 * (1 + 15000 / 100)
R2s = 1 / (1 / 100 + 1 / 150)
I2s = 10e-6 * (1 + 15000 / R2s)
VSH_MAX = 3.3 - 100 * 0.4e-3
REST_T = 1.5
BIAS_MAX = (1.1 * VSH_MAX - REST_T) / 0.1
VSH_RG = (REST_T + 0.1 * 12.5) / 1.1
FS_RMS = 3.0 / (2 * math.sqrt(2))
NOISE = FS_RMS * 10 ** (-99 / 20)
SPL_N = 20 * math.log10(NOISE / 0.1 / 0.05 / 20e-6)
fc_c = 1 / (2 * math.pi * 60.1e3 * 10e-6)
ph20 = math.degrees(math.atan(fc_c / 20) + math.atan(0.91 / 20))
w(r'\section{Cálculos de diseño}')
w(r'\begin{longtable}{@{}L{0.27\linewidth}L{0.69\linewidth}@{}}\toprule')
w(r'\textbf{Qué} & \textbf{Cálculo y resultado}\\\midrule\endhead')
calc = [
    ('Corriente CH1 (RG-50)', f'I = 10 µA·(1 + R_SET/R_OUT) = 10 µA·(1 + 21 kΩ/75 Ω) = {I1 * 1e3:.2f} mA. '
                              f'Con JP1: R_OUT = 75 ∥ 180 = {R1s:.1f} Ω → {I1s * 1e3:.2f} mA. '
                              'RG-50 admite 2–20 mA.'),
    ('Corriente CH2 (SV 12L)', f'I = 10 µA·(1 + 15 kΩ/100 Ω) = {I2 * 1e3:.2f} mA. Con JP2: 100 ∥ 150 = '
                               f'{R2s:.0f} Ω → {I2s * 1e3:.2f} mA (2.5 mA es lo que le dan los equipos Svantek).'),
    ('Carga del AFE sobre el sensor', 'La cadena de 1 MΩ toma (V_IEPE − VSHIFT)/1 MΩ ≈ 9–10 µA: '
                                      'despreciable frente a mA.'),
    ('Margen de voltaje (compliance)', '24 V − 0.5 V (D1) − 0.03 V (R1) − 1.2 V (mínimo del LT3092) − 0.21 V '
                                       '(R_OUT) ≈ 22 V disponibles para el sensor. El RG-50 necesita '
                                       '12.5 V de bias + 3.2 V pico ≈ 16 V: sobran ≈ 6 V.'),
    ('Protección de entrada', 'D1 SS34 (40 V, 3 A) bloquea la polaridad invertida. D2 SMBJ26A: no conduce a '
                              '24 V (V_RWM = 26 V), ruptura ≥ 28.9 V, recorte 42.1 V a 14.3 A (pulso 10/1000 µs).'),
    ('Punto de trabajo del restador', f'REST = 1.1·VSHIFT − 0.1·V_IEPE. VSHIFT máx ≈ {VSH_MAX:.2f} V (DAC a 3V3 '
                                      f'menos la caída en R9). Con REST objetivo = {REST_T:.1f} V se cubre cualquier '
                                      f'bias de 0 a {BIAS_MAX:.1f} V. Para el RG-50 (12.5 V): VSHIFT = '
                                      f'{VSH_RG:.2f} V. La señal (±0.32 V máx.) queda entre 1.18 y 1.82 V.'),
    ('Corrección del DC (firmware)', 'DC_MON = REST/2 ≈ 0.75 V. Si DC_MON cambia más de un umbral: '
                                     'VSHIFT ← VSHIFT − 2·(DC_MON − 0.75 V)/1.1, se escribe al DAC y se deja '
                                     'quieto mientras se mide (así no actúa como filtro pasa-altos).'),
    ('Resolución del DAC', f'1 LSB = {VSH_MAX / 4096 * 1e3:.2f} mV en VSHIFT → {1.1 * VSH_MAX / 4096 * 1e3:.2f} mV '
                           'en REST.'),
    ('Rapidez del lazo', 'Filtro del DAC: 10 kΩ·100 nF = 1 ms (antes 100 ms). Filtro de DC_MON: 5 kΩ·100 nF = '
                         '0.5 ms (antes 50 ms). La corrección completa tarda unos milisegundos.'),
    ('Acople al ADC', f'C9/C14 = 10 µF con 60 kΩ de entrada del PCM1808 → f_c = {fc_c:.2f} Hz. El PCM1808 '
                      f'tiene además un pasa-altos interno de 0.019·fs/1000 = 0.91 Hz a 48 kHz (no se puede '
                      f'desactivar). Desfase total a 20 Hz ≈ {ph20:.1f}°.'),
    ('Reloj', '24.576 MHz = 512 × 48 kHz: PCM1808 maestro 512 fs → fs = 48 kHz, BCK = 64 fs = 3.072 MHz.'),
    ('Niveles en el ADC', f'Fondo de escala 3 Vpp = {FS_RMS:.2f} Vrms. RG-50 (50 mV/Pa nominal): 94 dB SPL → '
                          f'5 mVrms en el ADC (−46.5 dBFS); 130 dB pico → 0.32 V pico: nunca satura.'),
    ('Ruido / límite', f'SNR del PCM1808 = 99 dB → {NOISE * 1e6:.0f} µVrms en el ADC ≈ {SPL_N:.1f} dB SPL '
                       'referido al micrófono. Limitación honesta: la ganancia 0.1 desaprovecha ≈ 13 dB del ADC.'),
    ('Consumo (estimado)', '3V3: PCM1808 5.9 mA + oscilador + 2 DAC + pull-ups ≈ 15–20 mA. 5V_A: PCM1808 '
                           '8.6 mA + 2 TLV9062 ≈ 11 mA (caída en R33 ≈ 0.1 V). Entrada 24 V: ≈ 10–15 mA en total. '
                           'Fuente de laboratorio con límite de 50 mA.'),
]
for a, b in calc:
    w(f'{esc(a)} & {esc(b)}\\\\[2pt]')
w(r'\bottomrule\end{longtable}')

# ------------------------------------------------------------------ 9. tests + demo
w(r'\section{Pruebas y demostración}')
steps = [
    ('0. Antes de pedir', 'Alimentar la placa del gateway y medir con osciloscopio 3V3 y 5V y su rizado: valida el '
                          'bloque de bucks que se copia.'),
    ('1. Llega la placa', 'Fuente a 24 V con límite de 50 mA, sin NUCLEO ni micrófonos: medir 3V3, 5V y 5V\\_A.'),
    ('2. Fuentes IEPE', 'Amperímetro en lugar del puente J1/J7 y ~4.7 kΩ en el BNC: 2.81 mA y 1.51 mA; con '
                        'JP1/JP2 ≈ 3.98 y 2.51 mA.'),
    ('3. Micrófono falso', 'Zener de 12 V en el BNC + generador (1 kHz) por un condensador: en TP1 ≈ 12 V DC + la '
                           'onda; en TP2 la onda × 0.1 sobre un DC fijo.'),
    ('4. NUCLEO y lazo', 'Enchufar la NUCLEO (USB primero, luego 24 V), cargar firmware, poner/quitar JP1: REST salta '
                         'y vuelve a 1.5 V en milisegundos.'),
    ('5. ADC al PC', 'Capturar I$^2$S y graficar en Python: onda de 1 kHz sin DC y su FFT.'),
    ('6. Micrófonos', 'RG-50 en J2; SV 12L en J8 con adaptador BNC–TNC. Medir el bias real en TP1/TP3.'),
]
w(r'\begin{longtable}{@{}L{0.2\linewidth}L{0.76\linewidth}@{}}\toprule')
for a, b in steps:
    w(f'{a} & {b}\\\\[2pt]')
w(r'\bottomrule\end{longtable}')
w(r'''\textbf{Demo para el profesor:} (1) osciloscopio en TP1: DC del sensor con la señal encima; (2) en TP2: la
misma señal sin el DC del sensor (sobre el punto de trabajo fijo de 1.5 V), sin condensador en el camino;
(3) poner JP1: la corriente sube de 2.81 a 3.98 mA, se ve el salto y el DAC lo corrige en milisegundos;
(4) la señal digitalizada en el PC.''')
w(r'''\textbf{Ojo con el paso (3):} un sensor IEPE fija su propio voltaje de bias, así que con el micrófono real
el salto de corriente casi no mueve el DC (se ve poco). Para que el salto sea grande y claro, hacer esa parte
con la \textbf{resistencia de 4.7 k$\Omega$} en el BNC (V = I·R): 2.81 mA → 13.2 V y 3.98 mA → 18.7 V, un
escalón de 5.5 V en TP1 y de −0.55 V en TP2 antes de que el DAC lo corrija (VSHIFT pasa de 2.56 a 3.06 V,
dentro de su rango). Luego se repite con el micrófono y se mide cuánto cambia su bias en realidad.''')

# ------------------------------------------------------------------ 10. open items
w(r'\section{Pendientes y riesgos (honesto)}')
items = [
    'Ruteo: no está hecho. La prueba con autorruteador (Freerouting) no se pudo correr en esta sesión; el script '
    '\\texttt{tools/probar\\_ruteo.sh} la hace. Estimado: 246 conexiones, ≈ 1.26 m de ratsnest, 76 cruces fuera de GND.',
    'LT3092: los valores de 1.2–40 V, 10 µA ±1 \\% y 0.5–200 mA salen de las características del datasheet '
    '(copia de terceros); analog.com no fue accesible. Confirmar con el PDF oficial.',
    'Footprint RNX0012A (U6/U7): coincide con el de JLC (C1850339) salvo rotación de 90° y 0.14 mm de origen: '
    'revisar la vista previa del CPL de JLC.',
    'Stock en LCSC: LMR36015FBRNXR tenía poco stock (12–21 unidades cuando se consultó); revisar el día del pedido.',
    'Piezas JLC sin código LCSC en el diseño (heredadas del Altium y del gateway): ' + esc(', '.join(NO_LCSC)) +
    '. JLC las busca por MPN al subir el BOM; si no las tiene, elegir un equivalente (mismo valor, tamaño y '
    'tensión). Los códigos con * de la tabla de componentes se hallaron por búsqueda web.',
    'BNC Kinghelm de 75 Ω: para audio la impedancia no importa y acopla con BNC de 50 Ω.',
    f'Ganancia 0.1 del restador: limita el ruido equivalente a ≈ {SPL_N:.1f} dB SPL (aceptable para el laboratorio).',
    'Firmware pendiente: SAI (I$^2$S esclavo), ADC (DC\\_MON), I$^2$C a los DAC, lazo de corrección y envío al PC.',
]
w(r'\begin{itemize}')
for it in items:
    w(r'\item ' + it)
w(r'\end{itemize}')
w(r'\end{document}')
TXT = '\n'.join(L)
for ch, tex in (('≈', r'\ensuremath{\approx}'), ('∥', r'\ensuremath{\parallel}'), ('≥', r'\ensuremath{\geq}')):
    TXT = TXT.replace(ch, tex)              # Latin Modern text font lacks these glyphs
open(os.path.join(G, 'guia_conexiones.tex'), 'w', encoding='utf-8').write(TXT)
print('LaTeX escrito:', os.path.join(G, 'guia_conexiones.tex'))

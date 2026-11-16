"""Genera CALCULOS.md con medidas tomadas de la placa ruteada (no de los docstrings de los bloques).

Mide con pcbnew: anchos y largos por red y capa, vías por red, resistencia del camino fuente -> carga más lejana
(grafo de pistas de todas las capas unido por las vías), separación mínima medida de las redes de 24 V y largo de
los relojes. Los datos de datasheet llevan su fuente y página; lo que viene de una copia secundaria o es una
estimación queda marcado.
Uso (Python de KiCad): python calculos.py [pcb] [salida.md]
"""
import collections
import heapq
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
mm = pcbnew.ToMM
RHO = 1.72e-8                     # Ω·m, cobre a 20 °C [copia: valor de manual]
T_CU = {pcbnew.F_Cu: 0.035, pcbnew.B_Cu: 0.035, pcbnew.In1_Cu: 0.0152, pcbnew.In2_Cu: 0.0152}   # mm (apilado JLC04161H-7628)
T_VIA = 0.018                     # mm de cobre en el barril de la vía [estimado: capacidad publicada por JLC, sin verificar]
H_PLACA = 1.6
DT = 10.0                         # °C de aumento admitido (pedido del dueño)


def ipc_ancho(i_a, externo=True, t_mm=0.035):
    """Ancho mínimo (mm) para I con ΔT = DT. IPC-2221: I = k·ΔT^0.44·A^0.725, A en mil², k = 0.048 externo /
    0.024 interno [copia: ajuste de las curvas de IPC-2221, calculadoras de DigiKey y mbedded.ninja]."""
    k = 0.048 if externo else 0.024
    a_mil2 = (i_a / (k * DT ** 0.44)) ** (1 / 0.725)
    return a_mil2 / (t_mm / 0.0254) * 0.0254


def ipc_corriente(a_mm2, externo=True):
    k = 0.048 if externo else 0.024
    return k * DT ** 0.44 * (a_mm2 / 0.0254 ** 2) ** 0.725


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'pcb.kicad_pcb')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'CALCULOS.md')
    b = pcbnew.LoadBoard(path)
    pt = lambda v: (mm(v.x), mm(v.y))                                    # noqa: E731
    segs = [(pt(t.GetStart()), pt(t.GetEnd()), t.GetLayer(), t.GetNetname(), mm(t.GetWidth()))
            for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [(pt(v.GetPosition()), v.GetNetname(), mm(v.GetDrill())) for v in b.GetTracks() if v.GetClass() == 'PCB_VIA']
    capa = {pcbnew.F_Cu: 'F.Cu', pcbnew.In1_Cu: 'In1', pcbnew.In2_Cu: 'In2', pcbnew.B_Cu: 'B.Cu'}

    # ---------------- resistencia de camino por red (Dijkstra sobre resistencia)
    def grafo(net):
        g = collections.defaultdict(list)
        k = lambda L, p: (L, round(p[0], 3), round(p[1], 3))           # noqa: E731
        for a, c, L, n, w in segs:
            if n != net:
                continue
            r = RHO * math.dist(a, c) * 1e-3 / (w * 1e-3 * T_CU[L] * 1e-3)
            g[k(L, a)].append((k(L, c), r, math.dist(a, c)))
            g[k(L, c)].append((k(L, a), r, math.dist(a, c)))
        for p, n, d in vias:
            if n != net:
                continue
            rv = RHO * H_PLACA * 1e-3 / (math.pi * d * 1e-3 * T_VIA * 1e-3)
            nodos = [k(L, p) for L in T_CU]
            for i in nodos:
                for j in nodos:
                    if i != j:
                        g[i].append((j, rv / 2, 0.0))
        return g

    def camino(net, fuente, destino):
        g = grafo(net)
        s = (pcbnew.F_Cu, round(fuente[0], 3), round(fuente[1], 3))
        dist = {s: (0.0, 0.0)}
        pq = [(0.0, 0.0, s)]
        while pq:
            r, L, u = heapq.heappop(pq)
            if dist.get(u, (1e9,))[0] < r:
                continue
            for v, dr, dl in g[u]:
                if r + dr < dist.get(v, (1e9,))[0]:
                    dist[v] = (r + dr, L + dl)
                    heapq.heappush(pq, (r + dr, L + dl, v))
        t = (pcbnew.F_Cu, round(destino[0], 3), round(destino[1], 3))
        return dist.get(t)

    def pad(ref, num):
        return pt(b.FindFootprintByReference(ref).FindPadByNumber(num).GetPosition())

    # ---------------- anchos y largos por red y capa
    def resumen(net):
        por = collections.defaultdict(lambda: [1e9, 0.0, 0.0])
        for a, c, L, n, w in segs:
            if n == net:
                e = por[capa[L]]
                e[0] = min(e[0], w)
                e[1] = max(e[1], w)
                e[2] += math.dist(a, c)
        nv = sum(1 for p, n, d in vias if n == net)
        return por, nv

    # ---------------- separación mínima medida de las redes de 24 V
    def sep_minima(grupo):
        """Separación mínima (mm) entre el cobre de las redes de `grupo` y el de cualquier otra red, por capa.
        Pistas como segmentos con su medio ancho; pads con su polígono real (GetEffectivePolygon); zonas con su
        relleno, huecos incluidos (los teardrops cuentan como parte de su pad o vía)."""
        def iu(q):
            return pcbnew.VECTOR2I(int(round(q[0] * 1e6)), int(round(q[1] * 1e6)))

        def verts(ps):
            o = ps.Outline(0)
            return [o.CPoint(k) for k in range(o.PointCount())]

        items = collections.defaultdict(list)          # capa -> [(net, 'seg', (a, c, w/2)) | (net, 'poly', polyset)]
        for a, c, L, n, w in segs:
            items[L].append((n, 'seg', (a, c, w / 2)))
        for fp in b.GetFootprints():
            for pd in fp.Pads():
                for L in T_CU:
                    if pd.IsOnLayer(L) and pd.FlashLayer(L):
                        items[L].append((pd.GetNetname(), 'poly', pd.GetEffectivePolygon(L)))
        for z in b.Zones():
            if z.IsTeardropArea():
                continue
            for L in T_CU:
                if z.IsOnLayer(L):
                    items[L].append((z.GetNetname(), 'poly', z.GetFilledPolysList(L)))

        def d_ss(a, c, e, f):
            def ds(q, u, v):
                dx, dy = v[0] - u[0], v[1] - u[1]
                L2 = dx * dx + dy * dy
                t = 0 if L2 == 0 else max(0, min(1, ((q[0] - u[0]) * dx + (q[1] - u[1]) * dy) / L2))
                return math.hypot(q[0] - u[0] - t * dx, q[1] - u[1] - t * dy)
            return min(ds(a, e, f), ds(c, e, f), ds(e, a, c), ds(f, a, c))

        def dist(i1, i2):
            (k1, g1), (k2, g2) = i1, i2
            if k1 == 'seg' and k2 == 'seg':
                return d_ss(g1[0], g1[1], g2[0], g2[1]) - g1[2] - g2[2]
            if k1 == 'seg':
                return math.sqrt(g2.SquaredDistanceToSeg(pcbnew.SEG(iu(g1[0]), iu(g1[1])))) / 1e6 - g1[2]
            if k2 == 'seg':
                return math.sqrt(g1.SquaredDistanceToSeg(pcbnew.SEG(iu(g2[0]), iu(g2[1])))) / 1e6 - g2[2]
            pequeño, grande = (g1, g2) if g1.FullPointCount() <= g2.FullPointCount() else (g2, g1)
            return min(math.sqrt(grande.SquaredDistance(v)) for v in verts(pequeño)) / 1e6

        def bbox(k, g):
            if k == 'seg':
                return (min(g[0][0], g[1][0]) - g[2], min(g[0][1], g[1][1]) - g[2],
                        max(g[0][0], g[1][0]) + g[2], max(g[0][1], g[1][1]) + g[2])
            bb = g.BBox()
            return (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))

        best = (1e9, None)
        for L, its in items.items():
            mios = [(n, k, g, bbox(k, g)) for n, k, g in its if n in grupo]
            otros = [(n, k, g, bbox(k, g)) for n, k, g in its if n not in grupo]
            for n1, k1, g1, b1 in mios:
                for n2, k2, g2, b2 in otros:
                    # descarte rápido por cajas (más de 1 mm de separación no interesa)
                    if b1[0] - 1 > b2[2] or b2[0] - 1 > b1[2] or b1[1] - 1 > b2[3] or b2[1] - 1 > b1[3]:
                        continue
                    d = dist((k1, g1), (k2, g2))
                    if d < best[0]:
                        best = (d, f'{n1} - {n2} en {capa[L]}')
        return best

    # ---------------- datos de entrada
    I_5VA = 0.011 + 2 * 2 * 0.00075          # PCM1808 ICC máx + 2 × TLV9152 (2 amplif. × 750 µA máx)
    I_3V3 = 0.0102 + 2 * 0.0004 + 2 * 3.3 / 4700 + 0.010   # PCM1808 IDD (96 kHz típ) + 2 MCP4725 + pull-ups + Y1 (estim.)
    I_5V = I_5VA
    I_24 = 0.050                              # cota de diseño (fuente de banco limitada a 30-50 mA, AGENTS.md)
    L3, L5 = 6.8e-6, 10e-6
    lineas = []
    w = lineas.append
    w('# CÁLCULOS — Sonómetro IEPE Rev B (placa de 4 capas, ruteada)')
    w('')
    w('Generado por `tools/calculos.py` a partir de `pcb.kicad_pcb`: anchos, largos, vías y separaciones son medidas '
      'de la placa. Etiquetas de origen: **[doc]** leído del PDF del fabricante (página indicada); **[copia]** de una '
      'fuente secundaria, sin verificar contra el original; **[estimado]** supuesto de diseño.')
    w('')
    w('## 1. Datos de entrada')
    w('')
    w('| Dato | Valor | Origen |')
    w('|---|---|---|')
    filas = [
        ('Cobre externo (F.Cu, B.Cu)', '35 µm (1 oz)', 'apilado JLC04161H-7628 (REGLAS.md §9)'),
        ('Cobre interno (In1, In2)', '15.2 µm (0.5 oz)', 'apilado JLC04161H-7628 (REGLAS.md §9)'),
        ('Resistividad del cobre', '1.72·10⁻⁸ Ω·m', '[copia]'),
        ('Cobre en el barril de la vía', '18 µm', '[estimado] capacidad publicada por JLC, sin verificar'),
        ('LMR36015 fOSC, variante 1 MHz', '0.85 / 1 / 1.15 MHz', '[doc] SNVSB49D p.7, Electrical Characteristics'),
        ('LMR36015 tON-MIN / tOFF-MIN', '55 típ, 83 máx ns / 53 típ, 73 máx ns', '[doc] SNVSB49D p.7, §8.6'),
        ('LMR36015 RDS-ON alto / bajo', '225 típ, 435 máx mΩ / 150 típ, 280 máx mΩ', '[doc] SNVSB49D p.7'),
        ('LMR36015 RθJA / RθJB / ψJT', '72.5 / 23.3 / 0.8 °C/W', '[doc] SNVSB49D p.6, §8.4 (JEDEC)'),
        ('LMR36015 FPWM', 'CCM sin carga, frecuencia fija', '[doc] SNVSB49D p.16, Tabla 9-1'),
        ('L1 (3V3) / L2 (5V)', '6.8 µH / 10 µH', 'design.py (XAL4030-682 / XAL4040-103)'),
        ('PCM1808 ICC (VCC 5 V)', '8.6 típ, 11 máx mA', '[doc] SLES177B p.6'),
        ('PCM1808 IDD (VDD 3.3 V)', '5.9 típ, 8 máx mA a 48 kHz; 10.2 típ a 96 kHz', '[doc] SLES177B p.6'),
        ('TLV9152 IQ por amplificador', '560 típ, 685 máx µA; 750 máx (−40…125 °C)', '[doc] SBOS986E p.12'),
        ('MCP4725 IDD', '210 típ, 400 máx µA', '[doc] DS22039D p.3'),
        ('Oscilador Y1 (O322524576MEEA4SC)', '≤ 10 mA', '[estimado] sin datasheet a mano'),
        ('LT3092 θJA (TS8)', '57 °C/W', '[copia] REGLAS.md §4'),
        ('Corrientes IEPE', 'CH1 2.81 → 3.98 mA; CH2 1.51 → 2.51 mA (con JP)', 'design.py, cambio C9'),
        ('D2 SMBJ26A', 'VRWM 26 V; VBR mín 28.9 V', '[copia] valores de la serie SMBJ, sin datasheet a mano'),
        ('IPC-2221 (ampacidad)', 'I = k·ΔT^0.44·A^0.725; k = 0.048 ext / 0.024 int', '[copia] REGLAS.md §5'),
    ]
    for f in filas:
        w('| ' + ' | '.join(f) + ' |')
    w('')
    w('**Corrientes de diseño por riel** (cotas superiores):')
    w(f'- 5V_A = PCM1808 ICC máx + 2 TLV9152 a 750 µA por amplificador = **{I_5VA * 1e3:.1f} mA**; 5V = 5V_A (R33 solo '
      'alimenta 5V_A).')
    w(f'- 3V3 = PCM1808 IDD (10.2 mA, 96 kHz) + 2 MCP4725 máx + pull-ups I2C + Y1 (estimado) = **{I_3V3 * 1e3:.1f} mA**.')
    w(f'- 24V_PROT: **{I_24 * 1e3:.0f} mA**, el límite de la fuente de banco (AGENTS.md §5); IEPE ≤ 3.98 + 2.51 mA.')
    w('')

    # ---------------- LMR36015
    w('## 2. LMR36015: tiempo de encendido, rizado en FPWM y disipación')
    w('')
    w('tON = D / fSW con D = VOUT / VIN (ideal; con pérdidas D sube un poco y tON también, a favor). '
      'tOFF = (1 − D) / fSW. Se compara con tON-MIN = 83 ns y tOFF-MIN = 73 ns máximos [doc SNVSB49D p.7].')
    w('')
    w('| Salida | VIN | fSW | tON | margen sobre 83 ns | tOFF | margen sobre 73 ns |')
    w('|---|---|---|---|---|---|---|')
    for vo in (3.3, 5.0):
        for vin in (18.0, 23.5, 26.0, 28.9):
            for f in (0.85e6, 1.15e6):
                d = vo / vin
                ton, toff = d / f * 1e9, (1 - d) / f * 1e9
                w(f'| {vo} V | {vin} V | {f / 1e6:.2f} MHz | {ton:.0f} ns | {ton - 83:+.0f} ns | {toff:.0f} ns | '
                  f'{toff - 73:+.0f} ns |')
    w('')
    w('VIN: 18 V es una entrada baja de prueba; 23.5 V es 24 V menos D1; 26 V es la VRWM del TVS; 28.9 V es la VBR '
      'mínima del TVS [copia]. Peor caso: 3.3 V con 28.9 V y 1.15 MHz da tON = 99 ns, 16 ns por encima del mínimo. '
      'No hay repliegue de frecuencia en ningún caso.')
    w('')
    w('**Rizado de la bobina en FPWM** (CCM aun sin carga [doc SNVSB49D p.16]): ΔIL = (VIN − VOUT)·VOUT / (VIN·L·fSW). '
      'El peor caso es el oscilador lento (0.85 MHz) con la VIN más alta.')
    w('')
    w('| Salida | L | VIN | fSW | ΔIL p-p | Pico (I + ΔIL/2) | RMS en la bobina |')
    w('|---|---|---|---|---|---|---|')
    rizo = {}
    for vo, L, io in ((3.3, L3, I_3V3), (5.0, L5, I_5V)):
        for vin in (23.5, 28.9):
            dil = (vin - vo) * vo / (vin * L * 0.85e6)
            pico = io + dil / 2
            rms = math.sqrt(io ** 2 + dil ** 2 / 12)
            rizo[(vo, vin)] = (dil, pico, rms)
            w(f'| {vo} V | {L * 1e6:.1f} µH | {vin} V | 0.85 MHz | {dil:.3f} A | {pico:.3f} A | {rms:.3f} A |')
    w('')
    pk = max(v[1] for v in rizo.values())
    w(f'Los tramos SW, bobina y COUT se dimensionan con el pico de **{pk:.2f} A** (ver §3), no con los 5–20 mA de la carga.')
    w('')
    dil3, _, rms3 = rizo[(3.3, 28.9)]
    d3 = 3.3 / 28.9
    pcond = rms3 ** 2 * (d3 * 0.435 + (1 - d3) * 0.280)
    psw = 0.5 * 28.9 * (dil3 / 2) * 10e-9 * 1.15e6
    w('**Disipación del LMR36015** [estimado]. El datasheet no da la corriente de entrada en FPWM sin carga: '
      f'conducción con RDS-ON máximas = {pcond * 1e3:.1f} mW; conmutación con 10 ns de flancos (supuesto) = '
      f'{psw * 1e3:.0f} mW; más el LDO interno y las cargas de compuerta, que no están publicados. Con una cota de '
      '0.15 W por integrado, ΔT = 0.15 · 72.5 = 11 °C con el RθJA JEDEC; la placa de 4 capas con plano GND entero queda '
      'por debajo. **A verificar en el banco:** corriente de entrada a 24 V sin carga en cada buck.')
    w('')

    # ---------------- anchos IPC
    w('## 3. Ancho de pista (IPC-2221, ΔT = 10 °C) contra el ancho usado')
    w('')
    w('| Tramo | Corriente | Capa | Ancho mínimo IPC | Ancho mínimo usado (medido) |')
    w('|---|---|---|---|---|')
    casos = [
        ('SW_3 / SW_5, bobina, COUT', pk, ['/SW_3', '/SW_5']),
        ('24V_PROT (bus, VIN)', I_24, ['24V_PROT']),
        ('3V3 (salida y distribución)', I_3V3, ['3V3']),
        ('5V (salida a R33)', I_5V, ['5V']),
        ('5V_A (distribución)', I_5VA, ['5V_A']),
        ('IEPE_SUP / IEPE_SUP_SV', 0.004, ['/IEPE_SUP', '/IEPE_SUP_SV']),
        ('GND (pistas)', I_24, ['GND']),
    ]
    for nombre, i, nets in casos:
        por = collections.defaultdict(lambda: [1e9, 0.0, 0.0])
        for n in nets:
            p, _ = resumen(n)
            for c, (wmin, wmax, L) in p.items():
                e = por[c]
                e[0] = min(e[0], wmin)
                e[1] = max(e[1], wmax)
                e[2] += L
        for c, (wmin, wmax, L) in sorted(por.items()):
            ext = c in ('F.Cu', 'B.Cu')
            need = ipc_ancho(i, ext, 0.035 if ext else 0.0152)
            w(f'| {nombre} | {i * 1e3:.0f} mA | {c} | {need:.3f} mm | {wmin:.2f} mm (máx {wmax:.2f}; {L:.0f} mm de pista) |')
    w('')
    w('En todos los rieles el ancho lo fija la fabricación y la regla de clase (0.25 mm mínimo en Potencia), no la '
      'corriente: el margen es de un orden de magnitud o más. Las zonas de VIN, VOUT y SW del bloque 1 son más anchas '
      'que cualquier pista.')
    w('')

    # ---------------- caídas de tensión
    w('## 4. Caída de tensión de la fuente a la carga más lejana')
    w('')
    w('Resistencia del camino de menor resistencia por el cobre de la red (pistas de todas las capas y vías; '
      'cobre a 20 °C). Caída = corriente total del riel × resistencia (cota: toda la corriente por el camino más largo).')
    w('')
    w('| Riel | Fuente | Carga | Largo del camino | R | Corriente | Caída |')
    w('|---|---|---|---|---|---|---|')
    rails = [
        ('3V3', 'tronco de 3V3 en la zona VOUT (139.8, 102.725)', (139.8, 102.725),
         [('R46', '2'), ('R9', '2'), ('R10', '2'), ('R11', '2'), ('U4', '4'), ('R49', '1'), ('C20', '1'), ('C13', '1')],
         I_3V3),
        ('5V_A', 'R33.2', pad('R33', '2'),
         [('U3', '8'), ('U9', '8'), ('U4', '3'), ('C18', '1'), ('C7', '2'), ('C54', '2')], I_5VA),
    ]
    peor_mv = 0.0
    for net, fn, fpos, cargas, i in rails:
        peor = None
        for ref, num in cargas:
            r = camino(net, fpos, pad(ref, num))
            if r and (peor is None or r[0] > peor[1][0]):
                peor = (f'{ref}.{num}', r)
        if peor:
            nombre, (r, L) = peor
            w(f'| {net} | {fn} | {nombre} | {L:.1f} mm | {r * 1e3:.0f} mΩ | {i * 1e3:.1f} mA | {i * r * 1e3:.2f} mV |')
            peor_mv = max(peor_mv, i * r * 1e3)
    w('')
    w(f'Las caídas por el cobre quedan por debajo de {math.ceil(peor_mv)} mV: despreciables frente a la regulación de '
      'los bucks (±1.5 % en FPWM [doc SNVSB49D p.8]). R33 (10 Ω) baja 5V_A en '
      f'{I_5VA * 10 * 1e3:.0f} mV y disipa {I_5VA ** 2 * 10 * 1e3:.1f} mW; R9/R46 (100 Ω) bajan cada 3V3_DAC en '
      '40 mV con el MCP4725 al máximo.')
    w('')

    # ---------------- vías
    w('## 5. Corriente por vía y vías por riel')
    w('')
    a_via = math.pi * 0.3 * T_VIA
    w(f'Barril de 0.3 mm con {T_VIA * 1e3:.0f} µm de cobre: sección {a_via:.4f} mm². Con la fórmula de capa externa '
      f'(práctica común para el barril), I(ΔT = 10 °C) = **{ipc_corriente(a_via):.2f} A** por vía; con la interna, '
      f'{ipc_corriente(a_via, False):.2f} A.')
    w('')
    w('| Red | Vías | Corriente del riel | Vías necesarias |')
    w('|---|---|---|---|')
    for n, i in (('3V3', I_3V3), ('5V_A', I_5VA), ('24V_PROT', I_24), ('5V', I_5V), ('GND', I_24),
                 ('I2C_SCL', 0.001), ('I2C_SDA', 0.001), ('DC_MON', 0.0001), ('DC_MON2', 0.0001)):
        nv = sum(1 for p, nn, d in vias if nn == n)
        w(f'| {n} | {nv} | {i * 1e3:.1f} mA | 1 |')
    w('')

    # ---------------- disipación
    w('## 6. Disipación y temperatura')
    w('')
    w('| Pieza | Peor caso | Potencia | ΔT | Nota |')
    w('|---|---|---|---|---|')
    p3092 = 0.00398 * 23.3
    w(f'| LT3092 (U1/U8) | IEPE en cortocircuito: 3.98 mA × 23.3 V | {p3092 * 1e3:.0f} mW | {p3092 * 57:.1f} °C | '
      'θJA [copia] |')
    w('| LMR36015 (U6/U7) | FPWM sin carga, 28.9 V | ≤ 150 mW [estimado] | ≤ 11 °C | ver §2; medir en el banco |')
    w(f'| D1 SS34 | {I_24 * 1e3:.0f} mA × 0.4 V | {I_24 * 0.4 * 1e3:.0f} mW | < 1 °C | VF [estimado] |')
    w(f'| R33 10 Ω | {I_5VA * 1e3:.1f} mA | {I_5VA ** 2 * 10 * 1e3:.1f} mW | despreciable | 0603, 100 mW |')
    w('| D2 SMBJ26A | en reposo (fuga) | despreciable | — | solo conduce en transitorios |')
    w('| PCM1808 | 48 kHz | 62 típ, 81 máx mW | — | [doc] SLES177B p.6 |')
    w('')

    # ---------------- separación por tensión
    w('## 7. Separación por tensión')
    w('')
    grupo = {'24V_PROT', 'Net-(D1-A)', '/IEPE_SUP', '/IEPE_SUP_SV', 'Net-(J1-Pin_2)', 'Net-(J7-Pin_2)', 'IEPE',
             'IEPE_SV', '/SW_3', '/SW_5'}
    grupo = {n for n in grupo if n in {s[3] for s in segs} | {p.GetNetname() for fp in b.GetFootprints()
                                                                 for p in fp.Pads()}}
    d, donde = sep_minima(grupo)
    w('IPC-2221B tabla 6-1 [copia, REGLAS.md §5]: hasta 30 V pide 0.1 mm en capa externa sin recubrimiento (B2, hasta '
      '3050 m; Manizales ≈ 2150 m) y 0.05 mm en capa interna (B1). De 31 a 50 V pide 0.6 mm externo. El TVS limita la '
      'tensión continua a la VRWM de 26 V, así que las redes de 24 V van en la fila de 16–30 V.')
    w('')
    w(f'- Redes con hasta 24–29 V: {", ".join(sorted(grupo))}.')
    w(f'- **Separación mínima medida** a cualquier otra red, en todas las capas: **{d:.3f} mm** ({donde}).')
    w(f'- Contra 0.1 mm (B2) y 0.05 mm (B1): margen de {d / 0.1:.1f}×. El diseño usa además 0.2–0.3 mm por clase '
      '(REGLAS.md §8).')
    w('')

    # ---------------- relojes
    w('## 8. Relojes: largo e impedancia')
    w('')
    w('No hay pares diferenciales ni USB en la placa. Para los relojes se compara el largo con el largo crítico '
      'Lc = tr / (2·tpd). tpd ≈ 5.6 ps/mm en microstrip FR-4 (εr 4.4) [copia: aproximación de IPC-2141]; con un flanco '
      'de 1 ns (supuesto conservador) Lc ≈ 90 mm.')
    w('')
    w('| Red | Largo medido | Relación con Lc |')
    w('|---|---|---|')
    for n in ('Net-(Y1-OUT)', 'Net-(U4-SCKI)', 'Net-(U4-BCK)', 'SAI_SCK', 'Net-(U4-LRCK)', 'SAI_FS', 'Net-(U4-DOUT)',
              'SAI_SD'):
        L = sum(math.dist(a, c) for a, c, LL, nn, ww in segs if nn == n)
        w(f'| {n} | {L:.1f} mm | {L / 90 * 100:.0f} % de Lc |')
    w('')
    z0 = 87 / math.sqrt(4.4 + 1.41) * math.log(5.98 * 0.2104 / (0.8 * 0.2 + 0.035))
    w(f'Impedancia de una pista de 0.2 mm en F.Cu sobre 0.21 mm de prepreg hasta In1: Z0 ≈ {z0:.0f} Ω (fórmula de '
      'IPC-2141 [copia]). Todas las líneas son mucho más cortas que Lc, así que no hace falta controlar la impedancia; '
      'las resistencias en serie R21–R24 amortiguan los flancos.')
    w('')

    # ---------------- TLV9152 (salida de tools/analisis_opamp.py)
    import contextlib
    import io
    sys.path.insert(0, HERE)
    import analisis_opamp as ao
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ao.resumen()
        ao.transicion()
    w('## 9. TLV9152 (U3/U9): estabilidad y región de transición de la entrada')
    w('')
    w('Salida de `tools/analisis_opamp.py`. Modelo de dos polos ajustado al GBW (4.5 MHz) y al margen de fase a G = +1 '
      '(60°) del datasheet [doc SBOS986E p.12]; capacidades de entrada ZID 100 MΩ ‖ 3 pF y ZICM 6 TΩ ‖ 1 pF [doc p.11]; '
      '1.5 pF de pistas [estimado]. Región de transición típica (V+) − 2 V a (V+) − 1 V [doc §7.3.4 p.26].')
    w('')
    w('```')
    w(buf.getvalue().strip())
    w('```')
    w('')
    w('- **U3A/U9A (sumador):** con CF = 10 pF, margen de fase ≈ 70° y sin pico; sin CF quedaría en ≈ 8° (por eso se '
      'agregó C56/C57).')
    w('- **U3B/U9B (seguidor de VSHIFT):** su carga es la entrada + del sumador, unos 5 pF; el datasheet admite 1000 pF '
      '[doc p.12]. La impedancia de fuente en la entrada + (R12/C4) no entra en el lazo del seguidor.')
    w('- **Región de transición:** las dos entradas de cada amplificador quedan en VSHIFT, un nivel de DC que no se mueve '
      'con la señal (configuración inversora más lazo de DC). Aun así, conviene quedar en el par P, que es donde la '
      'tabla especifica la CMRR. **Para el firmware: REST_OUT objetivo ≈ 1.5 V** (DC_MON ≈ 0.75 V). Así VSHIFT queda '
      'en 2.1–2.6 V para polarizaciones de 8–14 V, por debajo de la región, y la salida conserva margen: 1.5 ± 0.32 V '
      'con el RG-50 a 130 dB y 1.5 ± 1.08 V con la excursión máxima del SV 12. Con un objetivo de 2.45 V (mitad del '
      'riel), VSHIFT cae dentro de la región o el DAC llega al tope.')
    w('- **Sin verificar:** simulación con el modelo SPICE de TI y medición en banco (escalón del DAC y forma de VSHIFT y '
      'REST en el osciloscopio).')
    w('')
    open(out, 'w', encoding='utf-8').write('\n'.join(lineas) + '\n')
    print('CALCULOS.md escrito:', out)


if __name__ == '__main__':
    main()

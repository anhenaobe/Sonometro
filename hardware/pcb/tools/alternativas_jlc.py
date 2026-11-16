"""Busca equivalentes en el catálogo de JLCPCB para las piezas con riesgo (extended, sin stock o sin código).

Criterios (solo PROPUESTAS; nada se cambia sin aprobación del dueño):
  - resistencias: mismo valor, mismo encapsulado, tolerancia <= la original (1 % preferida);
  - condensadores: mismo valor, tensión >= la requerida, dieléctrico X7R (o X5R si el original es X5R),
    mismo encapsulado; si no hay en ese encapsulado, se listan otros (implica cambio de footprint).
Primero se buscan 'basic'; si no hay, 'extended' con stock suficiente.
Salida: tools/out/alternativas_jlc.json + tabla en pantalla.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from auditoria_jlc import query, rows, brief  # noqa: E402  (no vuelve a correr la auditoría: ver __main__)

# grupo -> (tipo, valor buscado, encapsulados aceptados, tensión mínima V, dieléctricos aceptados, tolerancia máx %)
NEED = [
    ('R2,R3', 'R', '150Ω', ['0603'], None, None, 1),
    ('R10,R11', 'R', '4.7kΩ', ['0603'], None, None, 1),
    ('R1,R36', 'R', '10Ω', ['0402'], None, None, 1),
    ('R33', 'R', '10Ω', ['0603'], None, None, 1),
    ('R9,R19-R24,R35,R46', 'R', '100Ω', ['0603'], None, None, 1),
    ('R4,R5,R12,R15,R17,R37,R44,R45,R49-R51', 'R', '10kΩ', ['0603'], None, None, 1),
    ('R6', 'R', '1kΩ', ['0603'], None, None, 1),
    ('R13,R38', 'R', '390kΩ', ['0603'], None, None, 1),
    ('R14,R39', 'R', '365kΩ', ['0603'], None, None, 1),
    ('R16,R40', 'R', '191kΩ', ['0603'], None, None, 1),
    ('R18,R41', 'R', '54.9kΩ', ['0603'], None, None, 1),
    ('R7,R8,R42,R43', 'R', '49.9kΩ', ['0603'], None, None, 1),
    ('R29,R31', 'R', '100kΩ', ['0603'], None, None, 1),
    ('R30', 'R', '43.2kΩ', ['0603'], None, None, 1),
    ('R32', 'R', '24.9kΩ', ['0603'], None, None, 1),
    ('R34', 'R', '15kΩ', ['0603'], None, None, 1),
    ('C10,C19', 'C', '10nF', ['0402'], 25, ('X7R',), None),
    ('C5,C9,C11,C14,C15,C18,C47,C52', 'C', '10uF', ['0603'], 10, ('X5R', 'X7R'), None),
    ('C27,C28,C37,C38 (CIN)', 'C', '4.7uF', ['2220', '1210', '1206', '1812'], 50, ('X7R',), None),
    ('C29,C30,C39,C40 (CHF)', 'C', '220nF', ['0805', '0603'], 50, ('X7R',), None),
    ('C31-C34,C41-C44 (COUT)', 'C', '15uF', ['1210'], 16, ('X7R', 'X5R'), None),
    ('C31-C34,C41-C44 (COUT 22uF)', 'C', '22uF', ['1210'], 16, ('X7R', 'X5R'), None),
    ('C36,C46 (VCC)', 'C', '2.2uF', ['0805', '0603'], 16, ('X7R', 'X5R'), None),
]


def attr(c, name):
    for a in c.get('attributes') or []:
        if a.get('attribute_name_en') == name:
            return a.get('attribute_value_name') or ''
    return ''


def num(s):
    m = re.match(r'\s*([\d.]+)\s*([pnuµmkKM]?)', s or '')
    if not m:
        return None
    return float(m.group(1)) * {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'k': 1e3, 'K': 1e3,
                                'M': 1e6, '': 1}[m.group(2)]


def ok(c, kind, value, pkgs, vmin, diel, tol):
    if (c.get('componentSpecificationEn') or '') not in pkgs or not c.get('stockCount'):
        return False
    d = c.get('describe') or ''
    if kind == 'R':
        res = attr(c, 'Resistance') or d
        if num(res.replace('Ω', '')) != num(value.replace('Ω', '')):
            return False
        t = num((attr(c, 'Tolerance') or '').replace('±', '').replace('%', ''))
        return t is not None and t <= tol
    cap = attr(c, 'Capacitance') or d
    if num(cap.replace('F', '')) != num(value.replace('F', '')):
        return False
    v = num((attr(c, 'Voltage Rating') or '').replace('V', ''))
    if v is None or v < vmin:
        return False
    return any(x in (attr(c, 'Temperature Coefficient') + ' ' + d) for x in diel)


if __name__ == '__main__':
    out = []
    for grp, kind, value, pkgs, vmin, diel, tol in NEED:
        found = {'basic': [], 'extended': []}
        for lib in ('base', 'expand'):
            for pkg in pkgs:
                kw = f'{value} {pkg}' + (f' {vmin}V' if vmin else '')
                for c in rows(query(kw, {'componentLibraryType': lib}, page_size=50)):
                    if ok(c, kind, value, pkgs, vmin or 0, diel, tol):
                        found['basic' if lib == 'base' else 'extended'].append(brief(c))
        for k in found:
            seen = set()
            found[k] = [x for x in sorted(found[k], key=lambda x: -(x['stock'] or 0))
                        if not (x['lcsc'] in seen or seen.add(x['lcsc']))][:4]
        out.append({'grupo': grp, 'valor': value, 'encapsulados': pkgs, 'vmin': vmin, **found})
        b = found['basic'][:2] or found['extended'][:2]
        print(f"{grp[:34]:34s} {value:7s} -> " + ('; '.join(f"{x['lcsc']} {x['type']} {x['package']} "
                                                            f"{x['mpn']} stock={x['stock']}" for x in b) or 'NADA'))
        sys.stdout.flush()
    json.dump(out, open(os.path.join(HERE, 'out', 'alternativas_jlc.json'), 'w', encoding='utf-8'), indent=1,
              ensure_ascii=False)

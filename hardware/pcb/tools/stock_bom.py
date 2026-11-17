"""Revisa fabricacion/bom.csv contra el diseño aprobado y contra el catálogo de JLCPCB del día.

Para cada línea del BOM:
  - el código LCSC es el de target.json (las elecciones aprobadas en design.py) para todas sus piezas;
  - consulta nueva a la API pública de piezas SMT de JLC (solo se envía el código LCSC; caché del día aparte):
    el código existe, el MPN coincide con el campo MPN de la placa, basic/extended, stock;
  - stock suficiente para 5 placas (cantidad de la línea × 5).
Uso: python tools/stock_bom.py   -> fabricacion/stock_bom.md (sale con código 1 si alguna línea no cumple)
"""
import csv
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import auditoria_jlc as aj  # noqa: E402

FAB = os.path.join(HERE, '..', 'fabricacion')
PLACAS = 5


def main():
    hoy = datetime.date.today().isoformat()
    aj.CACHE = os.path.join(aj.OUT, 'jlc_cache_' + hoy)          # consulta nueva, no la caché de la fase A
    os.makedirs(aj.CACHE, exist_ok=True)
    target = json.load(open(os.path.join(HERE, 'target.json'), encoding='utf-8'))
    filas, malos = [], 0
    for r in csv.DictReader(open(os.path.join(FAB, 'bom.csv'), encoding='utf-8')):
        lcsc = r['LCSC Part Number']
        refs = r['Designator'].split(',')
        notas = []
        aprob = {target.get(x, {}).get('lcsc', '') for x in refs}
        if aprob != {lcsc}:
            notas.append(f'en target.json: {", ".join(sorted(aprob))}')
        mpn_placa = {target.get(x, {}).get('mpn', '') for x in refs}
        c = next((x for x in aj.rows(aj.query(lcsc)) if x.get('componentCode') == lcsc), None)
        if c is None:
            notas.append('no aparece en el catálogo')
            filas.append((r, '—', '—', '—', notas))
            malos += 1
            continue
        b = aj.brief(c)
        if not any(aj.norm(m) and aj.norm(m) == aj.norm(b['mpn']) for m in mpn_placa):
            notas.append(f'MPN de la placa: {", ".join(sorted(mpn_placa))}')
        need = len(refs) * PLACAS
        if (b['stock'] or 0) < need:
            notas.append(f'stock {b["stock"]} < {need} para {PLACAS} placas')
        if notas:
            malos += 1
        filas.append((r, b['mpn'], b['type'], b['stock'], notas))
    with open(os.path.join(FAB, 'stock_bom.md'), 'w', encoding='utf-8') as f:
        f.write(f'# Stock y códigos del BOM en JLCPCB ({hoy})\n\n'
                f'Generado por `tools/stock_bom.py` con una consulta nueva a la API pública de piezas SMT de JLC. '
                f'Stock contra {PLACAS} placas. El stock cambia a diario: repetir antes del pedido.\n\n'
                '| Piezas | Valor | LCSC | MPN en JLC | Tipo | Stock | Observación |\n|---|---|---|---|---|---|---|\n')
        for r, mpn, tipo, stock, notas in filas:
            f.write(f'| {r["Designator"]} | {r["Comment"]} | {r["LCSC Part Number"]} | {mpn} | {tipo} | {stock} | '
                    f'{"; ".join(notas) or "ok"} |\n')
        f.write(f'\n**Líneas con observaciones: {malos} de {len(filas)}.**\n')
    print(f'{len(filas)} líneas, {malos} con observaciones -> fabricacion/stock_bom.md')
    for r, mpn, tipo, stock, notas in filas:
        if notas:
            print('  ', r['Designator'][:40], r['LCSC Part Number'], tipo, stock, '|', '; '.join(notas))
    sys.exit(1 if malos else 0)


if __name__ == '__main__':
    main()

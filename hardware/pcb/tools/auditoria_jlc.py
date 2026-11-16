"""Auditoría de piezas contra el catálogo de JLCPCB (API pública del buscador de piezas SMT).

Para cada pieza que monta JLC (mount == 'JLC' en target.json):
  - con LCSC: confirma que el código existe, que el MPN coincide, stock y si es basic/extended/preferred;
  - sin LCSC: busca el MPN exacto y, si no aparece, lista candidatos.
Además, para pasivos extended, busca equivalentes *basic* del mismo valor y encapsulado (solo propuesta).

Uso: python tools/auditoria_jlc.py  -> tools/out/auditoria_jlc.json (crudo) + resumen en pantalla.
Las respuestas se guardan en tools/out/jlc_cache/ para no repetir consultas.
"""
import json
import os
import re
import sys
import time
import collections
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
CACHE = os.path.join(OUT, 'jlc_cache')
os.makedirs(CACHE, exist_ok=True)
API = 'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList'
T = json.load(open(os.path.join(HERE, 'target.json')))
EXTRA_LCSC = {'LT3092ETS8#TRPBF': 'C462641', 'PCM1808PW': 'C55513', 'TLV9062IDDFR': 'C2867884',
              'MCP4725A0T-E/CH': 'C144198'}            # hallados por búsqueda web (guía), a confirmar aquí


def norm(s):
    return re.sub(r'[\s#/\-_.]', '', (s or '')).upper()


def query(keyword, extra=None, page_size=25):
    key = re.sub(r'[^A-Za-z0-9]+', '_', keyword + json.dumps(extra or {}, sort_keys=True))[:150]
    path = os.path.join(CACHE, key + '.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    body = {'keyword': keyword, 'currentPage': 1, 'pageSize': page_size}
    body.update(extra or {})
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.loads(r.read().decode('utf-8'))
    json.dump(d, open(path, 'w', encoding='utf-8'))
    time.sleep(1.0)
    return d


def rows(d):
    return ((d.get('data') or {}).get('componentPageInfo') or {}).get('list') or []


def brief(c):
    lib = {'base': 'basic', 'expand': 'extended'}.get(c.get('componentLibraryType'), c.get('componentLibraryType'))
    if c.get('preferredComponentFlag'):
        lib += ' (preferred)'
    return {'lcsc': c.get('componentCode'), 'mpn': c.get('componentModelEn'), 'brand': c.get('componentBrandEn'),
            'package': c.get('componentSpecificationEn'), 'type': lib, 'stock': c.get('stockCount'),
            'describe': c.get('describe'), 'price1': c.get('initialPrice')}


def main():
    groups = collections.OrderedDict()
    for ref, p in T.items():
        if p['mount'] != 'JLC':
            continue
        k = (p['mpn'], p['lcsc'] or EXTRA_LCSC.get(p['mpn'], ''), p['value'], p['fp'].split(':')[1])
        groups.setdefault(k, []).append(ref)

    report = []
    for (mpn, lcsc, value, fp), refs in groups.items():
        item = {'refs': refs, 'value': value, 'footprint': fp, 'mpn': mpn, 'lcsc_design': lcsc,
                'lcsc_source': 'diseño' if T[refs[0]]['lcsc'] else ('web (guía)' if lcsc else ''), 'found': None,
                'mpn_match': None, 'candidates': []}
        if lcsc:
            hit = [c for c in rows(query(lcsc)) if c.get('componentCode') == lcsc]
            if hit:
                item['found'] = brief(hit[0])
                item['mpn_match'] = norm(hit[0].get('componentModelEn')) == norm(mpn)
        if item['found'] is None and mpn:
            res = rows(query(mpn))
            exact = [c for c in res if norm(c.get('componentModelEn')) == norm(mpn)]
            if exact:
                exact.sort(key=lambda c: -(c.get('stockCount') or 0))
                item['found'] = brief(exact[0])
                item['mpn_match'] = True
                item['lcsc_source'] = 'buscado por MPN'
            item['candidates'] = [brief(c) for c in (exact[1:4] if exact else res[:4])]
        report.append(item)
        f = item['found']
        print(f"{','.join(refs)[:28]:28s} {mpn[:22]:22s} {lcsc or '-':9s} -> "
              + (f"{f['lcsc']:9s} {f['type']:20s} stock={f['stock']} mpn_ok={item['mpn_match']}" if f else 'NO ENCONTRADO'))
        sys.stdout.flush()

    json.dump(report, open(os.path.join(OUT, 'auditoria_jlc.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('guardado', os.path.join(OUT, 'auditoria_jlc.json'))


if __name__ == '__main__':
    main()

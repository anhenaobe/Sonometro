"""Mide la placa ruteada: caminos de cobre entre pads, vecinos de un pad por pista, largo de redes y lazos.

Grafo por capa: los nodos son los extremos de las pistas (y el centro de los pads, donde terminan las pistas según
las reglas de trazado); las aristas son los segmentos con su largo. Una pista que termina dentro de una zona llega a
un nodo 'zona:<nombre>'. Solo F.Cu salvo que se pida otra capa: así "unido en F.Cu" no cuenta caminos por el plano.
Uso como módulo (CALCULOS.md) o directo:  python medir.py [pcb]   -> mediciones del punto 7 de la revisión del bloque 1.
"""
import heapq
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))


def mm(v):
    return pcbnew.ToMM(v)


def key(x, y):
    return (round(x, 3), round(y, 3))


class Cobre:
    def __init__(self, b, capa=pcbnew.F_Cu):
        self.b = b
        self.capa = capa
        self.adj = {}                       # nodo -> [(vecino, largo, red)]
        self.pad_de = {}                    # nodo -> 'U6.2'
        self.nodo_pad = {}                  # 'U6.2' -> nodo
        self.red_pad = {}
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(capa):
                    k = key(mm(p.GetPosition().x), mm(p.GetPosition().y))
                    n = f'{fp.GetReference()}.{p.GetNumber()}'
                    self.pad_de[k] = n
                    self.nodo_pad[n] = k
                    self.red_pad[n] = p.GetNetname()
        self.segs = []
        for t in b.GetTracks():
            if t.GetClass() != 'PCB_TRACK' or t.GetLayer() != capa:
                continue
            a = key(mm(t.GetStart().x), mm(t.GetStart().y))
            c = key(mm(t.GetEnd().x), mm(t.GetEnd().y))
            L = math.dist(a, c)
            self.segs.append((a, c, t.GetNetname(), mm(t.GetWidth())))
            self.adj.setdefault(a, []).append((c, L, t.GetNetname()))
            self.adj.setdefault(c, []).append((a, L, t.GetNetname()))
        self.zona_de = {}
        for z in b.Zones():
            if not z.IsOnLayer(capa):
                continue
            fill = z.GetFilledPolysList(capa)
            for k in self.adj:
                if k not in self.pad_de and fill.Contains(pcbnew.VECTOR2I(int(round(k[0] * 1e6)),
                                                                          int(round(k[1] * 1e6)))):
                    if z.GetNetname() == next(r for _, _, r in self.adj[k]):
                        self.zona_de[k] = 'zona:' + (z.GetZoneName() or z.GetNetname())

    def camino(self, pa, pb):
        """Camino más corto por pistas de la capa entre dos pads (sin atravesar el centro de otros pads)."""
        s, t = self.nodo_pad[pa], self.nodo_pad[pb]
        dist, prev, h = {s: 0.0}, {}, [(0.0, s)]
        while h:
            d, u = heapq.heappop(h)
            if u == t:
                break
            if d > dist[u] or (u != s and u in self.pad_de):
                continue
            for v, L, _ in self.adj.get(u, []):
                if d + L < dist.get(v, 1e9):
                    dist[v], prev[v] = d + L, u
                    heapq.heappush(h, (d + L, v))
        if t not in dist:
            return None, []
        pts, u = [t], t
        while u != s:
            u = prev[u]
            pts.append(u)
        return dist[t], pts[::-1]

    def vecinos(self, pad):
        """Pads y zonas a los que llega una pista desde este pad sin pasar por el centro de otro pad."""
        s = self.nodo_pad[pad]
        vistos, pila, res = {s}, [s], set()
        while pila:
            u = pila.pop()
            for v, _, _ in self.adj.get(u, []):
                if v in vistos:
                    continue
                vistos.add(v)
                if v in self.pad_de:
                    res.add(self.pad_de[v])
                    continue
                if v in self.zona_de:
                    res.add(self.zona_de[v])
                pila.append(v)
        return sorted(res)

    def largo_red(self, red):
        return sum(math.dist(a, c) for a, c, r, _ in self.segs if r == red)


def area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def lazo_entrada(c, u, chf, vin, pgnd):
    """Lazo VIN–CHF–PGND: pin VIN -> CHF.1 (pista) -> CHF.2 (cuerpo) -> pin PGND (pista) -> pin VIN (encapsulado)."""
    l1, p1 = c.camino(f'{u}.{vin}', f'{chf}.1')
    l2, p2 = c.camino(f'{chf}.2', f'{u}.{pgnd}')
    if p1 == [] or p2 == []:
        return None
    cuerpo = math.dist(p1[-1], p2[0])
    paquete = math.dist(p2[-1], p1[0])
    return dict(pista_vin=l1, cuerpo=cuerpo, pista_pgnd=l2, paquete=paquete,
                total=l1 + cuerpo + l2 + paquete, area=area(p1 + p2))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    b = pcbnew.LoadBoard(path)
    c = Cobre(b)
    for u, chf_a, chf_b, fbr, fbt in (('U6', 'C29', 'C30', 'R29', 'R30'), ('U7', 'C39', 'C40', 'R31', 'R32')):
        print(f'== {u}')
        for pg, chf, vin in (('1', chf_a, '2'), ('11', chf_b, '10')):
            L, _ = c.camino(f'{u}.{pg}', f'{chf}.2')
            print(f'  PGND {u}.{pg} -> {chf}.2 (GND del CHF 220 nF) por F.Cu: '
                  + (f'sí, {L:.2f} mm de pista' if L is not None else 'NO'))
            lz = lazo_entrada(c, u, chf, vin, pg)
            if lz:
                print(f'  lazo VIN {u}.{vin} -> {chf} -> PGND {u}.{pg}: pista VIN {lz["pista_vin"]:.2f} + cuerpo '
                      f'{lz["cuerpo"]:.2f} + pista PGND {lz["pista_pgnd"]:.2f} + paquete {lz["paquete"]:.2f} = '
                      f'{lz["total"]:.2f} mm de perímetro, área {lz["area"]:.2f} mm²')
        fb = c.red_pad[f'{u}.7']
        l1, _ = c.camino(f'{u}.7', f'{fbr}.2')
        l2, _ = c.camino(f'{fbr}.2', f'{fbt}.1')
        print(f'  nodo FB ({fb}): pin 7 -> {fbr}.2 {l1:.2f} mm, {fbr}.2 -> {fbt}.1 {l2:.2f} mm, '
              f'cobre total de la red {c.largo_red(fb):.2f} mm')
        for p in (f'{u}.2', f'{u}.10', f'{chf_a}.1', f'{chf_b}.1'):
            print(f'  vecinos por pista de {p} (24V_PROT): {", ".join(c.vecinos(p))}')


if __name__ == '__main__':
    main()

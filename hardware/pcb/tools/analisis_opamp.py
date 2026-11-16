"""Estabilidad y ancho de banda de las etapas de U3/U9 (TLV9062 original vs TLV9152 propuesto).

Etapas (target.json):
  U3B: seguidor (VSHIFT = DAC_F), ganancia +1.
  U3A: sumador inversor. Entrada IEPE por la cadena R13+R14+R16+R18 = 1.0009 MΩ hacia SUM; realimentación R7+R8 =
       99.8 kΩ, sin condensador en paralelo; + = VSHIFT. Ganancias: −Rf/Rin para IEPE, 1 + Rf/Rin para VSHIFT.
Modelo del op-amp: dos polos. Polo dominante tal que |A| = 1 en GBW; segundo polo f2 ajustado para que el margen de
fase a ganancia unitaria sea el del datasheet. La capacidad del nodo SUM es CIC + CID + 1.5 pF de pistas y pads
(supuesto). Se barre CF (condensador en paralelo con Rf), que hoy no existe en el esquemático.
Uso: python analisis_opamp.py
"""
import cmath
import math

RIN = 390e3 + 365e3 + 191e3 + 54.9e3
RF = 49.9e3 * 2
OPS = {  # nombre: (GBW Hz, PM a G=+1 (°), CID F, CIC F, fuente)
    'TLV9062': (10e6, 55, 2e-12, 4e-12, 'SBOS839N p.13'),
    'TLV9152': (4.5e6, 60, 3e-12, 6e-12, 'SBOS986E p.11-12'),
}
C_PCB = 1.5e-12


def opamp(f, gbw, pm):
    f2 = gbw / math.tan(math.radians(90 - pm))          # segundo polo que da el PM del datasheet a G=+1
    s = 2j * math.pi * f
    return (2 * math.pi * gbw / s) / (1 + s / (2 * math.pi * f2))


def beta(f, csum, cf):
    s = 2j * math.pi * f
    zin = 1 / (1 / RIN + s * csum)                      # cadena de entrada (IEPE es nodo de baja impedancia)
    zf = RF if cf == 0 else 1 / (1 / RF + s * cf)
    return zin / (zin + zf)


def margen(gbw, pm, csum, cf):
    lo, hi = 1e3, 1e9
    for _ in range(200):                                # cruce |A·β| = 1 por bisección logarítmica
        m = math.sqrt(lo * hi)
        if abs(opamp(m, gbw, pm) * beta(m, csum, cf)) > 1:
            lo = m
        else:
            hi = m
    fc = math.sqrt(lo * hi)
    lg = opamp(fc, gbw, pm) * beta(fc, csum, cf)
    return fc, 180 + math.degrees(cmath.phase(lg))


def cl_signal(f, gbw, pm, csum, cf):
    """Ganancia de la señal IEPE -> REST (inversora) en lazo cerrado."""
    s = 2j * math.pi * f
    zf = RF if cf == 0 else 1 / (1 / RF + s * cf)
    ideal = -zf / RIN
    lg = opamp(f, gbw, pm) * beta(f, csum, cf)
    return ideal * lg / (1 + lg)


def resumen():
    print(f'Rin = {RIN / 1e3:.1f} kΩ, Rf = {RF / 1e3:.1f} kΩ, ganancia IEPE = {-RF / RIN:.4f}, '
          f'ganancia VSHIFT = {1 + RF / RIN:.4f}, ganancia de ruido = {1 + RF / RIN:.4f}')
    for name, (gbw, pm, cid, cic, src) in OPS.items():
        csum = cid + cic + C_PCB
        print(f'\n{name} ({src}): GBW {gbw / 1e6:.1f} MHz, PM(G=1) {pm}°, C_SUM = {csum * 1e12:.1f} pF')
        print(f'  seguidor U3B: cruce ~{gbw / 1e6:.1f} MHz, PM {pm}° (datasheet; carga = entrada + de U3A, ~8 pF)')
        for cf in (0, 4.7e-12, 10e-12, 22e-12, 47e-12):
            fc, ph = margen(gbw, pm, csum, cf)
            mags = [abs(cl_signal(f, gbw, pm, csum, cf)) for f in [10 ** (k / 50) for k in range(100, 400)]]
            g0 = abs(cl_signal(100, gbw, pm, csum, cf))
            peak = 20 * math.log10(max(mags) / g0)
            f3 = next((10 ** (k / 50) for k in range(100, 400)
                       if abs(cl_signal(10 ** (k / 50), gbw, pm, csum, cf)) < g0 / math.sqrt(2)), float('nan'))
            print(f'  U3A con CF = {cf * 1e12:4.1f} pF: cruce {fc / 1e3:7.0f} kHz, margen de fase {ph:5.1f}°, '
                  f'pico {peak:5.1f} dB, -3 dB en {f3 / 1e3:7.1f} kHz')


if __name__ == '__main__':
    resumen()

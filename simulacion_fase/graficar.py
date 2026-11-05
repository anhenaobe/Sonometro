#!/usr/bin/env python3
"""Lee los resultados de ngspice (carpeta resultados/) y genera las figuras PNG.

Requiere numpy y matplotlib.  Uso:  python3 graficar.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

R = "resultados"
G = 11.0
COL = {"x": "black", "A": "tab:red", "B": "tab:blue", "C": "tab:green"}
NOM = {
    "A": "A: acople AC 1 µF (fc = 1,6 Hz)",
    "B": "B: acople AC 10 µF (fc = 0,16 Hz)",
    "C": "C: acople DC + amp. diferencial (sin condensador)",
}
plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3})
resumen = []


def cargar(nombre):
    return np.loadtxt(os.path.join(R, nombre), skiprows=1)


def banda(ax):
    ax.axvspan(20, 20e3, color="0.9", zorder=0)


# ---------------------------------------------------------------- 1. fuente
d = cargar("fuente_corriente.txt")
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(d[:, 0], d[:, 1], lw=2, label="RE = 750 Ω (SV 12)")
ax.plot(d[:, 0], d[:, 2], lw=2, label="RE = 470 Ω (RG-50)")
ax.axvspan(8, 14, color="tab:green", alpha=0.12, label="polarización típica IEPE (8–14 V)")
ax.set_xlabel("Tensión en el conector del micrófono [V]")
ax.set_ylabel("Corriente entregada [mA]")
ax.set_ylim(0, 4.5)
ax.set_title("Fuente de corriente TL431 + 2N3906 (alimentación 24 V): corriente constante hasta ≈22 V")
ax.legend(loc="lower left")
fig.tight_layout()
fig.savefig(os.path.join(R, "01_fuente_corriente.png"), dpi=150)
i0 = np.interp(0, d[:, 0], d[:, 2])
i20 = np.interp(20, d[:, 0], d[:, 2])
resumen.append(f"Fuente 470 ohm: {i0:.3f} mA a 0 V, {i20:.3f} mA a 20 V (variacion {100*(i0-i20)/i0:.1f} %)")
i0 = np.interp(0, d[:, 0], d[:, 1])
i20 = np.interp(20, d[:, 0], d[:, 1])
resumen.append(f"Fuente 750 ohm: {i0:.3f} mA a 0 V, {i20:.3f} mA a 20 V (variacion {100*(i0-i20)/i0:.1f} %)")

# ---------------------------------------------------------------- 2. AC
d = cargar("ac_fase.txt")
f = d[:, 0]
ac = {}
for k, (cm, cp) in zip("ABC", [(1, 2), (3, 4), (5, 6)]):
    mag, ph = d[:, cm], d[:, cp]
    tg = -np.gradient(ph, 2 * np.pi * f)  # retardo de grupo [s]
    ac[k] = (mag, ph, tg)

fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
for k in "ABC":
    mag, ph, tg = ac[k]
    axs[0].semilogx(f, 20 * np.log10(mag), color=COL[k], lw=2, label=NOM[k])
    axs[1].semilogx(f, np.degrees(ph), color=COL[k], lw=2)
    axs[2].loglog(f, np.clip(np.abs(tg), 1e-8, None) * 1e3, color=COL[k], lw=2)
for ax in axs:
    banda(ax)
axs[0].set_ylabel("Magnitud [dB]\n(normalizada a G = 11)")
axs[0].set_ylim(-12, 2)
axs[0].legend(loc="lower center", fontsize=10)
axs[1].set_ylabel("Fase [°]")
axs[2].set_ylabel("Retardo de grupo [ms]")
axs[2].set_ylim(1e-4, 1e3)
axs[2].set_xlabel("Frecuencia [Hz]   (zona gris: banda de audio 20 Hz – 20 kHz)")
axs[0].set_title("Respuesta en frecuencia micrófono → ADC: lo que importa no es la fase sino el retardo de grupo")
axs[2].set_xlim(0.1, 2e5)
fig.tight_layout()
fig.savefig(os.path.join(R, "02_respuesta_frecuencia.png"), dpi=150)

resumen.append("")
resumen.append("Frecuencia | variante | |H| [dB] | fase [grados] | retardo de grupo [us]")
for fx in [20, 50, 85, 100, 300, 1000, 10000, 20000]:
    for k in "ABC":
        mag, ph, tg = ac[k]
        resumen.append(
            f"{fx:>7} Hz | {k} | {20*np.log10(np.interp(fx, f, mag)):7.3f} | "
            f"{np.degrees(np.interp(fx, f, ph)):8.3f} | {np.interp(fx, f, tg)*1e6:10.2f}"
        )

# ---------------------------------------------------------------- 3. barrido
d = cargar("tran_barrido.txt")
t, x = d[:, 0], d[:, 1]
ys = {k: (d[:, i] - d[0, i]) / G for k, i in zip("ABC", (2, 3, 4))}
T, f0, K = 1.0, 20.0, 1000.0
finst = f0 * K ** (t / T)


def t_de_f(fx):
    return T * np.log(fx / f0) / np.log(K)


tau1k = {k: np.interp(1000, f, ac[k][2]) for k in "ABC"}  # retardo "plano" de la banda media

fig, axs = plt.subplots(2, 2, figsize=(13, 8))
for ax, fx in zip(axs.flat, [25, 100, 1000, 10000]):
    tc = t_de_f(fx)
    per = 1 / fx
    m = (t > tc - 1.5 * per) & (t < tc + 1.5 * per)
    ax.plot((t[m] - tc) * 1e3, x[m] * 1e3, color=COL["x"], lw=3.5, alpha=0.35, label="entrada (micrófono)")
    for k in "ABC":
        ax.plot((t[m] - tc) * 1e3, ys[k][m] * 1e3, color=COL[k], lw=1.4, label=NOM[k])
    ax.set_title(f"Alrededor de {fx} Hz")
    ax.set_xlabel("t [ms]")
    ax.set_ylabel("mV (referido a la entrada)")
axs[0, 0].legend(fontsize=8, loc="lower left")
fig.suptitle("Barrido 20 Hz → 20 kHz en 1 s: entrada vs. salida (÷11). Las curvas casi se superponen.")
fig.tight_layout()
fig.savefig(os.path.join(R, "03_barrido_zoom.png"), dpi=150)

# error relativo por bandas de frecuencia, sin y con compensar un retardo constante
fb = np.logspace(np.log10(30), np.log10(18000), 45)  # desde 30 Hz: evita el arranque del barrido
fig, ax = plt.subplots(figsize=(12, 6))
resumen.append("")
resumen.append("Barrido: error rms relativo (salida/11 - entrada) por banda, con retardo constante compensado")
for k in "ABC":
    ycomp = np.interp(t + tau1k[k], t, ys[k])  # quita un retardo PURO (no deforma)
    e_raw, e_cmp = [], []
    for fx in fb:
        tc = t_de_f(fx)
        m = (t > tc - 1 / fx) & (t < tc + 1 / fx)
        rx = np.sqrt(np.mean(x[m] ** 2))
        e_raw.append(np.sqrt(np.mean((ys[k][m] - x[m]) ** 2)) / rx * 100)
        e_cmp.append(np.sqrt(np.mean((ycomp[m] - x[m]) ** 2)) / rx * 100)
    ax.loglog(fb, e_raw, color=COL[k], lw=1, ls=":")
    ax.loglog(fb, e_cmp, color=COL[k], lw=2.2, label=f"{NOM[k]}  (retardo puro compensado: {tau1k[k]*1e6:.1f} µs)")
    for fx, ec in zip(fb, e_cmp):
        pass
    resumen.append(
        f"  {k}: 30 Hz {np.interp(30, fb, e_cmp):.2f} %, 100 Hz {np.interp(100, fb, e_cmp):.2f} %, "
        f"1 kHz {np.interp(1000, fb, e_cmp):.2f} %, 10 kHz {np.interp(10000, fb, e_cmp):.2f} % "
        f"(retardo compensado {tau1k[k]*1e6:.1f} us)"
    )
ax.set_xlabel("Frecuencia instantánea del barrido [Hz]")
ax.set_ylabel("Error rms relativo [%]")
ax.set_ylim(0.01, 200)
ax.set_title("Diferencia entre la forma de onda de salida y la de entrada\n"
             "(línea continua: tras quitar un retardo constante de ~10 µs; punteada: sin quitarlo)")
ax.legend(fontsize=9, loc="upper center")
fig.tight_layout()
fig.savefig(os.path.join(R, "04_barrido_error.png"), dpi=150)

# ---------------------------------------------------------------- 4. voz
d = cargar("tran_voz.txt")
t, x = d[:, 0], d[:, 1]
ys = {k: (d[:, i] - d[0, i]) / G for k, i in zip("ABC", (2, 3, 4))}
fig, axs = plt.subplots(3, 1, figsize=(13, 10))
axs[0].plot(t * 1e3, x * 1e3, color=COL["x"], lw=2.5, alpha=0.4, label="entrada (micrófono)")
axs[0].plot(t * 1e3, ys["A"] * 1e3, color=COL["A"], lw=0.8, label=NOM["A"])
axs[0].set_title("Voz con cambios de tono muy rápidos (120→260 Hz en 30 ms, 260→100 Hz en 20 ms)")
axs[0].legend(fontsize=9, loc="lower right")
t0, t1 = (0.095, 0.140) if t[-1] > 0.3 else (t[-1] * 0.4, t[-1] * 0.4 + 0.045)
m = (t > t0) & (t < t1)
axs[1].plot(t[m] * 1e3, x[m] * 1e3, color=COL["x"], lw=3.5, alpha=0.35, label="entrada")
for k in "ABC":
    axs[1].plot(t[m] * 1e3, ys[k][m] * 1e3, color=COL[k], lw=1.2, label=NOM[k])
axs[1].set_title("Zoom durante el salto de tono")
axs[1].legend(fontsize=8, loc="lower left", ncol=2)
resumen.append("")
resumen.append("Voz: error rms relativo (retardo constante compensado)")
for k in "ABC":
    ycomp = np.interp(t + tau1k[k], t, ys[k])
    e = ycomp - x
    axs[2].plot(t * 1e3, e * 1e3, color=COL[k], lw=1, label=NOM[k])
    resumen.append(f"  {k}: {np.sqrt(np.mean(e**2))/np.sqrt(np.mean(x**2))*100:.2f} %")
axs[2].set_title("Error = salida/11 − entrada (tras quitar el retardo constante de ~10 µs)")
axs[2].legend(fontsize=8, loc="upper right")
for ax in axs:
    ax.set_xlabel("t [ms]")
    ax.set_ylabel("mV")
fig.tight_layout()
fig.savefig(os.path.join(R, "05_voz.png"), dpi=150)

with open(os.path.join(R, "resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(resumen) + "\n")
print("\n".join(resumen))
print("\nFiguras guardadas en resultados/*.png")

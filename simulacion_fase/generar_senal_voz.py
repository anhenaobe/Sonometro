#!/usr/bin/env python3
"""Genera senal_voz.inc (fuente PWL para ngspice) con una voz.

Uso:
  python3 generar_senal_voz.py                       # voz sintetica (por defecto)
  python3 generar_senal_voz.py mi_voz.wav            # grabacion real (WAV PCM 16 bits)
  python3 generar_senal_voz.py mi_voz.wav 0.5 1.0    # desde 0,5 s, duracion 1,0 s

La amplitud se normaliza a 50 mV pico (~94 dB SPL con un microfono de 50 mV/Pa).
Solo requiere numpy (y el modulo estandar 'wave').
"""
import sys
import wave

import numpy as np

AMPLITUD = 0.05  # V pico


def voz_sintetica(fs=50_000, dur=0.35):
    """Vocal /a/ cuyo tono salta rapidamente: 120 -> 260 Hz en 30 ms y 260 -> 100 Hz en 20 ms."""
    t = np.arange(int(fs * dur)) / fs
    f0 = np.interp(t, [0.0, 0.10, 0.13, 0.20, 0.22, dur], [120, 120, 260, 260, 100, 100])
    f0 = f0 * (1 + 0.02 * np.sin(2 * np.pi * 6 * t))  # vibrato leve
    fase = 2 * np.pi * np.cumsum(f0) / fs
    formantes = [(730, 130, 1.0), (1090, 160, 0.5), (2440, 250, 0.25)]  # vocal /a/
    x = np.zeros_like(t)
    for k in range(1, 31):
        fk = k * f0
        env = 0.15 + sum(g * np.exp(-0.5 * ((fk - F) / B) ** 2) for F, B, g in formantes)
        x += env / k * np.sin(k * fase) * (fk < 8000)
    rampa = np.clip(np.minimum(t, dur - t) / 0.01, 0, 1)  # entrada/salida suaves de 10 ms
    return fs, x * rampa


def leer_wav(ruta, inicio=0.0, dur=1.0):
    with wave.open(ruta, "rb") as w:
        fs, nch, ancho = w.getframerate(), w.getnchannels(), w.getsampwidth()
        if ancho != 2:
            sys.exit("El WAV debe ser PCM de 16 bits (exportelo asi desde Audacity).")
        datos = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float)
    datos = datos.reshape(-1, nch).mean(axis=1)
    a, b = int(inicio * fs), int((inicio + dur) * fs)
    x = datos[a:b]
    if len(x) == 0:
        sys.exit("Segmento vacio: revise inicio/duracion.")
    return fs, x - x.mean()


def main():
    if len(sys.argv) > 1:
        inicio = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
        dur = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        fs, x = leer_wav(sys.argv[1], inicio, dur)
        origen = f"grabacion {sys.argv[1]} ({inicio} s + {dur} s)"
    else:
        fs, x = voz_sintetica()
        origen = "voz sintetica (vocal /a/ con saltos de tono rapidos)"
    x = AMPLITUD * x / np.max(np.abs(x))
    t = np.arange(len(x)) / fs
    with open("senal_voz.inc", "w", encoding="ascii") as f:
        f.write(f"* senal_voz.inc - generado por generar_senal_voz.py: {origen}\n")
        f.write(f"* fs = {fs} Hz, {len(x)} muestras, {AMPLITUD*1000:.0f} mV pico\n")
        f.write("Vsig sig 0 PWL(\n")
        for ti, xi in zip(t, x):
            f.write(f"+ {ti:.7e} {xi:.6e}\n")
        f.write("+ )\n")
        f.write(f".tran {1/fs:.6e} {t[-1]:.6f} 0 {1/fs:.6e}\n")
    print(f"senal_voz.inc: {origen}, {len(x)} muestras a {fs} Hz")


if __name__ == "__main__":
    main()

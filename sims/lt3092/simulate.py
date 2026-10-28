"""Simulaciones LTspice del LT3092 como fuente de corriente IEPE para el ROGA RG-50.

Ejecuta los cinco circuitos de ``circuits/`` mediante spicelib (LTspice bajo Wine),
guarda las gráficas en ``figures/`` y los indicadores en ``results.json``.

Uso, desde la raíz del repositorio:
    .venv/bin/python sims/lt3092/simulate.py
"""

import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from spicelib import RawRead, SimRunner, SpiceEditor  # noqa: E402
from spicelib.simulators.ltspice_simulator import LTspice  # noqa: E402

os.environ.setdefault("WINEDEBUG", "-all")

HERE = Path(__file__).resolve().parent
CIRCUITS = HERE / "circuits"
RUNS = HERE / "runs"
FIGURES = HERE / "figures"
TIMEOUT_S = 300

# Programación del LT3092: I_OUT = 10 µA * RSET / ROUT + 10 µA (valores E96).
RSET = 20e3
ROUT_BY_CURRENT = {"2,4 mA": 84.5, "2,8 mA": 71.5, "4,0 mA": 49.9}
REFERENCE_CURRENT = "2,8 mA"
V_SUPPLY = 24.0

# Micrófono RG-50 (ficha ROGA). Sensibilidad: 55,6 mV/Pa según los datos de la
# unidad del repositorio y 51,2 mV/Pa en el certificado de ejemplo; se usa la
# mayor para el pico (peor caso de compliance) y la menor para el piso de ruido.
# La ficha da 130 dB como nivel de pico ("Max. Peak sound pressure level"), por eso
# no lleva √2; los 32 dB de ruido sí son rms.
P_REF = 20e-6
SENS_HIGH = 0.0556
SENS_LOW = 0.0512
V_BIAS = 12.5
SPL_PEAK_DB = 130
SPL_NOISE_DB = 32
V_PEAK = P_REF * 10 ** (SPL_PEAK_DB / 20) * SENS_HIGH
V_NOISE_FLOOR = P_REF * 10 ** (SPL_NOISE_DB / 20) * SENS_LOW

REGULATION_TOL = 0.01
AUDIO_BAND_HZ = (20.0, 20e3)
RIPPLE_V = 0.05
RIPPLE_HZ = 120.0
CSET_VALUES = {"sin CSET": 1e-15, "10 nF": 10e-9, "100 nF": 100e-9, "1 µF": 1e-6}
SETTLED_V = 0.1
SIGNAL_START_S = 1e-3

RUNNER = SimRunner(output_folder=str(RUNS), simulator=LTspice)


def simulate(netlist: str, run_name: str, **params) -> RawRead:
    for stale in RUNS.glob(f"{run_name}.*"):
        stale.unlink()
    editor = SpiceEditor(str(CIRCUITS / netlist))
    editor.set_parameters(**params)
    _, log = RUNNER.run_now(editor, run_filename=f"{run_name}.net", timeout=TIMEOUT_S)
    # Con .tran LTspice escribe también <nombre>.op.raw; el análisis pedido está en <nombre>.raw.
    raw = RUNS / f"{run_name}.raw"
    if log is None or not raw.exists():
        raise RuntimeError(f"LTspice no generó resultados para {run_name}; revisar {RUNS}")
    return RawRead(str(raw))


def wave(raw: RawRead, trace: str) -> np.ndarray:
    return np.asarray(raw.get_trace(trace).get_wave())


def axis(raw: RawRead) -> np.ndarray:
    # get_axis() de spicelib falla si aún no se ha cargado ninguna traza; el eje
    # (time/frequency) es siempre la primera traza del archivo.
    return np.real(wave(raw, raw.get_trace_names()[0]))


def min_regulated_supply(vin: np.ndarray, current: np.ndarray) -> float:
    """Menor tensión desde la cual la corriente queda dentro de la tolerancia."""
    nominal = current[-1]
    out_of_tol = np.nonzero(current < (1 - REGULATION_TOL) * nominal)[0]
    return float(vin[out_of_tol[-1] + 1]) if out_of_tol.size else float(vin[0])


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES / name, dpi=150)
    plt.close(fig)


def run_compliance() -> dict:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    results = {}
    sensor_cases = {"bias 12,5 V": V_BIAS, f"pico {V_BIAS + V_PEAK:.2f} V": V_BIAS + V_PEAK}
    for label, rout in ROUT_BY_CURRENT.items():
        for case, vsens in sensor_cases.items():
            raw = simulate("01_compliance_dc.net", f"01_{rout}_{vsens:.2f}", ROUT=rout, VSENS=vsens)
            vin, current = wave(raw, "V(vin)"), wave(raw, "I(Rmic)")
            vin_min = min_regulated_supply(vin, current)
            node = float(np.interp(vin_min, vin, wave(raw, "V(iepe)")))
            out = float(np.interp(vin_min, vin, wave(raw, "V(out)")))
            results[f"{label} / {case}"] = {
                "corriente_mA": round(float(current[-1]) * 1e3, 4),
                "vin_min_V": round(vin_min, 2),
                "caida_IN_a_nodo_sensor_V": round(vin_min - node, 2),
                "caida_IN_a_OUT_del_integrado_V": round(vin_min - out, 2),
            }
            style = "-" if vsens == V_BIAS else "--"
            ax.plot(vin, current * 1e3, style, label=f"{label}, {case}")
    open_raw = simulate("01_compliance_dc.net", "01_abierto", ROUT=ROUT_BY_CURRENT[REFERENCE_CURRENT], RMIC=1e9, VSENS=0)
    v_open = float(np.interp(V_SUPPLY, wave(open_raw, "V(vin)"), wave(open_raw, "V(iepe)")))
    results["circuito_abierto_V_iepe_a_24V"] = round(v_open, 2)
    ax.axvline(V_SUPPLY, color="gray", lw=0.8, ls=":")
    ax.set(xlabel="Alimentación VIN [V]", ylabel="Corriente al sensor [mA]",
           title="Compliance del LT3092 (RSET = 20 kΩ)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, ncol=2)
    save(fig, "01_compliance.png")
    return results


def run_signal(vin_low: float) -> dict:
    fig, (ax_v, ax_i) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    results = {}
    cases = [(label, rout, V_SUPPLY) for label, rout in ROUT_BY_CURRENT.items()]
    cases.append((REFERENCE_CURRENT, ROUT_BY_CURRENT[REFERENCE_CURRENT], vin_low))
    for label, rout, vin in cases:
        raw = simulate("02_senal_tran.net", f"02_{rout}_{vin}", ROUT=rout, VIN=vin, VPK=V_PEAK)
        settled = axis(raw) >= SIGNAL_START_S
        t, current = axis(raw)[settled] * 1e3, wave(raw, "I(Rmic)")[settled]
        node = wave(raw, "V(iepe)")[settled]
        mean = float(np.mean(current))
        name = f"{label}, VIN = {vin:g} V"
        results[name] = {
            "corriente_media_mA": round(mean * 1e3, 4),
            "variacion_pico_pico_pct": round(float(np.ptp(current) / mean * 100), 3),
            "corriente_minima_mA": round(float(current.min()) * 1e3, 4),
        }
        ax_v.plot(t, node, label=name)
        ax_i.plot(t, current * 1e3, label=name)
    ax_v.set(ylabel="V nodo IEPE [V]", title=f"Tono de 1 kHz, {V_PEAK:.2f} V de pico (130 dB SPL)")
    ax_i.set(xlabel="Tiempo [ms]", ylabel="Corriente [mA]")
    for ax in (ax_v, ax_i):
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    save(fig, "02_senal.png")
    return results


def run_supply_ripple() -> dict:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    results = {}
    for label, rout in ROUT_BY_CURRENT.items():
        raw = simulate("03_rizado_ac.net", f"03_{rout}", ROUT=rout)
        freq, gain = axis(raw), np.abs(wave(raw, "V(iepe)"))
        gain_ripple = float(np.interp(RIPPLE_HZ, freq, gain))
        gain_1k = float(np.interp(1e3, freq, gain))
        results[label] = {
            "atenuacion_120Hz_dB": round(20 * np.log10(gain_ripple), 1),
            "rizado_en_senal_uV": round(RIPPLE_V * gain_ripple * 1e6, 3),
            "impedancia_salida_1kHz_Mohm": round(50 * (1 / gain_1k - 1) / 1e6, 2),
        }
        ax.semilogx(freq, 20 * np.log10(gain), label=label)
    ax.set(xlabel="Frecuencia [Hz]", ylabel="V(iepe) / VIN [dB]",
           title="Rizado de la alimentación que llega a la señal")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    save(fig, "03_rizado.png")
    return results


def run_noise() -> dict:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    results = {}
    low, high = AUDIO_BAND_HZ
    for label, cset in CSET_VALUES.items():
        raw = simulate("04_ruido.net", f"04_{label.replace(' ', '_')}",
                       ROUT=ROUT_BY_CURRENT[REFERENCE_CURRENT], CSET=cset)
        freq, density = axis(raw), np.abs(wave(raw, "V(onoise)"))
        band = (freq >= low) & (freq <= high)
        rms = float(np.sqrt(np.trapezoid(density[band] ** 2, freq[band])))
        results[label] = {
            "ruido_20Hz_20kHz_uV": round(rms * 1e6, 3),
            "fraccion_del_piso_del_microfono_pct": round(rms / V_NOISE_FLOOR * 100, 2),
        }
        ax.loglog(freq, density * 1e9, label=f"{label}: {rms * 1e6:.2f} µV rms")
    ax.set(xlabel="Frecuencia [Hz]", ylabel="Densidad de ruido [nV/√Hz]",
           title=f"Ruido de la fuente en el nodo IEPE ({REFERENCE_CURRENT})")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    save(fig, "04_ruido.png")
    return results


def run_startup() -> dict:
    raw = simulate("05_arranque.net", "05_arranque", ROUT=ROUT_BY_CURRENT[REFERENCE_CURRENT])
    t, v_node, v_adc = axis(raw), wave(raw, "V(iepe)"), wave(raw, "V(acout)")
    unsettled = np.nonzero(np.abs(v_adc) > SETTLED_V)[0]
    settle_time = float(t[unsettled[-1]]) if unsettled.size else 0.0
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(t * 1e3, v_node, label="Nodo IEPE (sensor)")
    ax.plot(t * 1e3, v_adc, label="Tras acoplamiento AC (hacia el ADC)")
    ax.set(xlabel="Tiempo [ms]", ylabel="Tensión [V]",
           title="Arranque: CAC = 1 µF, RRET = 100 kΩ (fc ≈ 1,6 Hz), sin protección")
    ax.grid(alpha=0.3)
    ax.legend()
    save(fig, "05_arranque.png")
    return {
        "pico_hacia_ADC_V": round(float(v_adc.max()), 2),
        "tiempo_hasta_menos_de_0.1V_ms": round(settle_time * 1e3, 1),
    }


def main() -> None:
    RUNS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    compliance = run_compliance()
    worst_vin = max(v["vin_min_V"] for k, v in compliance.items() if isinstance(v, dict))
    results = {
        "parametros": {
            "RSET_ohm": RSET,
            "ROUT_ohm": ROUT_BY_CURRENT,
            "VIN_V": V_SUPPLY,
            "V_bias_V": V_BIAS,
            "V_pico_130dB_V": round(V_PEAK, 3),
            "piso_ruido_microfono_uV": round(V_NOISE_FLOOR * 1e6, 2),
        },
        "01_compliance": compliance,
        "02_senal": run_signal(vin_low=round(worst_vin - 1.0)),
        "03_rizado": run_supply_ripple(),
        "04_ruido": run_noise(),
        "05_arranque": run_startup(),
    }
    (HERE / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

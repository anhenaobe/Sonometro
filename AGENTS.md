# AGENTS.md — Sonómetro IEPE (single-channel sound level meter front end)

Read this file before doing anything in this repository. It is the source of truth for what the
project is, how the owner wants to work, and which facts have already been researched.
It applies to every coding agent (Claude Code, Codex, etc.).

Last updated: 2026-11-04.

---

## 1. What this project is

A university lab project (Colombia, Universidad Nacional — Manizales area) to build the **analog front end
of a single-channel sound level meter** for two IEPE measurement microphones:

1. **Power** two different IEPE microphones with constant-current sources and let the user **select** one.
2. **Extract** the acoustic signal from the IEPE line (AC voltage riding on a DC bias).
3. **Show the waveform** on the lab oscilloscope and on a microcontroller ADC plotted on a PC.

Scope agreed with the owner: **show the waveform**. dB SPL / A-weighting / Leq is an *optional*
extension only.

**Hard deadline: 2026-11-25.** Proposal to the professor first; build only after approval.

### Constraints (do not violate without asking)
- **No custom PCB.** Breadboard prototype → Manhattan / dead-bug on copper-clad board if noisy.
  The owner strongly dislikes point-to-point perfboard soldering.
- **Parts must be bought locally** in Manizales (Electrónicos Caldas) or, as backup, Didácticas
  Electrónicas (Medellín). Prefer **through-hole** (DIP, TO-92). SMD only with an adapter board.
- Lab equipment available: oscilloscope, bench supply, multimeter, function generator, BNC cables.
- The group has very little time and motivation; the professor is very demanding. Favour the
  **simplest design that clearly works and is easy to defend**, with sources from TI / ADI /
  sensor manufacturers.

---

## 2. How the owner wants to work

- **Language:** talk to the owner in English or Spanish (the owner usually writes in English). **Deliverable documents
  are in Spanish.**
- **Documents are written in LaTeX** and compiled locally with **Tectonic** (see §8).
- **Research before proposing**, cite primary sources (TI, Analog Devices, PCB Piezotronics,
  Svantek, ROGA, GRAS, B&K/HBK datasheets and app notes; GitHub repos when useful).
- **Label confidence honestly.** Distinguish *verified from the source document* vs *from search
  snippets* vs *unverified / estimated*. Never present a guess as a fact. Unverified items live in
  §7 until the owner confirms them.
- **Legacy repo content is not authoritative.** Everything in the repo before 2026-11-04 (README,
  `docs/`, `hardware/`, `sims/` LT3092 LTspice work, `firmware/`, `software/`, `tests/`) came from an
  earlier attempt. The owner asked to restart from scratch: do **not** rely on or extend it unless
  the owner explicitly asks. The current work lives in `propuesta/` and this file.
- **Git:**
  - **Never commit to `main`.** The owner's personal workspace branch is `workspace/voxter`
    (created from `docs/lt3092-simulacion-2026-10-27`, which is already merged into main).
  - Commit author email: `jevargaso@unal.edu.co` (already set in the repo's git config; GitHub
    account `Voxtercin`, a collaborator on `anhenaobe/Sonometro`).
  - Commit when asked. **Ask before pushing**, opening PRs, or deleting/renaming remote branches
    (the remote belongs to `anhenaobe`; teammates use it).
  - Conventional-commit style messages (`docs: ...`, `feat: ...`).

---

## 3. The microphones (researched 2026-11-04)

### 3.1 SVANTEK "SV 12 No. 18210" (salvaged, must be tested)
- **Identification (medium-high confidence):** a Svantek **½" IEPE microphone preamplifier**
  (SV 12 / SV 12L), *not* a complete microphone. "18210" is the serial number. A prepolarized ½"
  capsule (e.g. MK 255 50 mV/Pa, ACO 7052E 35 mV/Pa, 7052S 20 mV/Pa) screws on top; **without a
  capsule it will not respond to sound.**
- How to tell: SV 12/12L has a **TNC plug** with locking thread. If it has a **7-pin LEMO**, it is
  an SV 17 / SV 18 — **not IEPE** — stop and re-plan.
- Used with SVAN 94x, SVAN 953, SVAN 958/958A, SVAN 977 meters.
- Supply: "IEPE type – 1.5 mA @ 30 V" (SVAN 977W App. C, SV 977D manual); SVAN 958A supplies
  **2.5 mA @ 28 V**; meter input must stay 0…+28 V. Max current **not published**.
- DC bias voltage: **not published** → measure it.
- Gain ≈ −0.7 dB (with 18 pF capsule/dummy ST 02). Output swing ≥ 10.8 V peak at 28–30 V supply.
- TNC pinout: centre = signal + IEPE supply, shell = ground.
- **Never** apply 200 V polarization or 48 V phantom.
- Sources:
  - https://svantek.com/wp-content/uploads/2021/05/svan_977w_appendix_c_2017-03-06.pdf
  - https://svantek.com/wp-content/uploads/2023/01/SVAN958A-Man.EN_v.1.02_2023-03-03.pdf
  - https://svantek.com/wp-content/uploads/2022/06/SV-977D_Man_EN_v.1.00_2022-11-23.pdf
  - https://svantek.com/wp-content/uploads/2023/01/SV971A-Man.EN_v.1.03_2024-05-28.pdf (SV 18A, not IEPE)

### 3.2 ROGA Instruments RG-50 (the owner says it "looks like" one; BNC, external housing)
- ¼" prepolarized electret with integrated IEPE, class 1. **Medium confidence** on exact model:
  RG-50, MI17, MI19 look almost identical — read the engraving.
- Supply current **2–20 mA** (current datasheet); product page / older versions say **2–6 mA**.
  Supply 18–30 V. **Output bias 12.5 V.** Output impedance < 50 Ω.
- Sensitivity **50 mV/Pa** nominal. 5 Hz–4 kHz ±0.5 dB, up to 30 kHz ±1.5 dB.
  Max 130 dB peak (≈ 3.2 V peak). Noise ≈ 27 dB(A).
- Connector **BNC female**. (An XLR/48 V phantom variant exists — that one is NOT IEPE.)
- Sources: https://roga-instruments.com/downloads/PDF/RG-50-EN.pdf ,
  https://roga-instruments.com/array-mic-rg50/ , https://roga-instruments.com/1-4-inch-mic/

---

## 4. IEPE essentials (sourced)

- Two-wire scheme: one coax carries a **constant current** (2–20 mA, typ. 4 mA) from an
  18–30 V supply; the sensor sets a **DC bias** (≈ 8–14 V) and the **signal is an AC voltage on top
  of that bias**: `v_node(t) = V_B + S·p(t)`. Remove the DC with a coupling capacitor.
  (PCB G0001E, HBK TN119, GRAS FAQ.)
- Current-source accuracy is **not critical**; compliance, noise and regulation matter
  (TI TIDA-010249 / TIDUF13).
- Cable limit (PCB): `f_max = 1e9 / (2π·C[pF]·V_p/(I_c[mA] − 1))`. Bench cables are no issue.
- One current value works for both mics if inside both ranges; **2.5 mA** is documented by both
  manufacturers. **Each sensor needs its own source — never parallel two IEPE sensors.**
- Fault check by DC bias: ≈ 0 V = short; ≈ compliance = open/dead; 7–14 V = OK.
- Safety rules (PCB): never > 30 V or > 20 mA on the sensor; **never apply voltage without
  current limiting**; never 48 V phantom.
- Key references:
  - PCB General Signal Conditioning Guide: https://www.pcb.com/techsupport/docs/pcb/PCB-G0001E-0303.pdf
  - PCB/IMI long cables: https://www.pcb.com/contentstore/mktgcontent/IMI_Downloads/TipfromTech-DrivingLongCableLengths.pdf
  - HBK TN119: https://www.hbm.com/fileadmin/mediapool/files/technical-articles-technotes-white-papers/2021/TN119_HBK_IEPE-Sensing.pdf
  - TI TIDA-010249 (TIDUF13): https://www.ti.com/lit/pdf/TIDUF13
  - TI TIDA-01471 (TIDUD62): https://www.ti.com/lit/pdf/TIDUD62
  - TI SLYT768 high-side current sources: https://www.ti.com/lit/pdf/SLYT768
  - ADI CN0540 / CN0582 (LT3092-based, read only via search extracts): https://www.analog.com/CN0540 , https://www.analog.com/CN0582
  - Endevco LM317 4 mA source: https://endevco.com/our-resources/ask-the-experts/integrating-isotron-iepe-accelerometers-with-your-own-current-source
  - ESP Project 134 (discrete 4 mA mic supply): https://www.sound-au.com/project134.htm

---

## 5. Current design (as in the proposal, `propuesta/propuesta_sonometro.tex`)

**Power:** 24 V (bench supply limited to 30–50 mA, or 2×12 V batteries). 1N4007 series diode,
47 Ω + 100 µF/35 V + 100 nF filter.

**Current source, one per mic — TL431 + PNP (chosen):**
- TL431 with REF tied to cathode, cathode at +24 V, anode at PNP base; R_Z = 10 kΩ base→GND
  (I_Z ≈ 2.15 mA ≥ 1 mA). PNP = 2N3906 / BC557. R_E from +24 V to emitter.
- `I0 ≈ (2.495 − 0.65) / R_E` → **R_E = 750 Ω → 2.46 mA (SV 12)**, **R_E = 470 Ω → 3.93 mA (RG-50)**.
- Compliance ≈ 24 − 1.85 − 0.3 ≈ 21.9 V. No capacitor directly across the TL431.
- Why not the alternatives:
  - **LM317:** needs 3.5–10 mA minimum load, so it is unusable at 2.5 mA.
  - **LM334:** not sold locally.
  - **LT3092:** SMD only.
  - **JFET:** needs per-part trimming.
  - **CRD:** not available.

**Mic selection (option A, recommended):** both channels always powered; an SPDT toggle selects
*after* each channel's C1/R_B (no switching transient). Option B (single source + DPDT switching
R_E and output) is documented as the alternative.

**Signal chain to ADC:**
- C1 = 1 µF polyester ≥ 63 V.
- R_B = 100 kΩ to V_MID = 1.65 V, giving f_c = 1.6 Hz and τ = 0.1 s.
- R_S = 4.7 kΩ + 2×1N4148 clamps to 3.3 V / GND.
- Non-inverting gain G = 11 (R_F = 10 kΩ, R_G = 1 kΩ to V_MID, C_F = 470 pF, which puts the pole at 34 kHz).
- Output R_O = 1 kΩ + C_O = 4.7 nF (34 kHz anti-alias) to the ADC.
- V_MID: 10 k/10 k divider + 10 µF, buffered by the second op-amp half.
- Op-amp: **MCP6002 at 3.3 V** (Didácticas) or **LM358 at 5 V** (local).
- TL072/NE5532 are not suitable for a 0–3.3 V ADC drive.
- With 50 mV/Pa the chain clips near 100 dB SPL; 94 dB gives 0.78 V peak.

**Viewing:**
- **Milestone 1:** oscilloscope on the IEPE node, AC coupling, 5–20 mV/div, 200 µs/div, FFT for 60 Hz hum.
- **Milestone 2:** microcontroller burst capture, then serial, then Python (numpy/matplotlib).
  - **Raspberry Pi Pico** (12-bit, 500 kS/s, ENOB ≈ 8.7, `pico-examples/adc/dma_capture`) is preferred.
  - **ESP32** works too: use continuous mode on ADC1, keep the input in the usable ≈ 0.15–2.45 V window (V_MID ≈ 1.3 V).
  - Serial at 115200 baud is too slow to stream, so capture to RAM first, then send.

**Construction / noise:**
- Breadboard first, inside a grounded metal tin, BNCs on the tin.
- Star ground at the BNC shields; batteries or a floating supply.
- The main risk is 60 Hz hum from ground loops, not breadboard capacitance (≈ 2 pF between rows).
- If too noisy, use Manhattan construction on copper-clad board.

**Timeline:**

| Dates | Step |
|---|---|
| Nov 4–7 | Proposal approval |
| Nov 7–10 | Buy parts |
| Nov 10–13 | Current sources + scope (Milestone 1) |
| Nov 13–18 | ADC chain + MCU (Milestone 2) |
| Nov 18–21 | Copper-clad / enclosure, noise |
| Nov 21–24 | Report |
| **Nov 25** | **Delivery** |

---

## 6. Parts availability (checked online 2026-11-04 — stock changes, call first)

**Electrónicos Caldas** (Manizales): https://www.electronicoscaldas.com/es/ — tel. 321 896 5106.
- **Its site search returns nothing — browse by category.** Pickup in person ("Recoger personalmente").
- **The website appeared compromised** (injected spam links on every page): don't click strange
  links; pay at pickup.
- In stock:
  - TL072/TL074/TL082/TL084, NE5532, LM358, LM324, LF353, OP07
  - LM317 (TO-220 / LM317L SMD), **TL431**
  - JFETs J111/J112/J310/MPF102/BF256/2N5485
  - Polyester caps 100 pF–1 µF, copper-clad "baquelita" boards, universal boards
  - 12 V adapters, 9 V batteries, plastic boxes
  - ESP32 DevKitC (27,300 COP), Arduino Uno/Nano
- **Not listed:** LM334, MCP6002/OPA2134, any BNC/TNC/LEMO, SOIC-DIP adapters, 24 V adapter, metal
  boxes, Raspberry Pi Pico, STM32 Blue/Black Pill.

**Didácticas Electrónicas** (Medellín, backup): https://didacticaselectronicas.com/ (search `/shop?search=TERM`).

| Item | Price (COP) |
|---|---|
| Raspberry Pi Pico | 19,897 |
| MCP6002-E/P | 3,142 |
| Chassis BNC female CON-035A | 2,028 |
| BNC male–TNC female adapter | 3,928 |
| SMD-to-DIP 8-pin board | 595 |
| Metal box 150×70×200 | 69,184 |
| 24 V 5 A adapter | 82,415 |
| LM317T | 1,676 |

**Sigma Electrónica** (Bogotá): TL072/TL074/TL082 in stock. Electronilab, Vistronica, MercadoLibre: not verified.

Estimated BOM ≈ 43,000 COP (lab supplies the scope and the 24 V supply).

---

## 7. NOT yet verified — owner will confirm later (keep this list updated)

- [ ] SV 12 connector is TNC (→ IEPE) and not LEMO 7-pin.
- [ ] Whether the SV 12 has a capsule mounted, and which one (sensitivity).
- [ ] SV 12 vs SV 12L are electrically identical; SV 12 DC bias and max current (measure bias at 2.5 mA).
- [ ] The ROGA mic is really an RG-50 (vs MI17/MI19) and which generation (2–20 mA vs 2–6 mA).
- [ ] PNP 2N3906/BC557 availability at Electrónicos Caldas; 1 µF polyester voltage rating.
- [ ] Delivery time from Didácticas (Medellín) to Manizales.
- [ ] Exact professor requirements (only waveform, or also dB SPL?).
- [ ] Lab bench supply can deliver 24 V with a floating output.
- [ ] ADI CN0540/CN0582/LT3092 and ADI MT-100 details (only seen via search extracts; analog.com timed out).
- [ ] LM334 1–5 mA error spec (~8 % max) and LM317 min-load figure taken from secondary datasheet copies.
- [ ] Noise/self-heating figures, MCP6002 and filter values are engineering estimates, not sourced.

---

## 8. Tooling on the owner's machine (Windows 11)

- **Tectonic 0.17.0** installed at `%LOCALAPPDATA%\Programs\tectonic\tectonic.exe` (on user PATH).
  Compile: `tectonic propuesta/propuesta_sonometro.tex` (XeTeX engine, downloads packages on demand).
- LaTeX conventions used:
  - `fontspec`, `babel` with `spanish,es-noshorthands,es-tabla` (noshorthands avoids TikZ breakage).
  - `siunitx` with decimal comma.
  - `circuitikz [american]`, `pgfplots`, `tcolorbox`, `xurl`.
  - In siunitx, `\kilo\sample` and `\text{div}` are invalid; write `kS/s`, `/div` literally.
- To visually check PDFs, render pages to PNG (PyMuPDF in a throwaway venv) and inspect the
  circuit figures — label overlaps are common.
- Shell: PowerShell 5.1 and Git Bash are both available.
- **ngspice 47** at `%LOCALAPPDATA%\Programs\ngspice47\Spice64\bin\ngspice_con.exe` (not on PATH).
  Run simulations with `NGSPICE=<that path> PYTHON=<python with numpy+matplotlib> bash simulacion_fase/correr_todo.sh`.
- The owner **presents on a Linux laptop**: everything must run there with
  `sudo apt install ngspice python3-numpy python3-matplotlib` (no LTspice, no Windows-only tools).

---

## 9. Repository layout (current work)

```
AGENTS.md                         ← this file (CLAUDE.md just imports it)
propuesta/propuesta_sonometro.tex ← Spanish proposal for the professor (LaTeX source)
propuesta/propuesta_sonometro.pdf ← compiled proposal
simulacion_fase/                  ← ngspice + Python: phase / group delay study (answers the professor)
(legacy: README.md, docs/, hardware/, sims/, firmware/, software/, tests/ — see §2)
```

---

## 10. Professor feedback on proposal v1 (first review, early Nov 2026)

The professor **did not approve** v1. He distrusts AI-generated work: deliverables must stand on
primary sources, hand calculations and simulations the group can reproduce.

His objections:

1. **"Coupling capacitors introduce phase shift; voice changes frequency fast over 20 Hz–20 kHz."**
   Answered in `simulacion_fase/` with ngspice; see its README for numbers and talking points.
   - Phase shift is not distortion; group-delay variation is.
   - A (1 µF) gives 640 µs at 20 Hz; B (10 µF) gives 74 µs.
   - With voice, B's error equals the DC-coupled design: 0.71 % vs 0.71 %.
2. **Dislikes the DC offset (mid-scale V_MID) — "no defined reference".**
   - In v1, V_MID came from a 10k/10k divider of the MCU 3.3 V rail, **not** from the TL431.
     The owner initially thought it came from the TL431.
3. **Criticised the G = 11 stage.** The exact reason is unknown. Next version must *derive* the
   gain from a stated SPL range.
4. **His suggestion: differential amplifier (to reject noise) + bipolar ADC** (measures
   negative voltages).
   - The owner has **no DAQ / myDAQ**.

New possibility: build the circuit **on a classmate's PCB** (Altium library parts, ordered from
JLCPCB), keeping it small. Not confirmed:
- order date;
- whether JLCPCB assembly (PCBA) is available;
- which supply rails exist;
- which MCU will be used.

Next: get approval of the *idea* first, then design v2.
- Candidate v2 architecture: TL431+PNP sources, a DC-coupled difference amp that subtracts a
  reference (CN0540-style), and a bipolar ADC such as the AD7606 (±10 V from a single 5 V supply).
- Not yet checked: the ±12 V rail this needs and JLCPCB stock.
- Also fix the v1 anti-alias filter, which droops −3.4 dB at 20 kHz.

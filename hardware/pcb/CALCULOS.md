# CÁLCULOS — Sonómetro IEPE Rev B (placa de 4 capas, ruteada)

Generado por `tools/calculos.py` a partir de `pcb.kicad_pcb`: anchos, largos, vías y separaciones son medidas de la placa. Etiquetas de origen: **[doc]** leído del PDF del fabricante (página indicada); **[copia]** de una fuente secundaria, sin verificar contra el original; **[estimado]** supuesto de diseño.

## 1. Datos de entrada

| Dato | Valor | Origen |
|---|---|---|
| Cobre externo (F.Cu, B.Cu) | 35 µm (1 oz) | apilado JLC04161H-7628 (REGLAS.md §9) |
| Cobre interno (In1, In2) | 15.2 µm (0.5 oz) | apilado JLC04161H-7628 (REGLAS.md §9) |
| Resistividad del cobre | 1.72·10⁻⁸ Ω·m | [copia] |
| Cobre en el barril de la vía | 18 µm | [estimado] capacidad publicada por JLC, sin verificar |
| LMR36015 fOSC, variante 1 MHz | 0.85 / 1 / 1.15 MHz | [doc] SNVSB49D p.7, Electrical Characteristics |
| LMR36015 tON-MIN / tOFF-MIN | 55 típ, 83 máx ns / 53 típ, 73 máx ns | [doc] SNVSB49D p.7, §8.6 |
| LMR36015 RDS-ON alto / bajo | 225 típ, 435 máx mΩ / 150 típ, 280 máx mΩ | [doc] SNVSB49D p.7 |
| LMR36015 RθJA / RθJB / ψJT | 72.5 / 23.3 / 0.8 °C/W | [doc] SNVSB49D p.6, §8.4 (JEDEC) |
| LMR36015 FPWM | CCM sin carga, frecuencia fija | [doc] SNVSB49D p.16, Tabla 9-1 |
| L1 (3V3) / L2 (5V) | 6.8 µH / 10 µH | design.py (XAL4030-682 / XAL4040-103) |
| PCM1808 ICC (VCC 5 V) | 8.6 típ, 11 máx mA | [doc] SLES177B p.6 |
| PCM1808 IDD (VDD 3.3 V) | 5.9 típ, 8 máx mA a 48 kHz; 10.2 típ a 96 kHz | [doc] SLES177B p.6 |
| TLV9152 IQ por amplificador | 560 típ, 685 máx µA; 750 máx (−40…125 °C) | [doc] SBOS986E p.12 |
| MCP4725 IDD | 210 típ, 400 máx µA | [doc] DS22039D p.3 |
| Oscilador Y1 (O322524576MEEA4SC) | ≤ 10 mA | [estimado] sin datasheet a mano |
| LT3092 θJA (TS8) | 57 °C/W | [copia] REGLAS.md §4 |
| Corrientes IEPE | CH1 2.81 → 3.98 mA; CH2 1.51 → 2.51 mA (con JP) | design.py, cambio C9 |
| D2 SMBJ26A | VRWM 26 V; VBR mín 28.9 V | [copia] valores de la serie SMBJ, sin datasheet a mano |
| IPC-2221 (ampacidad) | I = k·ΔT^0.44·A^0.725; k = 0.048 ext / 0.024 int | [copia] REGLAS.md §5 |

**Corrientes de diseño por riel** (cotas superiores):
- 5V_A = PCM1808 ICC máx + 2 TLV9152 a 750 µA por amplificador = **14.0 mA**; 5V = 5V_A (R33 solo alimenta 5V_A).
- 3V3 = PCM1808 IDD (10.2 mA, 96 kHz) + 2 MCP4725 máx + pull-ups I2C + Y1 (estimado) = **22.4 mA**.
- 24V_PROT: **50 mA**, el límite de la fuente de banco (AGENTS.md §5); IEPE ≤ 3.98 + 2.51 mA.

## 2. LMR36015: tiempo de encendido, rizado en FPWM y disipación

tON = D / fSW con D = VOUT / VIN (ideal; con pérdidas D sube un poco y tON también, a favor). tOFF = (1 − D) / fSW. Se compara con tON-MIN = 83 ns y tOFF-MIN = 73 ns máximos [doc SNVSB49D p.7].

| Salida | VIN | fSW | tON | margen sobre 83 ns | tOFF | margen sobre 73 ns |
|---|---|---|---|---|---|---|
| 3.3 V | 18.0 V | 0.85 MHz | 216 ns | +133 ns | 961 ns | +888 ns |
| 3.3 V | 18.0 V | 1.15 MHz | 159 ns | +76 ns | 710 ns | +637 ns |
| 3.3 V | 23.5 V | 0.85 MHz | 165 ns | +82 ns | 1011 ns | +938 ns |
| 3.3 V | 23.5 V | 1.15 MHz | 122 ns | +39 ns | 747 ns | +674 ns |
| 3.3 V | 26.0 V | 0.85 MHz | 149 ns | +66 ns | 1027 ns | +954 ns |
| 3.3 V | 26.0 V | 1.15 MHz | 110 ns | +27 ns | 759 ns | +686 ns |
| 3.3 V | 28.9 V | 0.85 MHz | 134 ns | +51 ns | 1042 ns | +969 ns |
| 3.3 V | 28.9 V | 1.15 MHz | 99 ns | +16 ns | 770 ns | +697 ns |
| 5.0 V | 18.0 V | 0.85 MHz | 327 ns | +244 ns | 850 ns | +777 ns |
| 5.0 V | 18.0 V | 1.15 MHz | 242 ns | +159 ns | 628 ns | +555 ns |
| 5.0 V | 23.5 V | 0.85 MHz | 250 ns | +167 ns | 926 ns | +853 ns |
| 5.0 V | 23.5 V | 1.15 MHz | 185 ns | +102 ns | 685 ns | +612 ns |
| 5.0 V | 26.0 V | 0.85 MHz | 226 ns | +143 ns | 950 ns | +877 ns |
| 5.0 V | 26.0 V | 1.15 MHz | 167 ns | +84 ns | 702 ns | +629 ns |
| 5.0 V | 28.9 V | 0.85 MHz | 204 ns | +121 ns | 973 ns | +900 ns |
| 5.0 V | 28.9 V | 1.15 MHz | 150 ns | +67 ns | 719 ns | +646 ns |

VIN: 18 V es una entrada baja de prueba; 23.5 V es 24 V menos D1; 26 V es la VRWM del TVS; 28.9 V es la VBR mínima del TVS [copia]. Peor caso: 3.3 V con 28.9 V y 1.15 MHz da tON = 99 ns, 16 ns por encima del mínimo. No hay repliegue de frecuencia en ningún caso.

**Rizado de la bobina en FPWM** (CCM aun sin carga [doc SNVSB49D p.16]): ΔIL = (VIN − VOUT)·VOUT / (VIN·L·fSW). El peor caso es el oscilador lento (0.85 MHz) con la VIN más alta.

| Salida | L | VIN | fSW | ΔIL p-p | Pico (I + ΔIL/2) | RMS en la bobina |
|---|---|---|---|---|---|---|
| 3.3 V | 6.8 µH | 23.5 V | 0.85 MHz | 0.491 A | 0.268 A | 0.143 A |
| 3.3 V | 6.8 µH | 28.9 V | 0.85 MHz | 0.506 A | 0.275 A | 0.148 A |
| 5.0 V | 10.0 µH | 23.5 V | 0.85 MHz | 0.463 A | 0.246 A | 0.134 A |
| 5.0 V | 10.0 µH | 28.9 V | 0.85 MHz | 0.486 A | 0.257 A | 0.141 A |

Los tramos SW, bobina y COUT se dimensionan con el pico de **0.28 A** (ver §3), no con los 5–20 mA de la carga.

**Disipación del LMR36015** [estimado]. El datasheet no da la corriente de entrada en FPWM sin carga: conducción con RDS-ON máximas = 6.5 mW; conmutación con 10 ns de flancos (supuesto) = 42 mW; más el LDO interno y las cargas de compuerta, que no están publicados. Con una cota de 0.15 W por integrado, ΔT = 0.15 · 72.5 = 11 °C con el RθJA JEDEC; la placa de 4 capas con plano GND entero queda por debajo. **A verificar en el banco:** corriente de entrada a 24 V sin carga en cada buck.

## 3. Ancho de pista (IPC-2221, ΔT = 10 °C) contra el ancho usado

| Tramo | Corriente | Capa | Ancho mínimo IPC | Ancho mínimo usado (medido) |
|---|---|---|---|---|
| SW_3 / SW_5, bobina, COUT | 275 mA | F.Cu | 0.051 mm | 0.25 mm (máx 0.60; 12 mm de pista) |
| 24V_PROT (bus, VIN) | 50 mA | F.Cu | 0.005 mm | 0.25 mm (máx 1.00; 98 mm de pista) |
| 3V3 (salida y distribución) | 22 mA | B.Cu | 0.002 mm | 0.30 mm (máx 0.50; 4 mm de pista) |
| 3V3 (salida y distribución) | 22 mA | F.Cu | 0.002 mm | 0.25 mm (máx 0.50; 52 mm de pista) |
| 3V3 (salida y distribución) | 22 mA | In2 | 0.010 mm | 0.40 mm (máx 0.40; 117 mm de pista) |
| 5V (salida a R33) | 14 mA | B.Cu | 0.001 mm | 0.30 mm (máx 0.30; 2 mm de pista) |
| 5V (salida a R33) | 14 mA | F.Cu | 0.001 mm | 0.25 mm (máx 0.25; 29 mm de pista) |
| 5V_A (distribución) | 14 mA | F.Cu | 0.001 mm | 0.30 mm (máx 0.40; 26 mm de pista) |
| 5V_A (distribución) | 14 mA | In2 | 0.005 mm | 0.40 mm (máx 0.40; 53 mm de pista) |
| IEPE_SUP / IEPE_SUP_SV | 4 mA | F.Cu | 0.000 mm | 0.30 mm (máx 0.30; 23 mm de pista) |
| GND (pistas) | 50 mA | F.Cu | 0.005 mm | 0.25 mm (máx 0.50; 110 mm de pista) |

En todos los rieles el ancho lo fija la fabricación y la regla de clase (0.25 mm mínimo en Potencia), no la corriente: el margen es de un orden de magnitud o más. Las zonas de VIN, VOUT y SW del bloque 1 son más anchas que cualquier pista.

## 4. Caída de tensión de la fuente a la carga más lejana

Resistencia del camino de menor resistencia por el cobre de la red (pistas de todas las capas y vías; cobre a 20 °C). Caída = corriente total del riel × resistencia (cota: toda la corriente por el camino más largo).

| Riel | Fuente | Carga | Largo del camino | R | Corriente | Caída |
|---|---|---|---|---|---|---|
| 3V3 | tronco de 3V3 en la zona VOUT (139.8, 102.725) | U4.4 | 82.9 mm | 199 mΩ | 22.4 mA | 4.47 mV |
| 5V_A | R33.2 | U9.8 | 54.1 mm | 125 mΩ | 14.0 mA | 1.75 mV |

Las caídas por el cobre quedan por debajo de 5 mV: despreciables frente a la regulación de los bucks (±1.5 % en FPWM [doc SNVSB49D p.8]). R33 (10 Ω) baja 5V_A en 140 mV y disipa 2.0 mW; R9/R46 (100 Ω) bajan cada 3V3_DAC en 40 mV con el MCP4725 al máximo.

## 5. Corriente por vía y vías por riel

Barril de 0.3 mm con 18 µm de cobre: sección 0.0170 mm². Con la fórmula de capa externa (práctica común para el barril), I(ΔT = 10 °C) = **1.41 A** por vía; con la interna, 0.71 A.

| Red | Vías | Corriente del riel | Vías necesarias |
|---|---|---|---|
| 3V3 | 11 | 22.4 mA | 1 |
| 5V_A | 5 | 14.0 mA | 1 |
| 24V_PROT | 0 | 50.0 mA | 1 |
| 5V | 2 | 14.0 mA | 1 |
| GND | 299 | 50.0 mA | 1 |
| I2C_SCL | 3 | 1.0 mA | 1 |
| I2C_SDA | 2 | 1.0 mA | 1 |
| DC_MON | 1 | 0.1 mA | 1 |
| DC_MON2 | 2 | 0.1 mA | 1 |

## 6. Disipación y temperatura

| Pieza | Peor caso | Potencia | ΔT | Nota |
|---|---|---|---|---|
| LT3092 (U1/U8) | IEPE en cortocircuito: 3.98 mA × 23.3 V | 93 mW | 5.3 °C | θJA [copia] |
| LMR36015 (U6/U7) | FPWM sin carga, 28.9 V | ≤ 150 mW [estimado] | ≤ 11 °C | ver §2; medir en el banco |
| D1 SS34 | 50 mA × 0.4 V | 20 mW | < 1 °C | VF [estimado] |
| R33 10 Ω | 14.0 mA | 2.0 mW | despreciable | 0603, 100 mW |
| D2 SMBJ26A | en reposo (fuga) | despreciable | — | solo conduce en transitorios |
| PCM1808 | 48 kHz | 62 típ, 81 máx mW | — | [doc] SLES177B p.6 |

## 7. Separación por tensión

IPC-2221B tabla 6-1 [copia, REGLAS.md §5]: hasta 30 V pide 0.1 mm en capa externa sin recubrimiento (B2, hasta 3050 m; Manizales ≈ 2150 m) y 0.05 mm en capa interna (B1). De 31 a 50 V pide 0.6 mm externo. El TVS limita la tensión continua a la VRWM de 26 V, así que las redes de 24 V van en la fila de 16–30 V.

- Redes con hasta 24–29 V: /IEPE_SUP, /IEPE_SUP_SV, /SW_3, /SW_5, 24V_PROT, IEPE, IEPE_SV, Net-(D1-A), Net-(J1-Pin_2), Net-(J7-Pin_2).
- **Separación mínima medida** a cualquier otra red, en todas las capas: **0.200 mm** (24V_PROT - GND en F.Cu).
- Contra 0.1 mm (B2) y 0.05 mm (B1): margen de 2.0×. El diseño usa además 0.2–0.3 mm por clase (REGLAS.md §8).

## 8. Relojes: largo e impedancia

No hay pares diferenciales ni USB en la placa. Para los relojes se compara el largo con el largo crítico Lc = tr / (2·tpd). tpd ≈ 5.6 ps/mm en microstrip FR-4 (εr 4.4) [copia: aproximación de IPC-2141]; con un flanco de 1 ns (supuesto conservador) Lc ≈ 90 mm.

| Red | Largo medido | Relación con Lc |
|---|---|---|
| Net-(Y1-OUT) | 4.2 mm | 5 % de Lc |
| Net-(U4-SCKI) | 5.4 mm | 6 % de Lc |
| Net-(U4-BCK) | 1.9 mm | 2 % de Lc |
| SAI_SCK | 13.5 mm | 15 % de Lc |
| Net-(U4-LRCK) | 6.1 mm | 7 % de Lc |
| SAI_FS | 25.7 mm | 29 % de Lc |
| Net-(U4-DOUT) | 4.2 mm | 5 % de Lc |
| SAI_SD | 15.5 mm | 17 % de Lc |

Impedancia de una pista de 0.2 mm en F.Cu sobre 0.21 mm de prepreg hasta In1: Z0 ≈ 67 Ω (fórmula de IPC-2141 [copia]). Todas las líneas son mucho más cortas que Lc, así que no hace falta controlar la impedancia; las resistencias en serie R21–R24 amortiguan los flancos.

## 9. TLV9152 (U3/U9): estabilidad y región de transición de la entrada

Salida de `tools/analisis_opamp.py`. Modelo de dos polos ajustado al GBW (4.5 MHz) y al margen de fase a G = +1 (60°) del datasheet [doc SBOS986E p.12]; capacidades de entrada ZID 100 MΩ ‖ 3 pF y ZICM 6 TΩ ‖ 1 pF [doc p.11]; 1.5 pF de pistas [estimado]. Región de transición típica (V+) − 2 V a (V+) − 1 V [doc §7.3.4 p.26].

```
Rin = 1000.9 kΩ, Rf = 99.8 kΩ, ganancia IEPE = -0.0997, ganancia VSHIFT = 1.0997, ganancia de ruido = 1.0997

TLV9062 (SBOS839N p.13): GBW 10.0 MHz, PM(G=1) 55°, C_SUM = 7.5 pF
  seguidor U3B: cruce ~10.0 MHz, PM 55° (datasheet; carga = entrada + de U3A, ~5 pF: CID 3 + CICM 1 + pista)
  U3A con CF =  0.0 pF: cruce    1445 kHz, margen de fase   3.4°, pico  24.5 dB, -3 dB en  2290.9 kHz
  U3A con CF =  4.7 pF: cruce    3739 kHz, margen de fase  72.3°, pico   0.0 dB, -3 dB en   363.1 kHz
  U3A con CF = 10.0 pF: cruce    5352 kHz, margen de fase  68.8°, pico   0.0 dB, -3 dB en   166.0 kHz
  U3A con CF = 22.0 pF: cruce    6744 kHz, margen de fase  64.6°, pico   0.0 dB, -3 dB en    75.9 kHz
  U3A con CF = 47.0 pF: cruce    7611 kHz, margen de fase  61.9°, pico   0.0 dB, -3 dB en    34.7 kHz

TLV9152 (SBOS986E p.11-12 (ZID 100 MΩ || 3 pF, ZICM 6 TΩ || 1 pF)): GBW 4.5 MHz, PM(G=1) 60°, C_SUM = 5.5 pF
  seguidor U3B: cruce ~4.5 MHz, PM 60° (datasheet; carga = entrada + de U3A, ~5 pF: CID 3 + CICM 1 + pista)
  U3A con CF =  0.0 pF: cruce    1114 kHz, margen de fase   7.8°, pico  17.0 dB, -3 dB en  1819.7 kHz
  U3A con CF =  4.7 pF: cruce    2027 kHz, margen de fase  70.8°, pico   0.0 dB, -3 dB en   380.2 kHz
  U3A con CF = 10.0 pF: cruce    2741 kHz, margen de fase  69.7°, pico   0.0 dB, -3 dB en   166.0 kHz
  U3A con CF = 22.0 pF: cruce    3313 kHz, margen de fase  66.8°, pico   0.0 dB, -3 dB en    75.9 kHz
  U3A con CF = 47.0 pF: cruce    3649 kHz, margen de fase  64.9°, pico   0.0 dB, -3 dB en    34.7 kHz

V+ (5V_A) = 4.785–4.967 V; región de transición típica desde 2.785–2.967 V hasta 3.785–3.967 V; DAC máx ≈ 3.21 V; k = 0.0997
REST objetivo | VB 8 V | VB 10 V | VB 12.5 V (RG-50) | VB 14 V
1.50 V | 2.09 V (par P) | 2.27 V (par P) | 2.50 V (par P) | 2.63 V (par P)
2.00 V | 2.54 V (par P) | 2.73 V (par P) | 2.95 V (en transición) | 3.09 V (en transición)
2.45 V | 2.95 V (en transición) | 3.13 V (en transición) | 3.21 V (DAC al tope) | 3.21 V (DAC al tope)
  REST máximo para VSHIFT <= 2.70 V con VB = 8.0 V: 2.17 V
  REST máximo para VSHIFT <= 2.70 V con VB = 12.5 V: 1.72 V
  REST máximo para VSHIFT <= 2.70 V con VB = 14.0 V: 1.57 V
```

- **U3A/U9A (sumador):** con CF = 10 pF, margen de fase ≈ 70° y sin pico; sin CF quedaría en ≈ 8° (por eso se agregó C56/C57).
- **U3B/U9B (seguidor de VSHIFT):** su carga es la entrada + del sumador, unos 5 pF; el datasheet admite 1000 pF [doc p.12]. La impedancia de fuente en la entrada + (R12/C4) no entra en el lazo del seguidor.
- **Región de transición:** las dos entradas de cada amplificador quedan en VSHIFT, un nivel de DC que no se mueve con la señal (configuración inversora más lazo de DC). Aun así, conviene quedar en el par P, que es donde la tabla especifica la CMRR. **Para el firmware: REST_OUT objetivo ≈ 1.5 V** (DC_MON ≈ 0.75 V). Así VSHIFT queda en 2.1–2.6 V para polarizaciones de 8–14 V, por debajo de la región, y la salida conserva margen: 1.5 ± 0.32 V con el RG-50 a 130 dB y 1.5 ± 1.08 V con la excursión máxima del SV 12. Con un objetivo de 2.45 V (mitad del riel), VSHIFT cae dentro de la región o el DAC llega al tope.
- **Sin verificar:** simulación con el modelo SPICE de TI y medición en banco (escalón del DAC y forma de VSHIFT y REST en el osciloscopio).


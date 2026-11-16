# Auditoría de piezas para JLCPCB (PCBA Economic)

Generado por `tools/informe_auditoria.py` con la API pública del buscador de piezas de JLCPCB (consulta del 15/11/2026; stock en vivo, cambia a diario) y los footprints de EasyEDA/JLC bajados con `easyeda2kicad`. **Nada de esto se ha cambiado en el diseño: son propuestas para aprobar.**

## 1. Estado de cada pieza que monta JLC

| Refs | Valor | MPN del diseño | LCSC | Origen del código | Tipo | Stock | MPN coincide |
|---|---|---|---|---|---|---|---|
| U4 | PCM1808PW | PCM1808PW | C55513 | web (guía) | extended | 48926 | no (ver nota) |
| C9, C15, C14, C18, C11, C5, C47, C52 | 10uF | TCC0603X5R106K100CT | C380314 | diseño | extended | 423477 | sí |
| R20, R19, R9, R21, R22, R23, R24, R46 | 100R | FRC0603J101 TS | C2907089 | diseño | extended | 6205077 | sí |
| C10, C19 | 10nF | C0402C103K3REC7411 | C3854899 | buscado por MPN | extended | 49886 | sí |
| C16, C17, C12, C13, C4, C6, C7, C8, C20, C1, C3, C35, C45, C50, C48, C51, C53, C54, C55 | 100nF | CC0603KRX7R9BB104 | C14663 | diseño | basic | 34154464 | sí |
| U3, U9 | TLV9062IDDFR | TLV9062IDDFR | C2867884 | web (guía) | extended | 2 | sí |
| U2, U10 | MCP4725A0T-E/CH | MCP4725A0T-E/CH | C144198 | web (guía) | extended | 377 | sí |
| R12, R15, R17, R4, R5, R37, R44, R45, R49, R50, R51 | 10k | FRC0603J103TS | C2930027 | diseño | extended | 13111825 | sí |
| R13, R38 | 390k | RC0603FR-07390KL | C137735 | diseño | extended | 115760 | sí |
| R8, R7, R42, R43 | 49k9 | RC0603FR-0749K9L | C114624 | diseño | extended | 259350 | sí |
| R11, R10 | 4k7 | SCR0603F4K7 | C3016318 | diseño | extended | 19 | sí |
| R14, R39 | 365k | RC0603FR-07365KL | C185336 | diseño | extended | 3355 | sí |
| R16, R40 | 191k | AC0603FR-07191KL | C227635 | diseño | extended | 224 | sí |
| R18, R41 | 54k9 | RC0603FR-0754K9L | C185321 | diseño | extended | 3474 | sí |
| Y1 | 24.576MHz | O322524576MEEA4SC | C27869 | diseño | extended | 2396 | sí |
| U1, U8 | LT3092ETS8#TRPBF | LT3092ETS8#TRPBF | C462641 | web (guía) | extended | 2660 | sí |
| R6 | 1k | FRC0603J102 TS | C2907113 | diseño | extended | 11765993 | sí |
| R3, R2 | 150R | RTT031500FTP | C103302 | diseño | extended | 11 | sí |
| C2, C49 | 1uF | CL10A105KB8NNNC | C15849 | diseño | basic | 13199938 | sí |
| R1, R36 | 10R | CRCW040210R0FKED | C481926 | buscado por MPN | extended | 403514 | sí |
| U6, U7 | LMR36015FBRNXR | LMR36015FBRNXR | C1850339 | diseño | extended | 27 | sí |
| L1 | 6.8uH | XAL4030-682MEC | C3040663 | buscado por MPN | extended | 3030 | sí |
| C27, C28, C37, C38 | 4.7uF | C5750X7R2A475K230KA | C2168733 | buscado por MPN | extended | 0 | sí |
| C29, C30, C39, C40 | 220nF | C0805C224K1RACTU | C2167405 | buscado por MPN | extended | 1240 | sí |
| C31, C32, C33, C34, C41, C42, C43, C44 | 15uF | C3225X7R1C156M250AB | C2167855 | buscado por MPN | extended | 0 | sí |
| C36, C46 | 2.2uF | C0805C225K5RACTU | **no encontrado** | — | — | — | — |
| R29, R31 | 100k | RC0603FR-07100KL | C14675 | buscado por MPN | extended | 10605345 | sí |
| R30 | 43.2k | RC0603FR-0743K2L | C137720 | buscado por MPN | extended | 168 | sí |
| L2 | 10uH | XAL4040-103MEC | C5144883 | buscado por MPN | extended | 189 | sí |
| R32 | 24.9k | RC0603FR-0724K9L | C137761 | buscado por MPN | extended | 588468 | sí |
| R33 | 10R | CRCW0603010RJNEAHP | **no encontrado** | — | — | — | — |
| R34 | 15k | RC0603FR-0715KL | C114661 | buscado por MPN | extended | 744226 | sí |
| R35 | 100R | RC0603FR-07100RL | C105588 | buscado por MPN | extended | 8487808 | sí |
| D1 | SS34 | SS34 | C8678 | diseño | basic | 2699244 | sí |
| D2 | SMBJ26A | SMBJ26A | C123820 | diseño | extended | 55504 | sí |
| R47 | 180R | 0603WAF1800T5E | C22828 | diseño | extended (preferred) | 2195153 | sí |
| R48 | 150R | 0603WAF1500T5E | C22808 | diseño | basic | 1181381 | sí |

Nota: U4 figura como PCM1808PW en el diseño y C55513 es PCM1808PW**R** (la misma pieza en carrete).

Piezas *extended* distintas hoy (sin contar *preferred*): **30**. En Economic, JLC cobra una carga de alimentador por cada una (≈ USD 3.07 según su página de precios).

## 2. Propuestas de cambio (requieren aprobación)

| Refs | Problema | Propuesta | ¿Cambia footprint? | Motivo |
|---|---|---|---|---|
| U3, U9 | TLV9062IDDFR (C2867884): **stock 2** para 2 piezas, sin margen | TLV9152IDDFR **C2861011** (stock 542, mismo encapsulado DDF y pinout de doble op-amp estándar; 4.5 MHz, 2.7–16 V). Alternativa: TLV9002IDDFR C2862620 (stock 2331, 1 MHz). | no (mismo TSOT-23-8) | riesgo |
| C27, C28, C37, C38 (CIN) | C5750X7R2A475K230KA (C2168733): **stock 0** | PSA FS55X475K101EGG **C153031** (4.7 µF 100 V X7R 2220, stock 11 756). Mismo valor, tensión y tamaño. | no | riesgo |
| C31–C34, C41–C44 (COUT) | C3225X7R1C156M250AB (C2167855): **stock 0** | TDK C3225X7R1C156MT000N **C694469** (15 µF 16 V X7R 1210, stock 1338). Misma serie TDK. | no | riesgo |
| C36, C46 (VCC) | C0805C225K5RACTU: **no está en el catálogo** | Samsung CL21B225KOFNNNE **C28234** (2.2 µF 16 V X7R 0805, stock 73 051). El datasheet pide 1 µF/16 V. Basic más barato: C23630 (0603, cambia el footprint). | no (con C28234) | riesgo |
| R33 | CRCW0603010RJNEAHP: **no está en el catálogo** | **C22859** 10 Ω 1 % 0603 (basic). | no | riesgo |
| R2, R3 | RTT031500FTP (C103302): **stock 11** | **C22808** 150 Ω 1 % 0603 (basic, la misma de R48). | no | riesgo |
| R10, R11 | SCR0603F4K7 (C3016318): **stock 19** | **C23162** 4.7 kΩ 1 % 0603 (basic). | no | riesgo |
| C10, C19 | sin LCSC; el MPN existe como C3854899 (extended) | **C15195** 10 nF 50 V X7R 0402 (basic). | no | costo |
| R1, R36 | sin LCSC; el MPN existe como C481926 (extended) | **C25077** 10 Ω 0402 (basic). | no | costo |
| R9, R19–R24, R35, R46 | FRC0603J101 TS 5 % (extended) | **C22775** 100 Ω 1 % 0603 (basic). | no | costo |
| R4, R5, R12, R15, R17, R37, R44, R45, R49–R51 | FRC0603J103TS 5 % (extended) | **C25804** 10 kΩ 1 % 0603 (basic). Mejora: los divisores DC_MON quedan a 1 %. | no | costo |
| R6 | FRC0603J102 TS 5 % (extended) | **C21190** 1 kΩ 1 % (basic). | no | costo |
| R7, R8, R42, R43 | RC0603FR-0749K9L (extended) | **C23184** 49.9 kΩ 1 % (basic). | no | costo |
| R29, R31 | RC0603FR-07100KL (extended) | **C25803** 100 kΩ 1 % (basic). | no | costo |
| R34 | RC0603FR-0715KL (extended) | **C22809** 15 kΩ 1 % (basic). | no | costo |
| C5, C9, C11, C14, C15, C18, C47, C52 | TCC0603X5R106K100CT (extended) | **C19702** CL10A106KP8NNNC 10 µF 10 V X5R 0603 (basic). | no | costo |
| C29, C30, C39, C40 (CHF) | C0805C224K1RACTU 100 V (extended) | **C5378** CL21B224KBFNNNE 220 nF 50 V X7R 0805 (basic; 50 V ≥ 2 × 24 V). | no | costo |

Si se aceptan todas, las piezas *extended* bajan a las que no tienen equivalente basic: 390k, 365k, 191k, 54.9k, 43.2k y 24.9k (1 %), SMBJ26A, el oscilador, LT3092, MCP4725, PCM1808, TLV9152/9002, LMR36015, las dos bobinas Coilcraft, CIN y COUT.

**Riesgos de stock aunque no se cambie nada:** LMR36015FBRNXR **27** unidades (se necesitan 2), L2 XAL4040-103MEC 189, R16/R40 191k 224, R30 43.2k 168, MCP4725 377. Conviene pedir pronto o reservarlas en la biblioteca de piezas de JLC.

## 3. Footprints de KiCad contra el footprint de JLC/EasyEDA de esa pieza exacta

Se emparejan los pads por número y se busca el giro *d* y la traslación *t* que llevan el footprint de KiCad sobre el de JLC. *err* es el máximo desvío de posición de pad después de alinear; *Δtam* es la máxima diferencia de tamaño de pad. Si en una pieza polarizada la numeración no coincidiera, aparecería en "sin pareja" o con un error grande.

| LCSC | Footprint KiCad | Footprint JLC | d (°) | t (mm) | err (mm) | Δtam (mm) | Pads sin pareja |
|---|---|---|---|---|---|---|---|
| C3854899 | C_0402_1005Metric | C0402 | 0 | (+0.00, +0.00) | 0.060 | 0.080 | — |
| C15195 | C_0402_1005Metric | C0402 | 0 | (+0.00, +0.00) | 0.060 | 0.080 | — |
| C380314 | C_0603_1608Metric | C0603 | 0 | (+0.00, +0.00) | 0.075 | 0.100 | — |
| C14663 | C_0603_1608Metric | C0603 | 0 | (+0.00, +0.00) | 0.075 | 0.100 | — |
| C15849 | C_0603_1608Metric | C0603 | 0 | (+0.00, +0.00) | 0.075 | 0.100 | — |
| C23630 | C_0603_1608Metric | C0603 | 0 | (+0.00, +0.00) | 0.075 | 0.100 | — |
| C19702 | C_0603_1608Metric | C0603 | 0 | (+0.00, +0.00) | 0.075 | 0.100 | — |
| C2167405 | C_0805_2012Metric | C0805 | 0 | (+0.00, +0.00) | 0.050 | 0.410 | — |
| C5378 | C_0805_2012Metric | C0805 | 0 | (+0.00, +0.00) | 0.050 | 0.410 | — |
| C29823 | C_1206_3216Metric | C1206 | 0 | (+0.00, +0.00) | 0.115 | 0.335 | — |
| C2167855 | C_1210_3225Metric | C1210 | 0 | (+0.00, +0.00) | 0.045 | 0.485 | — |
| C694469 | C_1210_3225Metric | C1210 | 0 | (+0.00, +0.00) | 0.045 | 0.485 | — |
| C2168733 | C_2220_5750Metric | C2220 | 0 | (+0.00, +0.00) | 0.030 | 0.210 | — |
| C8678 | D_SMA | SMA_L4.3-W2.6-LS5.2-RD | 0 | (+0.00, +0.00) | 0.200 | 0.500 | — |
| C123820 | D_SMB | SMB_L4.6-W3.6-LS5.3-RD | 0 | (+0.00, +0.00) | 0.210 | 0.453 | — |
| C3040663 | L_Coilcraft_XAL4030-XXX | IND-SMD_L4.0-W4.0_XAL4030-682MEC | 0 | (+0.00, +0.00) | 0.055 | 0.320 | — |
| C5144883 | L_Coilcraft_XAL4040-XXX | IND-SMD_L4.0-W4.0_XAL4040 | 180 | (+0.00, +0.00) | 0.015 | 0.020 | — |
| C55513 | TSSOP-14_4.4x5mm_P0.65mm | TSSOP-14_L5.0-W4.4-P0.65-LS6.4-BL | 90 | (+0.00, +0.00) | 0.062 | 0.225 | — |
| C144198 | SOT-23-6 | SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL | 90 | (-0.00, +0.00) | 0.012 | 0.253 | — |
| C2867884 | TSOT-23-8 | TSOT-23-8_L2.9-W1.6-P0.65-LS2.8-BL | 90 | (+0.00, +0.00) | 0.123 | 0.425 | — |
| C462641 | TSOT-23-8 | TSOT-23-8_L2.9-W1.6-P0.65-LS2.8-BR | 180 | (+0.00, -0.00) | 0.073 | 0.136 | — |
| C2861011 | TSOT-23-8 | SOT-23-8_L3.0-W1.7-P0.65-LS2.8-BR | 180 | (+0.00, -0.00) | 0.093 | 0.136 | — |
| C2862620 | TSOT-23-8 | TSOT-23-8_L2.9-W1.6-P0.65-LS2.8-TL | 0 | (+0.00, -0.00) | 0.073 | 0.136 | — |
| C481926 | R_0402_1005Metric | R0402 | 0 | (+0.00, +0.00) | 0.080 | 0.100 | — |
| C25077 | R_0402_1005Metric | R0402 | 0 | (+0.00, +0.00) | 0.080 | 0.100 | — |
| C2907089 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C2930027 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C137735 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C114624 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C3016318 | R_0603_1608Metric | — | — | — | — | — | no se pudo cargar EasyEDA |
| C185336 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C227635 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C185321 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C2907113 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C103302 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C14675 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C137720 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C137761 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C114661 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C105588 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C22828 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C22808 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C22775 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C25804 | R_0603_1608Metric | R0603 | 0 | (+0.00, +0.00) | 0.075 | 0.086 | — |
| C27869 | Oscillator_YXC_SMD3225-4Pin_3.2x2.5mm | OSC-SMD_4P-L3.2-W2.5-BL | 0 | (+0.00, +0.00) | 0.000 | 0.000 | — |
| C1850339 | Texas_RNX0012A_VQFN-HR-12_2x3mm_P0.5mm | VQFN-12_L3.0-W2.0-P0.65-BL_TI_RNX | 90 | (-0.14, +0.00) | 0.006 | 0.000 | — |

**Lectura:**
- **Pasivos (R/C 0402–2220), diodos SMA/SMB, oscilador y bobinas:** misma orientación (d = 0°; la XAL4040 da
  180°, que en una bobina de 2 pads no importa), pin 1 y cátodo en el mismo lado, posiciones a ≤ 0.2 mm. Las
  diferencias de tamaño de pad (≤ 0.5 mm) son las de los distintos land patterns IPC (KiCad usa el nominal);
  no afectan el ensamblaje.
- **Integrados:** JLC los dibuja girados respecto a KiCad, y **el giro depende de la pieza exacta, no del
  encapsulado**:
  - TSSOP-14 (PCM1808): 90°;
  - SOT-23-6 (MCP4725): 90°;
  - TSOT-23-8: 90° (TLV9062), 180° (LT3092 y TLV9152) y 0° (TLV9002);
  - RNX (LMR36015): 90° y 0.14 mm de desplazamiento.

  Esto va a la tabla de rotaciones del CPL (`fabricacion/rotaciones.md`), por código LCSC.
- **TSOT-23-8 propuesto** (`Sonometro:TSOT-23-8_Pad0.40x1.22mm_P0.65mm_ADI`):
  - pads de 0.40 × 1.22 mm, filas a 2.62 mm (dibujo ADI LTC 05-08-1637);
  - 0.25 mm entre pads (antes 0.15);
  - puente de máscara 0.25 mm con apertura 1:1, o 0.15 mm si se usara la expansión de 0.05 mm del dibujo TI DDF
    (JLC pide 0.10 en verde);
  - JLC dibuja 0.364 × 1.222 (LT3092) y 0.40 × 0.90 (TLV9062): el nuestro cubre los dos.
- **Pendiente:** C3016318 (R10/R11) no se pudo comparar (la API de EasyEDA limitó las consultas). Es un 0603
  igual a los demás y además se propone reemplazarla.

## 4. Lo que va soldado a mano (no lo monta JLC)
| Refs | Pieza | LCSC (para comprar) | Nota |
|---|---|---|---|
| A1 | 2 tiras hembra 1×15 de 2.54 mm (KH-2.54FH-1X15P-H8.5) + NUCLEO-L432KC | C2932676 (×2) | zócalo; la NUCLEO va enchufada |
| J1, J5, J7 | bornera de 2 vías de 5.0 mm (JL126-50002G01) | C394556 | THT |
| J2, J8 | BNC hembra a 90° (KH-BNC75-3511) | C2837588 | THT; el barril sale por el borde inferior |
| JP1, JP2 | header 1×2 de 2.54 mm + jumper | — | THT |
| TP1–TP7 | punto de prueba (pad con agujero) | — | sin componente |

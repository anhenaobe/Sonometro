# Fabricación — Sonómetro IEPE Rev B

Exportado por `tools/fabricacion.py` desde el commit **970905d** (placa sin cambios sin commit), después de un
`verificar_bloque.py` limpio: DRC 0 con todos los chequeos activos, paridad 0, ERC 0, `revisar_pistas` 0,
0 conexiones sin rutear.

## Pedido de PCB
| Parámetro | Valor |
|---|---|
| Capas | 4 (F.Cu, In1.Cu = plano GND, In2.Cu = alimentación y señales lentas, B.Cu) |
| Apilado | JLC04161H-7628, 1.6 mm, cobre externo 1 oz, interno 0.5 oz (sin control de impedancia) |
| Tamaño | 90 × 64 mm |
| Pista / separación mínima de diseño | 0.2 / 0.2 mm |
| Vía | 0.3 mm de taladro, 0.6 mm de pad; recubrimiento: **plugged** (por defecto en 4 capas en JLC) |
| Máscara / serigrafía | verde / blanca |
| Acabado | **HASL sin plomo** (elección del dueño, 2026-11-16; precios en REGLAS.md §9) |
| Archivo | `sonometro_revB_gerber.zip` (14 archivos: pcb-B_Cu.gbl, pcb-B_Mask.gbs, pcb-B_Paste.gbp, pcb-B_Silkscreen.gbo, pcb-Edge_Cuts.gm1, pcb-F_Cu.gtl, pcb-F_Mask.gts, pcb-F_Paste.gtp, pcb-F_Silkscreen.gto, pcb-In1_Cu.g1, pcb-In2_Cu.g2, pcb-NPTH.drl, pcb-PTH.drl, pcb-job.gbrjob) |

## Pedido de PCBA (económico, cara superior)
- `bom.csv` (36 líneas, 112 piezas) y `cpl.csv` (112 piezas). Rotaciones y comprobación del pin 1 en
  `rotaciones.md`.
- 3 fiduciales en la placa (FID1–FID3). Rieles y agujeros de herramienta: los agrega JLC (REGLAS.md §2).
- Piezas a mano: `soldar_a_mano.md` (8 piezas). Designadores omitidos en la serigrafía: `montaje.pdf`.
- Stock y códigos: `stock_bom.md` (`tools/stock_bom.py`, consulta del día). Repetir antes del pedido.
- **Cantidad a ensamblar: hasta 4 placas** (decisión del dueño). El 2026-11-16, L2 (XAL4040-103MEC, C5144883) tenía
  4 en stock; las placas restantes se fabrican sin ensamblar.
- **En la vista previa del pedido (DFM de JLC), antes de pagar:** pin 1 de U1–U10 sobre la marca de la placa,
  cátodo de D1/D2 del lado de la franja, pin 1 de Y1 y el centrado de U6/U7 (RNX, giro de 90° y 0.14 mm de
  corrimiento respecto del footprint de JLC).

## Tenting de las vías (punto 6 de la revisión del bloque 1)
Comparación de los Gerber de máscara contra una copia de control con todas las vías sin tapar:

| Cara | Aperturas en la placa real | … en coordenadas de vía | Aperturas en la copia sin tenting | … en coordenadas de vía |
|---|---|---|---|---|
| F.Mask | 348 | **0** | 677 | 329 |
| B.Mask | 55 | **0** | 384 | 329 |

La placa tiene 329 vías. La copia de control demuestra que el método las encuentra; la placa real no tiene
ninguna apertura en una vía.

## Revisión de los Gerber
Revisados con gerbonara, una biblioteca existente instalada en un entorno aparte con permiso del dueño
(`tools/revisar_gerber.py` → `revision_gerber.md`):
- capas reconocidas;
- borde cerrado de 90 × 64 mm;
- agujeros PTH sobre pads en las dos caras, con anillo mínimo;
- ninguna apertura de máscara sobre las vías;
- serigrafía fuera de las aperturas.

Vistas `vista_gerber_superior.svg` e `inferior.svg` (abrir en el navegador). Como control final, mirar el zip en el
visor de JLC al subirlo:
1. 4 capas de cobre en el orden F, In1, In2, B.
2. In1 entera, salvo los huecos de los agujeros.

## Designadores que no están en la serigrafía
A 1.0 mm de alto no caben sin pisar pads, vías o cuerpos. Están en `montaje.pdf` (vectorial: con zoom se leen los
designadores dentro de cada cuerpo). Posición del centro de la pieza, desde la esquina superior izquierda de la
placa:

| Pieza | Valor | x (mm) | y (mm) |
|---|---|---|---|
| C10 | 10nF | 62.7 | 23.9 |
| C12 | 100nF | 62.4 | 35.2 |
| C19 | 10nF | 60.3 | 25.7 |
| C20 | 100nF | 68.1 | 32.1 |
| C29 | 220nF | 26.2 | 7.7 |
| C30 | 220nF | 31.8 | 8.0 |
| C32 | 15uF | 24.6 | 3.0 |
| C33 | 15uF | 33.4 | 3.0 |
| C39 | 220nF | 47.8 | 7.7 |
| C40 | 220nF | 53.4 | 8.0 |
| C42 | 15uF | 46.2 | 3.0 |
| C43 | 15uF | 55.0 | 3.0 |
| C57 | 10pF | 46.2 | 47.4 |
| L1 | 6.8uH | 29.0 | 3.5 |
| L2 | 10uH | 50.6 | 3.5 |
| R7 | 49k9 | 46.7 | 20.4 |
| R18 | 54k9 | 46.1 | 23.2 |
| R19 | 100R | 65.2 | 23.9 |
| R22 | 100R | 68.7 | 26.1 |
| R41 | 54k9 | 46.1 | 45.7 |
| R42 | 49k9 | 46.7 | 42.9 |

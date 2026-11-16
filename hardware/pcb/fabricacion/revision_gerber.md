# Revisión de los Gerber con gerbonara

Generado por `tools/revisar_gerber.py` (gerbonara, biblioteca existente; sin lector propio).

## 1. Capas reconocidas

| Capa | Archivo | Objetos |
|---|---|---|
| bottom copper | pcb-B_Cu.gbl | 448 |
| bottom mask | pcb-B_Mask.gbs | 55 |
| bottom paste | pcb-B_Paste.gbp | 0 |
| bottom silk | pcb-B_Silkscreen.gbo | 55 |
| inner_1 copper | pcb-In1_Cu.g1 | 385 |
| inner_2 copper | pcb-In2_Cu.g2 | 484 |
| mechanical outline | pcb-Edge_Cuts.gm1 | 4 |
| top copper | pcb-F_Cu.gtl | 1632 |
| top mask | pcb-F_Mask.gts | 348 |
| top paste | pcb-F_Paste.gtp | 290 |
| top silk | pcb-F_Silkscreen.gto | 3956 |
| taladro | pcb-PTH.drl | 384 |

Avisos del lector: cion\gerber\pcb-PTH.drl:20 "G90": G90 header statement found after end of header; ion\gerber\pcb-NPTH.drl:10 "G90": G90 header statement found after end of header

`pcb-NPTH.drl` no tiene agujeros (la placa no lleva NPTH); se envía igual, como pide JLC.

## 2. Borde

- 4 segmentos; caja 90.00 × 64.00 mm; contorno cerrado.

## 3. Agujeros

- 329 pth de 0.3 mm, 45 pth de 1.0 mm, 6 pth de 1.3 mm, 4 pth de 2.2 mm
- PTH sobre un pad o vía flasheado en F.Cu y B.Cu: todos; anillo mínimo 0.150 mm.

## 4. Máscara sobre las vías

- top: 348 aperturas, **0** sobre alguna de las 329 vías.
- bottom: 55 aperturas, **0** sobre alguna de las 329 vías.

## 5. Serigrafía sobre aperturas de máscara

- top: 0 trazos de serigrafía (polaridad oscura) con un punto dentro de la caja de una apertura de máscara; 348 objetos de polaridad clara = recorte de la máscara que hace KiCad con --subtract-soldermask.
- bottom: 0 trazos de serigrafía (polaridad oscura) con un punto dentro de la caja de una apertura de máscara; 55 objetos de polaridad clara = recorte de la máscara que hace KiCad con --subtract-soldermask.

Vista superior: `vista_gerber_superior.svg` (abrir en el navegador).

Vista inferior: `vista_gerber_inferior.svg` (abrir en el navegador).

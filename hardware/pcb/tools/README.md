# tools/: Altium → KiCad, reproducible y verificado (Rev B)

Estos scripts reconstruyeron `hardware/pcb/` (esquemático de una sola hoja + placement) a partir
del proyecto Altium de los compañeros (`hardware/Sonometro_2CH/*.SchDoc`) y de
`hardware/docs/connection_matrix.md`, más los cambios C1–C12 de la Rev B (NUCLEO enchufada, BNC,
protección de entrada, escalón de corriente, etc.). Sirven para demostrar que cada conexión sale
de una fuente y no está inventada.

La entrega para dibujar en Altium es **`hardware/pcb/guia_conexiones_altium.pdf`**.

| Archivo | Qué hace |
|---|---|
| `altparse.py`, `export_json.py` | Leen los `.SchDoc` binarios (OLE) y calculan la conectividad real: cables, uniones, etiquetas locales, puertos y puertos de alimentación. Salida: `altium.json` (64 componentes). |
| `design.py` | Netlist objetivo. Toma todo lo de Altium tal cual (referencias, valores, MPN y LCSC), agrega desde los docs la alimentación y el canal 2, y aplica los cambios C1–C12 con su justificación. Salida: `target.json` (125 componentes, 68 redes con nombre) y `changes.json`. |
| `buildlib.py` | Crea `lib/Sonometro.*`: los símbolos PCM1808, LMR36015, oscilador YXC, NUCLEO-L432KC y BNC; el footprint RNX0012A (land pattern de TI SNVSB49D), el zócalo NUCLEO-32 (UM1956) y los footprints del oscilador y del BNC (de `vendor_fp.pretty/`, convertidos desde EasyEDA/JLC). |
| `gen_sch_wired.py` | Genera `pcb.kicad_sch` en una hoja A3. Dentro de cada bloque todo va con cables visibles y uniones; entre bloques se usan etiquetas globales, y los rieles van con símbolos de alimentación. Antes de escribir, un autochequeo geométrico aborta si un cable toca otra red o si queda un pin suelto. |
| `gen_pcb.py`, `fix_pro.py` | Generaron el `pcb.kicad_pcb` inicial (90×64 mm, 2 capas, sin rutear; hoy la placa es de 4 capas y **no se vuelve a correr `gen_pcb.py`**, que borraría el ruteo) y las reglas JLCPCB del `.kicad_pro` (0.15 mm de separación; clase *Potencia* con pistas de 0.5 mm). Los bucks siguen el layout de TI (SNVSB49D fig. 12-2). |
| `verify.py` | Compara pin por pin una netlist de KiCad contra `target.json`. Las redes internas sin etiqueta llevan el nombre automático de KiCad (`Net-(...)`); ahí se compara solo qué pines contienen. |
| `verify_altium.py` | Compara **tu dibujo en Altium** (`.SchDoc`) contra `target.json`, por pines y no por nombres de red. Uso: `python verify_altium.py <carpeta_con_los_SchDoc>`. |
| `dump_placement.py`, `make_guide.py` | Exportan el placement (con el Python de KiCad) y generan `guia/guia_conexiones.tex`. Compilar con `tectonic guia/guia_conexiones.tex`. |
| `probar_ruteo.sh` | Prueba de ruteabilidad con Freerouting sobre una **copia** de la placa (no toca `hardware/pcb`). Necesita Java 21 y `FREEROUTING_JAR`. |

## Uso

```bash
bash hardware/pcb/tools/verificar.sh   # revisa lo ACTUAL de hardware/pcb (no modifica nada)
bash hardware/pcb/tools/regenerar.sh   # regenera todo en tools/out/ (no toca hardware/pcb)
python hardware/pcb/tools/verify_altium.py <carpeta_SchDoc>    # revisa el dibujo de Altium
FREEROUTING_JAR=/ruta/freerouting-2.5.0.jar bash hardware/pcb/tools/probar_ruteo.sh
```

Para regenerar la guía PDF:

```bash
"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch export pdf -o hardware/pcb/tools/guia/esquematico.pdf hardware/pcb/pcb.kicad_sch
"C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/tools/dump_placement.py
python hardware/pcb/tools/make_guide.py && tectonic hardware/pcb/tools/guia/guia_conexiones.tex
```

`verificar.sh` sirve después de editar el esquemático a mano. Si se cambia el diseño a propósito,
hay que actualizar `design.py`; si no, `verify.py` reportará esas diferencias. Las rutas de KiCad
apuntan a la instalación de Windows y se cambian con `KICAD_CLI`, `KICAD_PYTHON` y `PYTHON`.

La versión anterior (Rev A, 68×50 mm con STM32 soldado) quedó respaldada en `../respaldo_revA/`.

## Equivalencia de referencias (docs/connection_matrix.md → KiCad)

Lo dibujado en Altium conserva su referencia de Altium.

| Bloque | Doc → KiCad |
|---|---|
| CH1, ya en Altium | J102→J1, J101→J2, U101→U1, U202→U2, U201→U3, U301→U4, Y301→Y1 (U401/J401/J402 eliminados: cambio C1) |
| Entrada 24 V | J501→J5 (+ D1, D2 nuevos: cambio C4) |
| Buck 3V3 | U501→U6, L503→L1, C351/C352→C27/C28, C353/C354→C29/C30, C355–C358→C31–C34, C359→C35, C360→C36, R351→R29, R352→R30 |
| Buck 5V | U502→U7, L505→L2, C551/C552→C37/C38, C553/C554→C39/C40, C555–C558→C41–C44, C559→C45, C560→C46, R551→R31, R552→R32 |
| Filtro 5V_A | R501→R33, C501→C47 |
| Fuente IEPE CH2 | J112→J7, J110→J8, R114→R36, C112→C49, C113→C50, U111→U8, R111→R34, C111→C48, R113→R35 (J111 eliminado: cambio C5) |
| AFE/DAC CH2 | U211→U9, U212→U10, R211→R37, R212→R38+R39+R40+R41 (1M partido como en el CH1 de Altium), R213→R42+R43 (2×49k9), R214→R44, R215→R45, R218→R46, C211→C51, C216→C52, C215→C53, C212→C54, C214→C55 |
| Nuevos Rev B | A1 (NUCLEO), R47/JP1 y R48/JP2 (escalón), TP1–TP7, R49–R51 (MD0/MD1/FMT) |

## Resultado verificado (2026-11-15, Rev B)

- `verify.py`: 125 componentes, 68 redes, **0 diferencias**.
- ERC: **0 violaciones**.
- DRC con `--schematic-parity`: **0 errores, 0 diferencias de paridad**. Hay 246 conexiones sin
  rutear (normal: solo se hizo placement) y avisos de serigrafía.
- Footprint RNX0012A (U6/U7) comparado con el de JLC/EasyEDA (C1850339): los 12 pads tienen el
  mismo tamaño y separación. El de JLC está girado 90° y su origen está 0.14 mm corrido; hay que
  revisar la rotación en la vista previa del CPL de JLC.
- Ruteo: ver la sección siguiente.

## Ruteo (4 capas) y fabricación — estado al 2026-11-16

La placa está ruteada completa y verificada: DRC 0 con todos los chequeos activos, paridad 0, ERC 0,
`revisar_pistas` 0 hallazgos, 0 conexiones sin rutear y 0 pistas de In2/B.Cu bajo nodos protegidos. Las decisiones
de cada bloque están en `../PLAN_RUTEO.md` (§7–§17); las reglas y sus fuentes, en `../REGLAS.md`; los cálculos, en
`../CALCULOS.md`; el pedido a JLC, en `../fabricacion/LEEME.md`.

| Archivo | Qué hace |
|---|---|
| `config_reglas.py` | Escribe las clases de red y `pcb.kicad_dru` (mínimos de JLC, vías taponadas a ≥ 0.35 mm de los pads, reloj y SW lejos de lo analógico). Ningún chequeo del DRC queda en "ignorar". |
| `ruteo/bloques/*.py` | Un archivo por bloque con las polilíneas a mano (`PISTAS`, `VIAS`, `ZONAS`) y la explicación de cada decisión. |
| `ruteo/polilineas.py` | Aplica un bloque (`python polilineas.py <pcb> <bloque>`): valida 45°, largo ≥ 0.1 mm y giros antes de tocar la placa, y reemplaza solo el grupo `ruteo:<bloque>`. |
| `eco.py` | Movimientos de piezas: `alinear` (≤ 0.1 mm, autorizados) y `colocar` (aprobados por el dueño); los JSON quedan en `ruteo/`. |
| `ruteo/serigrafia.py` | Ubica los designadores a 1.0 mm sin pisar pads, vías, cuerpos ni máscara abierta; omite los que no caben (van en `montaje.pdf`). |
| `ruteo/cosido.py` | Propone las vías de cosido GND (`cosido.json`, que usa `bloques/b9_gnd.py`), evitando toda la serigrafía y con separación en las 4 capas. |
| `ruteo/teardrops.py` | Activa los teardrops en todos los pads y vías; `kicad-cli pcb drc --refill-zones --save-board` los genera. |
| `ruteo/verificar_bloque.py` | DRC con paridad (relleno y guardado), ERC, `revisar_pistas.py` e imágenes de las capas, en `out/verif_<bloque>/`. |
| `ruteo/revisar_pistas.py` | Chequeos que el DRC no hace (A–M): entrada a pads por el centro y por el eje, stubs, política de capas, plano GND bajo lo crítico, paralelo analógico–digital, vía GND junto a cada pad GND, desacoplos pegados y serigrafía sobre vías. |
| `ruteo/cruces_capas.py` | Cobre de F.Cu encima de cada pista de In2/B.Cu; marca nodos protegidos (SUM, filtro del DAC, cadena de 1 MΩ, realimentación). |
| `ruteo/conexion_solida.py` | Comprueba que CIN, CHF, COUT y PGND de cada buck quedan en la misma isla del relleno GND, sin alivios. |
| `ruteo/medir.py` | Mide lazos y caminos (lazo VIN–CHF–PGND, nodo FB). |
| `ruteo/geom_serigrafia.py` | Distancia al trazo real de la serigrafía (lo usan `cosido.py` y `revisar_pistas.py`). |
| `ruteo/sugerir_vias.py`, `ruteo/exportar_capas.py`, `ruteo/oraculo/` | Ayudas: correr vías a ≥ 0.35 mm, imágenes de capas, Freerouting como oráculo de factibilidad en copias. |
| `calculos.py` | Genera `../CALCULOS.md` con medidas de la placa y datos de datasheet con página. |
| `fabricacion.py` | Genera `../fabricacion/` desde un commit sin cambios: Gerber, taladros, BOM, CPL corregido, comprobación del pin 1, tenting, montaje. |
| `stock_bom.py` | Revisa `bom.csv` contra `target.json` y contra el catálogo de JLC del día (código, MPN, basic/extended, stock para 5 placas) → `../fabricacion/stock_bom.md`. |
| `revisar_gerber.py` | Revisa los Gerber con gerbonara (biblioteca existente; correr con un Python que la tenga): capas, borde, agujeros sobre pads, máscara sobre vías, serigrafía → `../fabricacion/revision_gerber.md` y vistas SVG. |

**Orden después de cambiar cualquier bloque** (KiCad cerrado):

```bash
K="C:/Program Files/KiCad/10.0/bin/python.exe"; P=hardware/pcb/pcb.kicad_pcb; R=hardware/pcb/tools/ruteo
"$K" $R/polilineas.py $P <bloque>
"$K" $R/polilineas.py $P b9_gnd --solo-borrar      # el cosido se rehace al final
"$K" $R/serigrafia.py --aplicar $P
"$K" $R/cosido.py $P $R/cosido.json && "$K" $R/polilineas.py $P b9_gnd
"$K" $R/teardrops.py $P
python $R/verificar_bloque.py <nombre>             # DRC, ERC, revisar_pistas, imágenes
"$K" $R/cruces_capas.py $P && "$K" $R/conexion_solida.py $P
```

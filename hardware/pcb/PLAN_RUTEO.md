# Plan de ruteo — punto de control 2

Estado al 15/11/2026. Todavía no hay ni una pista.

Este documento junta lo que encontró la fase A, la **decisión que bloquea el ruteo** y el plan de capas, zonas y
orden. Fuentes: `REGLAS.md`; piezas: `fabricacion/auditoria_piezas.md`.

---

## 1. Hallazgo: con la regla de cruces aprobada **no encontré solución** en 2 capas

**Regla aprobada:**
- B.Cu = plano GND.
- Solo I2C, DC_MON y DC_MON2 bajan a B.Cu, y solo en la zona digital (x ≥ 70 mm).
- Ninguna señal crítica pasa sobre B.Cu.

### 1.1 Cruces identificados por análisis topológico (placement actual)
| # | Cruce | Por qué no se evita en una capa | Cómo lo resolvería la opción A |
|---|---|---|---|
| 1 | **3V3 × 24V_PROT** | El bloque del buck de 3V3 (U6) queda encerrado por J5–D1–D2, los CIN, el bus de 24 V hacia U7 y el borde superior. La red de 24 V no tiene una pieza en serie bajo la que se pueda pasar. | Puente de 3V3 en B.Cu, de ≤ 3 mm, bajo el bus de 24 V entre los dos bloques de buck (x ≈ 40). Solo cruza potencia con potencia. |
| 2 | **5V_A × REST_OUT** | 5V_A llega a U3 (pin 8 / C7) desde la derecha. REST_OUT sale de U3 (pin 1) hacia la derecha (TP2 → C9) y tiene que cruzar el enlace C7–U3.8. | Puente de 5V_A (riel filtrado) bajo REST_OUT, a 90°. |
| 3 | **5V_A × REST_SV** | REST_SV sube de U9 a C14 entre el AFE y el ADC (x ≈ 57). 5V_A tiene que llegar a U9 y a U3, que quedan del otro lado. | Puente de 5V_A bajo REST_SV, a 90°. |
| 4 | **I2C × redes del AFE** (hacia U2/U10) | U2 y U10 están dentro de los AFE, rodeados por REST_*, la cadena de 1 MΩ y 5V_A. | **Sin resolver.** Depende de la corrida de factibilidad (sección 1.3). Candidatos: pasar bajo resistencias 0603 de la cadena (hay 0.8 mm entre pads, muy justo) o un ajuste de placement. |

### 1.2 Lo que está verificado y lo que no
| Afirmación | Estado |
|---|---|
| Cruces 1–3 | **Argumento topológico a mano** sobre las posiciones reales de los pads. Lo revisé, pero no lo validó una herramienta. |
| "Con la regla estricta quedan ~32 conexiones sin rutear" | **Indicio, no prueba.** |

Sobre ese número:
- Salió de Freerouting usado solo como prueba de factibilidad: GND al plano, todo en F.Cu salvo I2C/DC_MON/DC_MON2.
- Bajó de 74 a 32–36 y se estancó tras ~180 pasadas, de ~170 conexiones sin GND.
- Limitaciones:
  - no se guardó el resultado (SES), así que **no sé qué conexiones fallaron**;
  - la prueba usó los pads de 0.15 mm del TSOT viejo y pistas de 0.5 mm con 0.3 mm de separación en pines de paso
    0.5–0.65, así que parte de las fallas pueden ser de **acceso a pines** y no cruces;
  - no hubo corrida de control con las dos capas libres;
  - el límite de pasadas que le di no se aplicó: la clave correcta es `router.max_passes`, y su archivo de
    configuración seguía en 9999.
- Dos procesos de esa prueba quedaron vivos y se comieron la memoria del PC (~6 GB). Ya los detuve.

### 1.3 Propuesta: repetir la prueba bien (necesita tu autorización)
- Sobre una copia, con el TSOT de 0.4 mm, memoria limitada (`-Xmx3g`), `--router.max_passes=40`,
  `--router.job_timeout=00:10:00` y guardando el SES.
- Una corrida a la vez, en tres escenarios:
  1. **control**: las dos capas libres;
  2. **estricta**: la regla aprobada;
  3. **relajada**: la regla de la opción A.
- Resultado: qué conexiones fallan en cada escenario, y en la relajada el número **real** de puentes que hacen falta.
  Nada de eso se copia a la placa: el ruteo final sigue siendo por polilíneas.

## 2. Opciones (decide el dueño)

### Opción A (recomendada por defecto) — 2 capas con puentes cortos justificados
- **Nunca bajan a B.Cu ni pasan sobre un puente:**
  - relojes: MCLK, BCK, LRCK, DOUT, SAI_*;
  - SW_3/SW_5;
  - nodos de alta impedancia: SET de los LT3092, cadena de 1 MΩ, SUM, entradas del ADC, VREF;
  - IEPE_SV. No tengo la impedancia de salida del SV 12L; los < 50 Ω son solo del RG-50.
- **Pueden pasar sobre un puente corto** (≤ 3 mm, a 90°, con vías de cosido a los dos lados):
  - salidas de op-amp de baja impedancia y audio (REST_OUT/REST_SV);
  - DC_MON/DC_MON2 (DC filtrado);
  - IEPE (RG-50, < 50 Ω).
- **El puente que tienen debajo** solo puede ser de un riel **filtrado** (5V_A, 3V3_DAC*), de I2C o de una red estática.
  Nunca 3V3 crudo ni 24 V.
- **Por qué es aceptable:**
  - A frecuencias de audio, la corriente de retorno de la propia señal se reparte por el plano y no va concentrada
    bajo la pista. Una ranura de 3 mm cosida en los extremos no cambia su camino de forma medible.
  - Lo que lleva el puente es DC filtrado: 5V_A pasa por 10 Ω + 10 µF (fc ≈ 1.6 kHz). Los cruces a 90° minimizan
    el acople.
  - La regla de retorno justo debajo protege lo que sí la necesita: flancos rápidos y nodos de alta impedancia.
- **Ningún puente** queda debajo de un buck (lazo VIN-SW-PGND), del PCM1808 ni de la cadena de 1 MΩ.
- `revisar_pistas.py` verifica todo esto y lista cada puente con su coordenada.
- **Tiempo:** el ruteo es más lento, porque cada puente se diseña y se verifica.

### Opción B (alternativa) — 4 capas
- **Apilado:**
  - F.Cu: piezas y señales;
  - In1.Cu: GND entero;
  - In2.Cu: zonas de alimentación (24V_PROT, 3V3, 5V_A) y señales lentas;
  - B.Cu: señales y GND.
- **Ventajas:**
  - Cumple la regla de cruces **sin excepciones**.
  - Es lo que hacen los EVM de TI (LMR36015 y PCM1808 son de 4 capas).
  - Ruteo más rápido y limpio.
  - Mejor ruido y EMI.
  - No cambia el placement ni el esquemático. JLC Economic admite 4 capas.
- **Costo, sin verificar:** blogs de terceros dan ~USD 2–5 por 5 placas de 2 capas contra ~USD 18–25 de 4 capas, a
  100 × 100 mm, y JLC ajustó precios en agosto de 2026. El ensamblaje y las piezas cuestan igual. Hay que
  confirmarlo en el cotizador de JLC.
- **Tiempo:** es el ruteo más rápido de las tres opciones.

### Opción C — 2 capas, regla estricta y recolocación de bloques
Es un cambio grande de placement y no garantiza solución. No la recomiendo.

## 3. Plan de ruteo
**Común a A y B.** Los corredores de abajo son un **boceto**: no están verificados entre sí (por ejemplo, el cruce
5V_A–REST_OUT junto a U3 se descubrió así). Se cierran con la corrida de la sección 1.3 y bloque a bloque.

**Capas (opción A):**
- B.Cu: plano GND entero, salvo los puentes aprobados.
- F.Cu: todo lo demás, más relleno GND cosido.

En la opción B el GND va en In1 y la potencia en In2.

**Zonas y prioridades:**
| Zona | Capa | Prioridad | Conexión |
|---|---|---|---|
| GND (toda la placa) | B.Cu (In1 en B) | 0 | sólida en SMD, alivio en THT |
| GND de relleno | F.Cu | 0 | sólida en SMD, alivio en THT; islas eliminadas |
| VIN_3 / VIN_5 (24V_PROT en CIN–CHF–VIN) | F.Cu | 2 | sólida |
| VOUT 3V3 (L1, C31–C34) / 5V (L2, C41–C44, R33) | F.Cu | 2 | sólida |
| SW_3 / SW_5 (pad de L, pines 3/12 y CBOOT) | F.Cu | 3 | sólida, área mínima |

Distribución en pistas de 0.5 mm (0.3 mm donde no quepa, calculado en CALCULOS.md). Alivio térmico en J1/J5/J7,
J2/J8, A1, JP1/JP2 y TP1–TP7.

**Orden por bloques** (commit y verificación en cada uno):
1. Bucks U6/U7. **Parada para revisión en KiCad.**
2. Entrada y bus de 24 V.
3. Fuentes IEPE.
4. ADC.
5. AFE.
6. Analógicas largas.
7. Digital (I2S, I2C, DC_MON).
8. Distribución de 3V3/5V_A.
9. Planos GND y cosido.
10. Teardrops, serigrafía, fiduciales y DRC final.

Mientras no estén los planos GND (paso 9), los chequeos que dependen de ellos se corren sobre una **copia con un
relleno GND temporal en B.Cu**:
- I: GND debajo;
- F: vías sin usar.

Así, "0 hallazgos" significa algo desde el bloque 1.

**Corredores (boceto, mm desde abajo a la izquierda):**
- **24V_PROT:**
  - D2 → J1.1 → J7.1 pegado al borde (x ≈ 1.8, bajo las borneras);
  - D2 → CIN de U6 → peine por y ≈ 47 bajo los componentes de control de U6/U7 → CIN de U7.
- **3V3:** canal entre los bloques de los bucks (x ≈ 40) → [cruce 1] → corredor libre x ≈ 40.5 → franja entre los AFE
  (y ≈ 24–27): R9, R10, R11 → ADC y R46 según la corrida.
- **5V_A:** R33/C47 → franja libre (x 60–71, y 45–60) → ADC (U4.3, C17/C18) → U3 [cruce 2] y U9 [cruce 3].
- **Analógicas:**
  - IEPE por y ≈ 38–40;
  - IEPE_SV por y ≈ 9–15;
  - REST_OUT por y ≈ 42–44;
  - REST_SV por x ≈ 56.5–57.5.
- **I2S:** R22–R24 → CN3. SAI_FS/SAI_SD entran a CN3-1/2 desde la derecha, pasando entre pads de CN3.

## 4. Otras decisiones para este punto de control
| # | Tema | Propuesta | Evidencia |
|---|---|---|---|
| 1 | Piezas sin stock (JLC y LCSC lo confirman: TLV9062IDDFR 2/0, CIN 0/0, COUT 0/0, R2/R3 11/0, R10/R11 19/0) | TLV9152IDDFR (U3/U9; pinout DDF, alimentación y entrada rail-to-rail verificados en TI SBOS986E), CIN C153031 (mismo 2220), COUT C694469 (mismo 1210), C36/C46 C28234, R33 C22859, R2/R3 C22808, R10/R11 C23162 | auditoría §1–2 |
| 2 | Cambios a basic (costo) | 10 grupos de pasivos | auditoría §2 |
| 3 | Footprint TSOT-23-8 | pads de 0.40 × 1.22 mm (land pattern de ADI): 0.25 mm entre pads, puente de máscara 0.25 mm | auditoría §3 |
| 4 | Serigrafía | 1.0/0.15 mm: caben 97 de 125. Se omiten 28 (sección 5) y van a F.Fab y a `montaje.pdf` | `serigrafia.py --solo-medir` |
| 5 | Designador de J5 (obligatorio) | **bajar J1 y J7 0.6 mm** (borneras soldadas a mano). Sin eso no cabe sin ambigüedad | probado en copia: DRC sin errores nuevos |
| 6 | Borde de ensamblaje | que JLC agregue los rieles. L1/L2 y la fila de COUT quedan a 1.3 mm del borde (JLC pide 2.5 mm sin rieles) | JLC T&C |
| 7 | Fiduciales | 3 × `Fiducial_1mm_Mask2mm` en (4.5, 5), (82, 6) y (16, 44), *board only* | a ≥ 6 mm del pad más cercano |
| 8 | Nombres de red | en la fase A2, etiquetar en el esquemático las redes que hoy tienen nombre automático (SUM, divisores, PCM_BCK…). Así las clases no dependen de `Net-(...)` | las clases se asignan por patrón de nombre |

## 5. Designadores que se omitirían (a 1.0 mm, antes de rutear)
C4 C19 C20 C29 C30 C32 C33 C34 C39 C40 C42 C43 L1 L2 R6 R12 R13 R19 R22 R23 R29 R31 R33 R34 R37 U3 U4 U9.

- Las marcas de pin 1 y de polaridad de todos quedan.
- Los conectores (J*, A1, JP*) y los TP no se omiten nunca.
- Las vías GND pueden quitar algunos lugares más; el número final se informa al terminar.

## 6. Estado después del punto de control 2

**Cambios aprobados y aplicados** (commit `f78d6b1`):
- C29/C39 suben 0.3 mm; C35/C45 a la izquierda del integrado, girados 90°.
- CF = 10 pF C0G: C56 junto a U3, C57 junto a U9.
- U3/U9 TLV9152IDDFR; CIN C153031, COUT C694469, C36/C46 C125847.
- Pasivos a basic que cumplen tus criterios. CHF queda con el original de 100 V.

**Serigrafía con el bloque 1 puesto:** caben 109 de 127. Se omiten 18, ninguno U, D, J, JP ni TP:
C6 C19 C29 C30 C32 C33 C39 C40 C42 C43 L1 L2 R12 R18 R19 R22 R43 R49.

## 7. Bloque 1 — bucks U6/U7 (`tools/ruteo/bloques/b1_bucks.py`)

- **Lazo de potencia** (VIN–CHF–PGND–SW–L–COUT) entero en F.Cu, según TI SNVSB49D fig. 12-2. U7 es el mismo trazado
  desplazado 21.6 mm.
- **Pin 3 (NC) unido a SW (pin 12)** en la placa (SNVSB49D §12.1 ítem 3 y tabla de pines p.4), con una zona de SW de
  1.3 × 0.5 mm. Con pistas no se puede entrar al centro del pin 12 sin un giro de 90° ni pasar entre los pines 1/2 o
  10/11 (0.4 mm libres). No leí el layout de la EVM; la fuente es solo el datasheet.
- **Salidas del integrado:** cada pista sale del pin con el ancho del pad (0.25 mm) y se ensancha fuera de él. Así
  ninguna esquina entre pistas queda fuera del cobre del pad (por ejemplo EN–VIN en el pin 10).
- **CBOOT:** BOOT sale por la izquierda del pin 4 y baja por fuera de la pista de SW hasta C35/C45.
- **FB:** R29/R30 (R31/R32) junto al pin 7. El sensado de VOUT llega desde abajo:
  - U6: desde el tronco de 3V3;
  - U7: desde R33.1, en el punto de carga.
- **Puentes en B.Cu aprobados** bajo el bus de 24 V (bloque 2), con vías 0.6/0.3 en los extremos:

  | Red | x (mm KiCad) | y | Largo |
  |---|---|---|---|
  | 3V3, tronco | 139.8 | 116.3 → 118.5 | 2.2 mm |
  | 3V3, sensado FB U6 | 132.7 | 116.35 → 118.5 | 2.15 mm |
  | 5V, sensado FB U7 | 154.3 | 116.35 → 118.5 | 2.15 mm |

- **Zonas:** VOUT_3V3 y VOUT_5V (F.Cu, prioridad 2) sobre la salida de L1/L2 y los COUT; SW_3_PIN3 y SW_5_PIN3
  (prioridad 3).
- **Vías GND:** 13 por buck, junto a cada pad GND:
  - pines 1, 6 y 11 del integrado: 0.50–0.75 mm del pad;
  - CIN, CHF, COUT, CVCC y RFBB: 0.10–0.20 mm.
- **Anchos y vías por debajo de la clase (decisión deliberada):**
  - El ancho de clase de Potencia/Conmutado (0.5 mm) es el ancho por defecto de KiCad, no un mínimo del DRC.
  - SW a L va a 0.6 mm, VIN y PGND a 0.4–0.5 mm, el tronco de 3V3 a 0.5 mm.
  - Las salidas de pin van a 0.25 mm y el sensado de FB a 0.2 mm.
  - Las vías son 0.6/0.3 frente a 0.8/0.4 de la clase.
  - La corriente es de 5–20 mA por riel. CALCULOS.md justifica cada ancho y cada vía con IPC-2221.
  - No hay pistas de menos de 0.2 mm.
- **Pendiente para el bloque 2:** VIN de los dos lados de cada integrado (pin 2 y pin 10) se une por el bus de 24 V.

**Prueba del bus de 24 V (solo en copia, para validar los puentes):**
- El bus es una franja de zona 24V_PROT en F.Cu (y = 116.9–117.75, x = 121.3–158.3), con dientes de pista que van
  recto desde el centro de cada CIN.
- Resultado: DRC 0. Une los pines 2 y 10 de U6 y U7. Las 6 vías de los puentes quedan a ≥ 0.45 mm de la franja, y la
  franja termina a la izquierda del sensado de 5V (x = 161.275).
- **Una unión en T sobre pista desnuda la marca el DRC nativo** (`track_angle`, 90°). Tres ramas no pueden quedar
  todas a ≥ 135° entre sí, así que en toda la placa las ramificaciones van en un pad o en una zona, nunca en pista.

**Cambios al chequeo `revisar_pistas.py`** (para que lo revises):
- **B:**
  - En el centro de un pad o de una vía calcula la esquina interior entre los bordes de las dos pistas. Si cae dentro
    del cobre, se lista como «cumple»; si cae fuera, es hallazgo.
  - Ahora también marca las uniones en T sobre pista desnuda, igual que el DRC.
- **K:** ahora cubre también los pines GND SMD de los integrados. Mide borde a borde (≤ 1.0 mm). Las piezas que
  todavía no tienen ninguna pista se cuentan como pendientes.
- **L (nuevo):** condensador de desacoplo a ≤ 1.0 mm borde a borde de su pin (tabla `DESACOPLO`, se completa por
  bloque).

**Verificación** (`python tools/ruteo/verificar_bloque.py b1_bucks`):

| Chequeo | Resultado |
|---|---|
| DRC de la placa real | 26 `via_dangling`, exactamente las 26 vías GND: conectan solo en F.Cu hasta que exista el plano (bloque 9). Ninguna otra violación |
| Paridad / ERC | 0 / 0 |
| DRC de la copia con relleno GND temporal en B.Cu | 0 violaciones |
| `revisar_pistas.py` (en la copia) | **2 hallazgos (L): C36 y C46 a 3.00 mm del pin 5 (VCC)**. Decide el dueño |
| Cumple | 14 uniones en el centro de un pad con la esquina dentro del cobre; 22 pads GND con su vía (K); 4 CHF a 0.92 mm de su pin (L) |
| Conexiones sin rutear | 209 en la placa real, 178 en la copia con plano |

### 7.1 Revisión del dueño del bloque 1 (aplicada en `67b9c78`)

**Cambios hechos:**
- C36/C46 a 3.0 mm, aceptado:
  - VCC a 0.3 mm (sale del pin a 0.25 mm);
  - vía GND pegada a C36.2 (0.18 mm);
  - retorno de C36.2 al pin AGND por F.Cu (0.25 mm, a la derecha de la pista VCC).
- Clases Potencia/Conmutado con los valores reales (0.25 mm, vía 0.3/0.6). La regla `ancho_minimo_potencia` está
  probada con control.
- Plano GND de B.Cu creado (`bloques/gnd_bcu.py`). `verificar_bloque.py` lo rellena en cada verificación: el DRC
  de la placa real da 0.
- **Tenting:** comprobado en los Gerber de máscara contra una copia sin tenting (detalle en REGLAS.md §8). Ninguna
  vía tiene apertura de máscara.

**Mediciones** (`tools/ruteo/medir.py`; U7 da los mismos valores que U6):

| Medición | Valor |
|---|---|
| PGND pin 1 → C29.2 (CHF 220 nF) por F.Cu | sí, 2.61 mm de pista |
| PGND pin 11 → C30.2 por F.Cu | sí, 2.21 mm |
| Lazo VIN–CHF–PGND, lado pin 2 | 7.25 mm de perímetro, 3.32 mm² |
| Lazo VIN–CHF–PGND, lado pin 10 | 6.97 mm, 2.69 mm² |
| Nodo FB | pin 7 → R29.2 3.71 mm; R29.2 → R30.1 1.79 mm; 5.49 mm de cobre en total |
| Entrada del bus de 24 V | pin VIN solo a su CHF, CHF solo a su CIN, y el bus (zona y D2) solo a CIN |

**Pendientes anotados:**
- CALCULOS.md: los tramos SW, bobina y COUT se calculan con la corriente de rizado de la bobina en FPWM (≈ 0.42 A
  p-p a 24 V con 6.8 µH y 1 MHz para 3V3), no con 5–20 mA.
- Bloque 9: el relleno GND de F.Cu une con conexión sólida los pads GND de CIN y COUT y los pines PGND, sin alivios.

## 8. Bloque 2 — entrada y 24 V (`tools/ruteo/bloques/b2_entrada.py`)

- **Entrada:** J5.1 → D1.2 en recto (6.75 mm), luego D1.1 → D2.1 (3.56 mm), todo a 1.0 mm (camino del TVS).
- **Ramificación en pads:**
  - D2.1 reparte hacia C27.1 (bus de los bucks) y hacia J1.1;
  - J1.1 sigue a J7.1 por la izquierda de J1.2 (a ≥ 1.35 mm del borde). Así el lado derecho de J1.2 y J7.2 queda
    libre para IEPE_FEED.
- **Bus de 24 V:** franja de zona `BUS_24V` (F.Cu, y = 116.9–117.75) con dientes de 0.5 mm desde el centro de cada
  CIN. Queda encima de los tres puentes de B.Cu aprobados.
- **GND del TVS:** tres vías junto a D2.2 al plano de B.Cu. J5.2 (THT) conecta al plano con alivio térmico.
- **Verificación:**
  - DRC 0, paridad 0, ERC 0;
  - `revisar_pistas` 0 hallazgos (D2 a 0.85 mm de D1.1);
  - 0 conexiones sin rutear en 24V_PROT y 24V_IN; 169 en total.

## 9. Bloque 3 — fuentes IEPE CH1/CH2 (`tools/ruteo/bloques/b3_iepe.py`)

**Cambios previos aprobados:**
- Micro-alineación de 32 pasivos y puntos de prueba, ≤ 0.094 mm (`alineacion_bloque3.json`, commit `fdf9d7c`).
- **R6 movido** a (120.70, 139.35), horizontal y girado 180° (`colocar_bloque3.json`). Con R6 en su lugar, el enlace
  R5.1 → R6.1 no tenía camino en una capa: Freerouting lo dejó sin rutear tras 800 pasadas. Con R6 movido sale
  completo.

**Alimentación de CH2 (J7.2 → R36):**
- Queda encerrada. La conclusión es por topología más un prototipo, no un resultado del router:
  - IEPE tiene que ir de CH1 al AFE (R13). Por debajo de CH2 no puede, porque IEPE_SV va de CH2 a J8 y a R38.
  - Entonces sube por el canal entre CH1 y CH2 y pasa por encima de CH2.
  - Prototipo de ese tramo en una copia: DRC limpio. Imagen en `tools/out/bloque3_por_que_bajo_J2.png`.
  - Así R36 queda encerrado por IEPE (izquierda y arriba) y por CH2 (derecha).
- El puente en B.Cu bajo IEPE_FEED, que prefería el dueño, deja la pista encima de CH1, todavía fuera de ese
  encierro. Para llegar a R36 habría que cruzar IEPE, y eso está prohibido.
- Va por el único camino en F.Cu, el mismo que encontró Freerouting en la prueba solo en F.Cu:
  - baja por el borde izquierdo;
  - cruza en y = 153.5 bajo el bloque del BNC J2, a 1.1 mm de sus pines y 1.2 mm de sus anclajes;
  - sube por el hueco entre J2 y J8 (x = 125.5) hasta R36.1.
  - Son 0.25 mm y unos 63 mm.
- **KH-BNC75-3511** (Kinghelm, LCSC C2837588):
  - **Fotos de producto de LCSC:** el bloque cuadrado que apoya en la placa y la parte roscada son de plástico
    blanco. Solo el barril es metálico, y queda fuera del borde de la placa.
  - **Plano (rev. B 2020):** materiales cuerpo de zinc, patas de fijación de hierro y montaje de PBT blanco
    ("BNC WHITE JACK CONNECTOR"). Acota 0.5 mm entre el bloque y la placa y dibuja apoyos moldeados en la base.
  - Conclusión: el metal no toca la placa sobre la pista. No se agregó serigrafía bajo el cuerpo (la regla de
    serigrafía lo prohíbe salvo como aislamiento).

**Aviso temprano para los bloques 5 y 6 (AFE): R13.2 (entrada IEPE de CH1) queda en un bolsillo.**
- Arriba tiene R12/C4, de la red U3B+, unidos entre sí.
- Si IEPE entra desde arriba a la izquierda, corta el enlace U2.1 (VOUT del DAC) → R12.1.
- Abajo están I2C (U2.4/5) y los pull-ups R10/R11.
- A la derecha está R14.
- Con la ubicación actual, IEPE no entra a R13.2 en una capa sin cruzar una de esas redes. Probablemente R38 (CH2)
  tiene el mismo caso. Lo estudio en el bloque 5 y propongo antes de rutear.

**Ruteo:**
- Ramificación en pads (U1/U8, TP1, TP3, JP1.2, JP2.2, C1.1, R2.1, R2.2...), sin T en pista libre.
- N2 pasa por debajo de R5 y de R4, entre sus pads (0.85 mm libres, 0.325 mm de separación).
- Corredor libre para IEPE → R13 (bloque 6): sale de JP1.2 hacia la derecha y sube por x ≈ 124.3.

**Verificación:**
- DRC 0, paridad 0, ERC 0; 127 conexiones sin rutear.
- `revisar_pistas`: **4 hallazgos L**, los condensadores de entrada de los LT3092 lejos del pin. Decide el dueño:

  | Condensador | Pin | Distancia borde a borde |
  |---|---|---|
  | C2 (1 µF) | U1.8 | 4.30 mm |
  | C3 (100 nF) | U1.8 | 3.32 mm |
  | C49 (1 µF) | U8.8 | 4.04 mm |
  | C50 (100 nF) | U8.7 | 4.33 mm |

**Cambios al chequeo:**
- **I:** los puntos que caen en el anillo libre del plano alrededor de un pad THT de la misma red (donde la pista
  termina) se listan como «cumple».
  - Eran 23 de los 25 hallazgos iniciales.
  - Los otros 2 eran reales: IEPE_SV pasaba sobre el anillo de JP2.1. Se corrigió el trazado.
- **H:** IEPE_FEED e IEPE_FEED_SV se tratan como alimentación, como pidió el dueño.

### 9.1 Decisiones del dueño tras el bloque 3

- Aceptado: la ruta de 24 V de CH2 bajo J2, los condensadores de entrada de los LT3092 donde están y la ubicación
  de C56/C57.
- **Cruce de IEPE en el AFE** (CH1 hacia R13 y CH2 hacia R38), en este orden de preferencia:
  1. Bajar a B.Cu el enlace salida del DAC → R12 (o R37 en CH2), que es el tramo anterior al filtro RC: es un nivel
     casi estático.
  2. Si no cabe, bajar a B.Cu las líneas I2C en ese punto.
  3. Nunca cruzar el nodo R12/C4 después del filtro, ni el nodo SUM, ni nada de alta impedancia.
- Siempre con puente corto, a 90°, con vías de cosido, e IEPE cruzando en su tramo de baja impedancia.
- Si la opción 1 o la 2 funciona, se hace y se reporta con imagen. Solo se detiene si ninguna funciona.


## 10. Bloques 4–8: análisis antes de rutear (oráculo en copias, `tools/ruteo/oraculo/`)

**Etapa 1, redes críticas solas** (Analogica y Reloj de los bloques 4–7, solo F.Cu; las salidas de los DAC pueden ir
en B.Cu):
- Con el placement actual queda sin rutear el AFE de CH1, en dos enlaces:
  - IEPE → R13.2;
  - R16 → R18, el final de la cadena de 1 MΩ.
- Causa: en CH1, R14 y R16 están a la derecha de U3. En CH2, R39 y R40 están abajo y a la izquierda. U3 queda cerrado
  por sus redes (REST_OUT → R8, 5V_A → C7, U3B+ → C4/R12, SUM). La cadena es de alta impedancia, así que no admite
  puentes.
- **Propuesta (requiere aprobación):** R13, R14 y R16 en la columna libre x = 140.6, verticales y apilados
  (`propuesta_columna_ch1.json`):
  - IEPE entra a R13 por la izquierda, sin meterse al AFE;
  - la cadena sube y entra a R18.2 pasando entre los pads de R17;
  - DRC sin solapes de courtyard (solo serigrafía por reubicar).
- **Resultado con la propuesta:** todas las redes críticas de los bloques 4–7 salen en F.Cu, con 0 vías. Ni siquiera
  hace falta bajar la salida del DAC.
- Queda una observación: DOUT pasa a menos de 0.5 mm de R19.1. Freerouting no conoce esa regla; se corrige al trazar.

**Etapa 2: el resto** (alimentación, I2C, DC_MON*, straps), con el ruteo crítico congelado:

| Corrida | Uso de B.Cu | Bajo cuántas redes críticas | Sin rutear |
|---|---|---|---|
| B.Cu libre para esas redes | ~140 mm en 7 tramos | ~12 (REST_SV, SAI_FS/SCK, DOUT, VINL, AC_RIGHT, Y1-OUT, R39-Pad1, VSHIFT, REST_OUT…) | 3 |
| Vías penalizadas | I2C casi entero en B.Cu: entra por los pines THT de la NUCLEO, unos 37 mm por línea | ~10 | 17 |

- **Causa estructural:**
  - I2C y DC_MON/DC_MON2 nacen dentro de los dos AFE (izquierda) y van a la NUCLEO (derecha).
  - Entre ellos, las entradas del ADC y REST_SV (AFE CH2 → C14) bajan de arriba abajo.
  - 5V_A y 3V3 salen arriba y tienen que entrar a grupos cerrados (U3.8, U9.8, U4.3, el grupo 3V3 del ADC, C20/R49).
- Con la regla aprobada (puentes cortos, solo bajo redes no críticas, I2C/DC_MON solo en la zona digital), el ruteo
  no se puede completar en 2 capas.

**Decisión pendiente del dueño:**

| Opción | Qué implica |
|---|---|
| A' | 2 capas con excepciones: tramos largos de B.Cu bajo redes críticas |
| B | 4 capas (sección 2), sin excepciones; los bloques 1–3 siguen valiendo |
| C | Recolocar la mitad derecha |

Precio de 4 capas: sin cotización verificada para esta placa. Las cifras públicas son viejas o de terceros.

### 10.1 Decisiones del dueño

- **Aprobado:** R13, R14 y R16 en la columna (commit `0452393`).
- **4 capas** (commit `3ccda8e`):
  - F.Cu: señales;
  - In1.Cu: GND entero (bloque `gnd_in1`);
  - In2.Cu: alimentación y señales lentas;
  - B.Cu: señales y GND.
- **Política en `revisar_pistas` (G):** In1 sin pistas; las redes críticas solo en F.Cu, salvo DC_MON* e IEPE_FEED*.
  El chequeo I mide contra In1.

## 11. Bloque 4 — ADC PCM1808 (`tools/ruteo/bloques/b4_adc.py`)

- Topología de las redes críticas tomada del oráculo (etapa 1): todas en F.Cu.
- **Tierra:** AGND y DGND unidos debajo de U4, con una vía al plano. Cada desacoplo y cada strap a GND tiene su vía.
- **Straps:** MD1 y FMT bajan a In2.Cu, porque en F.Cu quedan encerrados por VINL y VINR. MD0 pasa por debajo del
  cuerpo de U4.
- **Reloj, distancia 0.5 mm reloj–analógica:**
  - DOUT pasa por debajo de R19 a ≥ 0.5 mm de AC_LEFT/VINL, gracias a que R19 subió 0.1 mm (ajuste autorizado,
    `alineacion_bloque4.json`).
  - LRCK pasa entre R49.1 y C20.1.
  - Y1-OUT entra a R21.1 pasando entre los pads de R21.
- **3V3 y 5V_A:** quedan las pistas pin → condensador. Las vías a In2 van en el bloque 8, en lugares reservados (ver
  docstring del bloque).
- **`polilineas.py`:** ahora valida el bloque antes de borrar nada de la placa. Antes, un bloque inválido dejaba la
  placa sin el grupo viejo.
- **Verificación:**
  - DRC 0 (incluida la regla reloj–analógica), paridad 0, ERC 0;
  - 90 conexiones sin rutear, ninguna interna del bloque 4 (faltan alimentación y REST_*);
  - `revisar_pistas`: 6 hallazgos L, para decisión del dueño:

    | Condensador | Pin | Distancia borde a borde |
    |---|---|---|
    | C17 (100 nF) | U4.3 (5V_A) | 3.42 mm |
    | C18 (10 µF) | U4.3 (5V_A) | 5.42 mm |
    | C11 (10 µF) | U4.4 (3V3) | 2.12 mm |
    | C12 (100 nF) | U4.4 (3V3) | 3.89 mm |
    | C15 (10 µF) | U4.1 (VREF) | 1.32 mm |
    | C16 (100 nF) | U4.1 (VREF) | 1.52 mm |

    C13 → Y1.1 queda a 0.52 mm.

### 11.1 Cambios después del bloque 4 (aprobados)
- **Vías taponadas:** JLC tapona las vías en 4 capas, y una vía a menos de 0.35 mm de un pad no se puede tapar. Regla
  `via_tapada_lejos_de_pad` en el `.kicad_dru`; 43 vías corridas en los bloques 1, 3 y 4 (`tools/ruteo/sugerir_vias.py`
  y a mano):
  - COUT y CIN de los bucks: vía bajo el cuerpo del condensador;
  - C29/C39 (220 nF VIN–PGND): usan la vía PGND del pin 1, a 0.475 mm;
  - C19 (10 nF, filtro de VINR): sin vía propia, no hay lugar legal; lo une el relleno GND de F.Cu (bloque 9);
  - puentes de sensado de FB de 3V3/5V: 0.05 mm a la derecha; vía del strap FMT en (163.0, 121.2).
- **Desacoplos del PCM1808:** C17 junto al pin 3 (0.71 mm); C11↔C12 y C15↔C16 intercambiados. C12 (2.12 mm) y C16
  (1.32 mm) aceptados como hallazgos; C11, C15 y C18 (10 µF) aceptados, confirmado tras el bloque 5.

## 12. Bloque 5 — AFE CH1/CH2 (`b5_afe_ch1.py`, `b5_afe_ch2.py`)
- **CH1:** todo en F.Cu.
  - Micro-ajustes autorizados: C56 +0.08 mm; C4, C6 y R9 por debajo de 1 µm (`alineacion_bloque5.json`).
  - REST_OUT: U3.1 → R8.1 → R15.2 por el hueco entre los pads de R7; R8.1 → por encima de C7 → TP2. No cabe entre U3.8 y
    C7 sin cortar el desacoplo.
  - C56.2 vuelve a TP2 entre los pads de R12 y por debajo de R12/C4. Entre R18.1 y los pads de U3 quedan 0.74 mm, sin
    lugar para la realimentación.
- **CH2:** con la colocación anterior no se podía rutear limpio.
  - El nodo R39–R40 rodeaba U10 y encerraba las salidas de SCL (U10.5) y A0 (U10.6).
  - En el grupo C57/R43, SUM, REST_SV y el nodo R42–R43 se cruzaban: hacían falta 3 entradas a 45°.
  - El oráculo tampoco lo había resuelto con la regla de entrada por el eje: salía de U9.1, U10.1 y U10.4 a 45°.
  - Prototipo en una copia → aprobado (`colocar_bloque5b.json`): R38/R39/R40 en columna en x 141.7 (el courtyard de J8
    llega a x 140.90), C57 en el lugar de C56 de CH1 y R43 vertical como R8. CH2 queda con la geometría de CH1
    desplazada 22.5 mm en y.
- **Resto de CH2 (aprobado, `colocar_bloque5c.json`):** con lo anterior, REST_SV quedaba partido en {U9.1, R43.1, R44.2}
  y {C57.2, TP4}. TP4 estaba encerrado por DC_MON2 (R44.1 → R45.2 → C55), C54 y el enlace de 5V_A de U9.8.
  - TP4, C54, R44, R45 y C55 pasaron al lugar de TP2, C7, R15, R17 y C8 de CH1. R44/R45/C55 van 0.2 mm más a la
    derecha por la columna. CH2 queda idéntico a CH1.
  - C54 queda a 0.97 mm de U9.8.
  - C57, R41 y R42 pierden el designador en la serigrafía y quedan en el PDF de montaje.
- **Aprobado por el dueño tras el bloque 5:**
  - **Nodo SUM:** el enlace CF → resistencia de entrada (C56.1 → R18.1, C57.1 → R41.1) no puede entrar por el eje con los
    quiebres fuera de los pads (1.52 mm en x, 1.76 mm en y, con el otro pad del CF al lado). Queda el enlace de 2.2 mm
    con el quiebre dentro del cobre de los pads: excepción al chequeo C (`ACEPTADOS_C` en `revisar_pistas.py`).
  - **C7:** 0.35 mm más abajo que el original; queda a 0.975 mm de U3.8. C54 (CH2) ya estaba a 0.74 mm.
  - **Desacoplos del MCP4725** (C5/C6, C52/C53): 1.22–1.48 mm de VDD. Se revisan con el límite del datasheet,
    ≤ 4 mm (DS22039D §8.3; `DESACOPLO_LIMITE`).
- **Reservado para otros bloques:**
  - I2C (bloque 7): vías a la derecha de U2/U10 en SCL (148.6, 129.5/152.0) y SDA (148.0, 130.45/152.95).
  - 5V_A (bloque 8): vías en (152.28, 120.9) junto a C7.2 y en (152.28, 143.4) junto a C54.2.
  - REST_OUT → C9 sale de TP2 y REST_SV → C14 de TP4, los dos por la derecha (bloque 6).
- **Verificación:** DRC 0, paridad 0, ERC 0, `revisar_pistas` 0 hallazgos; 29 conexiones sin rutear.

## 13. Bloque 6 — rutas analógicas largas (`b6_analogicas.py`)
Todo en F.Cu, sin vías.

- **IEPE (CH1):**
  - Sale de JP1.2 por la derecha y sube por x 124.0, entre TP5/R4 y el tramo de 24 V de CH2 (x 125.5).
  - Cruza a y 127.5 por encima del lazo IEPE_SUP_SV de U8 (0.83 mm) y entra a R13.2 por la izquierda.
  - Mide unos 33 mm; el nodo IEPE es la salida del sensor (baja impedancia).
- **IEPE_SV (CH2):**
  - Va de J8.1 a R38.2 en línea recta por y 153.825, bajo el bloque de PBT de J8. Es el mismo caso que el tramo de
    24 V bajo J2 aceptado en el bloque 3: el cuerpo queda a 0.5 mm de la placa y el metal no la toca.
  - Distancias: 1.45 mm al pad GND J8.2 y 0.91 mm al anclaje J8.3.
- **REST_OUT:**
  - Sale de TP2 por la derecha y pasa por encima de C14.
  - Pasa a 0.35 mm del sensado de 5V y a 0.39 mm de la vía GND de R51.2.
  - Entra a C9.1 desde arriba.
- **REST_SV:**
  - Sale de TP4 por la derecha y sube por x 156.5 (la vía GND de C16 está en x 157.425).
  - Entra a C14.1 por la izquierda, por debajo de REST_OUT; las dos diagonales paralelas quedan a 0.40 mm.
- **Verificación:** DRC 0, paridad 0, ERC 0, `revisar_pistas` 0 hallazgos; 25 conexiones sin rutear.
  - Faltan alimentación (3V3, 5V_A), I2C, SAI, DC_MON/DC_MON2 y dos uniones GND para el relleno.

## 14. Bloque 7 — digital (`b7_digital.py`)

### SAI (F.Cu, clase Reloj)
- El orden está invertido entre las dos puntas:
  - del lado de las resistencias, de arriba abajo: SD (R24), SCK (R22), FS (R23);
  - en A1: FS (pin 1), SD (pin 2), SCK (pin 12).
- Se resuelve como el oráculo, pero con entrada por el eje:
  - SAI_FS sale de R23.1 por arriba y sube por x 168.55–168.70, entre los pads de R22 y de R24 (0.325 mm a cada lado);
  - SAI_SD sale de R24.1 por arriba;
  - SAI_SCK sale de R22.1 por la derecha y baja por x 171.4.
- Las tres entran a A1 por la izquierda.

### I2C de CH1 (B.Cu)
- **SCL:** U2.5 → vía (148.6, 129.5), y R10.1 → entre R9 y R10 → vía (147.27, 137.1).
- **SDA:** U2.4 → R11.1 en F.Cu → vía (151.2, 133.02).
- **Recorrido común:**
  - corredor entre los AFE (y 137.55–138.15);
  - vuelta por x 157.6–158.2;
  - por debajo de TP7 (y 144.4–145.0);
  - suben por x 171.0/171.6 y entran a A1.7/A1.8 por la izquierda.

### I2C de CH2 (In2.Cu)
- U10.4/U10.5 → vías → In2 por y 151.2/152.0 → x 170.4/171.0 → A1.7/A1.8.
- En B.Cu tendría que cruzar DC_MON/DC_MON2.

### DC_MON (B.Cu)
- Recorrido:
  - R15.1 → vía → x 139.4, a la izquierda de la cadena de CH1;
  - corredor y 139.4 → x 156.3 → y 146.25, bajo la columna izquierda y el cuerpo de la NUCLEO;
  - entra a A1.27 por la izquierda.

### DC_MON2 (B.Cu e In2.Cu)
- Recorrido:
  - R44.1 → vía → corredor y 140.0 → x 155.7 → y 146.85;
  - vía en (186.6, 146.85) → In2 → A1.26.
- Llegan a A1 en orden invertido respecto de DC_MON; el cruce se hace con ese tramo en In2, bajo la NUCLEO.

### Separaciones
- DC_MON/DC_MON2 quedan a ≥ 1 mm (borde a borde) de I2C en todo el recorrido. Es el criterio del chequeo J, que solo
  mira F.Cu.

### `tools/ruteo/cruces_capas.py` (nuevo)
- Para cada pista de In2/B.Cu lista el cobre de F.Cu que tiene encima en planta.
- Marca como hallazgo los nodos protegidos: SUM, el nodo filtrado del DAC, la cadena de 1 MΩ y el nodo medio de la
  realimentación.
- **Resultado:** 0 cruces bajo nodos protegidos. Lo que queda encima es IEPE, REST_SV, SAI e I2C.

### `revisar_pistas` (chequeo I)
- El anillo libre del plano alrededor de una vía de la misma red se lista como información, igual que el de un pad
  THT. DC_MON/DC_MON2 son las primeras redes críticas que terminan en vía.

### Verificación
- DRC 0, paridad 0, ERC 0, `revisar_pistas` 0 hallazgos; 14 conexiones sin rutear.
- Faltan alimentación (bloque 8) y GND (bloque 9).

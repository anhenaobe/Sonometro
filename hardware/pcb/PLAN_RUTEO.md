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

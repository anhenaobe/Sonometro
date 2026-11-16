# Plan de ruteo — punto de control 2

Estado al 15/11/2026. Todavía no hay ni una pista. Este documento junta:
- lo que encontró la fase A;
- la **decisión que bloquea el ruteo**;
- el plan de capas, zonas y orden.

Los detalles con fuentes están en `REGLAS.md` y en `fabricacion/auditoria_piezas.md`.

---

## 1. Hallazgo principal: con la regla de cruces aprobada, el ruteo no cierra en 2 capas

**Regla aprobada:**
- B.Cu = plano GND.
- Solo I2C, DC_MON y DC_MON2 pueden bajar a B.Cu, y solo en la zona digital (x ≥ 70 mm).
- Ninguna señal crítica pasa sobre una pista de B.Cu.

### 1.1 Análisis topológico (placement actual, solo F.Cu)
1. **3V3 queda encerrado por 24V_PROT.**
   - El buck de 3V3 (U6, C27–C36, L1) está rodeado por la red de 24 V: J5–D1–D2 a la izquierda, los CIN y el bus a los
     dos bucks por debajo y el borde de la placa arriba.
   - La salida de 3V3 tiene que cruzar 24V_PROT sí o sí. No hay una pieza en serie de la red de 24 V bajo la que
     se pueda pasar.
2. **Las salidas analógicas forman paredes entre el AFE y el ADC.**
   - REST_SV va de U9 (abajo) a C14 (arriba a la izquierda del ADC), cruzando la placa en vertical por x ≈ 57.
   - REST_OUT va de U3 a C9, por arriba.
   - IEPE_SV va del BNC J8 a R38, por abajo a la izquierda.
3. **Quién tiene que cruzar esas paredes:**
   - 5V_A, que viene de R33 (arriba a la derecha) y alimenta a U3, U4 y U9;
   - 3V3, hacia el ADC y R46;
   - I2C, que va de la NUCLEO a U2 y U10, metidos dentro de los AFE.

   En la misma capa no se puede.

### 1.2 Prueba con un autorruteador
- Se usó Freerouting solo para medir factibilidad, sobre una copia: GND al plano, todo en F.Cu salvo I2C/DC_MON/DC_MON2.
- Empezó con 74 conexiones sin rutear y **se estancó entre 32 y 36 tras ~180 pasadas**, de ~170 conexiones sin contar GND.
- Un autorruteador no es óptimo, así que esto no es una prueba matemática. Pero coincide con el análisis de arriba.
- La segunda corrida (con la política relajada de la opción A) la detuvo Claude Code por falta de memoria en el PC.
  No la relancé.

## 2. Opciones (decide el dueño)

### Opción A — 2 capas con puentes cortos justificados (recomendada si 2 capas es obligatorio)
- **Nunca bajan a B.Cu ni pasan sobre un corte:**
  - relojes: MCLK, BCK, LRCK, DOUT, SAI_*;
  - nodos conmutados: SW_3, SW_5;
  - nodos de alta impedancia: SET de los LT3092, divisores de 1 MΩ, SUM, entradas del ADC, VREF.
- **Pueden pasar sobre un puente corto de B.Cu** de alimentación (≤ 3 mm, con vías de cosido a los dos lados):
  - salidas analógicas de **baja impedancia y baja frecuencia** (REST_OUT/REST_SV, salidas de op-amp hasta 20 kHz);
  - DC_MON/DC_MON2 (DC filtrado);
  - IEPE/IEPE_SV (salida de < 50 Ω del sensor);
  - I2C.
- **Por qué es seguro:**
  - A frecuencias de audio, la corriente de retorno no viaja concentrada bajo la pista: se reparte por el plano.
  - Una ranura de 3 mm con cosido en los extremos no cambia su camino de forma medible.
  - La regla de "retorno justo debajo" importa para flancos rápidos (relojes, SW) y para los nodos de alta
    impedancia (acople capacitivo), y esos quedan protegidos.
- **Puentes previstos** (se cuentan exactos al rutear y cada uno queda listado con su coordenada):
  - 3V3 bajo el bus de 24 V, entre los dos bucks (x ≈ 40);
  - 5V_A bajo REST_OUT y bajo REST_SV;
  - 3V3 hacia el ADC;
  - I2C en la zona digital y hacia U2/U10.
  - Estimado: 6–12 puentes.
- **Ninguno** queda debajo de un buck (lazo VIN-SW), del PCM1808 ni de los nodos de 1 MΩ.
- `revisar_pistas.py` verifica la regla y lista cada puente.

### Opción B — 4 capas
- **Apilado:**
  - F.Cu: piezas y señales;
  - In1.Cu: GND entero;
  - In2.Cu: zonas de alimentación (24V_PROT, 3V3, 5V_A) y señales lentas;
  - B.Cu: señales y GND.
- **Ventajas:**
  - Cumple la regla de cruces **sin excepciones**.
  - Es lo que hacen los EVM de TI (LMR36015 y PCM1808 son de 4 capas).
  - Ruteo más rápido y limpio.
  - Mejor desempeño de EMI y de ruido.
- **Costo:** JLC fabrica y ensambla 4 capas (Economic admite 2/4/6). Hay que comparar el precio en su cotizador;
  no lo verifiqué.
- No cambia el placement ni el esquemático.

### Opción C — 2 capas con la regla estricta, recolocando bloques
- Hay que reubicar el ADC junto al AFE en línea y mover la entrada de 24 V para abrir el bloque del buck de 3V3.
- Es un cambio grande de placement y no hay garantía de que alcance. No la recomiendo.

## 3. Plan de ruteo (común; los corredores exactos dependen de A o B)
**Capas (opción A):**
- B.Cu: plano GND entero, salvo los puentes aprobados.
- F.Cu: todo lo demás, más relleno GND cosido.

**Zonas y prioridades:**
| Zona | Capa | Prioridad | Conexión |
|---|---|---|---|
| GND (toda la placa) | B.Cu | 0 | sólida en SMD, alivio en THT |
| GND de relleno | F.Cu | 0 | sólida en SMD, alivio en THT; islas eliminadas |
| VIN_3 / VIN_5 (24V_PROT en CIN–CHF–VIN) | F.Cu | 2 | sólida |
| VOUT 3V3 (L1, C31–C34) / 5V (L2, C41–C44, R33) | F.Cu | 2 | sólida |
| SW_3 / SW_5 (solo pad de L + pines 3/12 + CBOOT) | F.Cu | 3 | sólida, área mínima |

- **Distribución:** pistas de 0.5 mm (0.3 mm donde no quepa, con cálculo en CALCULOS.md).
- **Alivio térmico:** J1/J5/J7, J2/J8, A1, JP1/JP2 y TP1–TP7.

**Orden por bloques (commit y verificación en cada uno):**
1. Bucks U6/U7 (TI fig. 12-2 adaptada a 2 capas: lazo de potencia en F.Cu). **Parada para revisión en KiCad.**
2. Entrada J5 → D1 → D2, bus 24V_PROT, EN, J1/J7.
3. Fuentes IEPE CH1/CH2.
4. ADC: desacoplos y vía GND en cada pad GND, AGND/DGND unidos debajo, GND entre L/R y alrededor de MCLK.
5. AFE CH1/CH2.
6. Analógicas largas: IEPE, IEPE_SV, REST_OUT, REST_SV.
7. Digital: I2S directo a CN3 (corto); I2C; DC_MON/DC_MON2 por debajo del cuerpo de la NUCLEO hasta CN4.
8. Distribución de 3V3 y 5V_A.
9. Planos GND y cosido.
10. Teardrops, serigrafía, fiduciales y DRC final.

**Corredores principales (mm desde abajo a la izquierda; opción A):**
- **24V_PROT:**
  - D2 → J1.1 → J7.1 por x ≈ 1.8 (pegado al borde, bajo las borneras);
  - D2 → CIN de U6 → peine por y ≈ 47 bajo los componentes de control de U6/U7 → CIN de U7.
- **3V3:**
  - canal entre los bloques de los bucks (x ≈ 40) → puente B.Cu bajo el peine → corredor libre x ≈ 40.5 (entre la
    fuente CH2 y el AFE);
  - franja entre los AFE (y ≈ 24–27): R9, R10, R11;
  - hacia el ADC y R46, por la franja superior (y ≈ 46.4) o por debajo, según los puentes aprobados.
- **5V_A:** R33/C47 → franja libre (x 60–71, y 45–60) → ADC (U4.3, C17/C18) → U3 (C7) → U9 (C54), con puentes bajo
  REST_OUT/REST_SV.
- **Analógicas:**
  - IEPE por y ≈ 38–40 sobre la fuente CH2;
  - IEPE_SV por y ≈ 9–15;
  - REST_OUT por y ≈ 42–44;
  - REST_SV por x ≈ 56.5–57.5 entre el AFE y el ADC.
- **I2S:** R22–R24 → CN3. SAI_FS/SAI_SD entran a CN3-1/2 desde la derecha, pasando entre pads de CN3; SAI_SCK por
  x ≈ 71.
- **I2C:** sale de CN3-7/8 hacia la zona digital y entra a los AFE por la franja central, con puentes según la opción.

## 4. Otras decisiones para este punto de control
| # | Tema | Propuesta | Evidencia |
|---|---|---|---|
| 1 | Piezas sin stock o con riesgo | TLV9152IDDFR (U3/U9), CIN C153031 (mismo 2220), COUT C694469 (mismo 1210), C36/C46 C28234, R33 C22859, R2/R3 C22808, R10/R11 C23162 | auditoría §1–2 |
| 2 | Cambios a basic (costo) | 10 grupos de pasivos | auditoría §2 |
| 3 | Footprint TSOT-23-8 | pads de 0.40 × 1.22 mm (land pattern de ADI): 0.25 mm entre pads, puente de máscara 0.25 mm | auditoría §3 |
| 4 | Serigrafía | 1.0/0.15 mm: caben 97 de 125. Se omiten 28 (lista en la sección 5) y van a F.Fab y a `montaje.pdf` | `serigrafia.py --solo-medir` |
| 5 | Designador de J5 (obligatorio) | **bajar J1 y J7 0.6 mm** (borneras soldadas a mano; abajo hay espacio libre). Sin eso no cabe sin ambigüedad | probado en copia: DRC sin errores nuevos |
| 6 | Borde de ensamblaje | que JLC agregue los rieles. L1/L2 y la fila de COUT quedan a 1.3 mm del borde (JLC pide 2.5 mm sin rieles) | JLC T&C |
| 7 | Fiduciales | 3 × `Fiducial_1mm_Mask2mm` en (4.5, 5), (82, 6) y (16, 44), *board only* | a ≥ 6 mm del pad más cercano |

## 5. Designadores que se omitirían (a 1.0 mm, antes de rutear)
C4 C19 C20 C29 C30 C32 C33 C34 C39 C40 C42 C43 L1 L2 R6 R12 R13 R19 R22 R23 R29 R31 R33 R34 R37 U3 U4 U9.

- Las marcas de pin 1 y de polaridad de todos quedan.
- Los conectores (J*, A1, JP*) y los TP no se omiten nunca.
- Al rutear, las vías GND pueden quitar algunos lugares más; el número final se informa al terminar.

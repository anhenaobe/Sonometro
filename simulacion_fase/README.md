# Simulación: ¿el condensador de acople deforma la señal del micrófono?

Responde a la objeción del profesor: *"los condensadores del acondicionamiento introducen un
desfase, y como la voz cambia de frecuencia muy rápido en una banda de 20 Hz–20 kHz, la señal
se deforma"*.

Se comparan **tres variantes del mismo front-end**, con el mismo micrófono IEPE (modelo RG-50:
12,5 V de polarización, 50 Ω de salida), la misma fuente de corriente (TL431 + 2N3906), la misma
ganancia (G = 11) y el mismo filtro antialias (dos polos de 34 kHz). **La única diferencia es
el acople**:

| Variante | Acople | Corte inferior |
|---|---|---|
| **A** | Propuesta v1: C1 = 1 µF, R_B = 100 kΩ | 1,6 Hz |
| **B** | C1 = 10 µF, R_B = 100 kΩ | 0,16 Hz |
| **C** | Idea del profesor: acople **DC**, amplificador diferencial que resta la polarización | 0 Hz (sin condensador) |

Todo es software libre (**ngspice** + Python). Corre igual en Linux, Windows o macOS.

---

## 1. Instalar y correr (Linux)

```bash
# Debian / Ubuntu / Mint
sudo apt install ngspice python3-numpy python3-matplotlib
# Fedora:  sudo dnf install ngspice python3-numpy python3-matplotlib
# Arch:    sudo pacman -S ngspice python-numpy python-matplotlib

cd simulacion_fase
bash correr_todo.sh
```

Tarda unos 10 s. Deja las figuras en `resultados/*.png` y los números en `resultados/resumen.txt`.

### Con su propia voz (muy convincente en vivo)
```bash
arecord -f S16_LE -r 48000 -c 1 -d 3 mi_voz.wav      # graba 3 s (ALSA, viene en casi todo Linux)
bash correr_todo.sh mi_voz.wav 0.5 1.0                # usa 1 s a partir de 0,5 s
```
Si `arecord` no está, grabe un WAV de 16 bits con Audacity.

---

## 2. Demostración interactiva en ngspice (para mostrar en clase)

Abrir un archivo **sin** `-b` deja la consola de ngspice abierta para graficar:

```bash
ngspice 02_ac_fase.cir
```
```text
* magnitud normalizada (dB)
plot db(v(adcA)/11) db(v(adcB)/11) db(v(adcC)/11) xlog ylimit -12 2
* fase (grados)
plot cph(v(adcA))*180/pi cph(v(adcB))*180/pi cph(v(adcC))*180/pi xlog
* retardo de grupo (segundos)  <- el dato que de verdad importa
plot -deriv(cph(v(adcA)))/(2*pi) -deriv(cph(v(adcB)))/(2*pi) -deriv(cph(v(adcC)))/(2*pi) xlog ylog
* valor puntual a 20 Hz
meas ac tg20 find -deriv(cph(v(adcA)))/(2*pi) at=20
```

```bash
ngspice 03_tran_barrido.cir      # barrido 20 Hz -> 20 kHz
```
```text
* entrada vs. salida (restando el nivel DC y dividiendo por 11), alrededor de 25 Hz
plot v(sig) (v(adcA)-1.6498)/11 (v(adcB)-1.6498)/11 (v(adcC)+0.0012)/11 xlimit 0.02 0.11
* alrededor de 100 Hz y de 1 kHz
plot v(sig) (v(adcA)-1.6498)/11 (v(adcC)+0.0012)/11 xlimit 0.225 0.255
plot v(sig) (v(adcA)-1.6498)/11 (v(adcC)+0.0012)/11 xlimit 0.5648 0.5678
```
Salir con `quit`.

---

## 3. Archivos

| Archivo | Qué hace |
|---|---|
| `modelos.lib` | 2N3906, TL431 (comportamental), micrófono IEPE, op-amp de 1 MHz |
| `circuito.inc` | Las tres variantes A, B, C conectadas a la misma señal acústica `sig` |
| `01_fuente_corriente.cir` | Corriente de la fuente vs. tensión del micrófono (0–23 V) |
| `02_ac_fase.cir` | Magnitud, fase y retardo de grupo, 0,1 Hz – 200 kHz |
| `03_tran_barrido.cir` | Transitorio: barrido logarítmico 20 Hz → 20 kHz en 1 s, 50 mV pico |
| `04_tran_voz.cir` | Transitorio: voz (sintética o grabada) |
| `generar_senal_voz.py` | Crea `senal_voz.inc` (vocal /a/ con saltos de tono, o un WAV) |
| `graficar.py` | Figuras y `resumen.txt` |
| `correr_todo.sh` | Todo lo anterior en orden |

---

## 4. Resultados (ngspice 47)

**Fuente de corriente:** 3,77 mA (RE = 470 Ω) y 2,38 mA (RE = 750 Ω). La corriente varía solo
**1,3 %** entre 0 y 20 V y se mantiene constante hasta ≈ 22 V (figura 01).

**Respuesta en frecuencia** (figura 02):

| f | A: fase / retardo de grupo | B: fase / retardo de grupo | C (sin condensador) |
|---|---|---|---|
| 20 Hz | 4,5° / **640 µs** | 0,4° / 74 µs | −0,1° / 11 µs |
| 100 Hz | 0,5° / 36 µs | −0,3° / 13 µs | −0,4° / 11 µs |
| 1 kHz | −3,8° / 11 µs | −3,8° / 11 µs | −4,1° / 11 µs |
| 20 kHz | −67° / 7 µs | −67° / 7 µs | −71° / 7,5 µs |

**Voz con saltos de tono** (120→260 Hz en 30 ms): diferencia rms entre salida y entrada, tras
quitar un retardo constante de ≈ 11 µs: **A 0,92 %, B 0,71 %, C 0,71 %** (figura 05).

---

## 5. Argumentos para la discusión

1. **Un desfase no deforma la señal; lo que la deforma es que distintas frecuencias se retrasen
   distinto** (retardo de grupo, τg = −dφ/dω). Un retardo puro desfasa todas las frecuencias y la
   forma de onda queda idéntica, solo corrida en el tiempo.
2. **Con 1 µF (A)** el condensador solo se nota por debajo de ~100 Hz: 640 µs de retardo a 20 Hz
   (1,3 % de un periodo de 50 ms). En la banda de la voz (85 Hz en adelante) el retardo ya es
   prácticamente constante (≈ 11–46 µs).
3. **Con 10 µF (B)** el condensador sigue ahí, pero el resultado con voz es **igual al de la
   variante sin condensador (C): 0,71 % frente a 0,71 %**. El único costo es ~5 s de
   estabilización al encender.
4. **"La voz cambia rápido de frecuencia"**: el circuito es lineal e invariante en el tiempo, así
   que la velocidad del cambio solo cambia el espectro, y cada componente se trata según la tabla.
   Los cambios de tono duran decenas de ms; el retardo es de µs.
5. **El desfase grande está arriba, no abajo**: −67° a 20 kHz, y **es igual en las tres variantes,
   incluida la de acople DC**, porque viene del filtro antialias que necesita *cualquier* ADC.
   Aun así el retardo de grupo apenas cambia (11 → 7 µs), así que casi no deforma.
6. Un sonómetro mide **energía (nivel rms, dB SPL)**, que no depende de la fase (Parseval).
7. La industria acopla en AC: el módulo NI 9234 para micrófonos IEPE tiene acople AC a 0,5 Hz
   (−3 dB). Fuente: https://ni.com/docs/en-US/bundle/ni-9234-specs
8. **El acople DC (C) también es válido**, pero exige que la referencia sea igual a la polarización
   del micrófono. Esa polarización cambia de un micrófono a otro y con la temperatura (ADI CN0540
   da 7–13 V). Cualquier diferencia se multiplica por 11 a la salida: 0,2 V de error dan 2,2 V.
   ADI lo resuelve con un DAC que corrige el offset (CN0540): https://www.analog.com/CN0540

---

## 6. Limitaciones (decirlas antes de que las pregunten)

- **Modelos simplificados:**
  - TL431 comportamental, sin dinámica interna.
  - Op-amp de un polo (1 MHz, 100 dB) sin límites de alimentación.
  - Micrófono = fuente ideal + 50 Ω: no incluye la respuesta propia de la cápsula, que también
    tiene su corte inferior (ventilación) y su resonancia.
  - Sin ruido.
  - Sin los diodos de protección (no conducen con señales normales).
- En la variante C la referencia se fijó **exactamente** en la polarización simulada (12,682 V).
- El filtro antialias de la propuesta v1 atenúa **−3,4 dB a 20 kHz**, en las tres variantes. Para
  cubrir bien hasta 20 kHz hay que subir los polos (p. ej. a ~100 kHz) y sobremuestrear.
  Pendiente para la versión 2.
- La subida del error de B hacia ~1 % en el barrido viene del arranque de la señal (la línea base
  tarda τ = 1 s en asentarse con 10 µF). No es una deformación de la forma de onda.

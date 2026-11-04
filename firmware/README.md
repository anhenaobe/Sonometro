# NUCLEO-L432KC — ADC+DMA, validación física OPEN

Proyecto C **STM32Cube HAL**, con captura de la entrada física. Prototipo solicitado el 2026-11-04; MCU final de PCB OPEN y F446RE conservada como propuesta anterior. Auditoría de todas las referencias disponibles: no había código de adquisición reutilizable. Base `origin/main` bbe481b; fuente IEPE conservada.

## Implementación

`PA0/ADC1_IN5 → TIM6 TRGO → DMA1_Channel1/request0 circular → SRAM → USART2 → ST-LINK VCP → PC`.

- ADC single-ended12 bits, sin oversampling ni procesamiento. SYSCLK=HSI16/PLLM1×PLLN12/PLLR4=**48MHz nominales**, APB1/APB2 sin división. TIM6 PSC0, ARR=round(48e6/fs)−1; fs inicial48k, ARR999. Comando1k–96k; no significa que esas tasas estén medidas.
- ADC SYSCLK/4=12MHz; muestreo47,5+conversión12,5 ciclos≈5µs. DMA circular1024 uint16; callbacks copian mitades512 a captura8192 y detienen temporizador. Se verifica alternancia, HT/TC simultáneos y posición DMA después de copiar. Overrun/error invalida captura; pérdidas desconocidas no se presentan como cuenta exacta.
- MCU tiene64KiB SRAM; linker usa solo SRAM1 **48KiB**, deja SRAM2 de16KiB libre y reserva ≥4KiB stack. Captura16KiB+ring2KiB; consumo total en MAP/build.
- USART2 **115200 8N1**, techo11520B/s antes de cabeceras; mono48k×uint16 necesita96000B/s. Se adquieren8192 muestras en170,667ms nominales y después se transmiten en≈1,52s. **No hay streaming continuo48k**; GAP explícito entre ráfagas. No enviar comandos durante adquisición/transmisión.
- Fs se transmite como fracción nominal48000000/(ARR+1), no medida; HSI varía con tensión/temperatura. VREF3,3V se marca asumida. No hay SPL, filtros ni cancelación de offset.

## Cableado verificado documentalmente

Fuentes: [DS11451 Rev4, pinout/AF/memoria](https://www.st.com/resource/en/datasheet/stm32l432kc.pdf), [UM1956 Rev6, tablas7/16 y §7.9](https://www.st.com/resource/en/user_manual/um1956-stm32-nucleo32-boards-mb1180-stmicroelectronics.pdf), [RM0394, ADC/TIM/DMA/SAI](https://www.st.com/resource/en/reference_manual/rm0394-stm32l41xxx42xxx43xxx44xxx45xxx46xxx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf). Comprobar revisión real de placa y puentes antes de conectar.

| Uso | MCU / función | Nucleo / conexión |
| --- | --- | --- |
| Entrada ADC | PA0, **ADC1_IN5**, analógica | **A0 CN4-12**; generador1kHz,1Vpp,offset1,65V; comprobar1,15–2,15V con osciloscopio |
| Masa | GND | **CN4-2 o CN3-4**; común con generador; CN4-4 es +5V |
| VCP TX/RX | PA2 AF7 / PA15 AF3, USART2 | SB2/SB3 según manual; PA2/A7 ocupado |
| Programación/VCP | ST-LINK integrado | USB CN1 al PC; no conecta USB nativo de aplicación |
| Indicador de adquisición | PB3 LED LD3 | Alto durante ráfaga; no es referencia precisa de fs |
| SWD | PA13/PA14 | Conservar ST-LINK |

Entrada entre0 y VDDA medida, sin transitorios. No conectar IEPE ni salida PCM centrada en2,5V. No alimentar entrada con MCU apagado sin resolver protección. El sample-and-hold requiere baja impedancia y comprobar asentamiento; protección/antialias pertenecen al bloque correspondiente.

## Compilar y programar

Dependencias utilizadas: **STM32CubeL4 1.18.1, GCC ARM 12.3.1, Python3.11.7**. Se enlazan HAL/CMSIS/startup externos conservando licencias ST/ARM, sin copiarlos al repo. Puede usarse [CubeL4 oficial v1.18.1](https://github.com/STMicroelectronics/STM32CubeL4/tree/v1.18.1) con submódulos o el paquete instalado de PlatformIO; `build.py` acepta rutas explícitas.

Desde raíz (ajustar rutas):

```powershell
python firmware/build.py --cube C:/Users/justa/.platformio/packages/framework-stm32cubel4 --gcc-bin C:/Users/justa/.platformio/packages/toolchain-gccarmnoneeabi/bin
# Solo con placa identificada y STM32CubeProgrammer CLI instalado:
STM32_Programmer_CLI -c port=SWD -w firmware/build/sonometro.elf -v -rst
```

Genera ELF/BIN/MAP y manifest con versión de compilador y hashes de fuentes. Código propio con `-Werror`, linker falla ante warnings; imagen C sin constructores/stdio/heap. Build ejecutado; **no se ejecutó programación**: no se detectó VCP ST-LINK, solo puertos Bluetooth. ADC/reloj/VCP físicos siguen OPEN. El módulo SAI se compila aunque no se activa.

## Protocolo v1

Enviar `R48000\n` y después `C`. R inválida bloquea C hasta otra R válida. Sin texto intercalado ni respuesta por muestra. Trama little-endian: cabecera64 bytes `<4sHH14I`, payload uint16 unsigned con12 bits válidos (máximo512 muestras), CRC32/ISO-HDLC `<I` de cabecera+payload:

```text
magic="IEP1", version=u16(1), header_bytes=u16(64)
sequence, capture_id, first_sample, count, fs_num, fs_den,
format(1=u12_in_u16LE), adc_bits(12), vref_uv(3300000),
total_samples, dropped_samples, adc_errors, flags, payload_bytes
```

Flags FIRST1,LAST2,GAP_BEFORE4,ERROR8,VREF_ASSUMED16. Secuencia global uint32, índice local por ráfaga; total_samples es cuenta copiada válidamente. Un error no cuantificable activa ERROR aunque dropped_samples=0. PC verifica CRC/continuidad/longitud. Fallo UART en MCU termina con LED encendido; reiniciar conservando la captura parcial, sin reintentos que oculten pérdidas.

## PCM1808/SAI: preparación, adquisición física OPEN

`pcm1808_config.c` no se llama desde main. Prepara slave RX, DMA2_Channel1/request1 circular por palabras, IRQ de DMA y SAI, I²S24 bits, dos slots32/frame64, FS activa baja y un BCK antes del primer bit, captura en flanco ascendente. Faltan callbacks half/full/error de aplicación y transporte PCM: el protocolo ADC actual no declara soporte PCM.

| PCM1808 | NUCLEO-L432KC | Sentido / AF |
| --- | --- | --- |
| BCK pin8 | PA8 **D9 CN3-12** | PCM→SAI1_SCK_A AF13 |
| LRCK pin7 | PA9 **D1 CN3-1** | PCM→SAI1_FS_A AF13 |
| DOUT pin9 | PA10 **D0 CN3-2** | PCM→SAI1_SD_A AF13 |
| SCKI pin6 | Oscilador externo12,288MHz, lógica3,3V | No generado por MCU |
| MCLK_A opcional | PA3 **A2 CN4-10**, AF13 | Sin conectar en esta opción |
| VDD/VCC | 3,3V/5V y masas comunes | Revisar capacidad, desacoplo y secuencia de fuentes |
| MD1 pin11/MD0 pin10/FMT pin12 | HIGH/HIGH/LOW antes de encender | Maestro256fs/I²S, [TI §7.3.5](https://www.ti.com/lit/ds/symlink/pcm1808.pdf) |

SCKI12,288MHz → LRCK48kHz/BCK3,072MHz, sujetos a tolerancia/jitter del oscilador. Para96k se requieren24,576MHz/6,144MHz; OPEN. Kernel SAI usa PLL-P192/7≈27,4286MHz para lógica interna; fs la determina LRCK externa. No se promete48k exacto desde PLL/RC interno.

SAI DR24 bits a derecha; helper explicita extensión de signo en complemento a dos. Verificar alineación, signo, L/R y retardo con analizador y seno real. Mantener ambos canales en DMA; terminación del analógico libre según TI/equipo ADC OPEN. Mono48k×int32=192kB/s, estéreo interno384kB/s: usar ráfagas o futuro USB nativo, no VCP continuo ni bit-banging.

USB nativo: **PA11 D10/CN3-13 DM y PA12 D2/CN3-5 DP, AF10**, sin conflicto con SAI_A ni VCP USART2. Requiere conector independiente, masa, ESD, VBUS/alimentación y relojUSB48MHz válidos; stack USB no implementado. USART1 PA9/10 sí colisionaría con SAI; evitarlo. SWD queda disponible.

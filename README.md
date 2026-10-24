# Sonómetro IEPE de un canal

Prototipo académico de sonómetro digital con micrófono IEPE externo, a desarrollar del **24 de octubre al 24 de noviembre de 2026**. Este repositorio es independiente de VibrationDAQ.

## Alcance

Adquirir un canal, transferir muestras al PC y visualizar señal temporal, RMS y FFT en Python; después calcular presión y SPL con calibración documentada. No se declara clase metrológica, cumplimiento normativo ni rendimiento acústico validado.

```text
Micrófono IEPE externo → corriente constante → protección y acoplamiento AC
→ acondicionamiento analógico → ADC de audio → STM32 → USB → Python/PC
```

**PROVISIONAL:** LT3092, NUCLEO-F446RE y PCM1808 (24 bits, hasta 96 kSPS; se utilizaría un canal de su interfaz estéreo). Alternativa inicial: ADC interno STM32 de 12 bits para desarrollar adquisición, DMA y transferencia sin esperar el ADC externo. Ninguna ruta está implementada o probada todavía.

Referencia de sensor: ROGA RG-50. Los datos aportados de la unidad son 55,6 mV/Pa, bias de 12,5 V y corriente indicada de 2,8 mA; su aplicabilidad debe verificarse antes de conectarla. La prueba de 2,4/2,8/4 mA empieza con cargas de prueba, sin micrófono.

## Cómo comenzar

1. Revisar [decisiones y fuentes oficiales](docs/decisions.md), identificar el micrófono y confirmar sus límites/certificado.
2. Asignar personas a los tres roles del [plan](docs/plan.md), comprobar existencias reales y completar la [BOM](hardware/bom.csv).
3. Ejecutar las pruebas separadas de corriente y adquisición del [protocolo](tests/README.md) para el 28 de octubre. Conservar datos crudos y configuración, incluidos fallos.
4. Implementar primero una captura reproducible en [firmware](firmware/README.md) y [software](software/README.md); integrar el sensor solo tras aprobar las verificaciones eléctricas.

Estados: **CONFIRMED** = evidencia o decisión explícita con alcance indicado; **PROVISIONAL** = candidato o meta revisable; **OPEN** = falta decidir/verificar. Ningún estado de selección equivale a prueba física aprobada.

La licencia existente se conserva en [LICENSE](LICENSE). Las referencias externas se enlazan y atribuyen en decisiones; no se incluyen copias de circuitos ni archivos de terceros.

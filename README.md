# Sonómetro IEPE de un canal

Prototipo académico de sonómetro digital con micrófono IEPE externo, a desarrollar del **24 de octubre al 24 de noviembre de 2026**. Este repositorio es independiente de VibrationDAQ.

## Alcance

Adquirir un canal, transferir muestras al PC y visualizar señal temporal, RMS y FFT en Python; después calcular presión y SPL con calibración documentada. No se declara clase metrológica, cumplimiento normativo ni rendimiento acústico validado.

```text
Micrófono IEPE externo → corriente constante → protección y acoplamiento AC
→ acondicionamiento analógico → ADC de audio → STM32 → USB → Python/PC
```

**PROVISIONAL:** LT3092 y PCM1808. **STM32L432KC es la MCU decidida**, con NUCLEO-L432KC para prototipo y PCB convencional como implementación final; F446RE se conserva como antecedente. Hay [firmware STM32Cube HAL](firmware/README.md) compilable para ADC interno de 12 bits + temporizador + DMA y capturas por bloques vía ST-LINK VCP, y [herramienta Python](software/README.md). La adquisición física sigue OPEN; SAI/PCM1808 requiere implementación y validación.

**Revisión para el 5/11:** [propuesta breve en PDF](output/pdf/propuesta-revisada-iepe.pdf), [informe de cálculos y decisiones](docs/revision-arquitectura.md) y [simulaciones reproducibles con gráficas](hardware/revision/README.md). Compara fuentes, filtros, referencias y cuatro arquitecturas ADC. Recomendación A3 condicionada a protección y pruebas; no autoriza fabricación todavía. Plazo actualizado de entrega: aproximadamente **25/11/2026**.

La [propuesta analógica](docs/analog-front-end.md) compara tres arquitecturas y entrega cálculos/netlists/simulaciones reproducibles. El contrato de protección, polarización y carga del acoplamiento previo sigue pendiente de cierre entre equipos.

Referencia de sensor: ROGA RG-50. Los datos aportados de la unidad son 55,6 mV/Pa, bias de 12,5 V y corriente indicada de 2,8 mA; su aplicabilidad debe verificarse antes de conectarla. La prueba de 2,4/2,8/4 mA empieza con cargas de prueba, sin micrófono.

## Cómo comenzar

1. Revisar [decisiones y fuentes oficiales](docs/decisions.md), identificar el micrófono y confirmar sus límites/certificado.
2. Asignar personas a los tres roles del [plan](docs/plan.md), comprobar existencias reales y completar la [BOM](hardware/bom.csv).
3. Ejecutar las pruebas separadas de corriente y adquisición del [protocolo](tests/README.md) para el 28 de octubre. Conservar datos crudos y configuración, incluidos fallos.
4. Implementar primero una captura reproducible en [firmware](firmware/README.md) y [software](software/README.md); integrar el sensor solo tras aprobar las verificaciones eléctricas.

Estados: **CONFIRMED** = evidencia o decisión explícita con alcance indicado; **PROVISIONAL** = candidato o meta revisable; **OPEN** = falta decidir/verificar. Ningún estado de selección equivale a prueba física aprobada.

La licencia existente se conserva en [LICENSE](LICENSE). Las referencias externas se enlazan y atribuyen en decisiones; no se incluyen copias de circuitos ni archivos de terceros.

# Firmware — OPEN

No hay firmware implementado ni validado. Responsable: Adquisición digital.

Primer incremento: proyecto real para NUCLEO-F446RE, ADC interno disparado por temporizador, DMA por bloques y captura reproducible en PC. Registrar versiones de herramientas, configuración/pines, fs medida, formato, contadores y pasos de compilación/flash cuando exista el proyecto.

Segundo incremento: PCM1808 por I2S/SAI con relojes y formato comprobados. Definir doble buffer y detectar overruns; conservar identificación de la ruta de adquisición. USB nativo y conexión física están OPEN; VCP del ST-LINK solo como arranque con caudal verificado.

Salida de cada incremento: evidencia [T4 y T5](../tests/README.md). No añadir controladores vacíos ni código que simule una adquisición física aprobada.

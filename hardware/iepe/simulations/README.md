# Simulaciones de fuente IEPE (LTspice)

Copias de los circuitos preparados el 27/10/2026 para el RG-50. **Solo se reportan resultados obtenidos por el usuario en LTspice con 01 y 02**; 03-07 no se han validado.

## Procedimiento para Windows
1. Clonar esta rama o descargar la carpeta y abrir PowerShell **dentro de este directorio**.
2. Ejecutar: powershell -NoProfile -ExecutionPolicy Bypass -File .\preparar_ASC.ps1
3. Abrir 01_LT3092_DC.asc en LTspice. Elegir Run y Ctrl+L. Continuar con 02 y 03.
4. Para la prueba 01 con 4,46 kΩ fija: dejar .param RL=4.46k y eliminar la instrucción .step. Para barrido de cargas, conservar .step con varios valores.
5. Para 04/05/07 ejecutar obtener_modelos_TI_Diodes.ps1, inspeccionar los archivos recibidos y la firma de los subcircuitos: puede requerirse adaptación PSpice/LTspice. No se incluyen copias de modelos de terceros.
6. El archivo 03 es una red filtrada experimental con 100 nF + RC, **no** una versión final recomendada. La alternativa de bajo ruido propuesta documentalmente usa 10 µF y requiere ensayos nuevos.

**Los archivos .cir LT3092 pueden necesitar adaptación al modelo nativo de cada instalación; los .asc generados usan el símbolo local.**

Revisar [selección](../../../docs/iepe-current-source-selection.md), [resumen](../README.md) y fuentes oficiales de LT3092, OPA192 y BSS84. Todas las variantes requieren ensayos de banco T1-T3; no conectar todavía el micrófono.

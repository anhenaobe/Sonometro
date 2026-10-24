# Aplicación PC — OPEN

No hay aplicación implementada ni resultados validados. Responsable: Adquisición digital.

Primer incremento Python: recibir bloques reales, validar secuencias/formato, guardar muestras crudas y metadatos, graficar tiempo y calcular RMS/FFT. Bibliotecas candidatas: pyserial para CDC, NumPy y Matplotlib; versiones y comandos de instalación/ejecución se fijarán al implementar y probar.

Conservar fs real, escala cuentas→voltios, ADC/ruta, ganancia, errores, versiones y datos del sensor por captura. Mostrar saturación y pérdidas; no mezclar datos sintéticos con mediciones. Segundo incremento: presión/SPL con coeficiente y procedencia de calibración, banda y estado visible cuando sea PROVISIONAL.

Criterios y formatos: [T5 y T6](../tests/README.md). Añadir código y dependencias solo al disponer de una implementación ejecutable.

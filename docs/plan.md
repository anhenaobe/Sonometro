# Plan: 24 de octubre – 24 de noviembre de 2026

Todos los hitos están **OPEN**. Las tolerancias que se proponen en pruebas son **PROVISIONAL**; acordarlas antes del ensayo y no cambiarlas para justificar un resultado.

## Responsables

| Rol | Responsabilidad | Persona |
| --- | --- | --- |
| Integración/PCB | Arquitectura, compatibilidad, BOM, esquemático, layout y revisión de fabricación | OPEN: asignar 24–25/10 |
| Electrónica IEPE | Corriente, compliance, bias, protección, acoplamiento y acondicionamiento | OPEN: asignar 24–25/10 |
| Adquisición digital | STM32, ADC, DMA, USB y Python; señal temporal, RMS, FFT y SPL | OPEN: asignar 24–25/10 |

## Milestones y criterio de salida

| Fechas de 2026 | Entrega / responsable principal | Evidencia exigida |
| --- | --- | --- |
| 24–25 octubre | Inventario y decisiones de arranque / Integración, con ambos equipos | Identificación RG-50 y límites aplicables; acceso a instrumentos, calibrador y placa; compras/plazos; banda, rango y tolerancias acordados |
| 26–28 octubre; hito **28/10** | Fuente IEPE y adquisición probadas por separado / Electrónica IEPE y Adquisición digital | Corriente 2,4/2,8/4 mA con cargas y compliance registrados; captura de señal de generador por ADC+DMA y transferencia al PC, frecuencia real y pérdidas registradas. ADC interno permitido; identificar ruta y tasa utilizada |
| 29 octubre–4 noviembre; hito **04/11** | Cadena acústica integrada / Integración, apoyo de ambos roles | Pruebas de bias y acoplamiento aprobadas antes de conectar micrófono; captura acústica reproducible sin clipping; ruido y respuesta preliminares. Si sigue ADC interno, declarar integración PCM1808 OPEN |
| 5–11 noviembre; hito **11/11** | Procesamiento SPL y calibración inicial / Adquisición digital + Electrónica IEPE | RMS/FFT verificados con señal conocida; coeficiente de calibración, nivel/frecuencia del calibrador, banda y error inicial documentados. Sin calibrador/certificado: SPL PROVISIONAL y hito de calibración OPEN |
| 12–18 noviembre; hito **18/11** | Esquemático, PCB y BOM para fabricación / Integración/PCB | Solo si la ruta final está validada: revisión eléctrica/pinout/footprints, ERC/DRC, BOM con compras verificadas, plazo de fabricación confirmado y revisión cruzada IEPE/digital. Si falla la condición, no liberar fabricación |
| 19–20 noviembre | Cierre de defectos y repetición dirigida / Cada responsable | Registro de correcciones y repetición de pruebas afectadas; congelar configuración candidata para entrega |
| **21–24 noviembre** | Validación y entrega / Integración coordina los tres roles | Corrida completa según tests, datos crudos, instrucciones reproducibles, revisión de calibración, lista de limitaciones y estado real del PCB. Entrega el 24/11 |

Prioridad diaria: ensayar, guardar evidencia y corregir el bloqueo más próximo. Revisar interfaces entre roles al integrar: tensiones, masas, ganancias, relojes, formato y pérdidas. No esperar al PCM1808 para desarrollar la ruta ADC interno → PC; tampoco liberar una PCB PCM1808 usando solo evidencia del ADC interno.

Registrar cada hito aquí con fecha real, responsable y enlace a evidencia cuando exista. No hay resultados registrados aún.

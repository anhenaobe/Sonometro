# Piezas que no monta JLC (se sueldan a mano)

THT, sin código LCSC o marcadas fuera del BOM. Los puntos de prueba TP1–TP7 son pads sin pieza. Generado por `tools/fabricacion.py`.

| Pieza | Valor | Footprint | MPN | LCSC | Nota |
|---|---|---|---|---|---|
| A1 | NUCLEO-L432KC | NUCLEO-32_Socket_2x15_P2.54mm_Row15.24mm | KH-2.54FH-1X15P-H8.5 (x2) + NUCLEO-L432KC | C2932676 (x2) | Zócalo de 2 × 1×15 hembra; la NUCLEO-L432KC va enchufada. Solo GND, I2C, SAI y DC_MON llegan a la placa. |
| J1 | EN_IEPE_CH1 | TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm_Borde | JL126-50002G01 | C394556 | Bornera: habilitación IEPE CH1 (24 V protegidos → fuente de corriente CH1). |
| J2 | BNC_MIC_CH1 | BNC_Kinghelm_KH-BNC75-3511_Horizontal | KH-BNC75-3511 | C2837588 | BNC del micrófono CH1 (centro = señal + polarización IEPE, carcasa = GND). |
| J5 | 24V_IN | TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm_Borde | JL126-50002G01 | C394556 | Bornera: entrada de 18–30 V. Protegida con D1 (SS34, polaridad) y D2 (SMBJ26A, TVS). |
| J7 | EN_IEPE_CH2 | TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm_Borde | JL126-50002G01 | C394556 | Bornera: habilitación IEPE CH2. |
| J8 | BNC_MIC_CH2 | BNC_Kinghelm_KH-BNC75-3511_Horizontal | KH-BNC75-3511 | C2837588 | BNC del micrófono CH2; el SV 12L (TNC) usa un adaptador BNC–TNC. |
| JP1 | STEP_CH1 | PinHeader_1x02_P2.54mm_Vertical | Header 1x2 2.54 + jumper |  | Tira de 2 pines + jumper: escalón de corriente CH1 para la demostración. |
| JP2 | STEP_CH2 | PinHeader_1x02_P2.54mm_Vertical | Header 1x2 2.54 + jumper |  | Tira de 2 pines + jumper: escalón de corriente CH2 para la demostración. |

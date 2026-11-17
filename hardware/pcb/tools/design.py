"""Single source of truth for the KiCad rebuild: parts, pin->net map, values, footprints.

* Everything drawn in the team's Altium project (Sonometro_2CH/*.SchDoc) is taken from
  altium.json exactly (refs, values, MPN/LCSC, connectivity).
* What Altium lacks is added from docs/connection_matrix.md:
    - 24 V input + two LMR36015 bucks (3V3, 5V) + 5V->5V_A RC filter   (BUCK_3/BUCK_5/POWER*)
    - channel 2 (SV 12L): LT3092 source (U111.. in the doc) and an AFE/DAC that mirrors the
      Altium CH1 block part-for-part (DAC A0 -> 3V3_DAC_SV, I2C address 0x61).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ALT = json.load(open(os.path.join(HERE, 'altium.json'), encoding='utf-8'))

RAILS = ['GND', '3V3', '5V', '5V_A', '24V_PROT']

REF_RENAME = {'?28': 'J3', '?55': 'J4'}
UNNAMED = {'C14.2': 'AC_RIGHT', 'C9.2': 'AC_LEFT', 'U2.3': '3V3_DAC', 'U2.1': 'DAC_RAW',
           'R13.1': 'IEPE_DIV1', 'R14.1': 'IEPE_DIV2', 'R16.1': 'IEPE_DIV3',
           'R27.1': 'BOOT0_DIV', 'R7.2': 'FB_MID'}

FP = {
    '0603_res': 'Resistor_SMD:R_0603_1608Metric',
    '0603_cap': 'Capacitor_SMD:C_0603_1608Metric',
    'RES_CRCW_0402': 'Resistor_SMD:R_0402_1005Metric',
    'CAPC10555_55N_KEM': 'Capacitor_SMD:C_0402_1005Metric',
    'CAP_CL21_SAM': 'Capacitor_SMD:C_0805_2012Metric',
    'PW14': 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
    'SOT_62IDDFR_TEX': 'Package_TO_SOT_SMD:TSOT-23-8',
    'SOT-23-6_MC_MCH': 'Package_TO_SOT_SMD:SOT-23-6',
    'TSOT-23_TS8_LIT': 'Package_TO_SOT_SMD:TSOT-23-8',
    'UFQFPN-32_STM': 'Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm',
    'OSC_KC2016Z25.0000C15XXK-4': 'Sonometro:Oscillator_Kyocera_KC2016-4Pin_2.0x1.6mm',
    'CON_2x1_TH_5MM': 'TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm',
    'H_6x1_TH_100mil': 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
}
SYM = {
    'U1': 'Reference_Current:LT3092xTS8', 'U2': 'Analog_DAC:MCP4725xxx-xCH',
    'U3': 'Sonometro:TLV9062', 'U4': 'Sonometro:PCM1808PWR',
    'U5': 'MCU_ST_STM32L4:STM32L432KCUx', 'Y1': 'Sonometro:KC2016Z25.0000C15XXK',
    'J1': 'Sonometro:Conn_01x02', 'J2': 'Connector_Generic:Conn_01x02',
    'J3': 'Connector_Generic:Conn_01x06', 'J4': 'Connector_Generic:Conn_01x06',
}
VALUE_FIX = {'R1': '10R', 'R25': '10R', 'C10': '10nF', 'C19': '10nF', 'C25': '4.7uF',
             'U4': 'PCM1808PW', 'Y1': 'KC2016Z25.0000C15XXK',
             'J1': 'EN_IEPE_CH1', 'J2': 'MIC_CH1_RG50', 'J3': 'SWD', 'J4': 'UART'}
DESC = {'J1': 'Puente/interruptor de habilitacion IEPE CH1 (24V_PROT -> IEPE_FEED)',
        'J2': 'Microfono CH1 (ROGA RG-50, IEPE): 1 = senal+polarizacion, 2 = GND',
        'J3': 'SWD: 1 3V3(sense) 2 SWDIO 3 SWCLK 4 NRST 5 GND 6 GND',
        'J4': 'UART: 1 TX 2 RX 3 GND 4 3V3 5,6 NC'}

parts = {}   # ref -> dict(sym, value, fp, mpn, lcsc, desc, src, pins{num: net|None})


def add(ref, sym, value, fp, pins, mpn='', lcsc='', desc='', src='connection_matrix.md', volt='', mount='JLC'):
    parts[ref] = dict(sym=sym, value=value, fp=fp, pins=dict(pins), mpn=mpn, lcsc=lcsc,
                      desc=desc, src=src, volt=volt, mount=mount)


# ------------------------------------------------------------------ Altium part
pin2net = {}
for n in ALT['nets']:
    name = n['names'][0] if n['names'] else None
    if len(set(n['names'])) > 1:
        raise SystemExit('net with several names: %r' % n)
    if name is None:
        for p in n['pins']:
            if p in UNNAMED:
                name = UNNAMED[p]
        if name is None and len(n['pins']) > 1:
            raise SystemExit('unnamed multi-pin net: %r' % n)
    for p in n['pins']:
        pin2net[p] = name

for aref, c in ALT['components'].items():
    ref = REF_RENAME.get(aref, aref)
    pr = c['params']
    sym = SYM.get(ref) or ('Device:R' if ref.startswith('R') else 'Device:C')
    value = VALUE_FIX.get(ref) or pr.get('Value') or pr.get('Comment')
    mpn = pr.get('Manufacturer Part Number') or pr.get('Manufacturer_Part_Number') or pr.get('MP') or ''
    lcsc = pr.get('Supplier Part Number 1') if (pr.get('Supplier 1') or '').upper() == 'LCSC' else ''
    pins = {}
    for k, net in pin2net.items():
        r, num = k.rsplit('.', 1)
        if r == aref:
            pins[num] = net
    add(ref, sym, value, FP[c['footprints'][0]], pins, mpn or '', lcsc or '',
        DESC.get(ref, ''), 'Altium ' + c['sheet'] + '.SchDoc')

# ------------------------------------------------------------- power (doc copy)
R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
C1210 = 'Capacitor_SMD:C_1210_3225Metric'
C2220 = 'Capacitor_SMD:C_2220_5750Metric'
TB = 'TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm'
BUCK_FP = 'Sonometro:Texas_RNX0012A_VQFN-HR-12_2x3mm_P0.5mm'

add('J5', 'Sonometro:Conn_01x02', '24V_IN', TB, {'1': '24V_PROT', '2': 'GND'},
    'JL126-50002G01', 'C394556', 'Entrada 18-30 V (doc J501). SIN proteccion de polaridad/TVS')


def buck(u, l, cin, chf, cout, cboot, cvcc, rtop, rbot, sfx, rail, lval, lmpn, lfp, rbotval, rbotmpn):
    add(u, 'Sonometro:LMR36015FBRNXR', 'LMR36015FBRNXR', BUCK_FP,
        {'1': 'GND', '2': '24V_PROT', '3': 'SW_' + sfx, '4': 'BOOT_' + sfx, '5': 'VCC_' + sfx,
         '6': 'GND', '7': 'FB_' + sfx, '8': None, '9': '24V_PROT', '10': '24V_PROT',
         '11': 'GND', '12': 'SW_' + sfx}, 'LMR36015FBRNXR', 'C1850339',
        'Buck 1 MHz FPWM -> ' + rail)
    add(l, 'Device:L', lval, lfp, {'1': 'SW_' + sfx, '2': rail}, lmpn)
    for c in cin:
        add(c, 'Device:C', '4.7uF', C2220, {'1': '24V_PROT', '2': 'GND'}, 'C5750X7R2A475K230KA', volt='100V')
    for c in chf:
        add(c, 'Device:C', '220nF', C0805, {'1': '24V_PROT', '2': 'GND'}, 'C0805C224K1RACTU', volt='100V')
    for c in cout:
        add(c, 'Device:C', '15uF', C1210, {'1': rail, '2': 'GND'}, 'C3225X7R1C156M250AB', volt='16V')
    add(cboot, 'Device:C', '100nF', C0603, {'1': 'BOOT_' + sfx, '2': 'SW_' + sfx}, 'C0603C104K5RACTU')
    add(cvcc, 'Device:C', '2.2uF', C0805, {'1': 'VCC_' + sfx, '2': 'GND'}, 'C0805C225K5RACTU')
    add(rtop, 'Device:R', '100k', R0603, {'1': rail, '2': 'FB_' + sfx}, 'RC0603FR-07100KL')
    add(rbot, 'Device:R', rbotval, R0603, {'1': 'FB_' + sfx, '2': 'GND'}, rbotmpn)


buck('U6', 'L1', ['C27', 'C28'], ['C29', 'C30'], ['C31', 'C32', 'C33', 'C34'], 'C35', 'C36',
     'R29', 'R30', '3', '3V3', '6.8uH', 'XAL4030-682MEC', 'Inductor_SMD:L_Coilcraft_XAL4030-XXX',
     '43.2k', 'RC0603FR-0743K2L')
buck('U7', 'L2', ['C37', 'C38'], ['C39', 'C40'], ['C41', 'C42', 'C43', 'C44'], 'C45', 'C46',
     'R31', 'R32', '5', '5V', '10uH', 'XAL4040-103MEC', 'Inductor_SMD:L_Coilcraft_XAL4040-XXX',
     '24.9k', 'RC0603FR-0724K9L')
add('R33', 'Device:R', '10R', R0603, {'1': '5V', '2': '5V_A'}, 'CRCW0603010RJNEAHP', '',
    'Filtro RC del riel analogico (doc R501)')
add('C47', 'Device:C', '10uF', C0603, {'1': '5V_A', '2': 'GND'}, 'TCC0603X5R106K100CT', 'C380314',
    'Filtro RC del riel analogico (doc C501), mismo 10uF que usa Altium')

# ---------------------------------------------------- CH2 IEPE source (doc U111)
add('J6', 'Connector_Generic:Conn_01x02', 'SV_EXT_IN', TB, {'1': 'SV_SUPPLY_EXTERNAL', '2': 'GND'},
    'JL126-50002G01', 'C394556', 'Alimentacion externa IEPE CH2 (doc J111), separada de 24V')
add('J7', 'Sonometro:Conn_01x02', 'EN_IEPE_CH2', TB,
    {'1': 'SV_SUPPLY_EXTERNAL', '2': 'IEPE_FEED_SV'}, 'JL126-50002G01', 'C394556',
    'Habilitacion IEPE CH2 (doc J112), mismo conector que J1')
add('J8', 'Connector_Generic:Conn_01x02', 'MIC_CH2_SV12L', TB, {'1': 'IEPE_SV', '2': 'GND'},
    'JL126-50002G01', 'C394556', 'Microfono CH2 (Svantek SV 12L): 1 = senal+polarizacion, 2 = GND')
add('R36', 'Device:R', '10R', 'Resistor_SMD:R_0402_1005Metric',
    {'1': 'IEPE_FEED_SV', '2': 'IEPE_SUP_SV'}, 'CRCW040210R0FKED', '', 'Espejo de R1')
add('C49', 'Device:C', '1uF', C0603, {'1': 'IEPE_SUP_SV', '2': 'GND'}, 'CL10A105KB8NNNC', 'C15849')
add('C50', 'Device:C', '0.1uF', C0603, {'1': 'IEPE_SUP_SV', '2': 'GND'}, '0603F104Z500CT', 'C83060')
add('U8', 'Reference_Current:LT3092xTS8', 'LT3092ETS8#TRPBF', 'Package_TO_SOT_SMD:TSOT-23-8',
    {'1': None, '2': 'OUT_SV', '3': 'OUT_SV', '4': 'OUT_SV', '5': 'SET_SV', '6': None,
     '7': 'IEPE_SUP_SV', '8': 'IEPE_SUP_SV'}, 'LT3092ETS8#TRPBF', '', 'Espejo de U1 (canal 2)')
add('R34', 'Device:R', '15k', R0603, {'1': 'SET_SV', '2': 'IEPE_SV'}, 'RC0603FR-0715KL', '',
    'RSET CH2: I = 10uA*15k/100R = 1.5 mA')
add('C48', 'Device:C', '0.1uF', C0603, {'1': 'SET_SV', '2': 'IEPE_SV'}, '0603F104Z500CT', 'C83060')
add('R35', 'Device:R', '100R', R0603, {'1': 'OUT_SV', '2': 'IEPE_SV'}, 'RC0603FR-07100RL', '',
    'ROUT CH2 1 %')

# ---------------------------------------- CH2 AFE + DAC: mirror of Altium CH1
MIRROR = {  # CH2 ref: CH1 ref
    'U9': 'U3', 'U10': 'U2', 'R37': 'R12', 'R38': 'R13', 'R39': 'R14', 'R40': 'R16',
    'R41': 'R18', 'R42': 'R7', 'R43': 'R8', 'R44': 'R15', 'R45': 'R17', 'R46': 'R9',
    'C51': 'C4', 'C52': 'C5', 'C53': 'C6', 'C54': 'C7', 'C55': 'C8'}
NETMAP = {'IEPE': 'IEPE_SV', 'SUM': 'SUM_SV', 'VSHIFT': 'VSHIFT_SV', 'REST_OUT': 'REST_SV',
          'DAC_F': 'DAC_F_SV', 'DAC_RAW': 'DAC_RAW_SV', '3V3_DAC': '3V3_DAC_SV',
          'DC_MON': 'DC_MON2', 'IEPE_DIV1': 'IEPE_DIV1_SV', 'IEPE_DIV2': 'IEPE_DIV2_SV',
          'IEPE_DIV3': 'IEPE_DIV3_SV', 'FB_MID': 'FB_MID_SV'}
for r2, r1 in MIRROR.items():
    p = dict(parts[r1])
    pins = {k: NETMAP.get(v, v) for k, v in p['pins'].items()}
    if r2 == 'U10':
        pins['6'] = '3V3_DAC_SV'      # A0 high -> I2C 0x61 (U2 stays 0x60)
    add(r2, p['sym'], p['value'], p['fp'], pins, p['mpn'], p['lcsc'],
        'Espejo de %s (canal 2)' % r1 + ('; A0=1 -> I2C 0x61' if r2 == 'U10' else ''),
        'mirror of Altium ' + r1)

# =====================================================================================
# v2 (2026-11-15): decisiones del equipo + correcciones. Cada cambio queda registrado y
# aparece en la guia PDF. Fuentes: UM1956 Rev 6 (NUCLEO-32), DS11451 Rev 4 (STM32L432),
# SLES177B (PCM1808), busquedas LCSC/JLCPCB y footprints bajados con easyeda2kicad.
# =====================================================================================
CHANGES = []


def change(cid, title, detail):
    CHANGES.append(dict(id=cid, title=title, detail=detail))


X7R_100N = ('CC0603KRX7R9BB104', 'C14663')        # Yageo X7R 50 V, JLC basic
for p in parts.values():
    p.setdefault('mount', 'JLC')

# C1: MCU soldado -> NUCLEO enchufada
for r in ('U5', 'C21', 'C22', 'C23', 'C24', 'C25', 'C26', 'R25', 'R26', 'R27', 'R28', 'J3', 'J4'):
    parts.pop(r)
change('C1', 'STM32 soldado → NUCLEO-L432KC enchufada',
       'Se eliminan U5, C21-C26, R25-R28, J3 (SWD) y J4 (UART). La NUCLEO trae su micro, su '
       'ST-LINK y su USB: por ese cable se programa y se envían los datos al PC.')
# C2: zocalo de la NUCLEO (UM1956 Rev 6, tabla 16; pines 1-15 = CN3-1..15, 16-30 = CN4-1..15)
NUC = {1: 'SAI_FS', 2: 'SAI_SD', 4: 'GND', 7: 'I2C_SDA', 8: 'I2C_SCL', 12: 'SAI_SCK',
       15 + 2: 'GND', 15 + 11: 'DC_MON2', 15 + 12: 'DC_MON'}
add('A1', 'Sonometro:NUCLEO-L432KC', 'NUCLEO-L432KC',
    'Sonometro:NUCLEO-32_Socket_2x15_P2.54mm_Row15.24mm',
    {str(n): NUC.get(n) for n in range(1, 31)}, 'KH-2.54FH-1X15P-H8.5 (x2) + NUCLEO-L432KC',
    'C2932676 (x2)',
    'Zocalo 2x 1x15 hembra 2.54 mm a 15.24 mm. Solo GND y senales; NO conectar +3V3, +5V ni VIN. '
    'CN4-7/CN4-8 (A5/A4) quedan libres: SB16/SB18 los unen a PB6/PB7 en la NUCLEO.',
    'cambio C2 (UM1956 tabla 16)')
parts['A1']['mount'] = 'Manual'
change('C2', 'Zócalo para la NUCLEO (A1)',
       'D1/PA9 = SAI_FS (CN3-1), D0/PA10 = SAI_SD (CN3-2), D9/PA8 = SAI_SCK (CN3-12), '
       'D4/PB7 = I2C_SDA (CN3-7), D5/PB6 = I2C_SCL (CN3-8), A0/PA0 = DC_MON (CN4-12), '
       'A1/PA1 = DC_MON2 (CN4-11), GND = CN3-4 y CN4-2. Funciones verificadas en DS11451 '
       '(PA8/9/10 = SAI1_SCK/FS/SD_A AF13; PB6/PB7 = I2C1 AF4).')
# C3: oscilador disponible en JLC, 24.576 MHz -> fs = 48 kHz exactos
y1 = parts['Y1']
y1.update(sym='Sonometro:O322524576MEEA4SC', value='24.576MHz',
          fp='Sonometro:Oscillator_YXC_SMD3225-4Pin_3.2x2.5mm', mpn='O322524576MEEA4SC', lcsc='C27869',
          desc='YXC YSO321SR 24.576 MHz 3.3 V +-25 ppm; 1 OE, 2 GND, 3 OUT, 4 VDD', src='cambio C3')
change('C3', 'Oscilador KC2016 25 MHz → YXC 24.576 MHz (C27869)',
       'El KC2016 no existe en LCSC. 24.576 MHz = 512 × 48 kHz (PCM1808 maestro 512 fs, SLES177B '
       'tabla 2): muestreo estándar de 48 kHz. Mismas funciones de pin; cambia el footprint (3.2 × 2.5 mm).')
# C4: proteccion de la entrada de 24 V
parts['J5']['pins']['1'] = '24V_IN'
parts['J5']['mount'] = 'Manual'
add('D1', 'Device:D', 'SS34', 'Diode_SMD:D_SMA', {'1': '24V_PROT', '2': '24V_IN'}, 'SS34', 'C8678',
    'Schottky 40 V 3 A en serie: bloquea la polaridad invertida (cae ~0.4 V)', 'cambio C4')
add('D2', 'Device:D_Zener', 'SMBJ26A', 'Diode_SMD:D_SMB', {'1': '24V_PROT', '2': 'GND'}, 'SMBJ26A',
    'C123820', 'TVS unidireccional 26 V (ruptura >=28.9 V): absorbe picos en 24V_PROT', 'cambio C4')
change('C4', 'Protección de entrada: D1 SS34 + D2 SMBJ26A',
       'J5 entra a la red 24V_IN; D1 (serie) bloquea la polaridad invertida y D2 recorta picos. '
       'Todo lo demás cuelga de 24V_PROT como antes.')
# C5: canal 2 alimentado de los mismos 24 V
parts.pop('J6')
parts['J7']['pins']['1'] = '24V_PROT'
for r in ('J1', 'J7'):
    parts[r]['mount'] = 'Manual'
change('C5', 'Se elimina J6 (fuente externa del canal 2)',
       'Siempre se usa la misma fuente de laboratorio de 24 V: J7 (habilitación CH2) toma 24V_PROT '
       'igual que J1. J1/J7 son puentes en serie: ahí se puede poner el amperímetro.')
# C6: lazo de correccion del DC mas rapido
for r in ('C4', 'C51', 'C8', 'C55'):
    parts[r].update(value='100nF', fp='Capacitor_SMD:C_0603_1608Metric', mpn=X7R_100N[0], lcsc=X7R_100N[1])
change('C6', 'Filtros del lazo de DC: C4/C51 y C8/C55 de 10 µF a 100 nF',
       'Filtro del DAC: 10 kΩ × 100 nF = 1 ms (antes 100 ms). Filtro de DC_MON: 5 kΩ × 100 nF = 0.5 ms '
       '(antes 50 ms). Así la corrección del DC tarda milisegundos.')
# C7: todos los 100 nF a X7R basico
n7 = 0
for r, p in parts.items():
    if p['sym'] == 'Device:C' and p['value'] in ('0.1uF', '100nF'):
        p.update(value='100nF', mpn=X7R_100N[0], lcsc=X7R_100N[1])
        n7 += 1
change('C7', f'Condensadores de 100 nF (×{n7}) a X7R: Yageo CC0603KRX7R9BB104 (C14663, JLC basic)',
       'Los 0603F104Z500CT del Altium son Y5V (pierden mucha capacidad con voltaje y temperatura).')
# C8: BNC en la placa para los microfonos
for r, net in (('J2', 'IEPE'), ('J8', 'IEPE_SV')):
    parts[r].update(sym='Sonometro:BNC', fp='Sonometro:BNC_Kinghelm_KH-BNC75-3511_Horizontal',
                    mpn='KH-BNC75-3511', lcsc='C2837588', mount='Manual',
                    pins={'1': net, '2': 'GND', '3': 'GND', '4': 'GND'},
                    value='BNC_MIC_CH1' if r == 'J2' else 'BNC_MIC_CH2')
change('C8', 'Micrófonos: borneras → BNC a 90° (Kinghelm KH-BNC75-3511, C2837588)',
       'Centro = señal + polarización IEPE, carcasa = GND. El SV 12L (TNC) usa un adaptador BNC–TNC. '
       'Es un BNC de 75 Ω: a frecuencias de audio la impedancia no importa y acopla con BNC de 50 Ω.')
# C9: escalon de corriente para la demo
add('R47', 'Device:R', '180R', R0603, {'1': 'OUT_I', '2': 'STEP1'}, '0603WAF1800T5E', 'C22828',
    'Con JP1 puesto queda en paralelo con R2||R3: I = 10uA(1+21k/52.9R) = 3.98 mA', 'cambio C9')
add('JP1', 'Sonometro:Jumper_2_Open', 'STEP_CH1', 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
    {'1': 'STEP1', '2': 'IEPE'}, 'Header 1x2 2.54 + jumper', '', 'Escalon de corriente CH1', 'cambio C9')
add('R48', 'Device:R', '150R', R0603, {'1': 'OUT_SV', '2': 'STEP2'}, '0603WAF1500T5E', 'C22808',
    'Con JP2 puesto queda en paralelo con R35: I = 10uA(1+15k/60R) = 2.51 mA', 'cambio C9')
add('JP2', 'Sonometro:Jumper_2_Open', 'STEP_CH2', 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
    {'1': 'STEP2', '2': 'IEPE_SV'}, 'Header 1x2 2.54 + jumper', '', 'Escalon de corriente CH2', 'cambio C9')
for r in ('JP1', 'JP2'):
    parts[r]['mount'] = 'Manual'
change('C9', 'Escalón de corriente para la demo: JP1 + R47 (CH1), JP2 + R48 (CH2)',
       'CH1: 2.81 → 3.98 mA. CH2: 1.51 → 2.51 mA. Provoca el cambio de DC que el lazo debe corregir.')
# C10: puntos de prueba
for i, net in enumerate(('IEPE', 'REST_OUT', 'IEPE_SV', 'REST_SV', 'GND', 'GND', 'GND'), 1):
    add(f'TP{i}', 'Connector:TestPoint', 'TP_' + net, 'TestPoint:TestPoint_THTPad_D2.0mm_Drill1.0mm',
        {'1': net}, '', '', 'Punto de prueba (pad con agujero, sin componente)', 'cambio C10')
    parts[f'TP{i}']['mount'] = 'Ninguno'
change('C10', 'Puntos de prueba TP1–TP7',
       'IEPE, REST_OUT, IEPE_SV, REST_SV y tres GND, para medir con el osciloscopio sin soldar cables.')
# C11: pines de control del PCM1808 por resistencias de 10k (SLES177B sec. 8.2.2.1)
parts['U4']['pins'].update({'10': 'MD0', '11': 'MD1', '12': 'FMT'})
for ref, pins_, note in (('R49', {'1': '3V3', '2': 'MD0'}, 'MD0 = 1'), ('R50', {'1': 'MD1', '2': 'GND'}, 'MD1 = 0'),
                         ('R51', {'1': 'FMT', '2': 'GND'}, 'FMT = 0 (I2S)')):
    add(ref, 'Device:R', '10k', R0603, pins_, 'FRC0603J103TS', 'C2930027',
        f'{note}; el datasheet pide 10 kohm a VDD/GND', 'cambio C11')
change('C11', 'MD0/MD1/FMT del PCM1808 por resistencias de 10 kΩ (R49–R51)',
       'SLES177B sec. 8.2.2.1: "should be controlled ... by biasing with a 10 kOhm resistor to VDD or GND". '
       'MD1 = 0, MD0 = 1: maestro 512 fs; FMT = 0: I2S de 24 bits.')
change('C12', 'Alimentación de la NUCLEO',
       'La NUCLEO se alimenta por su USB. Con la placa solo comparte GND y señales; su +3V3/+5V/VIN no se '
       'conectan (connection_matrix.md: no poner en paralelo con el buck de 3V3). Orden: USB primero, luego 24 V.')

# C13/C14 (punto de control 2 del ruteo, aprobados por el dueño): footprints para fabricar en JLCPCB
for r in ('U1', 'U3', 'U8', 'U9'):
    parts[r]['fp'] = 'Sonometro:TSOT-23-8_Pad0.40x1.22mm_P0.65mm_ADI'
change('C13', 'TSOT-23-8 con pads de 0.40 × 1.22 mm (U1, U3, U8, U9)',
       'Land pattern de ADI (LTC DWG 05-08-1637): 0.25 mm entre pads en vez de 0.15 mm y puente de máscara de '
       '0.25 mm. Compatible con el de TI para DDF (pads 0.45 × 1.05, filas a 2.6 mm): cubre todo el pie de la pata '
       '(ancho máx. 0.38 mm).')
for r in ('J1', 'J5', 'J7'):
    parts[r]['fp'] = 'Sonometro:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm_Borde'
change('C14', 'Borneras con serigrafía recortada al borde (J1, J5, J7)',
       'Mismo footprint MX126 de KiCad (mismos pads). El contorno de serigrafía queda a ≥ 0.5 mm del borde y la marca '
       'de pin 1 pasa al lado derecho del cuerpo; antes quedaba fuera de la placa.')

for r, p in parts.items():                       # C15: serigrafía a >= 0.15 mm de los pads (JLC)
    if p['fp'] in ('Resistor_SMD:R_0402_1005Metric', 'Capacitor_SMD:C_0402_1005Metric',
                   'TestPoint:TestPoint_THTPad_D2.0mm_Drill1.0mm'):
        p['fp'] = 'Sonometro:' + p['fp'].split(':')[1] + '_JLC'
change('C15', 'Serigrafía a 0.15 mm de los pads (0402, puntos de prueba, Y1)',
       'Copias locales de R/C_0402 y del punto de prueba con la serigrafía recortada o agrandada a 0.15 mm de los pads '
       '(mínimo de JLCPCB); en Y1 se quitó el punto de pin 1 que caía sobre el pad (queda la escuadra exterior). '
       'Los pads no cambian.')

# C16 (aprobado): CF del sumador. Sin él, 1 MΩ de entrada y 99.8 kΩ de realimentación con la capacidad del nodo SUM
# dejan 3-6° de margen de fase (tools/analisis_opamp.py); con 10 pF C0G queda ~70° y 166 kHz de ancho de banda.
add('C56', 'Device:C', '10pF', 'Capacitor_SMD:C_0603_1608Metric', {'1': 'SUM', '2': 'REST_OUT'}, 'CL10C100JB8NNNC',
    'C1634', 'CF del sumador CH1: 10 pF C0G 50 V en paralelo con R7+R8', 'cambio C16')
add('C57', 'Device:C', '10pF', 'Capacitor_SMD:C_0603_1608Metric', {'1': 'SUM_SV', '2': 'REST_SV'}, 'CL10C100JB8NNNC',
    'C1634', 'CF del sumador CH2: 10 pF C0G 50 V en paralelo con R42+R43', 'cambio C16')
change('C16', 'Condensador de realimentación CF = 10 pF C0G en los sumadores (C56, C57)',
       'En paralelo con R7+R8 (CH1) y R42+R43 (CH2). Sin CF el margen de fase era de 3-6° (riesgo de oscilación); con '
       '10 pF queda ~70° y el ancho de banda de la señal en 166 kHz.')

# C17 (aprobado): piezas con stock en JLCPCB y pasivos a basic (mismo valor y encapsulado, tolerancia igual o mejor,
# tensión igual o mayor, mismo dieléctrico; ver fabricacion/auditoria_piezas.md). Ningún footprint cambia.
C17 = {
    ('U3', 'U9'): ('TLV9152IDDFR', 'C2861011', 'TLV9152IDDFR'),
    ('C27', 'C28', 'C37', 'C38'): ('FS55X475K101EGG', 'C153031', None),
    ('C31', 'C32', 'C33', 'C34', 'C41', 'C42', 'C43', 'C44'): ('C3225X7R1C156MT000N', 'C694469', None),
    ('C36', 'C46'): ('CC0805KKX7R9BB225', 'C125847', None),
    ('C29', 'C30', 'C39', 'C40'): ('C0805C224K1RACTU', 'C2167405', None),          # el original (100 V) con su LCSC
    ('R33',): ('0603WAF100JT5E', 'C22859', None),
    ('R2', 'R3'): ('0603WAF1500T5E', 'C22808', None),
    ('R10', 'R11'): ('0603WAF4701T5E', 'C23162', None),
    ('R1', 'R36'): ('0402WGF100JTCE', 'C25077', None),
    ('C10', 'C19'): ('CL05B103KB5NNNC', 'C15195', None),
    ('R9', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R35', 'R46'): ('0603WAF1000T5E', 'C22775', None),
    ('R4', 'R5', 'R12', 'R15', 'R17', 'R37', 'R44', 'R45', 'R49', 'R50', 'R51'): ('0603WAF1002T5E', 'C25804', None),
    ('R6',): ('0603WAF1001T5E', 'C21190', None),
    ('R7', 'R8', 'R42', 'R43'): ('0603WAF4992T5E', 'C23184', None),
    ('R29', 'R31'): ('0603WAF1003T5E', 'C25803', None),
    ('R34',): ('0603WAF1502T5E', 'C22809', None),
    ('C5', 'C9', 'C11', 'C14', 'C15', 'C18', 'C47', 'C52'): ('CL10A106KP8NNNC', 'C19702', None),
    # mismo MPN del diseño, con el código LCSC encontrado
    ('U1', 'U8'): ('LT3092ETS8#TRPBF', 'C462641', None),
    ('U2', 'U10'): ('MCP4725A0T-E/CH', 'C144198', None),
    ('U4',): ('PCM1808PWR', 'C55513', None),
    ('L1',): ('XAL4030-682MEC', 'C3040663', None),
    ('L2',): ('XAL4040-103MEC', 'C5144883', None),
    ('R30',): ('RC0603FR-0743K2L', 'C137720', None),
    ('R32',): ('RC0603FR-0724K9L', 'C137761', None),
}
for refs, (mpn, lcsc, value) in C17.items():
    for r in refs:
        parts[r]['mpn'], parts[r]['lcsc'] = mpn, lcsc
        if value:
            parts[r]['value'] = value
change('C17', 'Piezas con stock en JLCPCB y pasivos a basic',
       'U3/U9 TLV9152IDDFR (TLV9062IDDFR sin stock; mismo pinout DDF). CIN PSA C153031 y COUT TDK C694469 (mismo valor, '
       'tensión y tamaño; capacitancia efectiva verificada). C36/C46 YAGEO X7R 50 V. Resistencias y 10 nF/10 µF a basic '
       '(tolerancia igual o mejor, misma tensión y dieléctrico). Códigos LCSC agregados a las piezas que no tenían.')

# ------------------------------------------------------------------- sanity
for ref, p in parts.items():
    for num, net in p['pins'].items():
        assert net is None or isinstance(net, str), (ref, num, net)

if __name__ == '__main__':
    import collections
    nets = collections.defaultdict(list)
    for ref, p in parts.items():
        for num, net in p['pins'].items():
            if net:
                nets[net].append(f'{ref}.{num}')
    print(len(parts), 'parts;', len(nets), 'named nets')
    for n, m in sorted(nets.items()):
        if len(m) < 2:
            print('  SINGLE-PIN NET', n, m)
    json.dump({r: p for r, p in parts.items()}, open(os.path.join(HERE, 'target.json'), 'w'), indent=1)
    json.dump(CHANGES, open(os.path.join(HERE, 'changes.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

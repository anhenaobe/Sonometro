"""Build the short Spanish professor brief from reproducible results, not measurements."""
import csv,json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'hardware/revision'
OUT=ROOT/'output/pdf';OUT.mkdir(parents=True,exist_ok=True)
FONT=Path('C:/Windows/Fonts/arial.ttf');BOLD=Path('C:/Windows/Fonts/arialbd.ttf')
if FONT.exists():
    pdfmetrics.registerFont(TTFont('Body',str(FONT)))
    pdfmetrics.registerFont(TTFont('BodyBold',str(BOLD)))
else:
    # ReportLab Vera is distributed with reportlab; avoid an unrecorded font dependency.
    import reportlab
    fonts=Path(reportlab.__file__).parent/'fonts'
    pdfmetrics.registerFont(TTFont('Body',str(fonts/'Vera.ttf')))
    pdfmetrics.registerFont(TTFont('BodyBold',str(fonts/'VeraBd.ttf')))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('Text',fontName='Body',fontSize=9.5,leading=13,spaceAfter=7,textColor=colors.HexColor('#223047')))
styles.add(ParagraphStyle('SmallText',parent=styles['Text'],fontSize=8,leading=10.5,spaceAfter=4))
styles.add(ParagraphStyle('BigTitle',parent=styles['Text'],fontName='BodyBold',fontSize=22,leading=26,spaceAfter=12))
styles.add(ParagraphStyle('SectionTitle',parent=styles['Text'],fontName='BodyBold',fontSize=14,leading=18,spaceBefore=6,spaceAfter=9))
story=[]
def para(t,style='Text'):story.append(Paragraph(t,styles[style]))
def title(t):para(t,'SectionTitle')
def table(rows,widths):
    data=[[Paragraph(str(v),styles['SmallText']) for v in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8f3')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#b6c5d6')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(t);story.append(Spacer(1,10))
def fig(name,width,height):story.append(Image(str(HERE/'figures'/name),width=width,height=height))
def footer(c,doc):
    c.setFont('Body',8);c.setFillColor(colors.HexColor('#53647a'))
    c.drawString(38,25,'Sonometro IEPE | Propuesta de ingeniería | 5 noviembre 2026')
    c.drawRightString(A4[0]-38,25,f'{doc.page}')

para('Sonómetro IEPE de un canal','BigTitle')
para('Propuesta revisada para discusión con el profesor - 5 de noviembre de 2026')
para('<b>Estado PROVISIONAL:</b> cálculos y simulaciones matemáticas reproducibles. Ningún circuito, captura física ni rendimiento acústico validado. STM32L432KC y PCB son decisiones cerradas.')
title('Recomendación: arquitectura 3, condicionada a pruebas')
para('<b>RG-50 → LT3092 → buffer OPA2192 a 24 V → divisor 1690/1000 Ω → Sallen-Key suave a 75 kHz → único acoplamiento AC de 4,7 µF → PCM1808 a 96 kSPS → SAI / STM32L432KC → PC.</b>')
para('La alta impedancia del primer buffer evita cargar la salida del sensor. El capacitor se sitúa al final para usar la polarización interna del ADC, sin V_MID externa. El doble OPA2192 utiliza una sola alimentación de 24 V. Esta opción exige protección directa del ADC y comprobación del filtro y sus cargas.')
table([['Resultado calculado','Valor / alcance'],
['Ganancia nominal','1000/2690 = 0,371747; 130 dB SPL pico → 3,516 V pico del sensor → 1,307 V pico al ADC.'],
['Filtro analógico','R1=1370 Ω + Rth=628,253 Ω; R2=2000 Ω; C1=1500 pF; C2=750 pF; f0=75,059 kHz; Q=0,707107.'],
['Banda propuesta','20 Hz-20 kHz. Modelo de cadena: -0,0394 dB a20 Hz y -0,0220 dB a20 kHz, antes de ripple FIR publicado.'],
['Ruido solo AFE','3,777 µV RMS referidos al sensor, 20 Hz-20 kHz, típico equivalente; excluye sensor, fuente y ADC.'],
['Costos de tres IC','LT3092 TSOT + OPA2192 + PCM1808: ~15,77 USD sin pasivos, protección, fuente, PCB ni envío.']],[125,390])
para('Sensibilidad 55,6 mV/Pa y bias ~12,5 V son provisionales para la unidad concreta. Catálogo RG-50: 2-20 mA, 18-30 V y máximo130 dB pico. Obtener identificación y certificado antes de conexión. Un segundo SV12/SV12L requiere identificar preamplificador y cápsula; no asumir compatibilidad de corriente.','SmallText')
title('Lo que impide liberar PCB hoy')
para('Protección ante encendido/desconexión y ADC apagado; capacitor real de baja fuga/absorción; ruido no ponderado del PCM a96 kSPS; stock y entrega local; reloj/SAI y transferencia por bloques. El circuito no está aprobado para fabricación.')
story.append(PageBreak())

title('Comparación de banda, fase y retardo')
fig('02_bode_arquitecturas.png',490,490)
para('Curvas de redes equivalentes, no capturas. La fase y el retardo mostrados retiran el retardo constante publicado del ADC para hacer visible la dispersión. FIR internos no disponibles: no se inventaron coeficientes. ADS8681 se representa mediante un Bessel equivalente a15 kHz, no su circuito interno.','SmallText')
table([['Ruta','Decisión'],['A1: Codex + PCM48','El capacitor1 µF queda cargado por el divisor: ~-0,60 dB a20 Hz. Conservar como antecedente.'],['A2: ADS8681 bipolar','SPI y entrada bipolar simplifican polarización. Su LP interno es -3 dB a15 kHz y -0,1 dB a2,5 kHz: no elegir para banda plana20 kHz.'],['A4: ADS127L01 diferencial','64 kSPS WB1, ruido3,79 µV RMS típico en condiciones de ficha. Requiere driver diferencial, referencia y más trabajo; no es bipolar físico respecto aGND.']],[135,380])
para('Un retardo constante desplaza la onda; un retardo de grupo variable cambia su forma. Para señales estacionarias LTI sin clipping, la fase sola no cambia RMS de banda completa. Sí puede cambiar picos y mediciones en ventanas transitorias. La magnitud altera SPL según el espectro.','SmallText')
story.append(PageBreak())

title('Amplificación y referencias: dos correcciones')
para('<b>Voxter:</b> Rf10k || Cf470p y Rg1k producen NG=(11+sτ)/(1+sτ), τ=4,7 µs: una ganancia que tiende a1, no un integrador. La red de salida1k/4,7n añade otro polo. Pérdida a20 kHz: -2,591 dB ideal; -3,423 dB con aproximación GBW1 MHz. Ganancia11 satura cerca de98,76 dB SPL RMS, bajo supuesto de1,5 V pico disponible.')
para('<b>V_MID:</b> procede del divisor10k/10k,10 µF y buffer; los1N4148 solo limitan aproximadamente en la entrada del opamp. No son referencia de precisión ni protegen automáticamente su salida/ADC. En audio Vmid→salida tiene ganancia cercana a-10; no+1.')
fig('07_referencias.png',490,327)
para('Perturbaciones deterministas sintéticas, sin clipping. Rizado compartido de VDDA=10 mV pico,100 Hz, seno94 dB/1 kHz. Se aplica la transferencia real de Vmid antes de convertir. El caso ideal de seguimiento ratiométrico es otra topología: cancela baseline, pero conserva modulación de escala. El nivel10 µV inyectado no es ruido garantizado de REF5025.','SmallText')
title('Precisión y ruido: conservar las condiciones de ficha')
para('STM32L432: ADC nativo12 bits, ENOB típico~10,4 en condiciones amplias de ficha. Entradas diferenciales pueden dar diferencia negativa, pero ambos pines siguen dentro de0…VREF+. UFQFPN32 une VDDA/VREF+; no hay VREFBUF utilizable. Sobremuestrear no garantiza16 bits efectivos.')
para('PCM: SNR99 dBA y24 bits nominales no son24 bits efectivos ni ruido20 Hz-20 kHz sin ponderación. El RG-50 publica32 dB SPL de ruido5 Hz-20 kHz: discutir si medir30 dB es objetivo viable. No sumar indiscriminadamente errores de ganancia/offset, ruido aleatorio y cuantización ya incluida en SNR.','SmallText')
story.append(PageBreak())

title('Siguiente prueba física y plan de integración')
para('<b>Primero:</b> fuente IEPE24 V limitada, sin micrófono ni ADC. Cargas4,46 kΩ y5,72 kΩ, al menos0,25 W. Medir corriente, tensión, temperatura, ruido y transitorios de encendido/desconexión. Ensayar2,4/2,8/4 mA; no declarar compatibles sin identificar y comprobar el sensor.')
para('<b>Después:</b> generador con offset12,5 V, Rs50 Ω y seno1 kHz/55,73 mV RMS. Sustituir ADC por60 kΩ a2,5 V. Medir ganancia, seis frecuencias, fase, THD y hasta3,516 V pico. No conectar ADC hasta demostrar límites de tensión/corriente en secuencias de alimentación, sensor abierto y ADC apagado.')
table([['Bloque','Estado / cambio requerido'],['Fuente IEPE','LT3092 sigue principal.120k/430Ω calcula2,8007 mA y menor error poroffset que20k/71,5Ω; nuevo ruido/arranque OPEN. TL431+PNP depende deVBE/β. LM334 deriva~0,336%/K.'],['Firmware existente','Conservado: ADC+TIM6+DMA,48kSPS nominal,8192 muestras, transferencia binaria posterior porVCP115200. No se reescribe ni se afirma prueba física.'],['PCM96 porSAI','PA8 BCK,PA9 FS,PA10 SD AF13; oscilador24,576 MHz aPCM maestro. Confirmar6,144 MHz BCK y96 kHz LRCK. Configurar24 bits firmados en32 y tratar canal2.'],['PC y transporte','Reutilizar receptor Python, secuencias/CRC. Mono96k/32bits=384 kB/s: VCP no ofrece flujo continuo. Empezar por capturas; USB nativo requiere conexión independientePA11/PA12 y nueva implementación.'],['Calendario','11/11 integración;18/11 liberarPCB solo con protección y pruebas;21-25/11 ensamblaje, validación y entrega real.']],[115,400])
title('Evidencia entregada y límites')
para('Diez conjuntos de gráficas, CSV/JSON, scripts y netlist. Ocho comprobaciones numéricas de modelos pasan; no son pruebas físicas. ngspice46 + modelo oficial TI OPA192: fallo de punto de operación por matriz singular interna; log conservado, sin resultados SPICE aceptados. LTspice no disponible; simulación LT3092 previa no repetida. Informe detallado: docs/revision-arquitectura.md. Reproducción: hardware/revision/README.md.','SmallText')
title('Preguntas para decidir con el profesor')
para('¿Banda20 Hz-20 kHz y error eléctrico calibrado≤0,2 dB? ¿Qué error de fase, retardo y ventana RMS exige? ¿Límite inferior realista con RG-50? ¿Acepta película radial sobre PCB si no haySMD adecuado? ¿Presupuesto y plazo de fabricación? ¿Se admite alternativa ADS8681 de banda≤2,5 kHz?','SmallText')
para('<b>Fuentes oficiales:</b> ST DS11451 y RM0394; TI PCM1808/SLES177B, ADS8681/SBAS633E, ADS127L01, OPA192; ADI LT3092 Rev.D; ficha ROGA RG-50. Enlaces y condiciones en el informe. Precios/stock son instantáneas de páginas DigiKey consultadas4/11 local, sin garantía de entrega.','SmallText')

pdf=OUT/'propuesta-revisada-iepe.pdf'
doc=SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=38,leftMargin=38,topMargin=35,bottomMargin=42,
    title='Propuesta revisada de sonometro IEPE',author='Equipo Sonometro - revision tecnica')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
import fitz
render=HERE/'runs/pdf';render.mkdir(parents=True,exist_ok=True)
with fitz.open(pdf) as rendered:
    for i,page in enumerate(rendered):page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(render/f'page-{i+1}.png')
    print(f'PDF: {pdf}; pages: {len(rendered)}; renders: {render}')

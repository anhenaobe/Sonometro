* circuito.inc - Tres variantes del front-end IEPE alimentadas por la MISMA senal
* acustica (nodo sig). Cada variante tiene su propia fuente de corriente y su
* propio "microfono" identico (RG-50: VBIAS = 12,5 V, ROUT = 50 ohm).
*
*  A) Propuesta v1: acople AC C1 = 1 uF, RB = 100 k  (fc = 1,6 Hz), G = 11, antialias 34 kHz
*  B) Igual que A pero C1 = 10 uF                      (fc = 0,16 Hz)
*  C) Acople DC (idea del profesor): amplificador diferencial que resta una
*     referencia igual a la polarizacion, G = 11, mismo antialias. Sin condensador.
*
* Salidas: adcA, adcB, adcC (lo que veria el ADC). Ganancia nominal 11 en todas.
* -----------------------------------------------------------------------------
.include modelos.lib

.param RB=100k RS=4.7k RG=1k RF=10k CF=470p RO=1k CO=4.7n

Vcc  vcc  0 24
Vmid vmid 0 1.65

* --- Variante A: acople AC 1 uF ---------------------------------------------
XIA vcc nA FUENTE_I RE=470
XMA nA sig MIC VBIAS=12.5 ROUT=50
C1A nA xA 1u
RBA xA vmid {RB}
RSA xA pA {RS}
XOA pA mA oA OPAMP
RGA mA vmid {RG}
RFA mA oA {RF}
CFA mA oA {CF}
ROA oA adcA {RO}
COA adcA 0 {CO}

* --- Variante B: acople AC 10 uF --------------------------------------------
XIB vcc nB FUENTE_I RE=470
XMB nB sig MIC VBIAS=12.5 ROUT=50
C1B nB xB 10u
RBB xB vmid {RB}
RSB xB pB {RS}
XOB pB mB oB OPAMP
RGB mB vmid {RG}
RFB mB oB {RF}
CFB mB oB {CF}
ROB oB adcB {RO}
COB adcB 0 {CO}

* --- Variante C: acople DC con amplificador diferencial ---------------------
* Vout = (110k/10k) * (V(nC) - Vref). Vref = polarizacion medida del microfono.
* (En la practica Vref vendria de una referencia de precision + DAC/trimmer,
*  como en ADI CN0540; el op-amp necesitaria alimentacion +-15 V.)
XIC vcc nC FUENTE_I RE=470
XMC nC sig MIC VBIAS=12.5 ROUT=50
VrefC refC 0 12.682
R1P nC pC 10k
R2P pC 0 110k
R1N refC mC 10k
R2N mC oC 110k
* Mismo polo de 34 kHz que C_F en A/B (110k || 43 pF), en ambas ramas (simetria)
CFN mC oC 43p
CFP pC 0 43p
XOC pC mC oC OPAMP
ROC oC adcC {RO}
COC adcC 0 {CO}

"""Explicit engineering equivalents, NOT manufacturer SPICE macromodels.

Analog networks are derived from circuit laws. Unknown converter filter coefficients
are never invented: only documented passband/delay and separately labelled fits.
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy import signal

SENS = .0556
P0 = 20e-6
K = 1.380649e-23
TEMP = 300.
CHECK_HZ = np.array([20.,100.,1000.,4000.,10000.,20000.])
ALPHA = 1000/2690
RTH = 1690*1000/2690


def pressure(level, peak=False):
    p=P0*10**(level/20)
    return {'p_rms_Pa':p/math.sqrt(2) if peak else p,
            'p_peak_Pa':p if peak else p*math.sqrt(2),
            'sensor_Vrms':SENS*p/math.sqrt(2) if peak else SENS*p,
            'sensor_Vpeak':SENS*p if peak else SENS*p*math.sqrt(2)}


def dbspl(v_rms):
    return 20*np.log10(np.asarray(v_rms)/SENS/P0)


def mul(*sections):
    num,den=np.array([1.]),np.array([1.])
    for n,d in sections:
        num=np.polymul(num,n);den=np.polymul(den,d)
    return num,den


def hp_cap(c, rs, rl):
    """Exact series C, Rs source and Rl to an AC-grounded reference.
    DC reference levels do not disappear from operating-point calculations.
    """
    return np.array([c*rl,0.]),np.array([c*(rs+rl),1.])


def lp1(fc):
    return np.array([1.]),np.array([1/(2*np.pi*fc),1.])


def lowpass(kind, order, fc):
    if kind=='butter': b,a=signal.butter(order,2*np.pi*fc,analog=True)
    else: b,a=signal.bessel(order,2*np.pi*fc,analog=True,norm='mag')
    return b,a


def sk_values(r1=1370.,r2=2000.,c1=1.5e-9,c2=750e-12,rth=RTH):
    """Unity Sallen-Key: C1 from intermediate node to output; C2 at + to GND.
    Finite divider Thevenin resistance is part of R1, not zero.
    """
    a=r1+rth
    den=np.array([a*r2*c1*c2,c2*(a+r2),1.])
    return {'num':np.array([1.]),'den':den,
            'f0_Hz':1/(2*np.pi*np.sqrt(den[0])),
            'Q':np.sqrt(den[0])/den[1]}


def voxter(finite_gbw=True):
    tau=10000*470e-12
    if finite_gbw:
        wt=2*np.pi*1e6
        feedback=([wt*tau,11*wt],[tau,wt*tau+11,wt])
    else: feedback=([tau,11],[tau,1])
    return mul(hp_cap(1e-6,50,100000),feedback,([1],[1000*4.7e-9,1]))


@dataclass
class Chain:
    key: str
    label: str
    num: np.ndarray
    den: np.ndarray
    scale: float
    fs: float
    adc: str
    delay_s: float=0.
    adc_hp_Hz: float=0.
    passband_Hz: float=float('inf')
    assumption: str=''

    def response(self,f,total=False):
        f=np.asarray(f,dtype=float)
        s=2j*np.pi*f
        h=np.polyval(self.num,s)/np.polyval(self.den,s)
        if total:
            if self.adc_hp_Hz:
                h*=s/(s+2*np.pi*self.adc_hp_Hz)
            h*=np.exp(-s*self.delay_s)
        return h

    def group_delay(self,f,total=False):
        # Local derivative avoids unwrap ambiguity of large pure delays on sparse grids.
        f=np.asarray(f,dtype=float)
        df=np.maximum(f*1e-4,1e-5)
        ratio=self.response(f+df,total)/self.response(f-df,total)
        return -np.angle(ratio)/(4*np.pi*df)

    def tf(self,total=False):
        if total and self.adc_hp_Hz:
            return mul((self.num,self.den),([1,0],[1,2*np.pi*self.adc_hp_Hz]))
        return self.num,self.den


def architectures():
    # 1. Existing Codex loading, with proposed required LP explicitly additional.
    load=1/(1/100000+1/26900)
    n,d=mul(([ALPHA],[1]),hp_cap(1e-6,50,load),lowpass('butter',2,75000))
    a1=Chain('A1','1 Codex + PCM48',n,d,ALPHA,48000,'PCM1808',17.4/48000,.91,.454*48000,
             'PCM internal HP approximated first-order; digital FIR coefficients unknown')
    # 2. ADS8681 15kHz internal second-order LP is a Bessel fit, NOT official coefficients.
    r_adc=1e6;rret=100000;rl=1/(1/r_adc+1/rret)
    n,d=mul(hp_cap(4.7e-6,50,rl),lowpass('bessel',2,15000))
    a2=Chain('A2','2 Bipolar ADS8681',n,d,1.,96000,'ADS8681',
             assumption='15kHz second-order Bessel surrogate; datasheet internal poles not published')
    sk=sk_values()
    # 3. DC-coupled HV buffer -> divider -> SK -> sole coupling capacitor -> ADC self-bias.
    n,d=mul(([ALPHA],[1]),(sk['num'],sk['den']),hp_cap(4.7e-6,1.,60000.))
    a3=Chain('A3','3 Buffer HV + PCM96',n,d,ALPHA,96000,'PCM1808',17.4/96000,1.82,.454*96000,
             '60k typical ADC impedance, ideal input bias, PCM HP first-order approximation')
    # 4. Candidate fully differential driver response uses an ideal gain; driver unsettled.
    n,d=mul(([.604],[1]),hp_cap(1e-6,50,1e6),lowpass('butter',2,75000))
    a4=Chain('A4','4 Diferencial ADS127L01',n,d,.604,64000,'ADS127L01',42/64000,0,.45*64000,
             'Ideal FDA gain .604; switched-cap ADC loading/driver design still OPEN')
    return [a1,a2,a3,a4]


def step_impulse(chain,t,total=False):
    """Continuous-time residue evaluation, including repeated-pole terms.
    Delays model ONLY documented pure converter group delay, not unknown full FIR.
    """
    num,den=chain.tf(total)
    delay=chain.delay_s if total else 0
    shifted=t-delay;active=shifted>=0
    def evaluate(n,d):
        residues,poles,direct=signal.residue(n,d)
        if len(direct): raise ValueError('distributional direct impulse requires separate handling')
        y=np.zeros_like(t,dtype=complex)
        previous=None;power=0
        for r,p in zip(residues,poles):
            power=power+1 if previous is not None and np.isclose(p,previous,rtol=1e-6,atol=1e-4) else 0
            y[active]+=r*np.exp(p*shifted[active])*shifted[active]**power/math.factorial(power)
            previous=p
        return y.real
    return evaluate(num,den),evaluate(num,np.polymul(den,[1,0]))


def adc_specs():
    return [
      dict(name='STM32L432KC',bits=12,span_V=3.3,gain=ALPHA,snr_db=65.,sinad_db=64.,
           fs_Hz=48000,noise_band='DS11451 table67: no oversampling; dynamic stimulus unspecified',weight='UNSPECIFIED',
           offset_max_V=5*3.3/4096,gain_error_max=.001708984375,reference='VDDA/VREF+ bonded; no VREFBUF',
           source='https://www.st.com/resource/en/datasheet/stm32l432kc.pdf'),
      dict(name='PCM1808',bits=24,span_V=3.,gain=ALPHA,snr_db=99.,sinad_db=None,
           fs_Hz=48000,noise_band='AP400Hz HP+20kHz LP; A weighted SNR; 48k512fs',weight='A',
           offset_max_V=None,gain_error_max=.06,reference='internal; 0.6VCC full span',
           source='https://www.ti.com/lit/ds/symlink/pcm1808.pdf'),
      dict(name='ADS8681',bits=16,span_V=10.24,gain=1.,snr_db=91.5,sinad_db=91.5,
           fs_Hz=1000000,noise_band='maxthroughput 1kHz -0.25dBFS, internal15kHz analog LP',weight='UNWEIGHTED_NOT_EXPLICIT',
           offset_max_V=.001,gain_error_max=.00025,reference='4.096V +/-1mV PW25C;7ppm/C max',
           source='https://www.ti.com/lit/ds/symlink/ads8681.pdf'),
      dict(name='ADS127L01',bits=24,span_V=5.,gain=.604,snr_db=113.4,sinad_db=None,
           fs_Hz=64000,noise_band='HR OSR256 WB1 VREF2.5V64k; noise3.79uVrms typical',weight='UNWEIGHTED',
           offset_max_V=None,gain_error_max=None,reference='external VREF2.5V, e.g. REF5025; input0..AVDD',
           source='https://www.ti.com/lit/ds/symlink/ads127l01.pdf')]

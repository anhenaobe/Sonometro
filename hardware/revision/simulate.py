"""Reproducible ANALYTICAL/LTI and ideal-conversion simulations; NOT measurements.

Run from repo root: python hardware/revision/simulate.py
Manufacturer SPICE execution is separate in spice.py. All equivalents and
missing coefficients are named in models.py and in the output manifest.
"""
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
PLOTS=ROOT/'figures'
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'runs/.mplconfig'))
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='Sonometro-revision-2026-11-05'
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy import signal,integrate
from models import (ALPHA,RTH,SENS,P0,K,TEMP,CHECK_HZ,Chain,architectures,
                    adc_specs,hp_cap,lp1,lowpass,mul,pressure,dbspl,sk_values,voxter,step_impulse)


def write_json(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def table(name,rows):
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def figure(name,fig):
    for fmt in ('png','svg'):
        path=PLOTS/f'{name}.{fmt}'
        fig.savefig(path,dpi=155,metadata={'Date':None} if fmt=='svg' else None)
        if fmt=='svg':
            # Matplotlib path newlines have trailing spaces; whitespace is not geometry.
            path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)


def db(x):return 20*np.log10(np.maximum(np.abs(x),1e-30))


def current_sources():
    rows=[]
    for name,rset,rout in [('LT3092 previo',20000.,71.5),('LT3092 mayor Vset',120000.,430.)]:
        nominal=10e-6*(1+rset/rout)
        record=dict(source=name,Rset_ohm=rset,Rout_ohm=rout,I_nominal_mA=1000*nominal,
                    nominal_error_percent=100*(nominal/.0028-1))
        for tag,dtemp,iset_error,vos in [('25C',0,.01,.002),('50K_envelope',50,.02,.004)]:
            choices=[]
            for a,b,c,d in itertools.product((-1,1),repeat=4):
                rs=rset*(1+a*.001)*(1+a*25e-6*dtemp)
                ro=rout*(1+b*.001)*(1+b*25e-6*dtemp)
                choices.append(10e-6*(1+c*iset_error)*(1+rs/ro)+d*vos/ro)
            record[f'I_min_mA_{tag}']=min(choices)*1000
            record[f'I_max_mA_{tag}']=max(choices)*1000
        # Specific circuit sensitivity; not copied from generic headline regulation.
        record['line_sensitivity_typ_ppm_per_V']=1e6*((1+rset/rout)*.03e-9+.003e-3/rout)/nominal
        record['line_sensitivity_max25_ppm_per_V']=1e6*((1+rset/rout)*.2e-9+.010e-3/rout)/nominal
        record['Vset_V']=10e-6*rset
        record['Vs_min_at_130peak_V_using_1p45_drop']=12.5+pressure(130,True)['sensor_Vpeak']+record['Vset_V']+1.45
        record['power_IC_bias_mW']=(24-12.5-record['Vset_V'])*nominal*1000
        record['power_Rout_mW']=(nominal-10e-6)**2*rout*1000
        record['Cset100nF_corner_Hz']=1/(2*np.pi*rset*100e-9)
        record['Cset100nF_tau_s']=rset*100e-9
        record['noise_status']='previous20k/71.5:0.464uVrms20-20k simulated;120k/430 OPEN'
        rows.append(record)
    table('current_source_lt3092.csv',rows)
    tl=[]
    # VBE and beta are explicit sensitivity assumptions, NOT guarantees at2.8mA.
    for re in (470,750,665):
        current=(2.495-.65)/re*100/101
        envelope=[]
        for vr,vbe,beta,tol in itertools.product((2.440,2.550),(.55,.75),(80,300),(-.001,.001)):
            envelope.append((vr-vbe)/(re*(1+tol))*beta/(beta+1))
        tl.append(dict(RE_ohm=re,assumed_VBE_V=.65,assumed_beta=100,nominal_mA=current*1e3,
                       conditional_min_mA=min(envelope)*1e3,conditional_max_mA=max(envelope)*1e3,
                       Vbase_at24V=24-2.495,TL431_I_mA=((24-2.495)/10000-current/100)*1000,
                       assumed_drift_ppm_K=1e6*.002/(2.495-.65),
                       conditional_compliance_V=24-(2.495-.65)-.2,
                       P_PNP_mW=(24-(2.495-.65)-12.5)*current*1000,
                       P_RZ_mW=(24-2.495)**2/10000*1000,
                       status='CONDITIONAL VBE/beta assumptions;not guaranteed or simulatedSPICE'))
    table('current_source_tl431.csv',tl)
    lm=dict(MPN='LM334M/NOPB',Rset_ohm=24.3,I_nominal_mA=.0677/24.3*1000,
            current_error_max_at1to5mA_percent=8,typical_drift_percent_per_K=.336,
            typical_line_percent_per_V=.02,headroom_V=1,
            approximate_drift_25K_percent=.336*25,noise_rms_A=None,
            reason='noise spectrum/integrated limits not guaranteed; no numeric total invented')
    write_json('current_source_lm334.json',lm)
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    temp=np.linspace(-10,50,300)
    axes[0].plot(temp,100*(.0677/24.3/.0028*(1+.00336*temp)-1),label='LM334 PTAT típico')
    axes[0].plot(temp,100*((2.495-.65+.002*temp)/665*100/101/.0028-1),label='TL431+PNP: VBE modelo -2mV/K')
    axes[0].axhspan(100*(rows[1]['I_min_mA_50K_envelope']/2.8-1),100*(rows[1]['I_max_mA_50K_envelope']/2.8-1),alpha=.2,label='LT3092 120k/430: envolvente, no pendiente')
    axes[0].set(xlabel='Cambio de temperatura (K)',ylabel='Error de corriente (%)',title='Modelos y límites: no mediciones')
    axes[0].legend(fontsize=7);axes[0].grid()
    supplies=np.linspace(17,30,200)
    for row in rows:
        i=row['I_nominal_mA']*(1+row['line_sensitivity_typ_ppm_per_V']*1e-6*(supplies-24))
        i[supplies<row['Vs_min_at_130peak_V_using_1p45_drop']]=np.nan
        axes[1].plot(supplies,i,label=row['source']+'; linealización típica')
    axes[1].set(xlabel='Alimentación IEPE (V)',ylabel='Corriente (mA)',title='Solo zona con compliance, 130dB pico')
    axes[1].legend(fontsize=7);axes[1].grid();figure('01_fuentes_corriente',fig)
    return rows,tl,lm


def frequency_comparison(chains):
    f=np.geomspace(.05,2e6,6000)
    rows=[]
    for a in chains:
        h=a.response(CHECK_HZ,True)
        for freq,v,gd in zip(CHECK_HZ,h,a.group_delay(CHECK_HZ,True)):
            rows.append(dict(architecture=a.key,frequency_Hz=freq,gain_V_per_V=abs(v),
                error_magnitude_dB_vs_nominal=float(db(v/a.scale)),
                phase_deg=float(np.angle(v,deg=True)),group_delay_us=float(gd*1e6),
                documented_constant_delay_us=a.delay_s*1e6,
                model=a.assumption))
    table('frequency_checkpoints.csv',rows)
    fig,axes=plt.subplots(3,1,figsize=(10,10),layout='constrained')
    for a in chains:
        show=(f>=10)&(f<=30000)&(f<=a.passband_Hz)
        h=a.response(f[show],True)
        axes[0].semilogx(f[show],db(h/a.scale),label=a.label)
        # Show delay-removed phase to distinguish dispersion from a pure delay.
        axes[1].semilogx(f[show],np.unwrap(np.angle(h*np.exp(2j*np.pi*f[show]*a.delay_s)))*180/np.pi,label=a.label)
        axes[2].semilogx(f[show],(a.group_delay(f[show],True)-a.delay_s)*1e6,label=a.label)
    axes[0].set(ylabel='Error de magnitud (dB)',ylim=(-10,.2),title='Cadena equivalente: resultados modelados, no medidos')
    axes[1].set(ylabel='Fase sin retardo constante (°)')
    axes[2].set(xlabel='Frecuencia (Hz)',ylabel='Retardo de grupo residual (µs)',ylim=(-5,4000))
    for ax in axes:ax.grid();ax.legend(fontsize=8)
    figure('02_bode_arquitecturas',fig)

    # Compare actual network equations, not manufacturer ADC digital filters.
    filters=[]
    for name,tf in [('AC existente 1u/21.2k',hp_cap(1e-6,50,1/(1/100000+1/26900))),
                    ('AC 4.7u/60k',hp_cap(4.7e-6,1,60000)),
                    ('Servo ideal fc0.1Hz',([1,0],[1,2*np.pi*.1])),
                    ('HP1.6Hz + Butterworth4 30k',mul(([1,0],[1,2*np.pi*1.6]),lowpass('butter',4,30000))),
                    ('HP1.6Hz + Bessel4 30k',mul(([1,0],[1,2*np.pi*1.6]),lowpass('bessel',4,30000)))]:
        filters.append(Chain(name,name,np.array(tf[0]),np.array(tf[1]),1,96000,'NONE'))
    bn,bd=signal.butter(2,[2*np.pi*1.6,2*np.pi*30000],btype='bandpass',analog=True)
    filters.append(Chain('BP','Pasabandas Butterworth orden4',bn,bd,1,96000,'NONE'))
    fig,axes=plt.subplots(3,1,figsize=(10,10),layout='constrained')
    ff=np.geomspace(.05,2e5,5000)
    for a in filters:
        h=a.response(ff)
        axes[0].semilogx(ff,db(h),label=a.label)
        axes[1].semilogx(ff,np.unwrap(np.angle(h))*180/np.pi,label=a.label)
        axes[2].semilogx(ff,a.group_delay(ff)*1e6,label=a.label)
    axes[0].set(ylabel='Magnitud (dB)',ylim=(-30,1),title='Filtros ideales derivados; servo no incluye errores de componentes')
    axes[1].set(ylabel='Fase (°)',ylim=(-400,100))
    axes[2].set(xlabel='Frecuencia (Hz)',ylabel='Retardo de grupo (µs)',ylim=(0,4000))
    for ax in axes:ax.set_xlim(10,1e5);ax.grid();ax.legend(fontsize=6.5)
    figure('03_filtros_comparados',fig)
    filter_rows=[]
    for a in filters:
        for freq,h,gd in zip(CHECK_HZ,a.response(CHECK_HZ),a.group_delay(CHECK_HZ)):
            filter_rows.append(dict(filter=a.label,frequency_Hz=freq,magnitude_dB=float(db(h)),
                                    phase_deg=float(np.angle(h,deg=True)),group_delay_us=float(gd*1e6)))
    table('filter_checkpoints.csv',filter_rows)
    return rows


def time_frequency(chains):
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    fast=np.linspace(0,120e-6,1800);slow=np.linspace(0,2,1600)
    for a in chains:
        impulse,step=step_impulse(a,fast)
        _,tail=step_impulse(a,slow)
        axes[0,0].plot(fast*1e6,impulse/a.scale,label=a.label)
        axes[0,1].plot(fast*1e6,step/a.scale,label=a.label)
        axes[1,0].plot(slow,tail/a.scale,label=a.label)
        # Linear prediction only: invalid when opamp or ADC clips; quantify hazard.
        if a.key in ('A1','A3'):
            axes[1,1].plot(slow,2.5+12.5*tail,label=a.label+'; sin clamps')
    axes[0,0].set(xlabel='Tiempo (µs)',ylabel='h(t)/ganancia (1/s)',title='Impulso analógico (sin FIR ADC)')
    axes[0,1].set(xlabel='Tiempo (µs)',ylabel='Salida normalizada (V/V)',title='Escalón, primeros120µs')
    axes[1,0].set(xlabel='Tiempo (s)',ylabel='Salida normalizada (V/V)',title='Eliminación DC y establecimiento')
    axes[1,1].axhline(5.3,c='r',ls='--',label='5.3V: límite absoluto PCM alimentado')
    axes[1,1].set(xlabel='Tiempo (s)',ylabel='Predicción lineal salida (V)',title='Salto de bias12.5V: NO es una tensión segura')
    for ax in axes.flat:ax.grid();ax.legend(fontsize=6)
    figure('04_impulso_escalon_arranque',fig)

    # Exact periodic steady state in frequency domain. No synthetic capture files.
    fs=192000;n=fs;t=np.arange(n)/fs
    x=sum(.12*np.sin(2*np.pi*f*t) for f in CHECK_HZ)
    bins=np.fft.rfftfreq(n,1/fs);X=np.fft.rfft(x)
    fig,axes=plt.subplots(3,1,figsize=(11,10),layout='constrained')
    axes[0].plot(t[:1920]*1000,x[:1920],c='k',lw=1,label='Entrada eléctrica de prueba')
    axes[2].plot(bins,db(np.abs(X)*2/n),c='k',label='Entrada')
    metrics=[]
    for a in chains:
        h=a.response(bins,True)
        y=np.fft.irfft(X*h,n=n)
        yn=y/a.scale
        aligned=np.fft.irfft(X*h/a.scale*np.exp(2j*np.pi*bins*a.delay_s),n=n)
        axes[0].plot(t[:1920]*1000,yn[:1920],label=a.label)
        axes[1].plot(t[:1920]*1000,(aligned-x)[:1920],label=a.label+' sin delay constante')
        axes[2].plot(bins,db(abs(np.fft.rfft(yn))*2/n),label=a.label)
        metrics.append(dict(architecture=a.key,input_rms_V=float(np.sqrt(np.mean(x*x))),
            output_rms_V=float(np.sqrt(np.mean(y*y))),
            gain_normalized_rms_error_dB=float(20*np.log10(np.linalg.norm(yn)/np.linalg.norm(x))),
            difference_raw_rms_V=float(np.sqrt(np.mean((yn-x)**2))),
            difference_delay_aligned_rms_V=float(np.sqrt(np.mean((aligned-x)**2))),
            test='SYNTHETIC_STEADY_PERIODIC_MULTITONE_NOT_CAPTURE'))
    axes[0].set(xlabel='Tiempo (ms)',ylabel='V, normalizada por ganancia',title='Multitono: forma de onda y retardo')
    axes[1].set(xlabel='Tiempo (ms)',ylabel='Diferencia (V)',title='Error temporal tras quitar SOLO el retardo constante conocido')
    axes[2].set(xlabel='Frecuencia (Hz)',ylabel='Amplitud pico (dBV)',xlim=(0,22000),ylim=(-130,0),title='Espectro periódico, sin ventana; mismo estímulo para todos')
    for ax in axes:ax.grid();ax.legend(fontsize=7)
    figure('05_multitono_tiempo_espectro',fig);table('multitone.csv',metrics)
    return metrics


def amplifier_comparison():
    vn,vd=voxter();vi,di=voxter(False)
    v=Chain('Voxter','Voxter MCP6002: GBW1MHz modelo',vn,vd,11,48000,'STM32')
    ideal=Chain('Ideal','Red Voxter ideal',vi,di,11,48000,'NONE')
    f=np.geomspace(20,1e6,3000)
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for a in (v,ideal):
        axes[0,0].semilogx(f,db(a.response(f)/11),label=a.label)
        axes[0,1].semilogx(f,np.unwrap(np.angle(a.response(f)))*180/np.pi,label=a.label)
    for gain in (ALPHA,1,3.750929368,10.09,11):
        amp=np.geomspace(1e-5,5,500)
        axes[1,0].loglog(amp,np.minimum(gain*amp,1.5),label=f'g={gain:.4g}, margen1.5Vp')
    rows=[]
    for level,peak in [(30,False),(60,False),(94,False),(100,False),(120,False),(130,True)]:
        p=pressure(level,peak)
        rows.append(dict(level_dB=level,definition='PEAK' if peak else 'RMS',**p,
                         A_Vpeak=ALPHA*p['sensor_Vpeak'],B10p09_Vpeak=10.09*p['sensor_Vpeak'],
                         C3p751_Vpeak=3.750929368*p['sensor_Vpeak'],Voxter11_Vpeak=11*p['sensor_Vpeak']))
    table('sensor_amplitudes.csv',rows)
    phase=[]
    for freq,hi,hv in zip(CHECK_HZ,ideal.response(CHECK_HZ),v.response(CHECK_HZ)):
        phase.append(dict(frequency_Hz=freq,ideal_gain=abs(hi),finite_gbw_gain=abs(hv),
                          ideal_error_vs11_dB=float(db(hi/11)),finite_gbw_error_vs11_dB=float(db(hv/11)),
                          finite_gbw_phase_deg=float(np.angle(hv,deg=True))))
    table('voxter_response.csv',phase)
    # GBW/SR limit, not an invented distortion prediction.
    for sr,label in [(.6e6,'MCP6002 SR0.6V/us típico'),(20e6,'OPA2192 SR20V/us típico')]:
        axes[1,1].loglog(f,np.minimum(1.5,sr/(2*np.pi*f)),label=label)
    axes[0,0].set(xlabel='Frecuencia (Hz)',ylabel='Ganancia/11 (dB)',title='Cf es shelving; la salida agrega otro polo')
    axes[0,1].set(xlabel='Frecuencia (Hz)',ylabel='Fase (°)')
    axes[1,0].set(xlabel='Entrada sensor (V pico)',ylabel='Salida limitada (V pico)',title='Clipping ideal, NO THD del fabricante')
    axes[1,1].set(xlabel='Frecuencia (Hz)',ylabel='Máximo por SR y margen (V pico)',title='Cota de gran señal: no garantiza THD')
    for ax in axes.flat:ax.grid();ax.legend(fontsize=7)
    figure('06_amplificacion_saturacion',fig)
    limits=[]
    for name,g in [('A',ALPHA),('B',10.09),('C_high',3.750929368),('Voxter',11),('A3_high',1)]:
        limits.append(dict(range=name,gain=g,max_sensor_Vpeak=1.5/g,
                           max_sine_dBSPL_RMS=float(dbspl(1.5/g/np.sqrt(2))),
                           max_dBSPL_peak=float(dbspl(1.5/g))))
    table('gain_limits.csv',limits)
    return phase,limits


def references():
    f=np.geomspace(.05,100000,4000);s=2j*np.pi*f
    tau=10000*470e-12;ng=(11+s*tau)/(1+s*tau)
    z=50+1/(s*1e-6);href_vox=ng*z/(100000+z)+(1-ng)
    # Codex source equivalent includes return100k before Rt.
    zup=1/(1/100000+1/z)
    a=10000/(16900+10000+zup)
    href_codex=1-a
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    axes[0,0].semilogx(f,db(href_vox),label='Voxter Vmid→salida antes RC')
    axes[0,0].semilogx(f,db(href_codex),label='Codex Vb→salida buffer')
    axes[0,0].semilogx(f,db(1-10.09*a),label='Codex alto, Vb=Vc perturbadas juntas')
    axes[0,0].set(xlabel='Frecuencia (Hz)',ylabel='Transferencia de referencia (dB)',title='El ruido de referencia no siempre entra con ganancia1')
    fs=192000;t=np.arange(fs)/fs;sig=.078816979*np.sin(2*np.pi*1000*t)
    vdd=3.3+.010*np.sin(2*np.pi*100*t)
    idx=int(np.argmin(abs(f-100)));hv=href_vox[idx]
    # Apply the actual topology's reference transfer, not a fictitious +1.
    midpoint_out=.005*abs(hv)*np.sin(2*np.pi*100*t+np.angle(hv))
    shared=(11*sig+1.65+midpoint_out)/vdd*3.3-1.65
    # Separate ideal tracking topology illustrates when ratiometry is valid.
    tracking_ideal=(11*sig/vdd)*3.3
    midfilter=1/(1+2j*np.pi*100*.05) #10k||10k and10uF:tau50ms
    mid=1.65+.005*abs(midfilter*hv)*np.sin(2*np.pi*100*t+np.angle(midfilter*hv))
    filtered=(11*sig+mid)/vdd*3.3-1.65
    independent=11*sig+.001*abs(hv)*np.sin(2*np.pi*100*t+np.angle(hv))
    reference10u=11*sig+10e-6*abs(hv)*np.sin(2*np.pi*100*t+np.angle(hv))
    cases={'mid_independent_1mVpeak':independent,'shared_VDDA_mid_10mVpeak':shared,
           'ideal_tracking_topology_NOT_Voxter':tracking_ideal,
           'filtered_mid_shared_VDDA_10mVpeak':filtered,'dedicated_residual10uVpeak':reference10u}
    metrics=[]
    for label,y in cases.items():
        e=y-11*sig
        axes[0,1].plot(t[:1920]*1000,e[:1920]*1000,label=label)
        spec=np.abs(np.fft.rfft(e))*2/fs
        axes[1,0].plot(np.fft.rfftfreq(fs,1/fs),db(spec),label=label)
        er=float(np.sqrt(np.mean(e*e)))
        metrics.append(dict(test=label,error_output_Vrms=er,error_sensor_equiv_Vrms=er/11,
                            equivalent_Pa_rms=er/11/SENS,equivalent_dBSPL=float(dbspl(er/11)),
                            status='DETERMINISTIC_PERTURBATION_NOT_RANDOM_NOISE'))
    for gain in (ALPHA,1,3.750929368,11):
        d=np.geomspace(1e-5,1e-1,200)
        axes[1,1].semilogx(d,20*np.log10(1+d/3.3),label=f'g={gain:g}: error relativo de escala igual')
    axes[0,1].set(xlabel='Tiempo (ms)',ylabel='Error convertido (mV)',title='Modelos de perturbaciones conocidas, sin clipping')
    axes[1,0].set(xlabel='Frecuencia (Hz)',ylabel='Amplitud error (dBV pico)',xlim=(0,2000),ylim=(-150,-20),title='Error aditivo y bandas laterales de modulación')
    axes[1,1].set(xlabel='Variación VREF (V)',ylabel='Error de escala (dB)',title='Ratiometría no elimina error multiplicativo')
    for ax in axes.flat:ax.grid();ax.legend(fontsize=6)
    figure('07_referencias',fig);table('reference_perturbations.csv',metrics)
    # Exact resistor corners for a subtractor with gain.375 (20k/7.5k).
    subtractor=[]
    for signs in itertools.product((-1,1),repeat=4):
        r1,r2,r3,r4=[v*(1+.001*sg) for v,sg in zip((20000,7500,20000,7500),signs)]
        ga=r2/r1;gp=(1+ga)*r4/(r3+r4)
        subtractor.append((gp-ga)*12.5)
    return dict(perturbations=metrics,subtractor_12p5V_offset_worst_V=max(abs(np.array(subtractor))),
                caveat='Reference noise10uV is an injected test level, NOT a REF5025 guaranteed noise specification')


def noise_and_adc(chains):
    f=np.geomspace(20,20000,12000);s=2j*np.pi*f
    # Fits to TYPICAL datasheet points, not guaranteed PSDs or manufacturer models.
    b=((10.5e-9)**2-(5.5e-9)**2)/(1/100-1/1000);a=(5.5e-9)**2-b/1000
    en2=a+b/f
    r1=1370+RTH;r2=2000;c1=1.5e-9;c2=750e-12
    den=1+s*c2*(r1+r2)+s*s*r1*r2*c1*c2
    hsig=1/den;hop=1+s*r1*c1/den;hr2=(1+s*r1*c1)/den
    cap=chains[2].response(f)/(ALPHA*hsig)
    psd={
        'OPA2192 bufferHV':en2*abs(ALPHA*hsig*cap)**2,
        'OPA2192 SK':en2*abs(hop*cap)**2,
        'Rt/Rb + R1':4*K*TEMP*r1*abs(hsig*cap)**2,
        'R2':4*K*TEMP*r2*abs(hr2*cap)**2,
        'in buffer con Rs50':(1.5e-15*50)**2*abs(ALPHA*hsig*cap)**2,
        'in SK, cota resistiva':(1.5e-15*(r1+r2))**2*abs(hop*cap)**2}
    total=sum(psd.values());noise=[]
    fig,axes=plt.subplots(2,1,figsize=(10,8),layout='constrained')
    for label,p in psd.items():
        rms=float(np.sqrt(integrate.trapezoid(p,f)))
        noise.append(dict(contribution=label,output_Vrms=rms,input_sensor_equiv_Vrms=rms/ALPHA,
                          equivalent_Pa_rms=rms/ALPHA/SENS,equivalent_dBSPL=float(dbspl(rms/ALPHA)),
                          kind='TYPICAL_EQUIVALENT20Hz-20kHz_UNWEIGHTED'))
        axes[0].loglog(f,np.sqrt(p)*1e9,label=label)
    rms=float(np.sqrt(integrate.trapezoid(total,f)))
    axes[0].loglog(f,np.sqrt(total)*1e9,c='k',label='Suma cuadrática, solo AFE')
    axes[1].semilogx(f,np.sqrt(integrate.cumulative_trapezoid(total,f,initial=0))*1e6/ALPHA)
    axes[0].set(xlabel='Frecuencia (Hz)',ylabel='Densidad a salida (nV/√Hz)',title='Modelo de ruido A3: no incluye ADC/micrófono/fuente')
    axes[1].set(xlabel='Frecuencia superior de integración (Hz)',ylabel='Ruido referido al sensor (µV RMS)',title='Integral desde20Hz: hipótesis de PSD típicas explícitas')
    for ax in axes:ax.grid();ax.legend(fontsize=7) if ax==axes[0] else None
    figure('08_ruido',fig);table('noise_budget_afe.csv',noise)
    specs=adc_specs();adcrows=[]
    for adc in specs:
        q=adc['span_V']/2**adc['bits']
        fullrms=adc['span_V']/2/np.sqrt(2)
        # ADS SNR stimulus is -0.25dBFS, not a full-scale sine.
        stimulus=10**(-.25/20) if adc['name']=='ADS8681' else 1.
        noiseADC=3.79e-6 if adc['name']=='ADS127L01' else fullrms*stimulus/10**(adc['snr_db']/20)
        adcrows.append({**adc,'q_V':q,'q_rms_ideal_V':q/np.sqrt(12),
                        'noise_from_snr_total_Vrms':noiseADC,
                        'noise_sensor_equiv_Vrms':noiseADC/adc['gain'],
                        'noise_sensor_equiv_dBSPL_NOT_SAME_BANDS':float(dbspl(noiseADC/adc['gain'])),
                        'dynamic_ENOB_from_SINAD':(adc['sinad_db']-1.76)/6.02 if adc['sinad_db'] else None,
                        'do_not_add_quantization_again':True})
    table('adc_comparison.csv',adcrows)
    fig,axes=plt.subplots(2,1,figsize=(10,8),layout='constrained')
    n=65536;t=np.arange(n)/65536
    for adc in specs:
        err=[]
        q=adc['span_V']/2**adc['bits'];half=adc['span_V']/2
        for level in range(20,131):
            amp=pressure(level)['sensor_Vpeak'];x=amp*np.sin(2*np.pi*1000*t)
            y=x*adc['gain']
            code=np.clip(np.floor((y+half)/q),0,2**adc['bits']-1)
            recovered=((code+.5)*q-half)/adc['gain']
            err.append(np.sqrt(np.mean((recovered-x)**2)))
        axes[0].semilogy(range(20,131),np.array(err)*1e6,label=adc['name'])
        axes[1].bar(adc['name'],20*np.log10(1+(adc['gain_error_max'] or .002)),label='ADS127:0.2% típico, no máximo' if adc['name']=='ADS127L01' else None)
    axes[0].set(xlabel='Nivel de seno (dB SPL RMS)',ylabel='Error referido a sensor (µV RMS)',title='Conversores IDEALES cuantizados y saturados: excluye ruido/INL')
    axes[1].set(ylabel='Error de escala sin calibrar (dB)',title='Ganancia: máximos cuando existen; ADS127 típico')
    for ax in axes:ax.grid();ax.legend(fontsize=7)
    figure('09_conversion_adc',fig)
    return dict(afe_total_output_Vrms=rms,afe_total_input_Vrms=rms/ALPHA,
                afe_equivalent_dBSPL=float(dbspl(rms/ALPHA)),
                lt3092_previous_noise_Vrms=.464e-6,mic_catalog_noise_Vrms=SENS*P0*10**(32/20),
                chain_total_noise_Vrms=None,
                reason='ADC PCM noise is A weighted400Hz-20k;cannot sum with unweighted20Hz-20k budget')


def tolerances_and_alias(chains):
    rows=[]
    for signs in itertools.product((-1,1),repeat=6):
        rt,rb,r1,r2,c1,c2=[v*(1+s*tol) for v,s,tol in zip((1690,1000,1370,2000,1.5e-9,750e-12),signs,(.001,.001,.001,.001,.01,.01))]
        g=rb/(rt+rb);rth=rt*rb/(rt+rb);sk=sk_values(r1,r2,c1,c2,rth)
        h=g/(np.polyval(sk['den'],2j*np.pi*CHECK_HZ))
        for f,v in zip(CHECK_HZ,h):
            rows.append(dict(corner=''.join('+' if x==1 else '-' for x in signs),frequency_Hz=f,
                             gain=float(abs(v)),error_dB_vs_nominal=float(db(v/ALPHA))))
    table('tolerance_corners.csv',rows)
    fig,axes=plt.subplots(2,1,figsize=(10,8),layout='constrained')
    for f in CHECK_HZ:
        values=[r['error_dB_vs_nominal'] for r in rows if r['frequency_Hz']==f]
        axes[0].plot([f,f],[min(values),max(values)],marker='_',ms=12,lw=4)
    axes[0].set_xscale('log');axes[0].set(xlabel='Frecuencia (Hz)',ylabel='Error de ganancia (dB)',title='64 esquinas: resistencias0.1%, C0G1%; sin ADC/capAC')
    f=np.linspace(20000,200000,2000)
    n,d=lowpass('butter',2,75000)
    butter=Chain('x','LP75k',n,d,1,96000,'NONE')
    axes[1].plot(f/1000,db(butter.response(f)),label='LP analógico75k: no basta solo')
    axes[1].axvline(48,c='k',ls='--',label='Nyquist PCM96k')
    axes[1].axvline(55.968,c='g',ls=':',label='Inicio stop digital .583fs (PCM96k)')
    axes[1].axhline(-65,c='g',ls='--',label='Rechazo digital65dB según ficha, no coeficientes simulados')
    axes[1].set(xlabel='Frecuencia de interferencia (kHz)',ylabel='Atenuación (dB)',title='Antialias: banda de transición y frecuencia de modulación importan')
    for ax in axes:ax.grid();ax.legend(fontsize=7) if ax==axes[1] else None
    figure('10_tolerancias_antialias',fig)
    # Leakage/DA values below are intentional test assumptions, not part specifications.
    cap=[]
    for leak in (1e-9,10e-9,100e-9,1e-6):
        cap.append(dict(test='leakage_current',injected_A=leak,output_offset_at60k_V=leak*60000,status='PARAMETRIC_NOT_COMPONENT_SPEC'))
    write_json('capacitor_nonideal_tests.json',dict(leakage=cap,
        DA_model='Cmain parallel (Rda series Cda), dielectric fraction .1% and1%,tau1s; generic sensitivity only',
        DA_relaxation_after_12p5V_step_V={'.1_percent':.001*12.5,'1_percent':.01*12.5},
        real_part_selection='OPEN: must verify leakage, absorption, voltage and availability for chosen MPN'))
    return rows


def main():
    OUT.mkdir(parents=True,exist_ok=True);PLOTS.mkdir(parents=True,exist_ok=True)
    chains=architectures()
    currents=current_sources()
    freq=frequency_comparison(chains)
    mt=time_frequency(chains)
    vox,limits=amplifier_comparison()
    ref=references();noise=noise_and_adc(chains);tol=tolerances_and_alias(chains)
    summary=dict(status='ANALYTICAL_AND_LTI_SIMULATION_NOT_PHYSICAL_VALIDATION',
        band_Hz=[20,20000],sensitivity_V_per_Pa_PROVISIONAL=SENS,
        versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__),
        chain_models=[dict(key=a.key,label=a.label,gain=a.scale,fs_Hz=a.fs,assumption=a.assumption) for a in chains],
        important=dict(ads8681_analog_bandwidth_3dB_Hz=15000,stm32_has_usable_VREFBUF=False,
            stm32_differential_physical_negative_allowed=False),
        recommended_architecture='A3 conditional on protection,capacitorselectionandbench;notfabricationrelease',
        sk={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in sk_values().items()},
        reference_results=ref,noise_results=noise,
        mt=mt,limits=limits,
        unknowns=['actualRG50certificate','SV12identity/capsule/supplyrequirements','unweightedPCMnoise20-20k',
          'exactPCMHP/FIRcoefficients','ADS8681internalfiltercoefficients','MCP6002SPICEmodelnotretrieved',
          'LT3092encryptedmodelnotrerun','protectionpoweroff','CacMPNleakage/DA','supplyandclocknoise'],
        source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('models.py','simulate.py')})
    write_json('summary.json',summary)
    print('Generated',len(list(PLOTS.glob('*.png'))),'PNG/SVG pairs, CSVtables and summary.json')
    print(json.dumps(dict(sk_Hz=sk_values()['f0_Hz'],afe_noise_input_uV=noise['afe_total_input_Vrms']*1e6,
                         A3_20Hz=[r for r in freq if r['architecture']=='A3' and r['frequency_Hz']==20][0]),indent=2))


if __name__=='__main__':main()

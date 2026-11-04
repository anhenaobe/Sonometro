"""Reproducible real SPICE cases; summary contains simulated, not measured, data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--dll',required=True)
    args=p.parse_args()
    cases=[('ac_nom','ac',[]),('ac_high','ac',['--ng','10.09']),
           ('zout','zout',[]),('loop','loop',[]),('loop_high','loop',['--ng','10.09']),
           ('noise_nom','noise',[]),('noise_high','noise',['--ng','10.09']),
           ('tolerance_min','ac',['--rt',str(16900*1.001*1.00125),'--rb',str(10000*.999*.99875)]),
           ('tolerance_max','ac',['--rt',str(16900*.999*.99875),'--rb',str(10000*1.001*1.00125),'--nodeset']),
           ('rs1000','ac',['--rs','1000']),
           ('existing_ac','ac',['--existing-coupling']),
           ('existing_tran','tran',['--existing-coupling']),
           ('existing_high','tran',['--existing-coupling','--ng','10.09','--amplitude','.07881698']),
           ('supply45','tran',['--supply','4.5']),('supply55','tran',['--supply','5.5']),
           ('overload','overload',['--amplitude','10']),('startup','startup',[])]
    for tag,amp in [('30dB',4.973015e-5),('60dB',.0015726055),('94dB',.07881698),
                    ('120dB',1.5726055),('130dB_peak',3.51645276)]:
        cases.append((tag,'tran',['--amplitude',str(amp)]))
    for f in (20,20000): cases.append((f'freq{f}','tran',['--frequency',str(f)]))
    cases.append(('high_overload','tran',['--ng','10.09','--amplitude','1.5726055']))
    summary={'status':'SIMULATED_NOT_MEASURED','engine':'ngspice46, KiCad10',
             'model':'TI OPAx192 Final1.7, unchanged','cases':{}}
    for tag,kind,extra in cases:
        print('Simulating:',tag,flush=True)
        result=subprocess.run([sys.executable,str(ROOT/'simulate.py'),'--dll',args.dll,
            '--case',kind,'--tag',tag,*extra],capture_output=True,text=True)
        if result.returncode:
            print(result.stdout,result.stderr)
            raise RuntimeError('SPICE case failed: '+tag)
        path=ROOT/'runs'/tag
        data=np.loadtxt(path/'data.txt',skiprows=1)
        if not np.isfinite(data).all():
            raise RuntimeError('non-finite SPICE data: '+tag)
        info={'analysis':kind,'options':extra,
              'data_sha256':hashlib.sha256((path/'data.txt').read_bytes()).hexdigest(),
              'manifest':json.loads((path/'manifest.json').read_text())}
        if kind in ('ac','zout'):
            output=data[:,1]+1j*data[:,2]
            for f in (20,1000,20000):
                i=int(np.argmin(abs(data[:,0]-f)))
                info[f'gain_at_{f}Hz']=float(abs(output[i]))
                info[f'phase_at_{f}Hz_deg']=float(np.angle(output[i],deg=True))
            if kind=='zout': info['units']='ohm, 1 A small-signal current injection'
        elif kind=='loop':
            loop=-(data[:,1]+1j*data[:,2])/(data[:,3]+1j*data[:,4])
            crossing=int(np.argmin(abs(20*np.log10(abs(loop)))))
            phase=np.unwrap(np.angle(loop))*180/np.pi
            info['unity_loop_frequency_Hz']=float(data[crossing,0])
            info['phase_margin_estimate_deg']=float(180+phase[crossing])
            info['scope']='TI model, 60kOhm load, assumed20pF only; not guaranteed'
        elif kind=='noise':
            info['interpretation']='OPEN: incompatible noise output; do not use as design budget'
            info['reason']='ngspice integrated noise print is inconsistent with exported spectrum and datasheet; model compatibility not established'
            info['integrated_output_noise_Vrms']=float(np.sqrt(np.trapezoid(data[:,1]**2,data[:,0])))
            info['integrated_input_noise_Vrms']=float(np.sqrt(np.trapezoid(data[:,2]**2,data[:,0])))
        else:
            selected=data[data[:,0]>=data[-1,0]*.6]
            info.update(output_min_V=float(np.min(data[:,2])),output_max_V=float(np.max(data[:,2])),
                        steady_output_min_V=float(np.min(selected[:,2])),
                        steady_output_max_V=float(np.max(selected[:,2])),
                        exceeds_PCM_1_to_4V=bool(np.any((data[:,2]<1)|(data[:,2]>4))))
        summary['cases'][tag]=info
    (ROOT/'simulation_results.json').write_text(json.dumps(summary,indent=2)+'\n')
    plot_summary()


def plot_summary():
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'runs/.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,1,figsize=(10,10),layout='constrained')
    for tag,label in [('ac_nom','A: Rs=50 ohm'),('existing_ac','A: acoplamiento existente')]:
        d=np.loadtxt(ROOT/'runs'/tag/'data.txt',skiprows=1)
        axes[0].semilogx(d[:,0],20*np.log10(abs(d[:,1]+1j*d[:,2])),label=label)
    axes[0].set(xlim=(20,20000),ylim=(-9.4,-8.4),xlabel='Frecuencia (Hz)',ylabel='Ganancia (dB)',title='SIMULADO: adaptación A, modelo TI + ngspice46')
    axes[0].legend();axes[0].grid(True)
    for tag,label in [('130dB_peak','130 dB SPL pico'),('overload','Sobrecarga 10 V pico')]:
        d=np.loadtxt(ROOT/'runs'/tag/'data.txt',skiprows=1)
        axes[1].plot(d[:,0]*1e3,d[:,2],label=label)
    axes[1].axhline(1,color='red',linestyle='--');axes[1].axhline(4,color='red',linestyle='--')
    axes[1].set(xlabel='Tiempo (ms)',ylabel='Salida (V)',title='Centro ideal 2,5 V; líneas = rango nominal PCM')
    axes[1].legend();axes[1].grid(True)
    d=np.loadtxt(ROOT/'runs/startup/data.txt',skiprows=1)
    axes[2].plot(d[:,0]*1000,d[:,2],label='Salida ante estímulo PWL de estrés')
    axes[2].axhline(4,color='red',linestyle='--')
    axes[2].set(xlabel='Tiempo (ms)',ylabel='Salida (V)',title='Arranque sin protección: NO conectar ADC')
    axes[2].legend();axes[2].grid(True)
    fig.savefig(ROOT/'simulation_summary.png',dpi=150);plt.close(fig)
    print('Written',ROOT/'simulation_summary.png')


if __name__=='__main__': main()

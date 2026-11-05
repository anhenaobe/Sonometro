"""ngspice 46 + unchanged official TI OPAx192. One engine process per case.
Raw waveforms/logs are ignored runs/; compact evidence in results/spice_CASE.json.
"""
import argparse, ctypes as ct, hashlib, json, os, shutil
from pathlib import Path
import numpy as np
from models import architectures

ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--dll',type=Path,required=True)
    p.add_argument('--case',choices=['ac','tran','overload','startup','unplug','poweroff','supply','tolerance'],default='ac')
    args=p.parse_args();out=ROOT/'runs'/args.case;out.mkdir(parents=True,exist_ok=True)
    model=ROOT.parent/'afe/models/ti/OPAx192.LIB'
    if not model.exists():p.error('fetch official model using ../afe/fetch_model.py first')
    deck=(ROOT/'chain.cir').read_text().replace('../afe/models/ti/OPAx192.LIB',model.as_posix())
    if args.case=='overload':deck=deck.replace('AMP=3.516','AMP=6')
    if args.case=='supply':deck=deck.replace('VS=24','VS=20')
    if args.case=='tolerance':
        deck=deck.replace('RT=1690 RB=1000','RT=1691.69 RB=999').replace('1370\n','1371.37\n').replace('2000\n','2002\n').replace('1500p','1515p').replace('750p','757.5p')
    if args.case in ('startup','unplug'):
        stimulus='PWL(0 0 1m 0 2m 12.5 200m 12.5)' if args.case=='startup' else 'PWL(0 12.5 1m 12.5 1.001m 24 200m 24)'
        deck=deck.replace('DC 12.5 AC 1 SIN(12.5 {AMP} {FREQ})',stimulus)
        if args.case=='startup':deck=deck.replace('Vcc vcc 0 {VS}','Vcc vcc 0 PWL(0 0 1m 24 200m 24)')
    if args.case=='poweroff':deck=deck.replace('Vbias bias 0 2.5','Vbias bias 0 0')
    (out/'run.cir').write_text(deck,encoding='utf-8');os.chdir(out)
    logs=[];cbtype=ct.CFUNCTYPE(ct.c_int,ct.c_char_p,ct.c_int,ct.c_void_p)
    @cbtype
    def log(msg,ident,user):logs.append(msg.decode(errors='replace'));return 0
    dll=args.dll.resolve();handle=os.add_dll_directory(str(dll.parent))
    lib=ct.CDLL(str(dll));lib.ngSpice_Init.argtypes=[ct.c_void_p]*7;lib.ngSpice_Command.argtypes=[ct.c_char_p]
    lib.ngSpice_Init(ct.cast(log,ct.c_void_p),None,None,None,None,None,None)
    def cmd(s):
        if lib.ngSpice_Command(s.encode()):raise RuntimeError(s)
    cm=dll.parent.parent/'lib/ngspice';cmhandle=os.add_dll_directory(str(cm))
    for name in ('analog.cm','spice2poly.cm','table.cm','xtradev.cm'):
        target=out/name;shutil.copy2(cm/name,target);cmd('codemodel '+target.as_posix())
    cmd('set ngbehavior=ps');cmd('set numdgt=15');cmd('set wr_vecnames');cmd('set wr_singlescale');cmd('source run.cir')
    ac=args.case in ('ac','tolerance')
    cmd('ac dec 100 10 10Meg' if ac else ('tran 2u 200m' if args.case in ('startup','unplug') else 'tran 0.2u 8m'))
    cmd('wrdata data.txt v(adc) v(filtered) v(b)')
    (out/'ngspice.log').write_text('\n'.join(logs),encoding='utf-8')
    if any('aborted' in x.lower() or x.startswith('stderr Error') for x in logs):
        failure=dict(status='FAILED_NO_SPICE_RESULT_ACCEPTED',case=args.case,engine='ngspice46 shared',
            model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),deck_sha256=hashlib.sha256(deck.encode()).hexdigest(),
            reason='Official TI macro model operating point fails: singular internal clamp nodes; no valid AC/transient result',
            log='spice_failure.log',physical_test=False)
        (ROOT/'results'/'spice_failure.log').write_text('\n'.join(logs[:30]+logs[-6:]),encoding='utf-8')
        (ROOT/'results'/('spice_'+args.case+'.json')).write_text(json.dumps(failure,indent=2)+'\n',encoding='utf-8')
        raise RuntimeError('NO ACCEPTED RESULT; see results/spice_'+args.case+'.json')
    data=np.loadtxt(out/'data.txt',skiprows=1)
    result=dict(case=args.case,engine='ngspice46 shared',model='TI OPAx192 Final1.7',
        model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),dll_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
        deck_sha256=hashlib.sha256(deck.encode()).hexdigest(),physical_test=False,
        limitations=['Ideal electrical sensor,Rs50 assumed','No ADC converter model, clamps or power-off diode model','No validated SPICE noise prediction','THD is macromodel output, not guaranteed physical THD'])
    if ac:
        f=data[:,0];h=data[:,1]+1j*data[:,2];rows=[]
        for freq in (20,100,1000,4000,10000,20000):
            idx=np.argmin(abs(f-freq));ideal=architectures()[2].response([f[idx]])[0]
            rows.append(dict(frequency_Hz=float(f[idx]),gain=float(abs(h[idx])),phase_deg=float(np.angle(h[idx],deg=True)),
                ratio_to_ideal_dB=float(20*np.log10(abs(h[idx]/ideal)))))
        result['checkpoints']=rows
    else:
        result['adc_min_V']=float(data[:,1].min());result['adc_max_V']=float(data[:,1].max())
        result['buffer_min_V']=float(data[:,3].min());result['buffer_max_V']=float(data[:,3].max())
        if args.case in ('tran','supply','overload','poweroff'):
            t=data[:,0];selected=t>=.004;tt=t[selected];y=data[selected,1]
            basis=np.column_stack([np.ones(len(tt))]+[v for k in range(1,11) for v in (np.sin(2*np.pi*1000*k*tt),np.cos(2*np.pi*1000*k*tt))])
            fit=np.linalg.lstsq(basis,y,rcond=None)[0];amp=np.hypot(fit[1::2],fit[2::2])
            result.update(fundamental_Vpeak=float(amp[0]),harmonics_2_to_10_ratio=float(np.linalg.norm(amp[1:])/amp[0]),
                          fit_note='least-squares4..8ms; unwindowed periodic sine; not real circuit THD')
    (ROOT/'results'/('spice_'+args.case+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()

"""Run real ngspice shared library (KiCad distribution), with official TI model.

No behavioral op-amp replacement is used. Netlists/logs/wrdata are kept in runs/.
LTspice can open afe.cir independently; this runner does NOT claim LTspice execution.
"""
import argparse
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--dll', type=Path, required=True)
    p.add_argument('--codemodel-dir', type=Path, help='directory containing analog.cm (KiCad auto-detected)')
    p.add_argument('--case', choices=['ac','tran','noise','overload','startup','zout','loop'], default='ac')
    p.add_argument('--amplitude', type=float, default=3.516)
    p.add_argument('--frequency', type=float, default=1000)
    p.add_argument('--supply', type=float, default=5)
    p.add_argument('--rs', type=float, default=50)
    p.add_argument('--rt', type=float, default=16900)
    p.add_argument('--rb', type=float, default=10000)
    p.add_argument('--ng', type=float, default=1, choices=[1,10.09])
    p.add_argument('--existing-coupling', action='store_true', help='include existing 1uF/100k example as external block')
    p.add_argument('--nodeset',action='store_true',help='2.5V numerical starting guess for difficult operating point')
    p.add_argument('--tag', default=None)
    args = p.parse_args()
    tag = args.tag or args.case
    if not re.fullmatch(r'[A-Za-z0-9_-]+',tag): p.error('invalid tag')
    out = ROOT/'runs'/tag
    out.mkdir(parents=True,exist_ok=True)
    model = ROOT/'models/ti/OPAx192.LIB'
    if not model.exists(): p.error('run fetch_model.py first')
    deck = (ROOT/'afe.cir').read_text()
    deck = deck.replace('"models/ti/OPAx192.LIB"','"'+model.as_posix()+'"')
    deck = re.sub(r'\.param VSUP=.*',f'.param VSUP={args.supply} VCM=2.5 VUP=2.5 AMP={args.amplitude} FREQ={args.frequency} RS={args.rs}',deck)
    rf,rg=(.001,1e12) if args.ng==1 else (9090,1000)
    deck = re.sub(r'\.param RT=.*',f'.param RT={args.rt} RB={args.rb} RF={rf} RG={rg}',deck)
    if args.existing_coupling:
        # Existing block copied as an INTERFACE MODEL, not a new filter design.
        deck=deck.replace('Rsource source input {RS}',
            'Rsource source before_c {RS}\nC_existing before_c input 1u\nR_existing_return input 0 100k')
        deck=deck.replace('Vref ref 0 {VCM}', 'Vref ref 0 2.710027100271')
        # Keep feedback gain referred to independent Vcenter, not Vbias.
        deck=deck.replace('Rg minus ref {RG}', 'Vcenter center 0 2.5\nRg minus center {RG}')
    deck = re.sub(r'^\.(ac|tran|noise).*\n','',deck,flags=re.M)
    if args.nodeset:
        deck=deck.replace('.end','.nodeset V(output)=2.5 V(plus)=2.5 V(minus)=2.5\n.end')
    if args.case in ('zout','loop'):
        deck=deck.replace('AC 1 SIN','AC 0 SIN')
        if args.case=='zout':
            deck=deck.replace('.end','Itest 0 output DC 0 AC 1\n.end')
        else:
            deck=deck.replace('Rf output minus', 'Vloop output feedback DC 0 AC 1\nRf feedback minus')
    if args.case=='startup':
        deck = deck.replace('Vcc vcc 0 {VSUP}','Vcc vcc 0 PWL(0 0 1m {VSUP})')
        deck = deck.replace('Vref ref 0 {VCM}','Vref ref 0 PWL(0 0 1m {VCM})')
        # Hazard reproduction at upstream port; not a designed protection.
        deck = re.sub(r'^Vsignal .*$', 'Vsignal source 0 PWL(0 0 1m 15.19 10m 14 50m 10 500m 2.5 600m 2.5)',deck,flags=re.M)
    (out/'run.cir').write_text(deck)
    os.chdir(out)
    logs=[]
    cbtype=ct.CFUNCTYPE(ct.c_int,ct.c_char_p,ct.c_int,ct.c_void_p)
    @cbtype
    def log(msg, ident, userdata):
        logs.append(msg.decode(errors='replace'))
        return 0
    if os.name=='nt': dll_directory=os.add_dll_directory(str(args.dll.resolve().parent))
    lib=ct.CDLL(str(args.dll.resolve()))
    lib.ngSpice_Init.argtypes=[ct.c_void_p]*7
    lib.ngSpice_Command.argtypes=[ct.c_char_p]
    lib.ngSpice_Init(ct.cast(log,ct.c_void_p),None,None,None,None,None,None)
    def command(s):
        code=lib.ngSpice_Command(s.encode())
        if code: raise RuntimeError(f'ngspice command failed ({code}): {s}')
    try:
        command('version')
        cm = args.codemodel_dir or args.dll.resolve().parent.parent/'lib/ngspice'
        if cm.exists():
            if os.name=='nt': cm_directory=os.add_dll_directory(str(cm.resolve()))
            local_cm = out/'codemodels'
            local_cm.mkdir(exist_ok=True)
            for name in ('analog.cm','spice2poly.cm','table.cm','xtradev.cm'):
                if (cm/name).exists():
                    shutil.copy2(cm/name,local_cm/name)
                    command('codemodel '+(local_cm/name).as_posix())
        command('set ngbehavior=ps')
        command('set numdgt=15')
        command('set wr_vecnames')
        command('set wr_singlescale')
        command('source run.cir')
        if args.case in ('ac','zout','loop'):
            command('ac dec 80 20 20Meg')
            command('wrdata data.txt v(output) v(feedback)' if args.case=='loop' else 'wrdata data.txt v(output)')
        elif args.case=='noise':
            command('noise v(output) vsignal dec 100 20 20k')
            command('setplot noise1')
            command('wrdata data.txt onoise_spectrum inoise_spectrum')
            command('setplot noise2')
            command('print onoise_total inoise_total')
        else:
            command('tran 50u 600m' if args.case=='startup' else
                    f'tran {1/args.frequency/500:.12g} {max(5/args.frequency,.25 if args.existing_coupling else 0):.12g}')
            command('wrdata data.txt v(input) v(output) v(vcc)')
    finally:
        (out/'ngspice.log').write_text('\n'.join(logs)+'\n')
        (out/'manifest.json').write_text(json.dumps({'engine':'ngspice shared','arguments':{k:str(v) for k,v in vars(args).items()},
            'dll_sha256':hashlib.sha256(args.dll.read_bytes()).hexdigest(),
            'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest()},indent=2)+'\n')
    if not (out/'data.txt').exists():
        raise RuntimeError('no output data; inspect runs log')
    errors=[line for line in logs if line.startswith('stderr Error') or 'aborted' in line.lower()]
    if errors: raise RuntimeError('\n'.join(errors))
    print('\n'.join(logs[-12:]))
    print('Simulation data:',out/'data.txt')


if __name__=='__main__': main()

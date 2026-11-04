"""Analytical design calculations, NOT SPICE or measurements. Standard library only."""
import cmath
import csv
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
S = 0.0556  # V/Pa, preliminary unit sensitivity
K, T, F0, F1 = 1.380649e-23, 300.0, 20.0, 20000.0
RT, RB, RF, RG, RS = 16900., 10000., 9090., 1000., 50.
ALPHA = RB / (RT + RB)
G = 1 + RF / RG


def dbspl(p):
    return 20 * math.log10(p / 20e-6)


def integrate(f, n=20000):
    # Log-frequency trapezoid integration handles 1/f and source impedance.
    x0, y0, total = F0, f(F0), 0.
    for i in range(1, n + 1):
        x = F0 * (F1 / F0) ** (i / n)
        y = f(x)
        total += (x - x0) * (y + y0) / 2
        x0, y0 = x, y
    return total


def noise_gain_budget(alpha, ng, rtop, rbottom, rf, rg):
    """Rs=50 ohm resistive baseline; reference ideal, its allowance listed separately."""
    zplus = 1 / (1 / (rtop + RS) + 1 / rbottom) if rbottom else RS
    zminus = rf * rg / (rf + rg) if rf else 0.
    # Fit en^2=a+b/f to OPA192 upper-common-mode TYP points (100Hz,32nV;1kHz,12.5nV).
    b = ((32e-9)**2 - (12.5e-9)**2) / (1/100 - 1/1000)
    a = (12.5e-9)**2 - b / 1000
    opamp = ng * math.sqrt(a * (F1-F0) + b * math.log(F1/F0))
    resistors = ng * math.sqrt(4*K*T*(zplus+zminus)*(F1-F0))
    current = ng * 1.5e-15 * math.sqrt((zplus*zplus + zminus*zminus)*(F1-F0))
    total = math.sqrt(opamp**2 + resistors**2 + current**2)
    # alpha includes loading from finite source resistance.
    return {'voltage_noise_out_uVrms': opamp*1e6,
            'resistors_out_uVrms_including_Rs': resistors*1e6,
            'current_noise_out_uVrms': current*1e6,
            'total_out_uVrms': total*1e6, 'total_input_uVrms': total/alpha/ng*1e6,
            'equivalent_Pa_rms': total/alpha/ng/S,
            'equivalent_dB_SPL_rms': dbspl(total/alpha/ng/S),
            'bias_reference_noise_transfer': ng*(1-alpha),
            'feedback_reference_noise_transfer': 1-ng,
            'reference_allowance_uVrms': 1.0}


def main():
    rows = []
    for level, kind in [(30,'RMS'),(60,'RMS'),(94,'RMS'),(120,'RMS'),(130,'PEAK')]:
        p = 20e-6 * 10**(level/20)
        vp = S * p * (math.sqrt(2) if kind == 'RMS' else 1)
        vr = vp / math.sqrt(2)
        rows.append({'level_dB': level, 'definition': kind, 'p_rms_Pa': p if kind=='RMS' else p/math.sqrt(2),
                     'p_peak_Pa': p*math.sqrt(2) if kind=='RMS' else p,
                     'sensor_Vrms_sine': vr, 'sensor_Vpeak': vp,
                     'A_Vpeak': ALPHA*vp, 'B_Vpeak': G*vp, 'C_high_Vpeak': ALPHA*G*vp,
                     'A_within_1p5Vpeak': ALPHA*vp<=1.5,
                     'B_within_1p5Vpeak': G*vp<=1.5,
                     'C_high_within_1p5Vpeak': ALPHA*G*vp<=1.5})
    alpha_loaded = RB / (RT + RB + RS)
    noise = {'A': noise_gain_budget(alpha_loaded, 1, RT, RB, 0, 0),
             'B': noise_gain_budget(1, G, 0, 0, RF, RG),
             'C_high': noise_gain_budget(alpha_loaded, G, RT, RB, RF, RG)}
    corners = []
    # Independent 0.1% +25ppm/K*50K components: worst-case bounds, no Monte Carlo.
    for dt in (0,50):
        for signs in itertools.product((-1,1), repeat=4):
            rt,rb,rf,rg = [v*(1+s*.001)*(1+s*25e-6*dt) for v,s in zip((RT,RB,RF,RG),signs)]
            alpha = rb/(rt+rb)
            corners.append({'delta_T_K':dt,'rt':rt,'rb':rb,'rf':rf,'rg':rg,
                            'gain_A':alpha,'gain_B':1+rf/rg,'gain_C_high':alpha*(1+rf/rg)})
    # Existing upstream example ONLY, not newly designed coupling/filter:
    # source Rs + 1/(s*1uF); shunt Rret100k; then RT/RB at ideal Vref AC-ground.
    response = []
    for f in (20,50,100,1000,10000,20000):
        z = RS + 1/(2j*math.pi*f*1e-6)
        load = 1/(1/100000 + 1/(RT+RB))
        h = ALPHA * load/(z+load)
        response.append({'frequency_Hz':f,'gain_sensor_to_out':abs(h),
                         'loading_error_dB_vs_ideal_A':20*math.log10(abs(h)/ALPHA),
                         'phase_deg':cmath.phase(h)*180/math.pi})
    results = {'status':'CALCULATED_NOT_MEASURED', 'band_Hz':[F0,F1], 'temperature_K':T,
               'sensitivity_V_per_Pa_PROVISIONAL':S, 'gain_A_ideal':ALPHA, 'gain_A_Rs50':alpha_loaded,
               'gain_B':G,'gain_C_high':ALPHA*G,'amplitudes':rows,'noise_typical_estimate':noise,
               'headroom':{name:{'max_sensor_Vpeak':1.5/g,'max_dB_SPL_peak':dbspl(1.5/g/S),
                                  'max_dB_SPL_RMS_sine':dbspl(1.5/g/S/math.sqrt(2))}
                           for name,g in [('A',ALPHA),('B',G),('C_high',ALPHA*G)]},
               'corners':{f'{name}_{dt}K':{'min':min(c[key] for c in corners if c['delta_T_K']==dt),
                                          'max':max(c[key] for c in corners if c['delta_T_K']==dt)}
                          for name,key in [('A','gain_A'),('B','gain_B'),('C_high','gain_C_high')] for dt in (0,50)},
               'upstream_example_loaded':response,
               'existing_return_DC':{'Rdc_ohm':100000,'bias_reference_required_V':2.5*(100000+RT+RB)/(100000+RT),
                    'bias_reference_E96_8k45_10k_from5V':5*10000/(8450+10000),
                    'output_center_with_E96_V':5*10000/(8450+10000)*(100000+RT)/(100000+RT+RB)},
               'max_signal_resistor_power_W':{ 'RT':(S*20e-6*10**6.5)**2/2/(RT+RB)**2*RT,
                                               'RB':(S*20e-6*10**6.5)**2/2/(RT+RB)**2*RB},
               'slew_required_V_per_us_at_20k_1p5Vpeak':2*math.pi*20000*1.5/1e6,
               'notes':['No guaranteed noise maximum; en fit is an estimate, common-mode crossover remains OPEN.',
                        'Noise excludes upstream electronics, actual Vref, ADC and out-of-band aliasing.',
                        'Separate bias and feedback references are required when NG>1 and input DC is not Vcenter.',
                        'PCM SNR99dB is A-weighted: not summed with unweighted20Hz-20kHz budget.']}
    (ROOT/'calculations.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    with (ROOT/'tolerance_corners.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=corners[0].keys());writer.writeheader();writer.writerows(corners)
    print(json.dumps({k:results[k] for k in ('gain_A_ideal','gain_C_high','headroom','noise_typical_estimate','corners')},indent=2))


if __name__=='__main__':
    main()

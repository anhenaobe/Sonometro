"""Synthetic numerical verification only: no physical circuit assertion."""
import sys, unittest,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'hardware/revision'))
import numpy as np
from scipy import signal
from models import pressure,hp_cap,sk_values,architectures,ALPHA,voxter

class Models(unittest.TestCase):
    def test_rms_peak_definition(self):
        rms=pressure(130-10*np.log10(2));pk=pressure(130,True)
        self.assertAlmostEqual(rms['sensor_Vpeak'],pk['sensor_Vpeak'],places=12)
        self.assertAlmostEqual(pressure(94)['p_rms_Pa'],1.002374467254545,places=12)

    def test_loaded_cap_against_complex_impedance(self):
        rs=50;rl=1/(1/100000+1/26900);c=1e-6
        n,d=hp_cap(c,rs,rl)
        for f in (20,100,1000,20000):
            s=2j*np.pi*f;h=np.polyval(n,s)/np.polyval(d,s)
            self.assertAlmostEqual(abs(h-rl/(rs+1/(s*c)+rl)),0,places=14)

    def test_sk_kcl_independent_solution(self):
        from models import RTH
        sk=sk_values();ra=1370+RTH;r2=2000;c1=1500e-12;c2=750e-12
        for f in (20,1000,20000,75000):
            s=2j*np.pi*f
            # vout=vplus; two independent node equations, not the polynomial formula.
            matrix=np.array([[1/ra+1/r2+s*c1,-1/r2-s*c1],[-1/r2,1/r2+s*c2]])
            out=np.linalg.solve(matrix,[1/ra,0])[1]
            expected=np.polyval(sk['num'],s)/np.polyval(sk['den'],s)
            self.assertLess(abs(out-expected),1e-12)
        self.assertAlmostEqual(sk['Q'],1/np.sqrt(2),places=6)

    def test_phase_alone_preserves_periodic_rms(self):
        t=np.arange(48000)/48000
        x=np.sin(2*np.pi*1000*t)+.3*np.sin(2*np.pi*4000*t)
        fft=np.fft.rfft(x);frequency=np.fft.rfftfreq(len(x),1/48000)
        y=np.fft.irfft(fft*np.exp(1j*.7*np.sin(frequency/1000)),n=len(x))
        self.assertAlmostEqual(np.mean(x*x),np.mean(y*y),places=12)
        self.assertGreater(np.sqrt(np.mean((x-y)**2)),.1)

    def test_group_delay_removes_documented_constant(self):
        a=architectures()[2];f=np.array([20,1000,20000])
        # ADC HP delay is independently derived from first-order pole.
        tau=(2*np.pi*a.adc_hp_Hz)/( (2*np.pi*f)**2+(2*np.pi*a.adc_hp_Hz)**2)
        np.testing.assert_allclose(a.group_delay(f,True)-a.group_delay(f),a.delay_s+tau,rtol=1e-7)

    def test_voxter_is_shelving_not_integrator(self):
        n,d=voxter(False)
        # The full network includes output LP, whose removal leaves NG tending to1.
        s=2j*np.pi*1e10;h=np.polyval(n,s)/np.polyval(d,s)
        self.assertAlmostEqual(abs(h*(1+s*4.7e-6)),100000/100050,places=7)

    def test_a3_headroom_nominal(self):
        self.assertLess(ALPHA*pressure(130,True)['sensor_Vpeak'],1.5)
        self.assertGreater(11*pressure(120)['sensor_Vpeak'],1.5)

    def test_reference_shared_ripple_is_not_tracking_topology(self):
        # Regression: feeding Vmid through RG gives about -10, not +1.
        path=Path(__file__).resolve().parents[2]/'hardware/revision/results/reference_perturbations.csv'
        with path.open(encoding='utf-8',newline='') as f:rows={r['test']:r for r in csv.DictReader(f)}
        vox=float(rows['shared_VDDA_mid_10mVpeak']['error_output_Vrms'])
        ideal=float(rows['ideal_tracking_topology_NOT_Voxter']['error_output_Vrms'])
        self.assertGreater(vox,.037)
        self.assertLess(vox,.041)
        self.assertLess(ideal,.002)

if __name__=='__main__':unittest.main()

"""Post-process the KiCad-written pcb.kicad_pro: JLCPCB-friendly rules + 'Potencia' net class."""
import json, sys, copy
p = sys.argv[1]
d = json.load(open(p))
ns = d['net_settings']
default = [c for c in ns['classes'] if c['name'] == 'Default'][0]
default.update(clearance=0.15, track_width=0.2, via_diameter=0.6, via_drill=0.3)
pot = copy.deepcopy(default)
pot.update(name='Potencia', clearance=0.15, track_width=0.5, via_diameter=0.8, via_drill=0.4, priority=0)
ns['classes'] = [c for c in ns['classes'] if c['name'] != 'Potencia'] + [pot]
ns['netclass_patterns'] = [{'netclass': 'Potencia', 'pattern': n} for n in
                           ('24V_IN', '24V_PROT', '3V3', '5V', '5V_A', 'GND', '*SW_3', '*SW_5',
                            '*IEPE_SUP', '*IEPE_SUP_SV', 'Net-(D1-A)')]
r = d['board']['design_settings']['rules']
r.update(min_clearance=0.15, min_track_width=0.15, min_via_diameter=0.5, min_through_hole_diameter=0.3,
         min_copper_edge_clearance=0.3)
json.dump(d, open(p, 'w'), indent=2)
print('project rules updated')

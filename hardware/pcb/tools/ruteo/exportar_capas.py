"""Exporta imágenes de cada capa (y de la serigrafía) a PNG para revisarlas a ojo.

Usa kicad-cli (PDF por capa) y pypdfium2 para rasterizar, recortando al contorno de la placa.
Uso: python exportar_capas.py [pcb] [carpeta_salida]   (Python del sistema con pypdfium2)
Salida: <carpeta>/F_Cu.png, B_Cu.png, F_Silkscreen.png, F_Mask.png, B_Mask.png
"""
import os
import subprocess
import sys

import pypdfium2 as pdfium

HERE = os.path.dirname(os.path.abspath(__file__))
KCLI = os.environ.get('KICAD_CLI', r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe')
SETS = {
    'F_Cu': 'F.Cu,Edge.Cuts',
    'B_Cu': 'B.Cu,Edge.Cuts',
    'F_Silkscreen': 'F.Silkscreen,Edge.Cuts,F.Mask',
    'F_Fab': 'F.Fab,Edge.Cuts',
    'F_Mask': 'F.Mask,Edge.Cuts',
    'B_Mask': 'B.Mask,Edge.Cuts',
}
X0, Y0, X1, Y1 = 98.0, 98.0, 192.0, 176.0      # mm de la hoja (KiCad imprime a escala 1:1); incluye el BNC
S = 24                                         # px por mm


def main():
    pcb = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'pcb.kicad_pcb')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'out', 'capas')
    os.makedirs(out, exist_ok=True)
    for name, layers in SETS.items():
        pdf = os.path.join(out, name + '.pdf')
        args = [KCLI, 'pcb', 'export', 'pdf', '--mode-single', '--layers', layers, '-o', pdf, pcb]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f'kicad-cli falló en {name}: {r.stdout}{r.stderr}')
        page = pdfium.PdfDocument(pdf)[0]
        wpt, hpt = page.get_size()
        scale = S * 25.4 / 72
        img = page.render(scale=scale).to_pil()
        mm_x, mm_y = wpt / 72 * 25.4, hpt / 72 * 25.4
        img = img.crop((int(X0 / mm_x * img.width), int(Y0 / mm_y * img.height),
                        int(X1 / mm_x * img.width), int(Y1 / mm_y * img.height)))
        img.save(os.path.join(out, name + '.png'))
        print('escrito', os.path.join(out, name + '.png'))


if __name__ == '__main__':
    main()

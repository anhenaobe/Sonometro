"""Download official model for local simulation; do not redistribute vendor archive."""
import hashlib
from pathlib import Path
import urllib.request
import zipfile
import io
root = Path(__file__).resolve().parent / 'models'
root.mkdir(exist_ok=True)
data = urllib.request.urlopen('https://www.ti.com/lit/zip/SBOM862', timeout=40).read()
(root/'SBOM862.zip').write_bytes(data)
with zipfile.ZipFile(io.BytesIO(data)) as z:
    matches = [name for name in z.namelist() if Path(name).name.lower() == 'opax192.lib']
    if len(matches) != 1:
        raise RuntimeError('unexpected TI archive structure')
    model = z.read(matches[0])
if b'.SUBCKT OPAx192 IN+ IN- VCC VEE OUT' not in model:
    raise RuntimeError('model pin order changed; inspect before simulation')
(root/'ti').mkdir(exist_ok=True)
(root/'ti/OPAx192.LIB').write_bytes(model)
print('OPAx192.LIB SHA256:', hashlib.sha256(model).hexdigest())

"""Receive real ADC bursts. No offset subtraction, filters, or fabricated captures."""
import argparse
import csv
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import struct
import time
import tempfile
import zlib

HEADER = struct.Struct('<4sHH14I')
FIELDS = ('sequence capture_id first_sample count fs_num fs_den format adc_bits '
          'vref_uv total_samples dropped_samples adc_errors flags payload_bytes').split()
FIRST, LAST, GAP, ERROR, VREF_ASSUMED = 1, 2, 4, 8, 16


class CaptureError(ValueError):
    pass


@dataclass
class Capture:
    headers: list
    samples: list


def exact_read(stream, size):
    chunks = bytearray()
    while len(chunks) < size:
        data = stream.read(size - len(chunks))
        if not data:
            raise CaptureError(f'incomplete block: {len(chunks)}/{size} bytes')
        chunks.extend(data)
    return bytes(chunks)


def read_capture(stream):
    headers, samples = [], []
    while True:
        packed = exact_read(stream, HEADER.size)
        magic, version, size, *values = HEADER.unpack(packed)
        if (magic, version, size) != (b'IEP1', 1, 64):
            raise CaptureError('invalid magic/version/header length; no silent resynchronization')
        h = dict(zip(FIELDS, values))
        if (not h['fs_num'] or not h['fs_den'] or h['format'] != 1 or
                h['adc_bits'] != 12 or not h['vref_uv'] or h['count'] > 512 or
                h['payload_bytes'] != h['count'] * 2 or h['total_samples'] > 8192):
            raise CaptureError('invalid or unsupported metadata')
        payload = exact_read(stream, h['payload_bytes'])
        crc, = struct.unpack('<I', exact_read(stream, 4))
        if zlib.crc32(packed + payload) != crc:
            raise CaptureError('CRC mismatch')
        if h['first_sample'] != len(samples):
            raise CaptureError('sample gap/duplicate')
        if not headers:
            if not h['flags'] & FIRST or not h['flags'] & GAP:
                raise CaptureError('missing burst boundary')
        else:
            prev = headers[-1]
            if h['sequence'] != (prev['sequence'] + 1) & 0xFFFFFFFF:
                raise CaptureError('block sequence gap/duplicate')
            constant = ('capture_id', 'fs_num', 'fs_den', 'format', 'adc_bits',
                        'vref_uv', 'total_samples')
            if any(h[k] != prev[k] for k in constant) or h['flags'] & (FIRST | GAP):
                raise CaptureError('metadata changed within capture')
        if h['dropped_samples'] or h['adc_errors'] or h['flags'] & ERROR:
            raise CaptureError(f'MCU acquisition error: {h}')
        if not h['count']:
            raise CaptureError('empty capture')
        block = struct.unpack('<' + 'H' * h['count'], payload)
        if any(x > 4095 for x in block):
            raise CaptureError('sample outside unsigned 12-bit range')
        samples.extend(block)
        headers.append(h)
        if len(samples) > 8192:
            raise CaptureError('capture exceeds SRAM capture contract')
        if h['flags'] & LAST:
            if len(samples) != h['total_samples'] or len(samples) != 8192:
                raise CaptureError('incorrect capture sample count')
            return Capture(headers, samples)


def analyze(samples, fs, vref):
    import numpy as np
    v = np.asarray(samples, dtype=float) * vref / 4095.0
    n = len(v)
    # Periodic Hann for spectral display only; raw samples and RMS are untouched.
    w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)
    spec = np.abs(np.fft.rfft(v * w)) / w.sum()
    spec[1:-1 if n % 2 == 0 else None] *= np.sqrt(2)
    freq = np.fft.rfftfreq(n, 1 / fs)
    # Constant DC with Hann occupies bins 0 and 1. Do not call this an AC filter.
    peak = 3 + int(np.argmax(spec[3:]))
    metrics = {'rms_total_V_including_DC': float(np.sqrt(np.mean(v * v))),
               'mean_V_reported_only': float(np.mean(v)),
               'dominant_tone_Hz': float(freq[peak]), 'bin_width_Hz': fs / n,
               'tone_search_min_Hz': float(freq[3]),
               'clipped_sample_count': int(np.count_nonzero((v <= 0) | (v >= vref))),
               'fft_units': 'V RMS per coherent tone bin; DC in V; periodic Hann',
               'offset_subtracted': False}
    return v, freq, spec, metrics


class RecordingReader:
    def __init__(self, port, raw):
        self.port, self.raw = port, raw
        self.first_read = True

    def read(self, n):
        data = self.port.read(n)
        if self.first_read and data:
            self.port.timeout = 3  # burst is now acquired; normal block deadline
            self.first_read = False
        self.raw.write(data)
        return data


def main():
    p = argparse.ArgumentParser(__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--port', help='ST-LINK VCP, e.g. COM5')
    source.add_argument('--replay', type=Path, help='existing .iep file; never generates data')
    p.add_argument('--rate', type=int, default=48000)
    p.add_argument('--baud', type=int, default=115200)
    p.add_argument('--output', type=Path, required=True, help='new output prefix')
    p.add_argument('--plot', action='store_true')
    args = p.parse_args()
    if not 1000 <= args.rate <= 96000:
        p.error('rate must be 1000..96000')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    paths = {s: args.output.with_suffix(s) for s in ('.iep', '.json', '.csv', '.png')}
    if any(path.exists() for path in paths.values()):
        p.error('output exists; choose a new prefix to preserve previous captures')
    metadata = {'origin': 'serial' if args.port else 'replay',
                'physical_validation': 'OPEN', 'requested_rate_Hz': args.rate,
                'port': args.port, 'baud': args.baud, 'utc_started': time.time()}
    try:
        if args.replay:
            raw = args.replay.read_bytes()
            paths['.iep'].write_bytes(raw)
            cap = read_capture(io.BytesIO(raw))
        else:
            import serial
            # At 1 kSPS the burst itself takes 8.192 s before any UART output.
            with serial.Serial(args.port, args.baud,
                               timeout=8192 / args.rate + 3, write_timeout=3) as port:
                port.reset_input_buffer()
                port.write(f'R{args.rate}\nC'.encode('ascii'))
                port.flush()
                with paths['.iep'].open('xb') as raw:
                    cap = read_capture(RecordingReader(port, raw))
        h = cap.headers[0]
        fs = h['fs_num'] / h['fs_den']
        voltage, freq, spectrum, metrics = analyze(cap.samples, fs, h['vref_uv'] / 1e6)
        metadata.update({'status': 'received_crc_and_continuity_valid', 'headers': cap.headers,
                         'fs_nominal_Hz': fs, 'fs_measured_Hz': None,
                         'vref_assumed': bool(h['flags'] & VREF_ASSUMED), **metrics})
        with paths['.csv'].open('x', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['index', 'time_s_nominal', 'adc_u12', 'voltage_V_assumed_vref', 'fs_nominal_Hz'])
            writer.writerows((i, i / fs, x, float(voltage[i]), fs) for i, x in enumerate(cap.samples))
        if args.plot:
            os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'sonometro-mpl'))
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(2, 1, figsize=(10, 7), layout='constrained')
            axes[0].plot([i / fs for i in range(len(voltage))], voltage)
            axes[0].set(xlabel='Tiempo (s, reloj nominal)', ylabel='V (VREF asumida)', title='Muestras recibidas sin restar offset')
            axes[1].plot(freq, spectrum)
            axes[1].set(xlabel='Frecuencia (Hz)', ylabel='V RMS/bin (DC: V)', title='FFT Hann; sin filtros ni cancelación de offset')
            fig.savefig(paths['.png'], dpi=140)
            plt.close(fig)
    except (CaptureError, OSError) as exc:
        metadata.update(status='FAIL', error=str(exc))
        raise SystemExit(str(exc)) from exc
    finally:
        paths['.json'].write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()

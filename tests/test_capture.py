"""Synthetic protocol/unit tests ONLY: no hardware results."""
import io
from pathlib import Path
import struct
import sys
import unittest
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'software'))
from capture import HEADER, CaptureError, read_capture, analyze


def frame(seq, first, count=512, flags=16, value=2048):
    header = HEADER.pack(b'IEP1', 1, 64, seq, 7, first, count, 48000000, 1000,
                         1, 12, 3300000, 8192, 0, 0, flags, count * 2)
    payload = struct.pack('<' + 'H' * count, *([value] * count))
    return header + payload + struct.pack('<I', zlib.crc32(header + payload))


def burst():
    return b''.join(frame(i, 512 * i, flags=16 | (5 if i == 0 else 0) |
                         (2 if i == 15 else 0)) for i in range(16))


class ProtocolTests(unittest.TestCase):
    def test_complete_synthetic_burst(self):
        result = read_capture(io.BytesIO(burst()))
        self.assertEqual(len(result.samples), 8192)
        self.assertEqual(result.headers[0]['fs_num'] / result.headers[0]['fs_den'], 48000)

    def test_truncated(self):
        with self.assertRaisesRegex(CaptureError, 'incomplete'):
            read_capture(io.BytesIO(burst()[:-1]))

    def test_corruption(self):
        data = bytearray(burst())
        data[75] ^= 1
        with self.assertRaisesRegex(CaptureError, 'CRC'):
            read_capture(io.BytesIO(data))

    def test_missing_sequence(self):
        data = frame(0, 0, flags=21) + frame(2, 512)
        with self.assertRaisesRegex(CaptureError, 'sequence'):
            read_capture(io.BytesIO(data))

    def test_duplicate_samples(self):
        with self.assertRaisesRegex(CaptureError, 'gap/duplicate'):
            read_capture(io.BytesIO(frame(0, 0, flags=21) + frame(1, 0)))

    def test_mcu_error(self):
        with self.assertRaisesRegex(CaptureError, 'MCU acquisition'):
            read_capture(io.BytesIO(frame(0, 0, flags=21 | 8)))

    def test_format_rejected(self):
        data = bytearray(burst())
        data[4] = 2
        with self.assertRaisesRegex(CaptureError, 'version'):
            read_capture(io.BytesIO(data))

    def test_synthetic_sine_rms_fft_without_offset_removal(self):
        import numpy as np
        n, fs, bin_number = 8192, 48000, 171
        volts = 1.65 + 0.5 * np.sin(2 * np.pi * bin_number * np.arange(n) / n)
        counts = np.rint(volts * 4095 / 3.3).astype(int)
        v, freq, spec, m = analyze(counts, fs, 3.3)
        self.assertAlmostEqual(m['rms_total_V_including_DC'], (1.65**2 + 0.5**2/2)**0.5, places=4)
        self.assertEqual(m['dominant_tone_Hz'], fs * bin_number / n)
        self.assertAlmostEqual(spec[bin_number], 0.5 / 2**0.5, places=4)
        self.assertAlmostEqual(spec[0], 1.65, places=4)
        self.assertFalse(m['offset_subtracted'])


if __name__ == '__main__':
    unittest.main()

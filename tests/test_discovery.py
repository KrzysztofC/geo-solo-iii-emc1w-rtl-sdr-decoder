import unittest
import numpy as np
from geo_decoder import crc16,decode_block
from cli import pretty

class DiscoveryTests(unittest.TestCase):
    def signal(self, header, payload_prefix=b''):
        data=header+payload_prefix+bytes(header[3]-len(payload_prefix))
        data+=crc16(data).to_bytes(2,'big')
        bits='01'*32+'0111101110111001'+''.join(f'{b:08b}' for b in data)+'01'*16
        index=(np.arange(int(len(bits)*62.5))/62.5).astype(int)
        tones=np.array([237000 if bit=='0' else 399000 for bit in bits])[index]
        burst=np.exp(2j*np.pi*np.cumsum(tones)/2400000)
        return np.concatenate([np.zeros(30000),burst,np.zeros(30000)]),data

    def test_unknown_header_discovered_but_not_selected(self):
        z,data=self.signal(bytes.fromhex('1234561d'))
        self.assertEqual(decode_block(z),[])
        self.assertTrue(any(frame==data for _,frame in decode_block(z,None)))
        self.assertTrue(any(frame==data for _,frame in decode_block(z,data[:4])))

    def test_short_family_discovery(self):
        z,data=self.signal(bytes.fromhex('ffc0ff12'))
        self.assertTrue(any(frame==data for _,frame in decode_block(z,None)))

    def test_shifted_measurements_only_appear_in_discovery(self):
        for header in (bytes.fromhex('b3c0eb1d'), bytes.fromhex('e980b81d')):
            for prefix_byte in (0x00, 0x47, 0x48, 0xff):
                with self.subTest(header=header.hex(), prefix_byte=prefix_byte):
                    prefix = bytes([prefix_byte, 0x40, 0x50])
                    normal, frame = self.signal(header, prefix)
                    shifted, shifted_frame = self.signal(header, b'\x00' + prefix)
                    self.assertIn(frame, [data for _, data in decode_block(normal, header)])
                    self.assertEqual(decode_block(shifted, header), [])
                    self.assertIn(shifted_frame, [data for _, data in decode_block(shifted, None)])

    def test_pretty_unknown_is_raw(self):
        output=pretty(dict(type='discovery',time_utc='test',header='ffc0ff12',payload_bytes=18,frame_bytes=24,frame_hex='example'))
        self.assertIn('Raw: example',output)
        self.assertNotIn('GEN',output)

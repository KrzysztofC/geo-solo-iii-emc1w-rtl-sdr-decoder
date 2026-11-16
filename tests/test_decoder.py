import unittest
from geo_decoder import crc16, reading

class DecoderTests(unittest.TestCase):
    def test_crc_known_vector(self):
        self.assertEqual(crc16(b'123456789'), 0xFEE8)

    def test_field_mapping(self):
        frame = bytearray(35)
        frame[:4] = bytes.fromhex('1d40861d')
        frame[7:9] = (900).to_bytes(2, 'big')
        frame[9:11] = (1200).to_bytes(2, 'big')
        frame[15:19] = (1234567).to_bytes(4, 'big')
        row = reading(frame)
        self.assertEqual(row['use_W'], 900)
        self.assertEqual(row['export_W'], 300)
        self.assertEqual(row['import_W'], 0)
        self.assertEqual(row['generation_kWh'], 1234.567)

if __name__ == '__main__':
    unittest.main()


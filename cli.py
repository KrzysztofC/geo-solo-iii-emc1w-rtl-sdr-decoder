"""Receive Geo Solo III measurements as JSON lines."""
import argparse
import json
import logging
import re
import signal
import threading
from geo_decoder import DEFAULT_METER_ID, live

def parse_meter_id(value):
    if not re.fullmatch(r'[0-9a-fA-F]{6}', value):
        raise argparse.ArgumentTypeError('meter ID must be exactly six hexadecimal digits')
    return bytes.fromhex(value)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=86400, help='Run duration (default: 24 hours)')
    parser.add_argument('--library', help='Windows DLL directory; Linux shared-library file')
    parser.add_argument('--device', type=int, default=0, help='RTL-SDR device index')
    parser.add_argument('--meter-id', type=parse_meter_id, default=DEFAULT_METER_ID,
                        help=f'Three-byte meter radio ID in hex (default: {DEFAULT_METER_ID.hex().upper()})')
    parser.add_argument('--include-frame', action='store_true', help='Include raw frame hex in output')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    def emit(row):
        if not args.include_frame:
            row.pop('frame_hex', None)
        print(json.dumps(row), flush=True)
    try:
        live(args.seconds, emit, stop, args.library, args.device, meter_id=args.meter_id)
    except Exception as exc:
        parser.exit(1, f'Receiver error: {exc}\n')

if __name__ == '__main__':
    main()


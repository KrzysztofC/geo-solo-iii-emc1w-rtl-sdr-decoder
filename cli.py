"""Receive Geo Solo III measurements as JSON lines."""
import argparse
import json
import logging
import signal
import threading
from geo_decoder import live

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=86400, help='Run duration (default: 24 hours)')
    parser.add_argument('--library', help='Windows DLL directory; Linux shared-library file')
    parser.add_argument('--device', type=int, default=0, help='RTL-SDR device index')
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
        live(args.seconds, emit, stop, args.library, args.device)
    except Exception as exc:
        parser.exit(1, f'Receiver error: {exc}\n')

if __name__ == '__main__':
    main()


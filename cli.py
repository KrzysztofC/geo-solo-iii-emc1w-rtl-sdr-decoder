"""Receive Geo Solo III measurements as JSON lines."""
import argparse
import json
import logging
import re
import signal
import threading
import sys
import os
from collections import Counter
from geo_decoder import live

def parse_meter_id(value):
    if not re.fullmatch(r'[0-9a-fA-F]{6}', value):
        raise argparse.ArgumentTypeError('meter ID must be exactly six hexadecimal digits')
    return value.lower()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=86400, help='Run duration (default: 24 hours)')
    parser.add_argument('--library', help='Windows DLL directory; Linux shared-library file')
    parser.add_argument('--device', type=int, default=0, help='RTL-SDR device index')
    parser.add_argument('--include-frame', action='store_true', help='Include raw frame hex in output')
    parser.add_argument('--discover',action='store_true',help='Show CRC-valid raw Geo frames without decoding measurements')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--header', help='Four header bytes as eight hex digits, including length')
    selection.add_argument('--meter-id', type=parse_meter_id,
                           help='Three-byte Solo III radio ID in hex (default: 1D4086)')
    parser.add_argument('--assume-solo-layout',action='store_true',help='Explicitly apply experimental Solo III mapping to a custom header')
    parser.add_argument('--format',choices=['json','pretty'],default='json')
    parser.add_argument('--color',choices=['auto','always','never'],default='auto')
    args = parser.parse_args()
    if args.meter_id is not None and args.discover:
        parser.error('--meter-id selects measurement frames; --discover scans all headers')
    header_hex = args.meter_id + '1d' if args.meter_id is not None else args.header
    try: header=bytes.fromhex('1d40861d' if header_hex is None else header_hex)
    except ValueError: parser.error('Header must contain eight hexadecimal digits')
    if len(header)!=4: parser.error('Header must contain four bytes including payload length')
    if args.seconds<=0 or args.device<0: parser.error('Seconds must be positive and device nonnegative')
    if not args.discover and (header[3]!=29): parser.error('Solo III measurement payload must be 0x1d bytes')
    if not args.discover and args.meter_id is None and header!=bytes.fromhex('1d40861d') and not args.assume_solo_layout:
        parser.error('Custom decoding requires --assume-solo-layout; inspect with --discover first')
    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    counts=Counter()
    color=args.color=='always' or (args.color=='auto' and sys.stdout.isatty() and 'NO_COLOR' not in os.environ)
    if args.assume_solo_layout or args.meter_id is not None:
        logging.warning('Experimental layout assumption: verify values against your meter/IHD')
    def emit(row):
        counts[row['header']]+=1
        if args.format=='pretty':
            output=pretty(row,args.include_frame)
            print(('\033[96m'+output+'\033[0m') if color else output,flush=True)
            return
        if not args.include_frame and not args.discover:
            row.pop('frame_hex', None)
        print(json.dumps(row), flush=True)
    try:
        live(args.seconds, emit, stop, args.library, args.device, header, args.discover)
    except Exception as exc:
        parser.exit(1, f'Receiver error: {exc}\n')
    finally:
        if args.discover: print('Discovery counts (fresh, deduplicated frames): '+json.dumps(dict(counts)),file=sys.stderr)

def pretty(row, include_frame=False):
    if row['type']=='discovery':
        return f"{row['time_utc']}  HEADER {row['header']}  PAYLOAD {row['payload_bytes']} B  FRAME {row['frame_bytes']} B  CRC OK\n  Raw: {row['frame_hex']}"
    output=(f"{row['time_utc']}  HEADER {row['header']}  CRC OK\n"
            f"  GEN {row['gen_W']:>7,d} W | USE {row['use_W']:>7,d} W | IMP {row['import_W']:>7,d} W | EXP {row['export_W']:>7,d} W\n"
            f"  Generation meter: {row['generation_kWh']:,.3f} kWh | Counter: {row['counter']}\n"
            f"  Inferred totals (kWh): USE {row['inferred_usage_kWh']:,.3f} | IMP {row['inferred_import_kWh']:,.3f} | EXP {row['inferred_export_kWh']:,.3f}")
    if include_frame: output+=f"\n  Raw: {row['frame_hex']}"
    return output

if __name__ == '__main__':
    main()


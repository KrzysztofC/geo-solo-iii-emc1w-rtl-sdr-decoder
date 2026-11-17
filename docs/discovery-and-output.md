# Discovery, meter selection and console output

Close other SDR applications first. On the dashboard machine stop its collector
before using this reader, and restart it afterwards. One application owns the SDR.

## Read the original supported measurement family

```sh
python cli.py --seconds 60 --format pretty
python cli.py --seconds 60 --format json --include-frame
```

JSON remains the default for existing integrations. Pretty output prints UTC
time, header, GEN/USE/IMP/EXP in watts, generation meter kWh and inferred totals.
For example, GEN 650 W and USE 700 W gives IMP 50 W and EXP 0 W.
Import/export power is calculated. Cumulative usage/import/export labels remain
inferred. CRC OK verifies integrity, not physical meter identity or field meaning.
Colour is automatic on terminals; use `--color never` or `--color always`.
Diagnostics go to stderr; JSON records go to stdout.

## Discover other headers

```sh
python cli.py --discover --seconds 180 --format pretty
python cli.py --discover --seconds 180 --format json > discovery.jsonl
```

Windows: optionally add `--library "C:\path\to\DLL-directory"`.
Linux: optionally add `--library /usr/lib/aarch64-linux-gnu/librtlsdr.so`.
Use your virtual environment's Python executable or activate it first.

Discovery reports all CRC-valid packets found by our current Geo demodulator,
including header, payload length, frame length and raw bytes. It does not decode
unknown packets into power or totals. At exit, stderr lists counts per header;
these count fresh, deduplicated callbacks, not guaranteed on-air packet counts.
The original measurement header is `1d40861d`; the last byte is the payload
length (0x1d = 29), rather than an independently established device identifier.
The `ffc0ff12` family has an 18-byte payload and remains unexplained.

This is not a full-band RF scanner: centre frequency, FSK passband, sample rate
and symbol timing remain those observed on the tested installation. Missing
output can reflect RF differences or reception issues, not only header filtering.

## Select a different measurement candidate

Only try this after identifying a 29-byte payload candidate and comparing its
structure with the documented Solo III layout:

```sh
python cli.py --header 1234561d --assume-solo-layout --seconds 60 --format pretty
```

`1234561d` is a fictitious example; replace it with the actual observed header.
The explicit assumption flag is required because a matching length does not
validate our field mapping. Compare readings against the physical meter/IHD,
including controlled load changes. Do not use unverified values for automation.
Exact header selection helps separate families but is not proven to uniquely
identify a meter. Never merge different headers automatically.

If discovery finds only unrelated packets, share the SDR model, meter/radio
module model, command, diagnostic messages and a few redacted raw frames.
R828D alone does not identify the SDR model. RTL-SDR Blog V4 requires a compatible
librtlsdr driver. A startup PLL warning alone is not proof of reception failure.
Do not change pairing merely because no packets were decoded.

Output is not saved unless redirected. Keep recordings bounded and review raw
frames for potentially identifying information before publishing them.

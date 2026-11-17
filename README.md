# Geo Solo III / emlite EMC1.w RTL-SDR decoder

An experimental, receive-only Python decoder for measurements transmitted by a Geo/ASL radio module attached to an emlite EMC1.w meter used with a Solo III system.

It receives locally at 868 MHz without the Geo cloud, hub, or IHD being powered on. No pairing code is required for the observed measurement broadcasts.

## Status and compatibility

Tested on one installation using Windows and a Nooelec NESDR Mini 2 (RTL2832U/R820T2). Instantaneous values matched the Solo III IHD during load tests, and the generation counter matched the physical meter register. Transmission continued with both hub and IHD off.

A Raspberry Pi 4B with an R828D-based RTL-SDR also recorded valid measurement frames from a second installation. Other firmware versions may use different frame formats. If several compatible transmitters are in range, verify your meter ID against the meter or the Solo III IHD.

## Find your meter ID

1. With the decoder and other SDR applications stopped, place the antenna near the meter's radio module and listen at 868 MHz.

   ```sh
   rtl_433 -f 868M -T 120
   ```

2. Look for a repeated `GEO-minimCT` result with `Integrity: CRC` and copy its six-digit hexadecimal `id`, such as `B3C0EB`. On the Raspberry Pi capture, this ID also appeared in the first three bytes of the 35-byte Solo III measurement frames.
3. Pass that ID to the decoder and compare the generation counter with the physical meter, or compare the instantaneous readings with the Solo III IHD. If you see multiple IDs, verify which one matches your meter.

   ```sh
   python cli.py --meter-id B3C0EB --seconds 60
   ```

If `rtl_433` prints no `GEO-minimCT` results, the ID can also be recovered from the first three bytes after sync word `7b b9` in a CRC-valid Solo III measurement frame. The following byte is the payload length `1d`. See the [protocol notes](docs/protocol.md).

`--meter-id` accepts uppercase or lowercase hex. It defaults to `1D4086` from the original installation.

## Requirements

- Python 3.10 or newer.
- RTL-SDR receiver covering 868 MHz and a suitable antenna.
- NumPy and a compatible librtlsdr installation.
- Exclusive access to the receiver: close SDR Console and other SDR applications.

## Windows quick start

Install WinUSB for the receiver's **Interface 0** using Zadig. Check the selected device carefully. Install SDR Console V3, whose installation includes the RTL-SDR DLL and dependencies used by the tested setup.

In PowerShell, from this project directory:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe cli.py --meter-id B3C0EB --seconds 60
```

The default library directory is `C:\Program Files\SDR-Radio.com (V3)`. For a different installation:

```powershell
.\.venv\Scripts\python.exe cli.py --library "C:\path\to\dll-directory" --meter-id B3C0EB --seconds 86400
```

Python and the native DLL must use matching architectures (normally 64-bit). A DLL-loading error can also mean a dependency is missing.

## Linux

Install your distribution's librtlsdr package and Python virtual environment support, then:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python cli.py --meter-id B3C0EB --seconds 60
```

Replace `B3C0EB` in the examples with your meter ID. If the shared library is outside the default library search path, pass its full path with `--library`. USB permissions and the DVB kernel driver may require distribution-specific configuration. Follow your RTL-SDR supplier's instructions.

## Output and operation

Standard output contains one JSON object per fresh decoded measurement; diagnostics go to standard error. Fields include `gen_W`, `use_W`, `import_W`, `export_W`, generation kWh, inferred cumulative counters, UTC timestamps and frame counter.

Import/export power is calculated from USE minus GEN. Cumulative usage/import/export labels are inferred; generation is independently checked against the physical meter. See [protocol notes](docs/protocol.md).

Use `--device 1` to select another receiver index. Press Ctrl+C to stop. The default duration is 24 hours; use an appropriate larger `--seconds` value or a service manager for longer operation. Automatic restart is the responsibility of that service manager.

No files or raw I/Q recordings are saved automatically. Redirecting output to a file creates an ever-growing log; configure rotation if you do so. `--include-frame` adds frame hex for investigation.

Reception is fixed at 868 MHz, 2.4 MS/s and 28 dB gain. Poor antenna placement, interference or different radio variants may prevent decoding. A quiet console means no fresh matching CRC-valid packets were found; it does not prove a hardware fault.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests cover a known CRC vector and synthetic field mapping. They do not substitute for live RF tests.

## Scope

This project does not implement cloud emulation, RF transmission, pairing, Home Assistant discovery or dashboard integration. It requires no account credentials. Never open a mains meter or disturb its seals to use this software.

## Contributing

Report OS, Python version, receiver model, library version and receiver errors. Redact device identifiers and household information before sharing captures. Protocol variants and independent hardware confirmations are particularly useful.

This is an independent reverse-engineering project, unaffiliated with Geo, ASL, emlite or Nooelec.

## License

No license has been selected yet. The repository owner should add their chosen license before publication; downloading source alone does not grant redistribution rights.


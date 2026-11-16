# Geo Solo III / emlite EMC1.w RTL-SDR decoder

An experimental, receive-only Python decoder for measurements transmitted by a Geo/ASL radio module attached to an emlite EMC1.w meter used with a Solo III system.

It receives locally at 868 MHz without the Geo cloud, hub, or IHD being powered on. No pairing code is required for the observed measurement broadcasts.

## Status and compatibility

Tested on one installation using Windows and a Nooelec NESDR Mini 2 (RTL2832U/R820T2). Instantaneous values matched the Solo III IHD during load tests, and the generation counter matched the physical meter register. Transmission continued with both hub and IHD off.

Other meters, firmware versions and nearby installations have not been tested. The fixed header filter is a message-family filter, **not a unique meter identity filter**. Do not assume this selects your meter if multiple compatible transmitters are in range. Linux library loading is provided but has not been hardware-tested.

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
.\.venv\Scripts\python.exe cli.py --seconds 60
```

The default library directory is `C:\Program Files\SDR-Radio.com (V3)`. For a different installation:

```powershell
.\.venv\Scripts\python.exe cli.py --library "C:\path\to\dll-directory" --seconds 86400
```

Python and the native DLL must use matching architectures (normally 64-bit). A DLL-loading error can also mean a dependency is missing.

## Linux

Install your distribution's librtlsdr package and Python virtual environment support, then:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python cli.py --seconds 60
```

USB permissions and the DVB kernel driver may require distribution-specific configuration. Follow your RTL-SDR supplier's instructions. This path is not yet hardware verified.

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


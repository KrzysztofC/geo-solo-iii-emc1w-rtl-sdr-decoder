# Geo Solo III / emlite EMC1.w RTL-SDR decoder

An experimental, receive-only Python decoder for measurements transmitted by a Geo/ASL radio module attached to an emlite EMC1.w meter used with a Solo III system.

It receives locally at 868 MHz without the Geo cloud, hub, or IHD being powered on. No pairing code is required for the observed measurement broadcasts.

## Status and compatibility

Tested on one installation using Windows and a Nooelec NESDR Mini 2 (RTL2832U/R820T2). Instantaneous values matched the Solo III IHD during load tests, and the generation counter matched the physical meter register. Transmission continued with both hub and IHD off.

A Raspberry Pi 4B with an R828D-based RTL-SDR also recorded valid measurement frames. Firmware versions may differ. Verify the selected radio ID against the physical meter or Solo III IHD.

## Find your meter ID

1. Close other SDR applications, place the antenna near the meter's radio module, and run:

   ```sh
   rtl_433 -f 868M -T 120
   ```

2. Copy the six-digit hexadecimal `id` from a repeated `GEO-minimCT` result with `Integrity: CRC`. For example, `B3C0EB` appeared both in the `rtl_433` output and at the start of the 35-byte Solo III frames in the Raspberry Pi capture.
3. Stop `rtl_433`, then pass the ID to the decoder. Compare the generation counter with the physical meter or compare instantaneous readings with the Solo III IHD.

   ```sh
   python cli.py --meter-id B3C0EB --seconds 60
   ```

If `rtl_433` shows no `GEO-minimCT` result, run `python cli.py --discover --format pretty --seconds 120`. Look for a repeated CRC-valid 35-byte frame with a header ending in `1d`. The first six hex digits are the candidate ID. Verify readings against the meter, especially if multiple candidates appear.

`--meter-id` accepts uppercase and lowercase hex and selects the 29-byte Solo III payload. Running without a selection uses the original ID `1D4086`.

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

USB permissions and the DVB kernel driver may require distribution-specific configuration. Follow your RTL-SDR supplier's instructions. If automatic library discovery fails, pass the full path to the shared library with `--library`.

## Output and operation

Standard output contains one JSON object per fresh decoded measurement; diagnostics go to standard error. Fields include `gen_W`, `use_W`, `import_W`, `export_W`, generation kWh, inferred cumulative counters, UTC timestamps and frame counter.

Import/export power is calculated from USE minus GEN. Cumulative usage/import/export labels are inferred; generation is independently checked against the physical meter. See [protocol notes](docs/protocol.md).

Use `--device 1` to select another receiver index. Press Ctrl+C to stop. The default duration is 24 hours; use an appropriate larger `--seconds` value or a service manager for longer operation. Automatic restart is the responsibility of that service manager.

No files or raw I/Q recordings are saved automatically. Redirecting output to a file creates an ever-growing log; configure rotation if you do so. `--include-frame` adds frame hex for investigation.

Reception is fixed at 868 MHz, 2.4 MS/s and 28 dB gain. Poor antenna placement, interference or different radio variants may prevent decoding. A quiet console means no fresh matching CRC-valid packets were found; it does not prove a hardware fault.

## Home Assistant

Publish the decoder's JSON readings from a Raspberry Pi to the MQTT broker used by Home Assistant. The examples use meter ID `B3C0EB`, broker `192.168.50.161:1883`, MQTT username `mqtt`, and Pi user `schriss`. Replace those values for your setup. If you change the MQTT topic, use the same topic in the publisher, MQTT Explorer, and Home Assistant.

### Set up the MQTT broker

Use an existing broker or install and start the Mosquitto broker app on Home Assistant OS. Create MQTT credentials for the Pi using your broker's authentication settings. In Home Assistant, add or configure the MQTT integration to use that broker. The Pi and MQTT Explorer connect to the broker's LAN address. [Home Assistant MQTT setup](https://www.home-assistant.io/integrations/mqtt/#setting-up-a-broker) · [Mosquitto broker app configuration](https://github.com/home-assistant/apps/blob/master/mosquitto/DOCS.md)

### Install the Raspberry Pi tools and test publishing

Clone this repository to `~/geo-solo-iii-emc1w-rtl-sdr-decoder`, plug in the RTL-SDR, and install the dependencies on Raspberry Pi OS. Use the [meter ID steps](#find-your-meter-id) if you need to find your ID. Stop `rtl_433` or any other SDR application before starting the decoder.

```sh
sudo apt update
sudo apt install python3-venv rtl-sdr rtl-433 mosquitto-clients
cd ~/geo-solo-iii-emc1w-rtl-sdr-decoder
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Create a private Mosquitto client config on the Pi. This keeps the password out of the repository and command line. [Mosquitto publisher configuration](https://mosquitto.org/man/mosquitto_pub-1.html)

```sh
install -d -m 700 ~/.config/geo-solo3
touch ~/.config/geo-solo3/mosquitto_pub
chmod 600 ~/.config/geo-solo3/mosquitto_pub
nano ~/.config/geo-solo3/mosquitto_pub
```

Save these lines in the file and replace `YOUR_MQTT_PASSWORD` with the broker password:

```text
-u mqtt
-P YOUR_MQTT_PASSWORD
```

Run a 60-second test from the repository directory:

```sh
.venv/bin/python cli.py --meter-id B3C0EB --format json --seconds 60 \
  | XDG_CONFIG_HOME="$HOME/.config/geo-solo3" mosquitto_pub \
      -h 192.168.50.161 -p 1883 -t 'geo/solo3/b3c0eb/state' -q 1 -l
```

The publisher sends one JSON message per line. Decoder logs go to stderr. If automatic library discovery fails, add `--library /path/to/librtlsdr.so` to the decoder command here and in the service below.

### Verify messages in MQTT Explorer

Install MQTT Explorer on a computer that can reach the broker. Connect to the same broker address and port with valid MQTT credentials. Expand `geo → solo3 → b3c0eb → state` while the decoder is running. Check that the JSON contains `crc_ok: true` and that `time_utc` and `counter` advance. The screenshot shows a successfully received reading. [MQTT Explorer downloads](https://mqtt-explorer.com/)

![MQTT Explorer showing a Geo Solo III JSON reading on geo/solo3/b3c0eb/state](docs/mqtt-explorer-solo3.png)

### Configure Home Assistant sensors

Add the following to Home Assistant's `configuration.yaml`. If you already have an `mqtt:` section, add the entries to its `sensor:` list. Validate the configuration and restart Home Assistant. With `expire_after: 30`, readings become unavailable after 30 seconds without a message. The publisher leaves MQTT retain off so the broker does not replay a stale reading on restart. [Home Assistant MQTT sensor configuration](https://www.home-assistant.io/integrations/sensor.mqtt/)

```yaml
mqtt:
  sensor:
    - name: "Geo Solar Power"
      unique_id: geo_solo3_b3c0eb_gen_w
      state_topic: "geo/solo3/b3c0eb/state"
      value_template: "{{ value_json.gen_W }}"
      device_class: power
      state_class: measurement
      unit_of_measurement: "W"
      expire_after: 30

    - name: "Geo Household Power"
      unique_id: geo_solo3_b3c0eb_use_w
      state_topic: "geo/solo3/b3c0eb/state"
      value_template: "{{ value_json.use_W }}"
      device_class: power
      state_class: measurement
      unit_of_measurement: "W"
      expire_after: 30

    - name: "Geo Grid Import Power"
      unique_id: geo_solo3_b3c0eb_import_w
      state_topic: "geo/solo3/b3c0eb/state"
      value_template: "{{ value_json.import_W }}"
      device_class: power
      state_class: measurement
      unit_of_measurement: "W"
      expire_after: 30

    - name: "Geo Grid Export Power"
      unique_id: geo_solo3_b3c0eb_export_w
      state_topic: "geo/solo3/b3c0eb/state"
      value_template: "{{ value_json.export_W }}"
      device_class: power
      state_class: measurement
      unit_of_measurement: "W"
      expire_after: 30

    - name: "Geo Solar Energy"
      unique_id: geo_solo3_b3c0eb_generation_kwh
      state_topic: "geo/solo3/b3c0eb/state"
      value_template: "{{ value_json.generation_kWh }}"
      device_class: energy
      state_class: total_increasing
      unit_of_measurement: "kWh"
      expire_after: 30
```

After comparing **Geo Solar Energy** with the physical meter, select it as the cumulative solar production sensor in the Energy dashboard. The `inferred_*_kWh` fields are also published. Verify them against your meter registers before using them as energy totals. [Home Assistant Energy dashboard sensor requirements](https://www.home-assistant.io/docs/energy/faq/#the-sensor-doesnt-appear-in-the-selection-list)

### Run continuously with systemd

Create `/etc/systemd/system/geo-solo3-mqtt.service` with `sudo nano`. Set `User`, `WorkingDirectory`, and `XDG_CONFIG_HOME` to match your Pi setup. The service restarts after the decoder's default 24-hour run or if the publisher exits. [systemd service documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)

```ini
[Unit]
Description=Geo Solo III meter to MQTT
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=schriss
WorkingDirectory=/home/schriss/geo-solo-iii-emc1w-rtl-sdr-decoder
Environment=XDG_CONFIG_HOME=/home/schriss/.config/geo-solo3
ExecStart=/bin/bash -c 'exec /usr/bin/mosquitto_pub -h 192.168.50.161 -p 1883 -t geo/solo3/b3c0eb/state -q 1 -l < <(exec .venv/bin/python cli.py --meter-id B3C0EB --format json)'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Stop the test pipeline and any other program using the SDR. Enable the service at boot and follow its logs:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now geo-solo3-mqtt.service
sudo journalctl -u geo-solo3-mqtt.service -f
```

Example journal output from a Raspberry Pi 4B:

```text
Nov 17 12:03:48 raspberrypi4b systemd[1]: Started geo-solo3-mqtt.service - Geo Solo III meter to MQTT.
Nov 17 12:03:49 raspberrypi4b bash[2460]: WARNING:root:Experimental layout assumption: verify values against your meter/IHD
Nov 17 12:03:49 raspberrypi4b bash[2460]: Detached kernel driver
Nov 17 12:03:49 raspberrypi4b bash[2460]: Found Rafael Micro R828D tuner
Nov 17 12:03:49 raspberrypi4b bash[2460]: Disabled direct sampling mode
Nov 17 12:03:49 raspberrypi4b bash[2460]: [R82XX] PLL not locked!
Nov 17 12:03:49 raspberrypi4b bash[2460]: [R82XX] PLL not locked!
Nov 17 12:03:50 raspberrypi4b bash[2460]: INFO:geo_decoder:Geo radio receiver started at 2026-11-17T12:03:50.081067+00:00
```

The journal shows the receiver starting. Use MQTT Explorer or Home Assistant's MQTT topic listener to confirm delivery. The startup PLL messages appeared on this working setup. Press **Ctrl+C** to leave the log view while the service keeps running.


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

## Discovery and readable output

Use `python cli.py --format pretty --seconds 60` for readable terminal output.
Use `python cli.py --discover --format pretty --seconds 180` to inspect other
CRC-valid Geo headers without interpreting them as measurements.
JSON remains the default. With `--header`, custom measurement headers require `--assume-solo-layout`. The `--meter-id` option selects that layout directly.
See [Discovery, selection and output](docs/discovery-and-output.md) for Windows
and Linux commands, field meanings, custom header examples and troubleshooting.


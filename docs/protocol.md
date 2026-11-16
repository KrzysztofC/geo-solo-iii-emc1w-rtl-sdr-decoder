# Observed protocol

All offsets below start immediately after the two-byte sync word and include the four-byte header. Findings are experimental and apply to the tested message family.

| Property | Observed value |
|---|---|
| Receiver centre | 868.000 MHz |
| Sample rate | 2.4 MS/s, unsigned 8-bit interleaved I/Q |
| FSK tones | Approximately 868.237 and 868.399 MHz |
| Bit rate | Approximately 38,400 bit/s |
| Sync | 7B B9 |
| Header | 1D 40 86 1D |
| Frame length | 35 bytes after sync |
| CRC | CRC-16, polynomial 0x8005, initial 0, no reflection, no final XOR |
| CRC encoding | Final two bytes, big endian, covers preceding 33 bytes |

| Offset | Length | Interpretation |
|---|---|---|
| 7 | 2 | Household USE, watts |
| 9 | 2 | Generation, watts |
| 11 | 4 | Inferred cumulative usage, Wh |
| 15 | 4 | Generation meter counter, Wh |
| 19 | 4 | Inferred cumulative import, Wh |
| 23 | 4 | Inferred cumulative export, Wh |
| 29 | 2 | Frame counter |

Numeric fields are unsigned big endian. Other bytes remain unexplained. Import W = max(USE - GEN, 0); export W = max(GEN - USE, 0).

The generation counter was checked against the physical meter LCD. Instantaneous readings were compared with the IHD, including household load changes. Meter identity was supported by continued transmissions with hub and IHD both powered off and by the physical register comparison. Cumulative usage/import/export labels remain inferred rather than independently verified register labels.

The six-character pairing code is not required by this decoder. Its exact role is unconfirmed. Receiving these frames does not establish what encryption or authentication other pairing/control message types use.

The demodulator locates bursts, filters the observed FSK band, tries sampling phases, and accepts only the expected header and valid CRC. It retains 25 ms overlap between blocks and briefly deduplicates identical frames. USB reads run on a separate thread with a bounded memory queue. Freshness timestamps are estimates anchored to USB arrival.

No claim is made that this header uniquely identifies a physical meter. Multi-meter selection requires additional investigation.


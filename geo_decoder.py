"""Local Solo III radio receiver and packet decoder.

Uses the installed SDR Console RTL-SDR library and NumPy. Only CRC-valid
frames matching the experimentally identified header are emitted.
"""
import ctypes as c
import datetime as dt
import os
import threading
import queue
import time
import logging
import numpy as np

logger = logging.getLogger(__name__)

FS = 2400000
SYNC = '0111101110111001'

def crc16(data):
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x8005 if crc & 0x8000 else 0)) & 0xffff
    return crc

def decode_block(z):
    """Return validated frames and offsets, preserving caller overlap."""
    nfft = 4096
    n = len(z) // nfft
    if not n:
        return []
    freq = np.fft.fftfreq(nfft, 1 / FS)
    spectrum = abs(np.fft.fft(z[:n*nfft].reshape(n, nfft) * np.hanning(nfft), axis=1)) ** 2
    energy = spectrum[:, (freq > 180000) & (freq < 290000)].mean(axis=1)
    mask = energy > max(np.median(energy) * 5, 1e-9)
    starts = np.where(np.diff(mask.astype(int), prepend=0) == 1)[0]
    ends = np.where(np.diff(mask.astype(int), append=0) == -1)[0]
    found = []
    for begin, end in zip(starts, ends):
        first = max(0, begin*nfft - 12000)
        last = min(len(z), (end+1)*nfft + 12000)
        burst = z[first:last]
        f = np.fft.fftfreq(len(burst), 1 / FS)
        spec = np.fft.fft(burst)
        spec[(f < 140000) | (f > 500000)] = 0
        filtered = np.fft.ifft(spec)
        amp = np.convolve(abs(filtered)**2, np.ones(24)/24, 'same')
        active = np.where(amp > max(np.percentile(amp,10)*5, amp.max()*.04))[0]
        if len(active) < 100:
            continue
        lo, hi = active[0]+20, active[-1]-20
        if hi-lo < 100:
            continue
        hz = np.angle(filtered[1:]*filtered[:-1].conj()) * FS / (2*np.pi)
        hz = np.convolve(hz, np.ones(9)/9, 'same')
        low, high = np.percentile(hz[lo:hi], [20,80])
        mid = (low+high)/2
        # Try best eye-opening phases first; CRC chooses the valid result.
        phases = []
        for phase in range(63):
            idx = lo + np.arange(phase, hi-lo, FS/38400).astype(int)
            phases.append((float(np.mean(abs(hz[idx]-mid))), idx))
        for _, idx in sorted(phases, key=lambda p:p[0], reverse=True):
            bits = ''.join((hz[idx] > mid).astype(int).astype(str))
            pos = bits.find(SYNC)
            if pos < 0:
                continue
            payload = bits[pos+16:]
            data = bytes(int(payload[j:j+8],2) for j in range(0,len(payload)-7,8))
            if len(data) < 4 or data[:4] != bytes.fromhex('1d40861d'):
                continue
            length = 4 + data[3] + 2
            if len(data) < length:
                continue
            data = data[:length]
            if crc16(data[:-2]) != int.from_bytes(data[-2:], 'big'):
                continue
            found.append(((first+lo)/FS, data))
            break
    return found

def reading(data):
    use = int.from_bytes(data[7:9], 'big')
    gen = int.from_bytes(data[9:11], 'big')
    return dict(gen_W=gen, use_W=use, import_W=max(use-gen,0),
                export_W=max(gen-use,0), counter=int.from_bytes(data[29:31],'big'),
                generation_kWh=int.from_bytes(data[15:19],'big')/1000,
                inferred_usage_kWh=int.from_bytes(data[11:15],'big')/1000,
                inferred_import_kWh=int.from_bytes(data[19:23],'big')/1000,
                inferred_export_kWh=int.from_bytes(data[23:27],'big')/1000,
                frame_hex=data.hex(), crc_ok=True)

def live(seconds, on_reading=None, external_stop=None, dll_path=None, device_index=0):
    base = dll_path or r'C:\Program Files\SDR-Radio.com (V3)'
    dll_dir = os.add_dll_directory(base)
    lib = c.CDLL(base+r'\rtlsdr.dll')
    dev = c.c_void_p()
    lib.rtlsdr_open.argtypes = [c.POINTER(c.c_void_p), c.c_uint32]
    lib.rtlsdr_close.argtypes = [c.c_void_p]
    for name in ['set_sample_rate','set_center_freq','set_tuner_gain_mode','set_tuner_gain','set_agc_mode','set_direct_sampling']:
        getattr(lib,'rtlsdr_'+name).argtypes = [c.c_void_p,c.c_int]
    lib.rtlsdr_reset_buffer.argtypes = [c.c_void_p]
    lib.rtlsdr_read_sync.argtypes = [c.c_void_p,c.c_void_p,c.c_int,c.POINTER(c.c_int)]
    def check(rc):
        if rc < 0:
            raise RuntimeError('RTL-SDR error '+str(rc))
    check(lib.rtlsdr_open(c.byref(dev),device_index))
    try:
        for name,val in [('set_direct_sampling',0),('set_sample_rate',FS),('set_center_freq',868000000),('set_tuner_gain_mode',1),('set_tuner_gain',280),('set_agc_mode',0)]:
            check(getattr(lib,'rtlsdr_'+name)(dev,val))
        check(lib.rtlsdr_reset_buffer(dev))
        began = time.monotonic()
        start_utc = dt.datetime.now(dt.timezone.utc)
        last_good = began
        last_notice = began
        seen = {}
        carry = np.empty(0,dtype=np.complex64)
        blocks = queue.Queue(maxsize=16)
        stop = threading.Event()
        def acquire():
            buf = (c.c_ubyte * 1048576)()
            count = c.c_int()
            try:
                while not stop.is_set():
                    check(lib.rtlsdr_read_sync(dev,buf,len(buf),c.byref(count)))
                    if count.value <= 0 or count.value % 2:
                        raise RuntimeError('Invalid USB read length')
                    blocks.put((c.string_at(buf,count.value), dt.datetime.now(dt.timezone.utc)),timeout=2)
            except Exception as exc:
                if not stop.is_set():
                    try:
                        blocks.put(exc,timeout=2)
                    except queue.Full:
                        pass
                    stop.set()
        worker = threading.Thread(target=acquire,daemon=True)
        worker.start()
        total = 0
        logger.info('Geo radio receiver started at %s', start_utc.isoformat())
        while time.monotonic()-began < seconds and not (external_stop and external_stop.is_set()):
            chunk = blocks.get(timeout=5)
            if isinstance(chunk,Exception):
                raise chunk
            chunk,chunk_end=chunk
            raw = np.frombuffer(chunk,dtype=np.uint8).astype(np.float32)-127.5
            z = raw[::2]+1j*raw[1::2]
            block = np.concatenate([carry,z])
            for offset,data in decode_block(block):
                now = time.monotonic()
                if data in seen and now-seen[data] < 3:
                    continue
                seen[data] = now
                seen = {k:v for k,v in seen.items() if now-v < 5}
                # Anchor to USB arrival rather than accumulating sample-clock
                # drift across missed samples or uncertain oscillator accuracy.
                stamp = chunk_end - dt.timedelta(seconds=(len(z)+len(carry))/FS-offset)
                received=dt.datetime.now(dt.timezone.utc)
                delay=(received-stamp).total_seconds()
                row = dict(time_utc=stamp.isoformat(), received_utc=received.isoformat(), estimated_delay_s=delay, fresh=delay<2, **reading(data))
                if on_reading and row['fresh']:
                    on_reading(row)
                last_good=now;total+=1
            carry = block[-int(FS*.025):]
            now=time.monotonic()
            if now-last_good > 5 and now-last_notice > 5:
                logger.warning('Geo radio has no validated packet for %.1f seconds', now-last_good)
                last_notice=now
        logger.info('Geo radio receiver stopped: %s valid packets', total)
    finally:
        if 'stop' in locals():
            stop.set()
            worker.join(timeout=4)
            if worker.is_alive():
                raise RuntimeError('USB worker did not stop; refusing to close its active device')
        lib.rtlsdr_close(dev)


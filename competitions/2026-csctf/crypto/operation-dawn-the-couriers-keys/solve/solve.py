import random
import gmpy2
import time as _time

# --- data pulled from the pcap in step 1 ---
TARGET_SERIAL = 6631
TARGET_N = int(
    "638c4593a4d52f4be3825d8c8193ccd9551aea1e1a047adb0db7907958e127c"
    "6ee53a926e982f602e0407e43eb14cb927f0e541543418256011fa132945f14"
    "e1a70cdf1ef277e9851219c8b93004fb29233e16bf51886108b0ee750151602"
    "cb2a6d56252adfd6c00159cbf4111a1fa4e14c4809008cf455fcccd78c9a247"
    "73af", 16,
)
C = int(
    "42c2b662d2c1e70dd9cccd665edfe9a6069dd031a5b0ddf904a819b90581ffd"
    "61c89eb1b1a1878acf3b6b45c8d5177796a4323f079ddf4e7f668410306c1d0"
    "4a6a995154a03f7257f8f89584ea1a6e3bb291d58893ae140dbf70f111c2f85"
    "5d686aca122996eb4453fa39a701e23471d516b9b42b78c3d73a9ca300beece"
    "078e", 16,
)
REG_ARRIVAL_TIME = 1699994070  # from the [53] REG packet timestamp (int seconds)
e = 65537


def gen_prime(rng, bits=512, max_tries=20000):
    """Exactly replays the device's spec: getrandbits -> force top+bottom bit -> keep first prime."""
    top = 1 << (bits - 1)
    for _ in range(max_tries):
        c = rng.getrandbits(bits)
        c |= top | 1
        if gmpy2.is_prime(c, 25):
            return c
    return None


def keys_for(epoch, serial):
    seed = (epoch << 16) | serial
    rng = random.Random(seed)
    p = gen_prime(rng)
    q = gen_prime(rng)
    return p, q, (p * q if p and q else None)


# --- brute force the epoch ---
t0 = _time.time()
found = None
for delta in range(-600, 60):           # window: 10 min before .. 1 min after arrival
    epoch = REG_ARRIVAL_TIME + delta
    p, q, n = keys_for(epoch, TARGET_SERIAL)
    if n == TARGET_N:
        found = (epoch, p, q)
        break

if not found:
    raise SystemExit("no match in window — widen the search range")

epoch, p, q = found
print(f"[+] epoch found: {epoch}  (offset {epoch - REG_ARRIVAL_TIME:+d}s from packet arrival)")
print(f"[+] took {_time.time() - t0:.2f}s")
print(f"p = {p}")
print(f"q = {q}")

# --- decrypt ---
n = p * q
phi = (p - 1) * (q - 1)
d = gmpy2.invert(e, phi)
m = pow(C, int(d), n)
msg = m.to_bytes((m.bit_length() + 7) // 8, "big")
print()
print("[+] decrypted order:", msg.decode())
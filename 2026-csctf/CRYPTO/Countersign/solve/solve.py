import struct
import requests
import time

# --- Configuration ---
TARGET_URL = "http://w01.ctf.chronos-security.ro:34356/api/command"
ORIG_HEX = "73746174696f6e3d53554253544e2d313926636d643d5354415455532674733d31373632363036303136266e6f6e63653d6633313962346666"
ORIG_MSG = bytes.fromhex(ORIG_HEX)
ORIG_SIG = "45146fd70fbbd1ffacd3140656652bdbcf3dc5dad0c0316e61d1c7d1cf019b0c"
APPEND_DATA = b"&cmd=DISPATCH"

# --- Pure Python SHA-256 Length Extension Implementation ---
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]

def rightrotate(x, n):
    return (x >> n) | (x << (32 - n))

def sha256_compress(state, block):
    w = list(struct.unpack('>16I', block)) + [0] * 48
    for i in range(16, 64):
        s0 = rightrotate(w[i-15], 7) ^ rightrotate(w[i-15], 18) ^ (w[i-15] >> 3)
        s1 = rightrotate(w[i-2], 17) ^ rightrotate(w[i-2], 19) ^ (w[i-2] >> 10)
        w[i] = (w[i-16] + s0 + w[i-7] + s1) & 0xffffffff

    a, b, c, d, e, f, g, h = state

    for i in range(64):
        S1 = rightrotate(e, 6) ^ rightrotate(e, 11) ^ rightrotate(e, 25)
        ch = (e & f) ^ ((~e) & g)
        temp1 = (h + S1 + ch + K[i] + w[i]) & 0xffffffff
        S0 = rightrotate(a, 2) ^ rightrotate(a, 13) ^ rightrotate(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (S0 + maj) & 0xffffffff

        h = g; g = f; f = e
        e = (d + temp1) & 0xffffffff
        d = c; c = b; b = a
        a = (temp1 + temp2) & 0xffffffff

    return [(x + y) & 0xffffffff for x, y in zip(state, [a, b, c, d, e, f, g, h])]

def sha256_padding(msg_len):
    pad = b'\x80'
    pad += b'\x00' * ((56 - (msg_len + 1) % 64) % 64)
    pad += struct.pack('>Q', msg_len * 8)
    return pad

def length_extension(orig_sig, orig_msg, append_data, key_len):
    state = list(struct.unpack('>8I', bytes.fromhex(orig_sig)))
    total_len = key_len + len(orig_msg)
    
    # Padding that the SERVER will insert when verifying the original message
    padding = sha256_padding(total_len)
    forged_msg = orig_msg + padding + append_data
    
    # For the new hash, we start from orig_state (which already covers key||msg||padding)
    # and only process append_data + new_padding
    new_total_len = total_len + len(padding) + len(append_data)
    new_padding = sha256_padding(new_total_len)
    process_data = append_data + new_padding   # <-- KEY FIX
    
    for i in range(0, len(process_data), 64):
        state = sha256_compress(state, process_data[i:i+64])
        
    return struct.pack('>8I', *state).hex(), forged_msg


# --- Main Exploit Loop ---
for key_len in range(8, 33):
    print(f"[*] Trying key length {key_len}...")
    new_sig, new_msg = length_extension(ORIG_SIG, ORIG_MSG, APPEND_DATA, key_len)
    
    payload = {
        "message_hex": new_msg.hex(),
        "sig": new_sig
    }
    
    try:
        r = requests.post(TARGET_URL, json=payload, timeout=10)
        print(f"    {r.status_code}: {r.text[:150]}")
        
        if "CSCTF{" in r.text:
            print("\n[+] FLAG FOUND:")
            print(r.text)
            break
    except Exception as e:
        print(f"    Error: {e}")
        
    time.sleep(0.2) # Respect the rate limit

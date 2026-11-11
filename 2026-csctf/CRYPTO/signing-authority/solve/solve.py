import json
import requests
from hashlib import sha256
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_string, sigdecode_string
from collections import defaultdict

# secp256k1 curve order
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def hash_int(msg: bytes) -> int:
    """Hash message using SHA-256 and return as integer modulo n."""
    return int.from_bytes(sha256(msg).digest(), 'big') % n

def parse_val(v):
    """Helper to parse hex strings or ints."""
    if isinstance(v, str):
        return int(v, 16) if v.startswith('0x') else int(v)
    return v

base_url = "http://w01.ctf.chronos-security.ro:34447"

# 1. Fetch Schema to find the exact target message
print("[*] Fetching schema...")
schema = requests.get(f"{base_url}/schema").json()
print(json.dumps(schema, indent=2))

# Try to find the target message in the schema automatically
target_msg_str = None
for key in ['master_message', 'master_arming_message', 'message', 'target']:
    if key in schema:
        target_msg_str = schema[key]
        break

if not target_msg_str:
    print("[-] Could not automatically find the target message in the schema.")
    print("[-] Please look at the schema output above and hardcode the exact string.")
    exit()

print(f"[*] Target message identified: {target_msg_str}")
target_msg = target_msg_str.encode()

# 2. Fetch Receipts
print("[*] Fetching receipts...")
receipts_resp = requests.get(f"{base_url}/receipts")
receipts = receipts_resp.json()

# Extract list if it's nested inside a dict
if isinstance(receipts, dict):
    for key in receipts:
        if isinstance(receipts[key], list):
            receipts = receipts[key]
            break

# 3. Find nonce reuse (two signatures with the same 'r')
by_r = defaultdict(list)
for rec in receipts:
    # Handle potential variations in receipt structure
    r_val = rec.get('r') or rec.get('signature', {}).get('r')
    s_val = rec.get('s') or rec.get('signature', {}).get('s')
    msg_val = rec.get('message') or rec.get('payload')

    if r_val is not None and s_val is not None and msg_val is not None:
        r_key = str(r_val).lower().replace('0x', '')
        by_r[r_key].append(rec)

reused_pair = None
for r_key, recs in by_r.items():
    if len(recs) >= 2:
        reused_pair = recs[:2]
        break

if not reused_pair:
    print("[-] No nonce reuse found among receipts.")
    exit()

rec1, rec2 = reused_pair

r = parse_val(rec1.get('r') or rec1.get('signature', {}).get('r'))
s1 = parse_val(rec1.get('s') or rec1.get('signature', {}).get('s'))
s2 = parse_val(rec2.get('s') or rec2.get('signature', {}).get('s'))

m1 = (rec1.get('message') or rec1.get('payload')).encode()
m2 = (rec2.get('message') or rec2.get('payload')).encode()

e1 = hash_int(m1)
e2 = hash_int(m2)

print(f"[*] Found reused nonce!")
print(f"    r = {hex(r)}")

# 4. Recover Private Key
k = ((e1 - e2) * pow(s1 - s2, -1, n)) % n
d = ((s1 * k - e1) * pow(r, -1, n)) % n

print(f"[+] Recovered Private Key: {hex(d)}")

# 5. Sign the Target Message
sk = SigningKey.from_secret_exponent(d, curve=SECP256k1)
# Use deterministic signing to avoid random nonce issues
sig_bytes = sk.sign_deterministic(target_msg, hashfunc=sha256, sigencode=sigencode_string)
r_target, s_target = sigdecode_string(sig_bytes, n)

print(f"[+] Forged Signature for target:")
print(f"    r = {hex(r_target)}")
print(f"    s = {hex(s_target)}")

# 6. Submit to /authorize
# The API likely expects JSON based on the schema output
payload = {
    "r": hex(r_target),
    "s": hex(s_target)
    # "message": target_msg_str # Uncomment if the API requires you to send the message back
}

print(f"[*] Submitting to /authorize...")
resp = requests.post(f"{base_url}/authorize", json=payload)
print(f"[*] Response:\n{resp.text}")

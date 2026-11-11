import json
import requests
from hashlib import sha256
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_string, sigdecode_string
from collections import defaultdict

# Group order (n) from schema
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def hash_int(msg: bytes) -> int:
    # Schema rule: sha256-int-be-mod-n
    return int.from_bytes(sha256(msg).digest(), 'big') % n

def parse_val(v):
    if isinstance(v, str):
        return int(v, 16) if v.startswith('0x') else int(v, 16)
    return v

base_url = "http://w01.ctf.chronos-security.ro:34447"

# 1. Fetch Schema
print("[*] Fetching schema...")
schema = requests.get(f"{base_url}/schema").json()
master_msg_hex = schema['master_message_hex']
target_msg = bytes.fromhex(master_msg_hex)
print(f"[*] Target message bytes:\n{target_msg.decode()}")

# 2. Fetch Receipts
print("[*] Fetching receipts...")
receipts_resp = requests.get(f"{base_url}/receipts")
receipts = receipts_resp.json()

# Handle if receipts are nested in a dictionary
if isinstance(receipts, dict):
    for key in receipts:
        if isinstance(receipts[key], list):
            receipts = receipts[key]
            break

print(f"[*] Found {len(receipts)} receipts. First receipt structure:")
print(json.dumps(receipts[0], indent=2))

# 3. Find Nonce Reuse
by_r = defaultdict(list)
for rec in receipts:
    r_val = rec.get('r')
    s_val = rec.get('s')
    # Schema suggests message_hex_encoding
    msg_val = rec.get('message_hex') or rec.get('message')

    if r_val and s_val and msg_val:
        r_key = str(r_val).lower().replace('0x', '')
        by_r[r_key].append(rec)

reused_pair = None
for r_key, recs in by_r.items():
    if len(recs) >= 2:
        reused_pair = recs[:2]
        break

if not reused_pair:
    print("[-] No nonce reuse found.")
    exit()

rec1, rec2 = reused_pair
r = parse_val(rec1['r'])
s1 = parse_val(rec1['s'])
s2 = parse_val(rec2['s'])

msg1_hex = rec1.get('message_hex') or rec1.get('message')
msg2_hex = rec2.get('message_hex') or rec2.get('message')

m1 = bytes.fromhex(msg1_hex.replace('0x', ''))
m2 = bytes.fromhex(msg2_hex.replace('0x', ''))

e1 = hash_int(m1)
e2 = hash_int(m2)

# 4. Recover Private Key
k = ((e1 - e2) * pow(s1 - s2, -1, n)) % n
d = ((s1 * k - e1) * pow(r, -1, n)) % n
print(f"[+] Recovered Private Key: {hex(d)}")

# 5. Sign the Target Message
sk = SigningKey.from_secret_exponent(d, curve=SECP256k1)
sig_bytes = sk.sign_deterministic(target_msg, hashfunc=sha256, sigencode=sigencode_string)
r_target, s_target = sigdecode_string(sig_bytes, n)

# Schema rule: authorize_s_rule is "low-s"
if s_target > n // 2:
    s_target = n - s_target

# 6. Format Payload
# Schema rules: 64-char width, no 0x prefix, lowercase hex
r_str = f"{r_target:064x}"
s_str = f"{s_target:064x}"

payload = {
    "message_hex": master_msg_hex,
    "r": r_str,
    "s": s_str
}

# Schema rule: wire_json_rule is "minified-fixed-order-no-escapes"
json_payload = json.dumps(payload, separators=(',', ':'))

print(f"[*] Submitting payload:\n{json_payload}")

# Send as raw data to prevent requests from modifying the exact bytes
resp = requests.post(
    f"{base_url}/authorize", 
    data=json_payload, 
    headers={"Content-Type": "application/json"}
)
print(f"[*] Response:\n{resp.text}")

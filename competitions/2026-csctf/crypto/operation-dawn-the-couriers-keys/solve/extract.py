import scapy.all as scapy

pkts = scapy.rdpcap("fleet-provisioning.pcap")
print(f"{len(pkts)} packets, span {pkts[-1].time - pkts[0].time:.0f}s")
print()

for i, p in enumerate(pkts):
    if p.haslayer(scapy.Raw):
        load = bytes(p[scapy.Raw].load)
        try:
            s = load.decode('utf-8', errors='replace')
        except Exception:
            s = repr(load)
        if any(k in s for k in ('REG', 'ACK', 'ORDER', 'provisioning')):
            print(f"[{i}] t={p.time:.3f}")
            print(s[:400])
            print('-' * 60)
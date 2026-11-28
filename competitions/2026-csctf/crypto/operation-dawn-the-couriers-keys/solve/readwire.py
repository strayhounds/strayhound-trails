import scapy.all as scapy
pkts = scapy.rdpcap("fleet-provisioning.pcap")
for p in pkts:
    if p.haslayer(scapy.Raw):
        print(bytes(p[scapy.Raw].load))
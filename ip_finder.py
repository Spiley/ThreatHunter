import psutil
import ipaddress
import socket

# Virtuele MAC prefixes (wereldwijd gebruikt)
VIRTUAL_MAC_PREFIXES = [
    # Hyper-V / WSL
    "00:15:5d",

    # VMware
    "00:05:69",
    "00:0c:29",
    "00:50:56",

    # VirtualBox
    "08:00:27",
    "0a:00:27",

    # Docker / container runtimes
    "02:42",
    "02:16:3e",   # LXC
    "00:16:3e",   # Xen, QEMU

    # Parallels
    "00:1c:42",

    # Microsoft Teredo / VPN adapters
    "00:ff",

    # Misc virtual / cloud hypervisors
    "52:54:00",  # QEMU/KVM
    "06:00:00",  # Virtual vendors
]

def normalize_mac(mac):
    """Converts 00-11-22-33-44-55 → 00:11:22:33:44:55"""
    if not mac:
        return ""
    mac = mac.replace("-", ":").lower()
    return mac

def is_virtual_mac(mac):
    mac = normalize_mac(mac)
    return any(mac.startswith(prefix) for prefix in VIRTUAL_MAC_PREFIXES)

local_ip = None
netmask = None
iface_name = None

for iface, addrs in psutil.net_if_addrs().items():
    mac = None

    # Vind het MAC-adres
    for addr in addrs:
        if addr.family == psutil.AF_LINK:
            mac = addr.address

    # Sla virtuele interfaces over
    if is_virtual_mac(mac):
        continue

    # Kies de eerste fysieke IPv4 interface
    for addr in addrs:
        if addr.family == socket.AF_INET:
            local_ip = addr.address
            netmask = addr.netmask
            iface_name = iface
            break

    if local_ip:
        break

if not local_ip:
    raise RuntimeError("Geen fysieke netwerkadapter gevonden.")

network = ipaddress.IPv4Network(f"{local_ip}/{netmask}", strict=False)

print("Interface:", iface_name)
print("IP-adres:", local_ip)
print("Subnetmask:", netmask)
print("Subnet:", network)
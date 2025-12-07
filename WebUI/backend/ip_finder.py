import psutil
import subprocess
import ipaddress
import socket
import platform

def run_scan():
    def get_default_route_windows():
        output = subprocess.check_output("route print 0.0.0.0", shell=True).decode()
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("0.0.0.0"):
                parts = line.split()
                gateway = parts[2]
                local_ip = parts[3]
                return gateway, local_ip
        raise RuntimeError("Kon default route niet vinden op Windows.")

    def get_default_route_linux():
        output = subprocess.check_output("ip route show default", shell=True).decode()
        parts = output.split()
        gateway = parts[2]
        iface = parts[4]
        addrs = psutil.net_if_addrs()[iface]
        for addr in addrs:
            if addr.family == socket.AF_INET:
                return gateway, addr.address
        raise RuntimeError("Geen IPv4 adres gevonden op Linux interface.")

    def find_interface_by_ip(ip):
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == ip:
                    return iface
        raise RuntimeError(f"Geen interface gevonden met IP {ip}")

    os_name = platform.system().lower()
    if os_name == "windows":
        gateway, local_ip = get_default_route_windows()
    else:
        gateway, local_ip = get_default_route_linux()

    iface = find_interface_by_ip(local_ip)

    addrs = psutil.net_if_addrs()[iface]
    for addr in addrs:
        if addr.family == socket.AF_INET:
            netmask = addr.netmask
            subnet = ipaddress.IPv4Network(f"{local_ip}/{netmask}", strict=False)

    return {
        "os": os_name,
        "interface": iface,
        "gateway": gateway,
        "local_ip": local_ip,
        "netmask": netmask,
        "subnet": str(subnet)
    }

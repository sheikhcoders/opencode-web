"""mDNS discovery module for OpenCode Web."""
import socket
import click
from zeroconf import IPVersion, ServiceInfo, Zeroconf

def advertise_service(port, domain):
    """Advertise the web server over mDNS."""
    desc = {'version': '0.1.0'}

    if domain.endswith(".local"):
        name = domain.replace(".local", "")
    else:
        name = domain

    # Zeroconf expects the service name to end with ._http._tcp.local.
    service_name = f"{name}._http._tcp.local."

    # We need an IP address to advertise
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
    except Exception: # pylint: disable=broad-exception-caught
        ip_address = "127.0.0.1"

    info = ServiceInfo(
        "_http._tcp.local.",
        service_name,
        addresses=[socket.inet_aton(ip_address)],
        port=port,
        properties=desc,
        server=f"{name}.local.",
    )

    zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
    click.echo(f"Advertising mDNS service: {service_name} at {ip_address}:{port}")
    zeroconf.register_service(info)
    return zeroconf, info

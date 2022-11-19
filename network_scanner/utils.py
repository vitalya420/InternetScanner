import socket
import struct
import typing

from network_scanner.ip_addr import IPAddr


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def total_ip_addr(ips):
    return sum([len(ip[0]) for ip in ips])


def ip2str(ip_addr: typing.Union[str, int, IPAddr]):
    if isinstance(ip_addr, IPAddr):
        return str(ip_addr)
    if isinstance(ip_addr, str):
        return ip_addr
    if isinstance(ip_addr, int):
        return socket.inet_ntoa(struct.pack('!L', ip_addr))

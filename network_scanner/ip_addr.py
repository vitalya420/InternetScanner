import socket
import struct
import typing

from .ip_range import IPRange


class IPAddr:
    def __init__(self, ip: typing.Union[int, str], ip_range: IPRange = None):
        super().__init__()
        self.ip = socket.inet_ntoa(struct.pack('!L', ip)) if isinstance(ip, int) else ip

        self.__ip_range = ip_range

    def _get_ip_range(self, refresh=False):
        if self.__ip_range and not refresh:
            return self.__ip_range
        self.__ip_range = IPRange.lookup_ip_addr(self.ip)
        return self.__ip_range

    @classmethod
    def lookup(cls, ip):
        res = IPRange.lookup_ip_addr(ip)
        return cls(ip, res)

    def serialize(self):
        return {
            'ip': self.ip,
            'ip_dec': self.dec,
            'country_code': self.country_code,
            'country': self.country,
            'region': self.region,
            'city': self.city,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'zipcode': self.zipcode,
            'timezone': self.timezone
        }

    @property
    def dec(self):
        return struct.unpack("!L", socket.inet_aton(self.ip))[0]

    def __getattribute__(self, item):
        if item in ('country_code', 'country', 'region', 'city',
                    'latitude', 'longitude', 'zipcode', 'timezone'):
            return getattr(self._get_ip_range(), item)
        return super().__getattribute__(item)

    def __str__(self):
        return str(self.ip)

    def __repr__(self):
        return f"<IPAddr(ip={self.ip})>"

import asyncio
import socket
import struct
import typing

from network_scanner import utils
from network_scanner.ip_range import IPRange
from network_scanner.port_checker import PortCheckerAsync


class AsyncRangeScanner(PortCheckerAsync):
    def __init__(self, ip_range: typing.Union[IPRange, None], ports: typing.Iterable,
                 timeout: int = 3, ip_chunk_size: int = 100,
                 port_chunk_size: int = 5, *args, **kwargs):
        super().__init__(ip=None, ports=ports, *args, **kwargs)
        self.ip_range = ip_range
        self.timeout = timeout
        self.ip_chunk_size = ip_chunk_size
        self.port_chunk_size = port_chunk_size

    async def check_ports(self, timeout=None, port_chunk_size=5, ip=None):
        ret = []
        for ip_chunk in utils.chunks(list(range(self.ip_range.start, self.ip_range.end)), self.ip_chunk_size):
            tasks = []
            for ip in ip_chunk:
                task = self.event_loop.create_task(super().check_ports(
                    ip=socket.inet_ntoa(struct.pack('!L', ip)),
                    timeout=timeout or self.timeout, port_chunk_size=self.port_chunk_size or port_chunk_size
                ))
                tasks.append(task)
            res = await asyncio.gather(*tasks)
            ret.extend(res)
        return ret


class AsyncToSyncRangeScanner(AsyncRangeScanner):
    def check_ports(self, timeout=3, port_chunk_size=5, ip=None):
        task = self.event_loop.create_task(super().check_ports(timeout=timeout,
                                                               port_chunk_size=port_chunk_size,
                                                               ip=ip))
        res = self.event_loop.run_until_complete(asyncio.gather(task))
        return res[0]

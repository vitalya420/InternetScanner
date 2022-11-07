import asyncio
import socket
import struct
import typing
from typing import Union, Any

from . import utils


class PortChecker:
    def __init__(self, event_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()):
        self.event_loop = event_loop

    @staticmethod
    def check_port_sync(ip: str, port: int, timeout: int = 3) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            s.close()
            return result == 0
        except socket.error:
            return False

    async def check_port_async(self, ip: str, port: int, timeout: int = 3,
                               event_loop: asyncio.AbstractEventLoop = None) -> tuple[str, int, bool]:
        using_loop = event_loop or self.event_loop or asyncio.get_event_loop()
        _future = using_loop.create_connection(asyncio.Protocol, ip, port)
        try:
            await asyncio.wait_for(_future, timeout=timeout)
            return ip, port, True
        except OSError:
            return ip, port, False
        except asyncio.exceptions.TimeoutError:
            return ip, port, False

    def check_ports_sync(self, ip: str, ports: typing.Union[typing.Iterable, typing.Sized], chunk_size: int = None,
                         timeout: int = 3, event_loop: asyncio.AbstractEventLoop = None) -> tuple[
        Union[BaseException, Any], Union[BaseException, Any], Union[BaseException, Any], Union[BaseException, Any],
        Union[BaseException, Any]]:
        using_loop = event_loop or self.event_loop or asyncio.get_event_loop()
        tasks = []
        for port_chunk in utils.chunks(ports, chunk_size or len(ports)):
            tasks.append(using_loop.create_task(self._check_ports(ip, port_chunk, timeout, event_loop=using_loop)))
        res = using_loop.run_until_complete(asyncio.gather(*tasks))
        return res

    async def _check_ports(self, ip, ports, *args, **kwargs):
        res = []
        for port in ports:
            res.append(await self.check_port_async(ip, port, *args, **kwargs))
        return res

    def check_many(self, ip_rows, ports):
        tasks = []
        for ip_row in ip_rows:
            tasks.append(self.event_loop.create_task(self.check_range_async(ip_row[1], ip_row[2], ports)))
        results = self.event_loop.run_until_complete(asyncio.gather(*tasks))
        ret = []
        for res in results:
            ret += res
        return ret

    async def check_many_async(self, ip_rows, port):
        tasks = []
        for ip_row in ip_rows:
            tasks.append(self.event_loop.create_task(self.check_range_async(ip_row[1], ip_row[2], port)))
        results = await asyncio.gather(*tasks)
        return results

    async def check_range_async(self, ip_a, ip_b, ports):
        tasks = []
        for ip in range(ip_a, ip_b):
            ip_str = socket.inet_ntoa(struct.pack('!L', ip))
            if isinstance(ports, list):
                for port in ports:
                    tasks.append(self.event_loop.create_task(self.check_port_async(ip_str, port)))
            else:
                tasks.append(self.event_loop.create_task(self.check_port_async(ip_str, ports)))
        results = await asyncio.gather(*tasks)
        return results

    def check_range(self, ip_a, ip_b, port):
        tasks = []
        for ip in range(ip_a, ip_b):
            ip_str = socket.inet_ntoa(struct.pack('!L', ip))
            tasks.append(self.event_loop.create_task(self.check_port_async(ip_str, port)))
        results = self.event_loop.run_until_complete(asyncio.gather(*tasks))
        return results


_inst = PortChecker()
check_port_sync = _inst.check_port_sync
check_port_async = _inst.check_port_async
check_ports_sync = _inst.check_ports_sync

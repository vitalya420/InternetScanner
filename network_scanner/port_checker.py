import asyncio
import time
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass

from network_scanner import utils
from network_scanner.ip_addr import IPAddr
from network_scanner.ip_range import IPRange
from network_scanner.utils import ip2str


@dataclass
class PortCheckResult:
    ip: str
    port: int
    timeout: float
    start_time: float
    checker_class: object
    status: bool = False
    finish_time: float = None


class AbstractPortChecker(ABC):
    @abstractmethod
    def check_port(self, ip: typing.Union[str, IPAddr], port: int):
        pass

    @abstractmethod
    def check_ports(self, ip: typing.Union[str, int, IPAddr],
                    ports: typing.Union[typing.Iterable, typing.Sized],
                    timeout: float = 3, port_chunk_size: typing.Union[int, None] = None):
        pass


class PortCheckerAsync(AbstractPortChecker, ABC):
    def __init__(self, event_loop=asyncio.new_event_loop(),
                 callback: typing.Callable = None):
        self.event_loop = event_loop
        self.callback = callback

    async def check_port(self, ip: typing.Union[str, int, IPAddr], port: int, timeout: float = 3):
        ip = ip2str(ip)
        result = PortCheckResult(ip=ip, port=port, timeout=timeout,
                                 start_time=time.time(), checker_class=self.__class__)

        future_ = self.event_loop.create_connection(asyncio.Protocol, ip, port)
        try:
            await asyncio.wait_for(future_, timeout=timeout)
            result.status = True
        except (OSError, asyncio.exceptions.TimeoutError):
            result.status = False
        result.finish_time = time.time()
        if result.status and self.callback:
            self.callback(result)
        return result

    async def check_ports(self, ip: typing.Union[str, int, IPAddr],
                          ports: typing.Union[typing.Iterable, typing.Sized],
                          timeout: float = 3, port_chunk_size: typing.Union[int, None] = None):
        ip = ip2str(ip)
        ret = []
        for port_chunk in utils.chunks(ports, port_chunk_size or len(ports)):
            tasks = [self.event_loop.create_task(self.check_port(ip, port, timeout)) for port in port_chunk]
            res = await asyncio.gather(*tasks)
            ret.extend(res)
        return ret

    async def check_range(self, ip_range: IPRange, ports: typing.Union[typing.Iterable, typing.Sized],
                          timeout: float = 3, port_chunk_size: typing.Union[int, None] = None):
        tasks = [self.event_loop.create_task(self.check_ports(ip, ports, timeout, port_chunk_size))
                 for ip in ip_range]
        res = await asyncio.gather(*tasks)
        return res

    async def check_many(self, ips: list[IPRange], ports: typing.Union[typing.Iterable, typing.Sized],
                         timeout: float = 3, ip_chunk_size: typing.Union[int, None] = None,
                         port_chunk_size: typing.Union[int, None] = None):
        for ip_chunk in utils.chunks(ips, ip_chunk_size or len(ips)):
            tasks = [self.event_loop.create_task(self.check_range(ip_range[0], ports, timeout, port_chunk_size))
                     for ip_range in ip_chunk]
            res = await asyncio.gather(*tasks)
            yield [j for i in res for j in i]

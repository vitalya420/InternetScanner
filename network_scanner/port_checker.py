import asyncio
import time
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass

from network_scanner import utils
from network_scanner.ip_addr import IPAddr


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
    def __init__(self, ip, ports: typing.Iterable = tuple()):
        self.ip = str(ip) if isinstance(ip, IPAddr) else ip
        self.ports = ports

    @abstractmethod
    def check_port(self, port, ip=None):
        pass

    @abstractmethod
    def check_ports(self, timeout=3):
        pass


class PortCheckerAsync(AbstractPortChecker, ABC):
    def __init__(self, ip, ports: typing.Iterable = tuple(),
                 event_loop=asyncio.new_event_loop(),
                 callback: typing.Callable = None):
        super().__init__(ip, ports)
        self.event_loop = event_loop
        self.callback = callback

    async def check_port(self, port, timeout=3, ip=None):
        result = PortCheckResult(
            ip=ip or self.ip,
            port=port, timeout=timeout, start_time=time.time(),
            checker_class=self.__class__
        )
        future_ = self.event_loop.create_connection(asyncio.Protocol, ip or self.ip, port)
        try:
            await asyncio.wait_for(future_, timeout=timeout)
            result.status = True
        except (OSError, asyncio.exceptions.TimeoutError):
            result.status = False
        result.finish_time = time.time()
        if result.status and self.callback:
            self.callback(result)
        return result

    async def check_ports(self, timeout=3, chunk_size=5, ip=None):
        ret = []
        for port_chunk in utils.chunks(self.ports, chunk_size):
            tasks = []
            for port in port_chunk:
                task = self.event_loop.create_task(self.check_port(port, timeout=timeout, ip=ip))
                tasks.append(task)
            res = await asyncio.gather(*tasks)
            ret.extend(res)
        return ret


class PortCheckerAsyncToSync(PortCheckerAsync):
    def check_ports(self, timeout=3, chunk_size=5, ip=None):
        task = self.event_loop.create_task(super().check_ports(timeout, chunk_size))
        res = self.event_loop.run_until_complete(asyncio.gather(task))
        return res[0]

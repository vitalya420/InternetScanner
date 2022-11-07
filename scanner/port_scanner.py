import asyncio
from multiprocessing import Process, Queue

from . import utils
from .port_checker import PortChecker


class PortScanner(Process, PortChecker):
    def __init__(self, ip, ports, timeout,
                 queue, chunk_size=5,
                 event_loop=asyncio.new_event_loop()):
        super().__init__()
        self.ip = ip
        self.ports = ports
        self.event_loop = event_loop
        self.timeout = timeout
        self.queue = queue
        self.chunk_size = chunk_size

    def run(self) -> None:
        res = super().check_ports_sync(self.ip, self.ports,
                                       chunk_size=self.chunk_size, timeout=self.timeout)
        self.queue.put(res)


def scan_ports(ip, ports, processes, chunk_size, timeout, *args, **kwargs):
    queue = Queue()
    res = []
    scanners = [
        PortScanner(ip=ip, ports=ports_chunk,
                    timeout=timeout, queue=queue,
                    chunk_size=chunk_size)
        for ports_chunk in utils.chunks(ports, len(ports) // processes)
    ]
    for scanner in scanners:
        scanner.start()
    while True:
        # Temp solution
        p = queue.get()
        res.append(p)
        if len(res) == len(scanners):
            return res

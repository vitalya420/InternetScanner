import asyncio
from multiprocessing import Process


class PortScanner(Process):
    def __init__(self, ip, ports, callback, timeout,
                 event_loop=asyncio.new_event_loop()):
        super().__init__()
        self.ip = ip
        self.ports = ports
        self.callback = callback
        self.event_loop = event_loop
        self.timeout = timeout

    async def check_port(self, port, proto='TCP'):
        try:
            if proto == 'TCP':
                fut = self.event_loop.create_connection(asyncio.Protocol, self.ip, port)
                await asyncio.wait_for(fut, timeout=self.timeout)
                self.callback(self.ip, port)
                return True
            return False
        except asyncio.exceptions.TimeoutError:
            return False
        except OSError:
            return False

    async def _run(self):
        tasks = []
        for port in self.ports:
            task = self.event_loop.create_task(self.check_port(port))
            tasks.append(task)
        await asyncio.gather(*tasks)

    def run(self) -> None:
        self.event_loop.run_until_complete(self._run())

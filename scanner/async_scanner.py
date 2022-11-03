import asyncio
import socket
import struct
import time
from multiprocessing import Process
from typing import Union, Callable


class EchoClientProtocol:
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print('Send:', self.message)
        self.transport.sendto(self.message.encode())

    def datagram_received(self, data, addr):
        print("Received:", data.decode())

        print("Close the socket")
        self.transport.close()

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        print("Connection closed")
        self.on_con_lost.set_result(True)


class AsyncPortChecker:
    def __init__(self, event_loop: asyncio.AbstractEventLoop = asyncio.get_event_loop(),
                 timeout: Union[int, float] = 10, callback: Callable = None):
        self.loop = event_loop
        self.timeout = timeout
        self.callback = callback

    async def check_async(self, ip, port, proto='TCP'):
        try:
            if proto == 'TCP':
                fut = self.loop.create_connection(asyncio.Protocol, ip, port)
                await asyncio.wait_for(fut, timeout=self.timeout)
                if self.callback and callable(self.callback):
                    self.callback(ip, port)
                return True
            return False
            # elif proto == 'UDP':
            #     on_con_lost = self.loop.create_future()
            #     fut = self.loop.create_datagram_endpoint(
            #         lambda: EchoClientProtocol('asd', on_con_lost),
            #         remote_addr=(ip, port))
            #     res = await asyncio.wait_for(fut, timeout=self.timeout)
            #     return True
        except asyncio.exceptions.TimeoutError:
            return False
        except OSError:
            return False

    def check_one(self, ip, port, proto='TCP'):
        task = self.loop.create_task(self.check_async(ip, port, proto))
        return self.loop.run_until_complete(task)

    def check_range(self, ip_a, ip_b, port):
        tasks = []
        for ip in range(ip_a, ip_b):
            ip_str = socket.inet_ntoa(struct.pack('!L', ip))
            tasks.append(self.loop.create_task(self.check_async(ip_str, port)))
        results = self.loop.run_until_complete(asyncio.gather(*tasks))
        return results

    async def check_range_async(self, ip_a, ip_b, ports):
        tasks = []
        for ip in range(ip_a, ip_b):
            ip_str = socket.inet_ntoa(struct.pack('!L', ip))
            if isinstance(ports, list):
                for port in ports:
                    tasks.append(self.loop.create_task(self.check_async(ip_str, port)))
            else:
                tasks.append(self.loop.create_task(self.check_async(ip_str, ports)))
        results = await asyncio.gather(*tasks)
        return results

    def check_many(self, ip_rows, ports):
        tasks = []
        for ip_row in ip_rows:
            tasks.append(self.loop.create_task(self.check_range_async(ip_row[1], ip_row[2], ports)))
        results = self.loop.run_until_complete(asyncio.gather(*tasks))
        return results

    async def check_many_async(self, ip_rows, port):
        tasks = []
        for ip_row in ip_rows:
            tasks.append(self.loop.create_task(self.check_range_async(ip_row[1], ip_row[2], port)))
        results = await asyncio.gather(*tasks)
        return results

    def check_all(self, ips, port, block=10):
        tasks = []
        for i in range(len(ips) // block):
            tasks.append(self.check_many_async(ips[i * block:i * block + block], port))
        result = self.loop.run_until_complete(asyncio.gather(*tasks))
        return result


class MultiProcessedAsyncPortChecker(Process):
    def __init__(self, ip_rows, block, ports, callback, *args, **kwargs):
        super().__init__()
        self.ip_rows = ip_rows
        self.block = block
        self.ports = ports
        self.callback = callback

    @staticmethod
    def calc_ips(ip_range):
        total = 0
        for ip_row in ip_range:
            total += ip_row[2] - ip_row[1]
        return total

    def run(self):
        rows_amount = len(self.ip_rows)
        checker = AsyncPortChecker(event_loop=asyncio.new_event_loop(), timeout=3, callback=self.callback)
        for i in range(0, len(self.ip_rows), self.block):
            ips_amount_to_be_checked = self.calc_ips(self.ip_rows[i:i + self.block])
            if ips_amount_to_be_checked < 20_000:
                start = time.perf_counter()
                checker.check_many(self.ip_rows[i:i + self.block], self.ports)
                print(
                    f"[{self.name}][{i} - {i + self.block}][{ips_amount_to_be_checked}][Progress: {((i + self.block) / rows_amount) * 100:.2f}%]check time: {time.perf_counter() - start}.]")
            else:
                for j, s_ip_row in enumerate(self.ip_rows[i:i + self.block]):
                    start = time.perf_counter()
                    checker.check_range(s_ip_row[1], s_ip_row[2], self.ports)
                    print(
                        f"[{self.name}][{i} - {i + self.block}][Part {j}][Progress: {((i + self.block) / rows_amount) * 100:.2f}%]check time: {time.perf_counter() - start}.]")


# checker = MultiProcessedAsyncPortChecker(timeout=1)
# print(checker.loop.run_until_complete(checker.check_range_async(34953472, 34953727, 25565)))

import asyncio
import socket

from mcstatus import JavaServer

ips = """
"""


async def check(address=None, ip=None, port=None):
    try:
        server = await JavaServer.async_lookup(address or f'{ip}:{port}', timeout=1)
        print(f'{address} {server.status().raw}')
        with open('good.txt', 'a') as file:
            file.write(f'{address} {server.status().raw}\n')
    except socket.timeout:
        # print("timeout")
        pass
    except OSError:
        # print('Pizda OSError')
        pass
    except Exception:
        pass


loop = asyncio.get_event_loop()
tasks = []
for ip in ips.split('\n'):
    tasks.append(loop.create_task(check(ip)))
asyncio.gather(*tasks)
loop.run_forever()

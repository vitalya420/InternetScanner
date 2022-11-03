from scanner import Scanner


class Controller:
    def __init__(self, all_ips, port):
        self.all_ips = all_ips
        self.port = port
        self._scanners = []

    def get_not_busy_scanner(self, last_scanner):
        for scanner_ in self._scanners:
            if scanner_ is not last_scanner and not scanner_.is_busy:
                return scanner_

    @staticmethod
    def callback(scan_proc, all_res):
        print(f"got {len(all_res)} results for {scan_proc.name}")
        for res in all_res:
            if res.opened:
                print(scan_proc.name, res.ip)

    def manage(self, amount):
        for i in range(amount):
            scanner_ = Scanner()
            scanner_.start()
            self._scanners.append(scanner_)

        last_scanner = None
        for ip in self.all_ips:
            scanner_ = None
            while not scanner_:
                scanner_ = self.get_not_busy_scanner(last_scanner)
            last_scanner = scanner_
            scanner_.scan_nowait(ip, [25565, 80], callback=self.callback)

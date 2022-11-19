import csv
import socket
import struct

from sqlalchemy import Integer, Column, String, BigInteger, Float, and_, select

from network_scanner import Base, db_manager


class IPRange(Base):
    _session = None

    __tablename__ = 'ip_ranges'
    id = Column(Integer, primary_key=True)
    start = Column(BigInteger)
    end = Column(BigInteger)
    country_code = Column(String)
    country = Column(String)
    region = Column(String)
    city = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    zipcode = Column(String)
    timezone = Column(String)

    @staticmethod
    def lookup_ip_addr(ip):
        dec_ip = struct.unpack("!L", socket.inet_aton(ip))[0]
        q = select(IPRange).where(and_(IPRange.start <= dec_ip), (IPRange.end > dec_ip))
        res = db_manager.session.execute(q)
        return res.fetchone()[0]

    @staticmethod
    def fetch_all_by_country_code(cc):
        q = select(IPRange).where(IPRange.country_code == cc)
        res = db_manager.session.execute(q)
        return res.fetchmany()

    @staticmethod
    def get_by_country_code(cc):
        q = select(IPRange).where(IPRange.country_code == cc)
        res = db_manager.session.execute(q)
        return res

    @property
    def amount(self):
        return self.end - self.start

    def __iter__(self):
        self.__cur = self.start
        return self

    def __next__(self):
        if self.__cur <= self.end:
            ret = self.__cur
            self.__cur += 1
            return ret
        else:
            raise StopIteration

    def __repr__(self):
        return f"<IPRange(start={self.start}, end={self.end}, " \
               f"country_code={self.country_code}, region={self.region}, " \
               f"city={self.city}, latitude={self.latitude}, longitude={self.longitude}, " \
               f"zipcode={self.zipcode}, timezone={self.timezone}, amount={self.amount})>"

    def __len__(self):
        return self.amount


def import_from_csv(filepath):
    with open(filepath, 'r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for i, row in enumerate(csv_reader):
            start, end, cc, country, region, city, lat, long, zipcode, tz = row
            ip_range = IPRange(start=start, end=end, country_code=cc,
                               country=country, city=city, latitude=lat,
                               region=region, longitude=long, zipcode=zipcode,
                               timezone=tz)
            db_manager.session.add(ip_range)
            if i % 100000 == 0:
                db_manager.session.commit()
                print('commit')
        else:
            print('commit')
            db_manager.session.commit()

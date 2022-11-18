import logging

from sqlalchemy.orm import declarative_base, sessionmaker

_logger = logging.getLogger()


class DatabaseManager:
    def __init__(self, session=None, engine=None):
        self.session = session
        self.engine = engine

        self._base = None
        _logger.debug(f'DB manager initialized with values {session=}, {engine=}')

    @property
    def base(self):
        if self._base:
            return self._base
        self._base = declarative_base()
        _logger.debug(f'Declared base class')
        return self._base

    def setup_database(self, engine):
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.engine = engine
        _logger.debug('Database setted up')

    def create_all(self, *args, **kwargs):
        self.base.metadata.create_all(self.engine, *args, **kwargs)


db_manager = DatabaseManager()
Base = db_manager.base

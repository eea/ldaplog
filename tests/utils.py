import sqlalchemy, sqlalchemy.orm


def create_memory_db(metadata):
    engine = sqlalchemy.create_engine('sqlite:///:memory:', echo=True, encoding='latin1')
    engine.raw_connection().connection.text_factory = str
    metadata.create_all(engine)
    return sqlalchemy.orm.sessionmaker(bind=engine)

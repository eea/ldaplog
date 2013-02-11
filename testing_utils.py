import sqlalchemy, sqlalchemy.orm


def create_memory_db(metadata):
    engine = sqlalchemy.create_engine('sqlite:///:memory:', echo=True)
    metadata.create_all(engine)
    return sqlalchemy.orm.sessionmaker(bind=engine)

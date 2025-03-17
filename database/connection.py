from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

DATABASE_URL = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
engine = create_engine(DATABASE_URL, echo = False)

SessionFactory = sessionmaker(bind = engine)

def get_session() -> Session:
    return SessionFactory()
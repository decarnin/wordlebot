from sqlalchemy import Column, BigInteger, String, Date, ForeignKey, ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'user_data'
    user_id = Column(BigInteger, primary_key = True)
    user_name = Column(String(32), nullable = False)
    avatar = Column(String(255), nullable = False)

class ServerData(Base):
    __tablename__ = 'server_data'
    server_id = Column(BigInteger, primary_key = True)
    prefix = Column(String(5), nullable = False, default = '!')
    wordle_channel_id = Column(BigInteger, nullable = True)

class ServerMembership(Base):
    __tablename__ = 'server_membership'
    user_id = Column(BigInteger, ForeignKey('user_data.user_id'), primary_key = True)
    server_id = Column(BigInteger, ForeignKey('server_data.server_id'), primary_key = True)
    display_name = Column(String(32), nullable = False)

class WordleData(Base):
    __tablename__ = 'wordle_data'
    user_id = Column(BigInteger, ForeignKey('user_data.user_id'), primary_key = True)
    wordle_id = Column(String(100), primary_key = True)
    wordle_score = Column(String(1), nullable = False)
    wordle_grid = Column(String(35), nullable = False)
    wordle_date = Column(Date, nullable = False)

class WordleServerMembership(Base):
    __tablename__ = 'wordle_server_membership'
    user_id = Column(BigInteger, ForeignKey('user_data.user_id'), primary_key = True)
    server_id = Column(BigInteger, ForeignKey('server_data.server_id'), primary_key = True)
    wordle_id = Column(String(100), primary_key = True)

    __table_args__= (
        ForeignKeyConstraint(
            ['user_id', 'wordle_id'],
            ['wordle_data.user_id', 'wordle_data.wordle_id']
        ),
    )

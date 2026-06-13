from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
import datetime

class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True)
    event_title = Column(String)
    market_id = Column(String, index=True) # ID from polymarket
    market_type = Column(String, default="Moneyline")
    option_name = Column(String) # e.g., "Brazil"
    home_team_code = Column(String, default="")  # FIFA code of the home team, e.g. "USA"
    odds = Column(Float)
    start_time = Column(DateTime)
    votes = Column(Integer, default=0)
    order_placed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class VoteRecord(Base):
    __tablename__ = "vote_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market_id = Column(Integer, ForeignKey("markets.id"))
    
class OrderHistory(Base):
    __tablename__ = "order_history"
    
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer)
    status = Column(String) # e.g., 'success', 'failed'
    volume = Column(Float)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)

class SharedFund(Base):
    __tablename__ = "shared_fund"
    
    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, default=1000.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

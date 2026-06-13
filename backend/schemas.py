from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
from datetime import datetime
from typing import List, Optional

class MarketBase(BaseModel):
    event_id: str
    event_title: str
    market_id: str
    market_type: str
    option_name: str
    home_team_code: Optional[str] = ""
    odds: float
    start_time: Optional[datetime] = None

class MarketCreate(MarketBase):
    pass

class MarketResponse(MarketBase):
    id: int
    votes: int
    order_placed: bool
    created_at: datetime

    class Config:
        from_attributes = True

class EventResponse(BaseModel):
    event_id: str
    event_title: str
    markets: List[MarketResponse]

class VoteResponse(BaseModel):
    message: str
    market_id: int
    new_votes: int
    order_triggered: bool

class FundResponse(BaseModel):
    balance: float
    updated_at: datetime
    
    class Config:
        from_attributes = True

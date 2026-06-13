import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

import models, schemas, database, auth

# Create tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="World Cup Market Voting API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VOTE_THRESHOLD = 6 # 6 votes needed since there are 6 people
ORDER_VOLUME = 10.0 # Mock volume

import requests
import json

import random

import time

def fetch_polymarket_events(db: Session):
    if db.query(models.Market).count() > 0:
        return

    print("Fetching real Polymarket events using World Cup 2026 schedule...")
    try:
        base_path = os.path.join(os.path.dirname(__file__), "worldcup2026_data")
        
        # Load teams
        teams_dict = {}
        teams_name_dict = {}
        with open(os.path.join(base_path, "football.teams.json"), "r", encoding="utf-8") as f:
            teams = json.load(f)
            for t in teams:
                teams_dict[t["id"]] = t["fifa_code"].lower()
                teams_name_dict[t["id"]] = t["name_en"]
                
        # Load matches
        with open(os.path.join(base_path, "football.matches.json"), "r", encoding="utf-8") as f:
            matches = json.load(f)
            
        markets_to_add = []
        now_utc = datetime.utcnow()
        count = 0
        for match in matches:
            if count >= 15:
                break
            home_code = teams_dict.get(match["home_team_id"])
            away_code = teams_dict.get(match["away_team_id"])
            if not home_code or not away_code:
                continue

            # local_date is in US local time (UTC-4 to UTC-7).
            # Add 7h (Pacific offset) to convert to UTC conservatively —
            # this avoids filtering out late-evening US matches that haven't
            # started yet but whose date is already "yesterday" in UTC.
            try:
                match_local_dt = datetime.strptime(match['local_date'], "%m/%d/%Y %H:%M")
                match_utc_dt = match_local_dt + timedelta(hours=7)
                if match_utc_dt < now_utc:
                    continue
            except Exception:
                date_parts = match['local_date'].split(' ')[0].split('/')
                date_str = f"{date_parts[2]}-{date_parts[0]}-{date_parts[1]}"
                if date_str < now_utc.strftime("%Y-%m-%d"):
                    continue

            count += 1

            date_parts = match['local_date'].split(' ')[0].split('/')
            date_str = f"{date_parts[2]}-{date_parts[0]}-{date_parts[1]}"
            slug = f"fifwc-{home_code}-{away_code}-{date_str}"
            
            url = f"https://gamma-api.polymarket.com/events?slug={slug}"
            try:
                response = requests.get(url, timeout=5)
            except Exception as e:
                print(f"Request timeout for {slug}: {e}")
                continue
            if response.status_code == 200:
                events = response.json()
                if not events:
                    continue
                event = events[0]
                event_id = event.get("id", slug)
                event_title = event.get("title", f"{home_code.upper()} vs {away_code.upper()}")
                
                for market in event.get("markets", []):
                    if market.get("closed"):
                        continue
                        
                    market_id = market.get("id")
                    group_title = market.get("groupItemTitle", market.get("question", "Unknown"))
                    if group_title.startswith("Draw"):
                        group_title = "DRAW"
                    
                    home_name = teams_name_dict.get(match["home_team_id"], "Home").upper()
                    away_name = teams_name_dict.get(match["away_team_id"], "Away").upper()
                    
                    def unify_team_name(text: str) -> str:
                        t = text
                        if "BIH" in away_code.upper() or "BIH" in home_code.upper():
                            t = t.replace("Bosnia and Herzegovina", "BIH")
                            t = t.replace("Bosnia-Herzegovina", "BIH")
                            t = t.replace("Bosnia", "BIH")
                            
                        t = t.replace(home_name.title(), home_code.upper())
                        t = t.replace(away_name.title(), away_code.upper())
                        t = t.replace(home_name.capitalize(), home_code.upper())
                        t = t.replace(away_name.capitalize(), away_code.upper())
                        t = t.replace(home_name, home_code.upper())
                        t = t.replace(away_name, away_code.upper())
                        return t
                        
                    group_title = unify_team_name(group_title)
                    
                    outcome_prices = market.get("outcomePrices", [])
                    if isinstance(outcome_prices, str):
                        try:
                            outcome_prices = json.loads(outcome_prices)
                        except:
                            outcome_prices = ["0.5", "0.5"]
                            
                    # We want the "Yes" odds, converted to cents for Polymarket style display
                    odds = float(outcome_prices[0]) * 100 if len(outcome_prices) > 0 else 50.0
                    
                    new_market = models.Market(
                        event_id=str(event_id),
                        event_title=event_title,
                        market_id=str(market_id),
                        market_type="Moneyline",
                        option_name=str(group_title),
                        home_team_code=home_code.upper(),
                        odds=round(odds, 1),
                        start_time=datetime.utcnow() + timedelta(days=2)
                    )
                    markets_to_add.append(new_market)
                


                # Fetch Real Spreads and Totals
                more_markets_url = f"https://gamma-api.polymarket.com/events?slug={slug}-more-markets"
                try:
                    mm_response = requests.get(more_markets_url, timeout=5)
                    if mm_response.status_code == 200:
                        mm_events = mm_response.json()
                        if mm_events:
                            mm_event = mm_events[0]
                            for market in mm_event.get("markets", []):
                                if market.get("closed"):
                                    continue
                                
                                group_title = market.get("groupItemTitle", "")
                                
                                outcome_prices = market.get("outcomePrices", [])
                                if isinstance(outcome_prices, str):
                                    try:
                                        outcome_prices = json.loads(outcome_prices)
                                    except:
                                        outcome_prices = ["0.5", "0.5"]
                                
                                if "O/U" in group_title and not any(x in group_title for x in ["1st Half", "2nd Half", home_code.upper(), away_code.upper()]):
                                    # It's a Total
                                    # group_title like "O/U 2.5"
                                    # Create "Over"
                                    markets_to_add.append(models.Market(
                                        event_id=str(event_id), event_title=event_title, market_id=str(market.get("id"))+"-over",
                                        market_type="Totals", option_name=unify_team_name(group_title.replace("O/U", "Over")), home_team_code=home_code.upper(), odds=round(float(outcome_prices[0])*100, 1),
                                        start_time=datetime.utcnow() + timedelta(days=2)
                                    ))
                                    # Create "Under"
                                    markets_to_add.append(models.Market(
                                        event_id=str(event_id), event_title=event_title, market_id=str(market.get("id"))+"-under",
                                        market_type="Totals", option_name=unify_team_name(group_title.replace("O/U", "Under")), home_team_code=home_code.upper(), odds=round(float(outcome_prices[1])*100, 1),
                                        start_time=datetime.utcnow() + timedelta(days=2)
                                    ))
                                elif "(-" in group_title or "(+" in group_title:
                                    # It's a Spread
                                    # We can dynamically determine the other team name
                                    team_in_title = group_title.split("(")[0].strip()
                                    is_home = home_name.lower() in team_in_title.lower()
                                    my_team_code = home_code.upper() if is_home else away_code.upper()
                                    other_team_code = away_code.upper() if is_home else home_code.upper()
                                    
                                    my_spread = group_title.split("(")[1].split(")")[0]
                                    if not my_spread.endswith(")"):
                                        my_spread += ")"
                                        
                                    # Add the negative spread (Yes side)
                                    markets_to_add.append(models.Market(
                                        event_id=str(event_id), event_title=event_title, market_id=str(market.get("id")),
                                        market_type="Spreads", option_name=f"{my_team_code} ({my_spread}", home_team_code=home_code.upper(), odds=round(float(outcome_prices[0])*100, 1),
                                        start_time=datetime.utcnow() + timedelta(days=2)
                                    ))
                                    # Add the corresponding positive spread (No side)
                                    opposite_spread = "+" + my_spread[1:] if my_spread.startswith("-") else "-" + my_spread[1:]
                                    
                                    markets_to_add.append(models.Market(
                                        event_id=str(event_id), event_title=event_title, market_id=str(market.get("id"))+"-opp",
                                        market_type="Spreads", option_name=f"{other_team_code} ({opposite_spread}", home_team_code=home_code.upper(), odds=round(float(outcome_prices[1])*100, 1),
                                        start_time=datetime.utcnow() + timedelta(days=2)
                                    ))
                except Exception as e:
                    print(f"Error fetching more markets for {slug}: {e}")
            
            time.sleep(0.5)
                
        if markets_to_add:
            db.add_all(markets_to_add)
            db.commit()
    except Exception as e:
        print(f"Error generating events: {e}")

@app.on_event("startup")
def startup_event():
    db = database.SessionLocal()
    fetch_polymarket_events(db)
    
    # Initialize SharedFund if it doesn't exist
    if db.query(models.SharedFund).count() == 0:
        fund = models.SharedFund(balance=1000.0)
        db.add(fund)
        db.commit()
        
    db.close()

# Auth Endpoints
@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Market Endpoints
@app.get("/api/fund", response_model=schemas.FundResponse)
def get_fund(db: Session = Depends(database.get_db)):
    fund = db.query(models.SharedFund).first()
    if not fund:
        fund = models.SharedFund(balance=1000.0)
        db.add(fund)
        db.commit()
        db.refresh(fund)
    return fund
@app.get("/api/markets", response_model=list[schemas.EventResponse])
def get_markets(db: Session = Depends(database.get_db)):
    markets = db.query(models.Market).all()
    
    # Simulate realtime price updates for mock markets
    for market in markets:
        if market.market_type != "Moneyline" and not market.order_placed:
            change = random.uniform(-0.02, 0.02)
            market.odds = max(1.01, round(market.odds + change, 2))
    db.commit()
    
    events_dict = {}
    for market in markets:
        if market.event_id not in events_dict:
            events_dict[market.event_id] = {
                "event_id": market.event_id,
                "event_title": market.event_title,
                "markets": []
            }
        events_dict[market.event_id]["markets"].append(market)
    
    return list(events_dict.values())

def execute_polymarket_order(market_id: int, db: Session):
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market or market.order_placed:
        return
    
    print(f"--- POLYMARKET EXECUTION START ---")
    print(f"Connecting to Polymarket via py-clob-client...")
    print(f"Executing BUY order for {market.event_title} - {market.option_name} at odds {market.odds}")
    
    # In a real scenario, py_clob_client would be used here.
    # client = ClobClient(host="https://clob.polymarket.com", key=PRIVATE_KEY, chain_id=137)
    # order = client.create_and_post_order(order_args)
    
    print(f"Order successful on Polymarket for Market ID {market.id}")
    print(f"----------------------------------")
    
    # Record order
    order = models.OrderHistory(
        market_id=market.id,
        status="success",
        volume=ORDER_VOLUME
    )
    db.add(order)
    
    # Update market
    market.order_placed = True
    
    # Deduct from SharedFund
    fund = db.query(models.SharedFund).first()
    if fund:
        fund.balance -= ORDER_VOLUME
        
    db.commit()

@app.post("/api/vote/{market_id}", response_model=schemas.VoteResponse)
def vote_market(market_id: int, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    # Check if user already voted in this event/market_type
    existing_vote = db.query(models.VoteRecord).join(models.Market, models.VoteRecord.market_id == models.Market.id).filter(
        models.VoteRecord.user_id == current_user.id,
        models.Market.event_id == market.event_id,
        models.Market.market_type == market.market_type
    ).first()
    
    if existing_vote:
        if existing_vote.market_id == market_id:
            # Toggle off vote
            db.delete(existing_vote)
            market.votes = max(0, market.votes - 1)
            db.commit()
            return schemas.VoteResponse(message="Vote removed", market_id=market.id, new_votes=market.votes, order_triggered=False)
        else:
            # Change vote
            old_market = db.query(models.Market).filter(models.Market.id == existing_vote.market_id).first()
            if old_market:
                old_market.votes = max(0, old_market.votes - 1)
            db.delete(existing_vote)
            
    # Record new vote
    new_vote = models.VoteRecord(user_id=current_user.id, market_id=market_id)
    db.add(new_vote)
    
    market.votes += 1
    db.commit()
    db.refresh(market)
    
    order_triggered = False
    if market.votes >= VOTE_THRESHOLD and not market.order_placed:
        order_triggered = True
        # Run Polymarket order execution in background
        background_tasks.add_task(execute_polymarket_order, market.id, database.SessionLocal())
        
    return schemas.VoteResponse(
        message="Vote cast successfully",
        market_id=market.id,
        new_votes=market.votes,
        order_triggered=order_triggered
    )

# Serve React frontend static files (production only)
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        index = os.path.join(_frontend_dist, "index.html")
        return FileResponse(index)

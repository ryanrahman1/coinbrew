import os
from apscheduler.schedulers.background import BackgroundScheduler
from db.queries import get_all_coins, calculate_new_price
import pytz

def update_all_coin_prices():
    coins = get_all_coins(limit=1000, offset=0)
    for coin in coins:
        calculate_new_price(coin["id"]) 

if not os.getenv("VERCEL", ""):  # Avoid starting background jobs on Vercel serverless
    scheduler = BackgroundScheduler(timezone=pytz.UTC)
    scheduler.add_job(update_all_coin_prices, 'interval', hours=6)
    scheduler.start()

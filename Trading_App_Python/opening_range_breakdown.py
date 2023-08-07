import sqlite3
import config
import alpaca_trade_api as tradeapi
from datetime import date
import pandas as pd
import smtplib, ssl
from alpaca_trade_api.rest import TimeFrame
from timezone import is_dst
from helpers import calculate_quantity

context = ssl.create_default_context()

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
    SELECT id FROM strategy WHERE name = 'opening_range_breakdown'
""")

strategy_id = cursor.fetchone()['id']

cursor.execute("""
    SELECT symbol, name
    FROM stock
    JOIN stock_strategy on stock_strategy.stock_id = stock.id
    WHERE stock_strategy.strategy_id = ?
""", (strategy_id,))

stocks = cursor.fetchall()
symbols = [stock['symbol'] for stock in stocks]

#current_date = date.today().isoformat()
current_date = '2022-02-07'


if is_dst():
    #start_minute_bar = f"{current_date} 08:30-09:30"
    #end_minute_bar = f"{current_date} 08:45:00-09:30"
    start_minute_bar = f"{current_date} 09:30-5:30"
    end_minute_bar = f"{current_date} 09:45:00-5:30"
else:
    start_minute_bar = f"{current_date} 19:30:00"
    end_minute_bar = f"{current_date} 19:45:00"

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

orders = api.list_orders(status='all', after = current_date)
existing_order_symbol = [order.symbol for order in orders if order.status != 'canceled']

messages = []

for symbol in symbols:
    
    minute_bars = api.get_bars(symbol, TimeFrame.Minute, current_date, current_date).df

    opening_range_mask = (minute_bars.index >= start_minute_bar) & (minute_bars.index < end_minute_bar)
    opening_range_bars = minute_bars.loc[opening_range_mask]

    if not minute_bars.empty:
        opening_range_low = opening_range_bars['low'].min()
        opening_range_high = opening_range_bars['high'].max()

    opening_range = opening_range_high - opening_range_low


    after_opening_range_mask = minute_bars.index >= end_minute_bar
    after_opening_range_bars = minute_bars.loc[after_opening_range_mask]
    after_opening_range_breakdown = after_opening_range_bars[after_opening_range_bars['close'] < opening_range_high]
    
    if not after_opening_range_breakdown.empty:
        if symbol not in existing_order_symbol:

            limit_price = after_opening_range_breakdown.iloc[0]['close']

            message = f"Selling short {symbol} at {limit_price}, closed below {opening_range_low}\n\n{after_opening_range_breakdown.index[0]}\n\n"
            messages.append(message)


            try:
                api.submit_order(
                    symbol=symbol,
                    side='sell',
                    type='limit',
                    qty=calculate_quantity(limit_price),
                    time_in_force='day',
                    order_class='bracket',
                    limit_price=limit_price,
                    take_profit=dict(
                        limit_price=limit_price - opening_range,
                    ),
                    stop_loss=dict(
                        stop_price=limit_price + opening_range,
                    )
                )

                cursor.execute("""
                    SELECT email_id 
                    FROM user
                    WHERE is_active = 'T';
                """)

                active = cursor.fetchone()
                SEND_TO = active['email_id']

                with smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT, context=context) as server:
                    server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)

                    email_message = f"Subject: Trade Notifications for {current_date}\n\n"
                    email_message += "\n\n".join(messages)

                    server.sendmail(config.EMAIL_ADDRESS, SEND_TO, email_message)

            except Exception as e:
                print(f"could not submit order {e}")

        else:
           print(f"Already in order for {symbol}, skipping")




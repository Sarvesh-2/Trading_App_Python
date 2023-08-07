import sqlite3
import config
import tulipy
import alpaca_trade_api as tradeapi
import pandas as pd
import datetime
from alpaca_trade_api.rest import TimeFrame
from timezone import is_dst
from helpers import calculate_quantity
import smtplib, ssl

context = ssl.create_default_context()

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
    SELECT id FROM strategy 
    WHERE name = 'bollinger_bands'
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

start_minute_bar = f"{current_date} 09:30:00"
end_minute_bar = f"{current_date} 10:00:00"


api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

orders = api.list_orders(status='all', after=current_date)
existing_order_symbol = [
    order.symbol for order in orders if order.status != 'canceled']




for symbol in symbols:
    minute_bars = api.get_bars(
        symbol, TimeFrame.Minute, current_date, current_date).df

    market_open_mask = (minute_bars.index >= start_minute_bar) & (
        minute_bars.index < end_minute_bar)
    market_open_bars = minute_bars.loc[market_open_mask]

    if len(market_open_bars) >= 20:
        closes = market_open_bars.close.values
        lower, middle, upper = tulipy.bbands(closes, 20, 2)

        current_candle = market_open_bars.iloc[-1]
        previous_candle = market_open_bars.iloc[-2]

        if current_candle.close < lower[-1] and previous_candle.close < lower[-2]:
            print(f"{symbol} closed above lower bollinger band")
            print(current_candle)

            if symbol not in existing_order_symbol:
                limit_price = current_candle.close
                candle_range = current_candle.high - current_candle.low
                messages.append(f"Placing order for {symbol} at {limit_price}\n\n")
                print(f"Placing order for {symbol} at {limit_price}")
                try:
                    api.submit_order(
                        symbol=symbol,
                        side='buy',
                        type='limit',
                        qty=calculate_quantity(limit_price),
                        time_in_force='day',
                        order_class='bracket',
                        limit_price=limit_price,
                        take_profit=dict(
                        limit_price=limit_price + (candle_range * 3),
                        ),
                        stop_loss=dict(
                         stop_price=previous_candle.low,
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

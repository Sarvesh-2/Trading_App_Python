import config
import sqlite3
import pandas
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
from alpaca_trade_api.rest import TimeFrame

#pandas.set_option('display.max_rows', -1)

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

cursor.execute("""
SELECT * FROM(
            SELECT symbol, name, stock_id, max(close), date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            GROUP BY stock_id
            ORDER BY symbol
        ) WHERE date = (SELECT max(date) from stock_price)
""")
rows = cursor.fetchall()

symbols = []
stock_dict = {}


for row in rows:
    symbol = row['symbol']
    symbols.append(symbol)
    stock_dict[symbol] = row['stock_id']



for symbol in symbols:
    start_date = datetime(2022, 1, 1 ).date()
    end_date_range = datetime(2022, 2, 2).date()

    try:
        while start_date < end_date_range:
            end_date = start_date + timedelta(days=4)

            print(f"===Fetching minute bars {start_date}-to-{end_date} for {symbol}")

            api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

            minutes = api.get_bars(symbol, TimeFrame.Minute, start_date, end_date).df


            for index, row in minutes.iterrows():
                cursor.execute("""
                    INSERT INTO stock_price_minute (stock_id, datetime, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (stock_dict[symbol], index.tz_localize(None).isoformat(), row['open'], row['high'], row['low'], row['close'], row['volume']))
        
            start_date = start_date + timedelta(days=7)
    except Exception as e:
            print(f"Error: {e}")

connection.commit()
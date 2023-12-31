import sqlite3
import config

connection = sqlite3.connect(config.DB_FILE)

cursor=connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS user(
        username VARCHAR2(10) NOT NULL UNIQUE,
        email_id VARCHAR2(30) NOT NULL UNIQUE,
        password VARCHAR2(30) NOT NULL UNIQUE,
        is_active char[4],
        PRIMARY KEY(username, email_id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY, 
        symbol TEXT NOT NULL UNIQUE, 
        name TEXT NOT NULL,
        exchange TEXT NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_price (
        id INTEGER , 
        stock_id INTEGER ,
        date NOT NULL,
        open NOT NULL, 
        high NOT NULL, 
        low NOT NULL, 
        close NOT NULL,  
        volume NOT NULL,
        sma_20,
        sma_50,
        rsi_14,
        PRIMARY KEY(id, stock_id)
        FOREIGN KEY(stock_id) REFERENCES stock(id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_price_minute (
        id INTEGER, 
        stock_id INTEGER,
        datetime NOT NULL,
        open NOT NULL, 
        high NOT NULL, 
        low NOT NULL, 
        close NOT NULL,  
        volume NOT NULL,
        PRIMARY KEY(id, stock_id)
        FOREIGN KEY(stock_id) REFERENCES stock(id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy(
        id INTEGER PRIMARY KEY,
        name NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_strategy (
        stock_id INTEGER NOT NULL PRIMARY KEY,
        strategy_id INTEGER NOT NULL,
        FOREIGN KEY(stock_id) REFERENCES stock (id)
        FOREIGN KEY(strategy_id) REFERENCES strategy(id)
    )
""")


strategies = ['opening_range_breakout', 'opening_range_breakdown', 'bollinger bands']

for strategy in strategies:
    cursor.execute("""
        INSERT INTO strategy (name) VALUES (?)
    """, (strategy,))

connection.commit()

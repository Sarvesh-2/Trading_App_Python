import sqlite3
import config
import alpaca_trade_api as tradeapi
from fastapi import FastAPI, Request, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from datetime import date
import tulipy, numpy
from pathlib import Path



app = FastAPI()

templates = Jinja2Templates(directory="templates")
current_date = date.today().isoformat()

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.absolute() / "static"),
    name="static",
)

@app.get("/")
def index(request: Request, msg:str=None):
    return templates.TemplateResponse("login.html", {"request": request, "msg":msg})


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    errors = []

    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
         SELECT * 
        FROM USER
        WHERE username = ? 
        AND password = ?
    """, (username, password))
    info = cursor.fetchone()

    if info is not None:
        if info['username'] == username and info['password'] == password:
            boolean = "T"
            cursor.execute("""
                UPDATE user SET is_active = ?
                WHERE username = ?;
            """, (boolean, username))
            connection.commit()

            return RedirectResponse(url=f"/stocks", status_code=303)

    else:
        errors.append("Incorrect credentials")
        return templates.TemplateResponse("login.html", {"request": request, "errors": errors})


@app.post('/register')
async def register(request: Request):
    form = await request.form()
    username = form.get("one")
    email_id = form.get("two")
    password = form.get("three")

    errors = []
    if len(password) < 6:
        errors.append("Password Should be of > 6 character,Try Again")
        return templates.TemplateResponse("login.html", {"request": request, "errors": errors})

    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO user (username, email_id, password) VALUES(?, ?, ?)
        """, (username, email_id, password))

        connection.commit()

    except sqlite3.IntegrityError:
        errors.append("User Already Exists")
        return templates.TemplateResponse("login.html", {"request": request, "errors": errors})
        
    return RedirectResponse(url=f"/?msg=Successfully Registered", status_code=303)


@app.get("/stocks")
def index(request: Request):
    stock_filter = request.query_params.get('filter', False)

    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    if stock_filter == 'new_closing_highs':
        cursor.execute("""
        SELECT * FROM(
            SELECT symbol, name, stock_id, max(close), date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            GROUP BY stock_id
            ORDER BY symbol
        ) WHERE date = (SELECT max(date) FROM stock_price)
        """)

    elif stock_filter == 'new_closing_lows':
        cursor.execute("""
            SELECT * FROM(
            SELECT symbol, name, stock_id, min(close), date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            GROUP BY stock_id
            ORDER BY symbol
            ) WHERE date = (SELECT max(date) FROM stock_price)
        """)

    elif stock_filter == 'rsi_overbought':
        cursor.execute("""
            SELECT symbol, name, stock_id, date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            WHERE rsi_14 > 70
            AND date = (SELECT max(date) FROM stock_price)
            ORDER BY symbol
        """) 
        
    elif stock_filter == 'rsi_oversold':
        cursor.execute("""
            SELECT symbol, name, stock_id, date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            WHERE rsi_14 < 30
            AND date = (SELECT max(date) FROM stock_price)
            ORDER BY symbol
        """)       

    elif stock_filter == 'above_sma_20':
        cursor.execute("""
            SELECT symbol, name, stock_id, date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            WHERE close > sma_20
            AND date = (select max(date) from stock_price)
            ORDER BY symbol
        """)  

    elif stock_filter == 'below_sma_20':
        cursor.execute("""
            SELECT symbol, name, stock_id, date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            WHERE close < sma_20
            AND date = (select max(date) from stock_price)
            ORDER BY symbol
        """)       

    elif stock_filter == 'above_sma_50':
        cursor.execute("""
            SELECT symbol, name, stock_id, date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            WHERE close > sma_50
            AND date = (select max(date) from stock_price)
            ORDER BY symbol
        """)  

    elif stock_filter == 'below_sma_50':
        cursor.execute("""
            SELECT symbol, name, stock_id, date
            FROM stock_price JOIN stock on stock.id = stock_price.stock_id
            WHERE close < sma_50
            AND date = (select max(date) from stock_price)
            ORDER BY symbol
        """) 

    else:
        cursor.execute("""
            SELECT id, symbol, name FROM stock ORDER BY symbol
        """)

    rows = cursor.fetchall()
   
    cursor.execute("""
        SELECT symbol, rsi_14, sma_20, sma_50, close
        FROM stock JOIN stock_price ON stock_price.stock_id = stock.id
        WHERE date = (SELECT max(date) from stock_price);
    """)

    indicator_rows = cursor.fetchall()
    indicator_values = {}
    for row in indicator_rows:
        indicator_values[row['symbol']] = row

    ###check for logged in or not###
    cursor.execute("""
        SELECT * 
        FROM user
        WHERE is_active = 'T';
    """)

    active = cursor.fetchone()
    errors = []
    
    if active is not None:
        return templates.TemplateResponse("index.html", {"request": request, "stocks": rows, "indicator_values": indicator_values}) 
    else:
        return RedirectResponse(url=f"/?msg=Please Login", status_code=303)

@app.get("/stock/{symbol}")
def stock_detail(request: Request, symbol):


    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM strategy
    """)

    strategies = cursor.fetchall()

    cursor.execute("""
        SELECT id, symbol, name FROM stock WHERE symbol = ?
    """, (symbol,))
    row = cursor.fetchone()

    cursor.execute("""select * FROM stock_price where stock_id = ? ORDER BY date DESC
    """, (row['id'],))

    prices = cursor.fetchall()
    
    cursor.execute("""
        SELECT * 
        FROM user
        WHERE is_active = 'T';
    """)

    active = cursor.fetchone()
    errors = []

    if active is not None:
        return templates.TemplateResponse("stock_detail.html", {"request": request, "stock": row, "bars":prices, "strategies":strategies})
    else:
       return RedirectResponse(url=f"/?msg=Please Login", status_code=303)   


@app.post("/apply_strategy")
def apply_strategy(strategy_id: int = Form(...), stock_id: int = Form(...)):
    connection = sqlite3.connect(config.DB_FILE)
    cursor = connection.cursor()
    errors = []
    try:
    
        cursor.execute("""
            INSERT INTO stock_strategy (stock_id, strategy_id) values(?, ?)
        """, (stock_id, strategy_id))

        connection.commit()

    except sqlite3.IntegrityError:
        errors.append("Stock Already Added")

    cursor.execute("""
        SELECT * 
        FROM user
        WHERE is_active = 'T';
    """)

    active = cursor.fetchone()
    errors = []
    if active is not None:
        return RedirectResponse(url=f"/strategy/{strategy_id}", status_code=303)
    else:
       return RedirectResponse(url=f"/?msg=Please Login", status_code=303)   


@app.get("/strategies")
def strategies(request: Request):
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * 
        FROM strategy
    """)
    strategies = cursor.fetchall()

    cursor.execute("""
        SELECT * 
        FROM user
        WHERE is_active = 'T';
    """)

    active = cursor.fetchone()
    errors = []
    if active is not None:
        return templates.TemplateResponse("strategies.html", {"request": request, "strategies": strategies})
    else:
       return RedirectResponse(url=f"/?msg=Please Login", status_code=303) 


@app.get("/orders")
def orders(request: Request):
    api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()


    orders = api.list_orders(status='all')

    cursor.execute("""
        SELECT * 
        FROM strategy
    """)
    strategies = cursor.fetchall()

    cursor.execute("""
        SELECT * 
        FROM user
        WHERE is_active = 'T';
    """)

    active = cursor.fetchone()
    errors = []
    if active is not None:
        return templates.TemplateResponse("orders.html", {"request": request, "orders": orders})
    else:
       return RedirectResponse(url=f"/?msg=Please Login", status_code=303)

    

@app.get("/strategy/{strategy_id}")
def strategy(request: Request, strategy_id):
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name
        FROM strategy
        where id = ?
    """, (strategy_id,))

    strategy  = cursor.fetchone()

    cursor.execute("""
        SELECT symbol, name
        FROM stock JOIN stock_strategy on stock_strategy.stock_id = stock.id
        WHERE strategy_id = ?
    """, (strategy_id,))

    stocks = cursor.fetchall()

    cursor.execute("""
        SELECT * 
        FROM user
        WHERE is_active = 'T';
    """)

    active = cursor.fetchone()
    errors = []
    if active is not None:
        return templates.TemplateResponse("strategy.html", {"request": request, "stocks": stocks, "strategy": strategy})
    else:
       return RedirectResponse(url=f"/?msg=Please Login", status_code=303)

    


@app.get('/logout')
def logout():
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    boolean = "F"

    cursor.execute("""
        SELECT * 
        FROM user
        WHERE is_active = 'T';
    """)

    active = cursor.fetchone()
    uname = active['username']

    cursor.execute("""
        UPDATE user SET is_active = ?
        where username = ? 
    """, (boolean, uname))
    connection.commit()
    return RedirectResponse(url=f"/", status_code=303)
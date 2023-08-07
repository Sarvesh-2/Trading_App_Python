import config
import alpaca_trade_api as tradeapi
from helpers import calculate_quantity


api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

symbols = ['SPY', 'IWM']

for symbol in symbols:
    api.submit_order(symbol)

    quote = api.get_last_quote(symbol)

    api.submit_order(
        symbol=symbol,
        side='buy',
        type='market',
        qty=calculate_quantity(quote.bidprice),
        time_in_force='day'
    )
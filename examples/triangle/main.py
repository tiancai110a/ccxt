import asyncio
import os
import time
from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager


import logging
import threading
import json
import order
import strategy
import pairs
import recycle
import utils

default_mid_cur ='USDT'

test_Exchange ='binance' # 测试使用的单一的交易所


good_exchange_name = [test_Exchange]


ticker_data = {}
order_data= {}
good_exchange_list = []
binance_websocket_api_manager = BinanceWebSocketApiManager()

def print_stream_data_from_stream_buffer(binance_websocket_api_manager):
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        oldest_stream_data_from_stream_buffer = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()
        if oldest_stream_data_from_stream_buffer is False:
            time.sleep(0.01)
        else:
            try:
                data = json.loads(oldest_stream_data_from_stream_buffer)
                symbol = data['data']['s']
                if symbol not in ticker_data:
                    ticker_data[symbol] ={}
                ticker_data[symbol]['bid'] = data['data']['b']
                ticker_data[symbol]['bidsize'] = data['data']['B']
                ticker_data[symbol]['ask'] = data['data']['a']
                ticker_data[symbol]['asksize'] = data['data']['A']
            except Exception:
                binance_websocket_api_manager.add_to_stream_buffer(oldest_stream_data_from_stream_buffer)

def trigger():
    time.sleep(3)
    loop = asyncio.get_event_loop()
    global good_exchange_list
    good_exchange_list = utils.get_exchange_list(good_exchange_name)
    cnt = 0
    trade_pairs = pairs.get_trade_pairs()
    while True:
        tick(loop, trade_pairs)
        time.sleep(0.01)
        cnt = cnt + 1 
        if cnt >= 5000:
            cnt = 0
            time.sleep(1) # 等一秒 卡住当前所有任务,回收完在进行下一次
            for exchange in good_exchange_list:
                recycle.recycle(exchange, order_data)
    time.sleep(10)

def tick(loop, trade_pairs):
    global good_exchange_list
    taskList = []
    for exchange in good_exchange_list:
        for trade_symbol in trade_pairs:
            taskList.append(strategy.find_trade_chance(exchange, trade_symbol[0], trade_symbol[1], default_mid_cur,ticker_data, order_data))
    loop.run_until_complete(asyncio.gather(*taskList))




worker_thread = threading.Thread(target=print_stream_data_from_stream_buffer, args=(binance_websocket_api_manager,))
worker_thread.start()


print('before proxy ip is {}'.format(utils.get_host_ip()))
utils.set_proxy()
newmarkets = []
for p in pairs.get_markets():
    a,b = p.split("/")
    newmarkets.append(a+b)

marketsticker_stream_id = binance_websocket_api_manager.create_stream(["bookTicker"], newmarkets)
trigger()

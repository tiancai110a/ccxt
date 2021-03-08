# ws 推送行情 
# 回撤熔断 不能一直亏
# 成交推送微信, 可视化资产曲线
# 被动挂单  延时取消 未成功的不当时取消
# 自动均仓,平衡基础货币
# ...
import asyncio
import os
import time
import socket
from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
import ccxt.async_support as ccxta

import logging
import threading
import json
import order
import strategy
import pairs
default_mid_cur ='USDT'

test_Exchange ='binance' # 测试使用的单一的交易所


good_exchange_name = [test_Exchange]

config_key = dict()
# binance testnet 
config_key['binance'] = ['i3bEQ2PECV68BDMRXuQO1nWvn8WNr2mXa1RCJs8MB1GK6Ge0qcxjrOomutR0QkU5','QlFZ6xbAQ6myXWXYoBKrwXwbuLM57tSRxNwxOWUqaSFsI3GJCzZ21BoI40trTknU']

proxy_flag = False
tickerData = {}
orderData= {}

binance_websocket_api_manager = BinanceWebSocketApiManager()

def print_stream_data_from_stream_buffer(binance_websocket_api_manager):
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        oldest_stream_data_from_stream_buffer = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()
        time.sleep(0.01)
        if oldest_stream_data_from_stream_buffer is False:
            time.sleep(0.01)
        else:
            try:
                data = json.loads(oldest_stream_data_from_stream_buffer)
                symbol = data['data']['s']
                if symbol not in tickerData:
                    tickerData[symbol] ={}
                tickerData[symbol]['bid'] = data['data']['b']
                tickerData[symbol]['bidsize'] = data['data']['B']
                tickerData[symbol]['ask'] = data['data']['a']
                tickerData[symbol]['asksize'] = data['data']['A']
            except Exception:
                binance_websocket_api_manager.add_to_stream_buffer(oldest_stream_data_from_stream_buffer)



def set_proxy():
    if proxy_flag:
        os.environ.setdefault('http_proxy', 'http://127.0.0.1:1087')
        os.environ.setdefault('https_proxy', 'http://127.0.0.1:1087')





# 设置交易所key
def set_exchange_key(exchange,good_list):
    if exchange.id in good_list:
        exchange.apiKey = config_key[exchange.id][0]
        exchange.secret = config_key[exchange.id][1]
        print('set_exchange_key name is {},key is {},secret is {}'.format(exchange.name,exchange.apiKey,exchange.secret))
    else:
        print('set_exchange_key name is {} no key'.format(exchange.name))


def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


# 获取指定交易所列表
# 获取指定交易所列表
def get_exchange_list(good_list):
    exchange_list = []
    for exchange_name in good_list:
        exchange = getattr(ccxta,exchange_name)()
        if exchange:
            exchange.enableRateLimit = True
            exchange_list.append(exchange)
            set_exchange_key(exchange ,good_list)
    return exchange_list

good_exchange_list= []
def trigger():
    time.sleep(3)
    loop = asyncio.get_event_loop()
    global good_exchange_list
    good_exchange_list = get_exchange_list(good_exchange_name)
    while True:
        tick(loop)
        time.sleep(0.01)
    time.sleep(10)

def tick(loop):
    global good_exchange_list
    taskList = []
    for exchange in good_exchange_list:
        for trade_symbol in pairs.trade_pairs:
            taskList.append(strategy.find_trade_chance(exchange, trade_symbol[0], trade_symbol[1], default_mid_cur,tickerData, orderData))
    loop.run_until_complete(asyncio.gather(*taskList))




worker_thread = threading.Thread(target=print_stream_data_from_stream_buffer, args=(binance_websocket_api_manager,))
worker_thread.start()


print('before proxy ip is {}'.format(get_host_ip()))
set_proxy()
newmarkets = []
for p in pairs.markets:
    a,b = p.split("/")
    newmarkets.append(a+b)

marketsticker_stream_id = binance_websocket_api_manager.create_stream(["bookTicker"], newmarkets)
trigger()

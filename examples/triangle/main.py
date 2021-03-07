# TODO
# ws 推送行情 
# 手续费
# 回撤熔断 不能一直亏
# 成交推送微信, 可视化资产曲线
# 被动挂单  延时取消 未成功的不当时取消
# 跨交易所三角套利
# 多空双持 用来做套保的合约同时也用来做套利 或者加入合约平仓或者爆仓的停止机制,或者做平仓套利
# 自动均仓,平衡基础货币
# ...
import asyncio
import os
import time
import socket
from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
import ccxt.async_support as ccxta

from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
import logging
import threading
import json
import order
import strategy

test_Exchange ='binance' # 测试使用的单一的交易所

# good_coin = ['ETH', 'XRP', 'BCH', 'EOS', 'XLM', 'EOS', 'ADA', 'XMR', 'TRX', 'BNB', 'ONT', 'NEO', 'DCR']

good_exchange_name = [test_Exchange]
good_coin = ['ETH', 'XRP', 'BCH', 'EOS', 'XLM', 'EOS', 'ADA', 'XMR', 'BNB', 'ONT', 'NEO', 'DCR']
#good_coin = ['ADA']

# quote_mid p1 BTC/USDT
# base_quote p2 EOS/BTC
# base_mid p3 EOS/USDT
default_base_cur = 'ADA'
default_quote_cur = 'BTC'
default_mid_cur = 'USDT'



config_key = dict()
# binance testnet 
#config_key['binance'] = ['AWuYhmjZNPfgtt6XWshQe2zZ6jtTiSqrY5IsZY7O4HjDBG9A6flJ2hbbApMpa3Ln','qHHaevrs3W1Qiy7jrx8aqoQ5f4BM2wXrcJzUXqWZSiNwSd6SrBRXjKSdzAM9H7hv'] 
config_key['binance'] = ['i3bEQ2PECV68BDMRXuQO1nWvn8WNr2mXa1RCJs8MB1GK6Ge0qcxjrOomutR0QkU5','QlFZ6xbAQ6myXWXYoBKrwXwbuLM57tSRxNwxOWUqaSFsI3GJCzZ21BoI40trTknU']
# test_Exchange testnet
#config_key[test_Exchange] = ['I4OAaJJxB2Elpb3SX8pekX0S','BnQ9N4dAACnkxT-tR3dRNWJ684WbCkkA58oKQf_okA0MkTqD'] 


# good_exchange_name = ['binance', 'fcoin', 'gateio', 'huobipro', 'kucoin', 'okex']
# good_exchange_name = ['binance', 'fcoin', 'gateio', 'huobipro', 'kucoin', 'okex','bcex','bibox','bigone','bitfinex','bitforex',
#                       'bithumb','bitkk','cex','coinbase','coinex','cointiger','exx','gdax','gemini','hitbtc','rightbtc',
#                       'theocean','uex']
has_config_exchange = [test_Exchange]
test_Exchange ='binance' # 测试使用的单一的交易所


proxy_flag = False
tickerData = {}
orderData= {}
# logging.basicConfig(level=logging.DEBUG,
#                     filename=os.path.basename(__file__) + '.log',
#                     format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
#                     style="{")


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
def set_exchange_key(exchange):
    if exchange.id in has_config_exchange:
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
            set_exchange_key(exchange)
    return exchange_list

good_exchange_list= []
def trigger():
    time.sleep(3)
    loop =  asyncio.get_event_loop()
    global good_exchange_list
    good_exchange_list = get_exchange_list(good_exchange_name)
    while True:
        tick(loop)
        time.sleep(0.01)
    time.sleep(10)

def tick(loop):
    global good_exchange_list
    taskList = []  
    for symbol in good_coin:
        for exchange in good_exchange_list:
            taskList.append(strategy.find_trade_chance(exchange, symbol, default_quote_cur, default_mid_cur,tickerData, orderData))
    loop.run_until_complete(asyncio.gather(*taskList))




worker_thread = threading.Thread(target=print_stream_data_from_stream_buffer, args=(binance_websocket_api_manager,))
worker_thread.start()


print('before proxy ip is {}'.format(get_host_ip()))
set_proxy()
markets = []
for base in good_coin:
    p1_trade_pair = default_quote_cur +  default_mid_cur #P1 symbol
    p2_trade_pair = base + default_quote_cur #P2 symbol
    p3_trade_pair = base + default_mid_cur #P3 symbol
    markets.append(p1_trade_pair) #TODO 去重
    markets.append(p2_trade_pair) #TODO 去重
    markets.append(p3_trade_pair) #TODO 去重

print(markets)
ticker_stream_id = binance_websocket_api_manager.create_stream(["bookTicker"], markets)
# print('after proxy ip is {}'.format(get_host_ip()))
trigger()
# 在good_coin作为base，quote=BTC,mid=USDT 在good_exchange_list交易所列表中寻找套利机会

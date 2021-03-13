# 检测所有交易对,发现机会
import threading
import time
import pairs
import json
from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
cost_P1 = 0.0075
cost_P2 = 0.0075
cost_P3 = 0.0075


slippage = 0.0075


ticker_data ={}
binance_websocket_api_manager = BinanceWebSocketApiManager()
registry = CollectorRegistry()
g = Gauge('unit_proifit_diff', 'profit', registry=registry)

def print_stream_data_from_stream_buffer(binance_websocket_api_manager):
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        oldest_stream_data_from_stream_buffer = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()
        time.sleep(1)
        if oldest_stream_data_from_stream_buffer is False:
            time.sleep(1)
        else:
            try:
                data = json.loads(oldest_stream_data_from_stream_buffer)
                if 'data' not in data:
                    continue
                symbol = data['data']['s']
                if symbol not in ticker_data:
                    ticker_data[symbol] ={}
                ticker_data[symbol]['bid'] = data['data']['b']
                ticker_data[symbol]['bidsize'] = data['data']['B']
                ticker_data[symbol]['ask'] = data['data']['a']
                ticker_data[symbol]['asksize'] = data['data']['A']
                
            except Exception as e:
                print('print_stream_data_from_stream_buffer e is {}'.format(e.args[0]))
                binance_websocket_api_manager.add_to_stream_buffer(oldest_stream_data_from_stream_buffer)



def calc_chance(base='EOS',quote='BTC',mid='USDT', ticker_data={}):
    p1_trade_pair = quote +  mid #P1 symbol
    p2_trade_pair = base + quote #P2 symbol
    p3_trade_pair = base + mid #P3 symbol

    p1_trade_pair_order = quote + "/" + mid #P1 symbol
    p2_trade_pair_order = base + "/" +quote #P2 symbol
    p3_trade_pair_order = base + "/" +mid #P3 symbol

    if p1_trade_pair not in ticker_data or p2_trade_pair not in ticker_data or p3_trade_pair not in ticker_data:
        return 

    if len(ticker_data) < 3:
        print("ticker_data<3")
        return
    # P1
    if p1_trade_pair not in ticker_data:
        return
    price_p1_bid1 = float(ticker_data[p1_trade_pair]['bid'] if ticker_data[p1_trade_pair]['bid'] else None)
    price_p1_ask1 = float(ticker_data[p1_trade_pair]['ask'] if ticker_data[p1_trade_pair]['ask'] else None)

    size_p1_bid1 =  float(ticker_data[p1_trade_pair]['bidsize'] if ticker_data[p1_trade_pair]['bidsize'] else None)
    size_p1_ask1 =  float(ticker_data[p1_trade_pair]['asksize'] if ticker_data[p1_trade_pair]['asksize'] else None)
   
    if p2_trade_pair not in ticker_data:
        return
    #print(price_p1_bid1, price_p1_ask1, size_p1_bid1,size_p1_ask1)
    # P2
    price_p2_bid1 = float(ticker_data[p2_trade_pair]['bid'] if ticker_data[p2_trade_pair]['bid'] else None)
    price_p2_ask1 = float(ticker_data[p2_trade_pair]['ask'] if ticker_data[p2_trade_pair]['ask'] else None)
    size_p2_bid1 = float(ticker_data[p2_trade_pair]['bidsize'] if ticker_data[p2_trade_pair]['bidsize'] else None)
    size_p2_ask1 = float(ticker_data[p2_trade_pair]['asksize'] if ticker_data[p2_trade_pair]['asksize'] else None)
   

    if p3_trade_pair not in ticker_data:
        return
    # P3
    price_p3_bid1 = float(ticker_data[p3_trade_pair]['bid'] if ticker_data[p3_trade_pair]['bid'] else None)
    price_p3_ask1 = float(ticker_data[p3_trade_pair]['ask'] if ticker_data[p3_trade_pair]['ask'] else None)

    size_p3_bid1 = float(ticker_data[p3_trade_pair]['bidsize'] if ticker_data[p3_trade_pair]['bidsize'] else None)
    size_p3_ask1 = float(ticker_data[p3_trade_pair]['asksize'] if ticker_data[p3_trade_pair]['asksize'] else None)
   

    if price_p1_bid1 is None or \
    price_p1_ask1 is None or \
    size_p1_bid1 is None or \
    size_p1_ask1 is None:
        print("symbol not avilable", p1_trade_pair)
        return


    if price_p2_bid1 is None or \
    price_p2_ask1 is None or \
    size_p2_bid1 is None or \
    size_p2_ask1 is None:
        print("symbol not avilable", p2_trade_pair)
        return

    if price_p3_bid1 is None or \
    price_p3_ask1 is None or \
    size_p3_bid1 is None or \
    size_p3_ask1 is None:
          print("symbol not avilable", p3_trade_pair)
          return

    positive_buy = (1 + slippage) * price_p1_ask1 * price_p2_ask1  * (1 + cost_P1) * (1 + cost_P2)
    positive_sell  =  price_p3_bid1 * (1 - slippage) / (1 + cost_P3)

    negative_sell = (1 - slippage) * price_p1_bid1 * price_p2_bid1 /((1 + cost_P1) * (1 + cost_P2))
    negative_buy = price_p3_ask1 * (1 + slippage) * (1 + cost_P3)
    g.set(float((positive_sell - positive_buy) / price_p3_ask1 ))
    res =push_to_gateway('localhost:9091', job='triangle_'+mid+'-' + quote+'-' + base + "_p", registry=registry)


    g.set(float((negative_sell - negative_buy) / price_p3_ask1))
    res =push_to_gateway('localhost:9091', job='triangle_'+ mid+'-' + quote+'-' + base + "_n", registry=registry)

    if positive_sell - positive_buy > 0:
        print("{}-{}-{} positive unit profit:{}".format(mid,quote,base, positive_sell - positive_buy))
    if negative_sell - negative_buy > 0:
        print("{}-{}-{} nagative unit profit:{}".format(mid,quote,base, negative_sell - negative_buy))

    
worker_thread = threading.Thread(target=print_stream_data_from_stream_buffer, args=(binance_websocket_api_manager,))
worker_thread.start()

newmarkets = []
for p in pairs.get_markets():
    a,b = p.split("/")
    newmarkets.append(a+b)

marketsticker_stream_id = binance_websocket_api_manager.create_stream(["bookTicker"], newmarkets)
while True:
    for l in pairs.get_trade_pairs():
        calc_chance(l[0],l[1],'USDT',ticker_data)
    time.sleep(1)





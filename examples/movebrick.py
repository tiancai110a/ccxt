#-*- coding: utf-8 -*-
# 找出每个指定交易对在指定交易所中价差最大的2个，可以在这2个交易所进行搬砖套利

import ccxt
import time
import os
import asyncio

import nest_asyncio
nest_asyncio.apply()

good_coin = ['BTC', 'ETH', 'XRP', 'BCH', 'EOS', 'XLM', 'LTC', 'ADA', 'XMR', 'TRX', 'BNB', 'ONT', 'NEO', 'DCR']
# good_coin = ['BTC', 'ETH', 'XRP']
good_exchange_name = ['binance', 'huobipro', 'okex']

def_quote = 'USDT'
delay = 1
totalprofit = 0

all_exchange = ccxt.exchanges

# print ('gateio markets is {}'.format(gate.markets))



def set_proxy():
    os.environ.setdefault('http_proxy', 'http://127.0.0.1:1087')
    os.environ.setdefault('https_proxy', 'http://127.0.0.1:1087')


#获取指定交易所列表
def get_exchange_list(good_list):
    exchange_list = []
    for exchange_name in good_list:
        exchange = getattr(ccxt,exchange_name)()
        if exchange :
            exchange_list.append(exchange)
            try:
                exchange.load_markets()  #TODO 需不需要每次都load
            except Exception as e:
                print('---get_exchange_list load_markets exception is {},exchange is {}'.format(e.args[0], exchange.name))
            try:
                exchange.set_sandbox_mode(True)
            except Exception as e:
                print('---get_exchange_list set_sandbox_mode exception is {},exchange is {}'.format(e.args[0], exchange.name))
    return exchange_list 


async def fetchOrder(exchange,symbol):
    return  exchange.fetch_order_book(symbol)

# 低买高卖，先去ask1卖一最低（卖的最便宜的bid1）的买入，立刻去bid1买一最高（买起来最贵的bid1）卖出
async def find_trade_object(symbol,exchange_list):
    pass
    max_bid1 = 0
    min_ask1 = 10000
    bid_exchange = None
    ask_exchange = None
    bid_time = None
    ask_time = None
    bid_amount = None
    ask_amount = None
    print('async version current symbol is {}'.format(symbol))
    loop = asyncio.get_event_loop()
    for exchange in exchange_list:
        #获取市场交易对数据
        if exchange.markets is None:
            try:
                exchange.load_markets()
            except Exception as e:
                print('---find_trade_object load_markets exception is {},exchange is {},symbol is {}'.format(e.args[0],exchange.name,symbol))
                continue
            print('exchange markets {} is None'.format(exchange))
            continue
        try:
            task = loop.create_task(fetchOrder(exchange, symbol))
            loop.run_until_complete(task)
            orderbook =  task.result() 
        except Exception as e:
            print('-------find_trade_object fetch_order_book exception is {},exchange is {},symbol is {}'.format(e.args[0], exchange.name, symbol))
            continue
        date_time = exchange.last_response_headers['Date']
        bid1 = orderbook['bids'][0][0] if len(orderbook['bids']) > 0 else None
        bid1_amount = orderbook['bids'][0][1] if len(orderbook['bids']) > 0 else None
        ask1 = orderbook['asks'][0][0] if len(orderbook['asks']) > 0 else None
        ask1_amount = orderbook['asks'][0][1] if len(orderbook['asks']) > 0 else None
        #print('exchange {} bid1 ask1 is \n---- {},{}, {},{},date_time is {}'.format(exchange.name, bid1, bid1_amount,ask1, ask1_amount, date_time))
        #比较价格并保存 最低卖一价和最高买一价
        #找到最贵的买一，进行卖操作
        if bid1 and (bid1 > max_bid1):
            max_bid1 = bid1
            bid_exchange = exchange
            bid_time = date_time
            bid_amount = bid1_amount
            #print('get new max_bid1 is {},exchange is {},date_time is {}'.format(max_bid1, exchange.name, date_time))
        #找到最便宜的卖一，进行买操作
        if ask1 and (ask1 < min_ask1):
            min_ask1 = ask1
            ask_exchange = exchange
            ask_time = date_time
            ask_amount = ask1_amount
            #print('get new min_ask1 is {},exchange is {},date_time is {}'.format(min_ask1, exchange.name, date_time))
        #time.sleep(delay)
                
    if bid_exchange and ask_exchange:
        price_diff = max_bid1 - min_ask1
        percent = price_diff / min_ask1 * 100
        trade_volume = min(ask_amount,bid_amount)
        profits = min_ask1 * trade_volume * percent/100
        if price_diff < 0:
            #print('{}:,no pair to make money'.format(symbol))
            return min_ask1, None, max_bid1, None
        print('\n\n++++++++ symbol {} find good exchange,\n percent {}%,price_diff {},trade_volume {},profits {},'
        '\nbuy at {},{},{},{},\nsell at {},{},{},{}'.
        format(symbol, percent, price_diff, trade_volume, profits, min_ask1, ask_amount, min_ask1 * ask_amount, ask_exchange.name,
        max_bid1, bid_amount, max_bid1*bid_amount, bid_exchange.name))
        global totalprofit
        totalprofit =totalprofit +profits+1
        return percent, price_diff, trade_volume, profits, min_ask1, ask_amount, min_ask1 * ask_amount, ask_exchange.name, ask_time, \
            max_bid1,bid_amount,max_bid1*bid_amount,bid_exchange.name,bid_time
    else :
        #print('\n\n******------ symbol {} not find good exchange'.format(symbol))
        return min_ask1, None, max_bid1, None
        

def tick():
        tasks = []
        set_proxy()
        for base in good_coin:
            symbol = base + '/' + def_quote
            tasks.append(find_trade_object(symbol,good_exchange_list))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(tasks))
        global totalprofit
        print('totalprofits is {}'.format(totalprofit))


if __name__ == '__main__':
    good_exchange_list = get_exchange_list(good_exchange_name)

    print('exchange list is {},\ncoin list is {},\nquote is {}'.format(good_exchange_name, good_coin, def_quote))
    while True:
        time.sleep(delay)
        tick()
    
    print('-----------all over---------------')


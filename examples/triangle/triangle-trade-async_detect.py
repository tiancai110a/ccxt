import asyncio
import os
import time
import socket
import ccxtpro
from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
import ccxt.async_support as ccxta

from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
import logging
import threading
import json



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


"""
    三角套利demo2：寻找三角套利空间，包含下单模块，异步请求处理版
    交易对：用一种资产（quote currency）去定价另一种资产（base currency）,比如用比特币（BTC）去定价莱特币（EOS），
    就形成了一个EOS/BTC的交易对，
    交易对的价格代表的是买入1单位的base currency（比如EOS）
    需要支付多少单位的quote currency（比如BTC），
    或者卖出一个单位的base currency（比如EOS）
    可以获得多少单位的quote currency（比如BTC）。
    中间资产mid currency可以是USDT等稳定币
"""
# quote_mid p1 BTC/USDT
# base_quote p2 EOS/BTC
# base_mid p3 EOS/USDT
default_base_cur = 'EOS'
default_quote_cur = 'BTC'
default_mid_cur = 'USDT'

test_Exchange ='binance' # 测试使用的单一的交易所

cost_P1 = 0.00075
cost_P2 = 0.00075
cost_P3 = 0.00075


slippage = 0
delay = 1
# 最小下单价格(usdt)
min_notional = 10

# good_exchange_name = ['binance', 'fcoin', 'gateio', 'huobipro', 'kucoin', 'okex']
# good_exchange_name = ['binance', 'fcoin', 'gateio', 'huobipro', 'kucoin', 'okex','bcex','bibox','bigone','bitfinex','bitforex',
#                       'bithumb','bitkk','cex','coinbase','coinex','cointiger','exx','gdax','gemini','hitbtc','rightbtc',
#                       'theocean','uex']
# good_coin = ['ETH', 'XRP', 'BCH', 'EOS', 'XLM', 'EOS', 'ADA', 'XMR', 'TRX', 'BNB', 'ONT', 'NEO', 'DCR']

good_exchange_name = [test_Exchange]
#good_coin = ['ETH', 'XRP', 'BCH', 'EOS', 'XLM', 'EOS', 'ADA', 'XMR', 'TRX', 'BNB', 'ONT', 'NEO', 'DCR']
good_coin = ['ETH', 'XRP', 'BCH', 'EOS', 'XLM', 'LTC', 'ADA', 'XMR', 'TRX', 'BNB', 'ONT', 'NEO', 'DCR', 'LBA', 'RATING']
#good_coin = ['EOS']


has_config_exchange = [test_Exchange]
config_key = dict()
# binance testnet 
#config_key['binance'] = ['AWuYhmjZNPfgtt6XWshQe2zZ6jtTiSqrY5IsZY7O4HjDBG9A6flJ2hbbApMpa3Ln','qHHaevrs3W1Qiy7jrx8aqoQ5f4BM2wXrcJzUXqWZSiNwSd6SrBRXjKSdzAM9H7hv'] 
config_key['binance'] = ['i3bEQ2PECV68BDMRXuQO1nWvn8WNr2mXa1RCJs8MB1GK6Ge0qcxjrOomutR0QkU5','QlFZ6xbAQ6myXWXYoBKrwXwbuLM57tSRxNwxOWUqaSFsI3GJCzZ21BoI40trTknU']
# test_Exchange testnet
#config_key[test_Exchange] = ['I4OAaJJxB2Elpb3SX8pekX0S','BnQ9N4dAACnkxT-tR3dRNWJ684WbCkkA58oKQf_okA0MkTqD'] 


# 交易相关常量
# 订单交易量吃单比例 压这个比例没啥用
order_ratio = 1
# 账户资金保留比例
reserve_ratio_base = 0
reserve_ratio_quote = 0
reserve_ratio_mid = 0

# 最小成交量比例设定
min_trade_percent = 0.2

# 是否真正下单
order_flag = False

sandbox_mode = True

proxy_flag = False

ticker_data ={}

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
        if oldest_stream_data_from_stream_buffer is False:
            time.sleep(0.01)
        else:
            try:
                data = json.loads(oldest_stream_data_from_stream_buffer)
                symbol = data['data']['s']
                ticker_data[symbol] ={}
                ticker_data[symbol]['bid'] = data['data']['b']
                ticker_data[symbol]['bidsize'] = data['data']['B']
                ticker_data[symbol]['ask'] = data['data']['a']
                ticker_data[symbol]['asksize'] = data['data']['A']
                time.sleep(0.01)
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


# 在指定交易所寻找三角套利机会，根据P3与P2/P1大小关系进行套利，暂不考虑滑点和手续费，目标保持base,quote数量不变，使mid数量增多
async def find_trade_chance(exchange,base='EOS',quote='BTC',mid='USDT'):
    #print('-----find_trade_chance开始在交易所{}寻找三角套利机会,base:{},quote:{},mid:{}'.format(exchange.name,base,quote,mid))
    # try:
    #     markets =  await exchange.load_markets()
    #     for market in markets:
    #         print('+++++++++++',market)
    # except Exception as e:
    #     print('load_markets e is {} ,exchange is {}'.format(e.args[0],exchange.name))
    #     await exchange.close()
    #     return
    p1_trade_pair = quote +  mid #P1 symbol
    p2_trade_pair = base + quote #P2 symbol
    p3_trade_pair = base + mid #P3 symbol

    p1_trade_pair_order = quote + "/" + mid #P1 symbol
    p2_trade_pair_order = base + "/" +quote #P2 symbol
    p3_trade_pair_order = base + "/" +mid #P3 symbol


    print('begin  ================>>>>>>>>   P1:{},P2:{},P3: {}'.format(p1_trade_pair,p2_trade_pair,p3_trade_pair))
    if len(ticker_data) < 3:
        return

    if  p1_trade_pair not in  ticker_data.keys():
        print("{}  data not exist".format(p3_trade_pair))
        return

    if  p2_trade_pair not in ticker_data.keys():
        print("{} data not exist".format(p2_trade_pair))
        return
        
    if p3_trade_pair not in ticker_data.keys():
        print("{} data not exist".format(p3_trade_pair))
        return
    # P1
    price_p1_bid1 = float(ticker_data[p1_trade_pair]['bid'] if ticker_data[p1_trade_pair]['bid'] else 0)
    price_p1_ask1 = float(ticker_data[p1_trade_pair]['ask'] if ticker_data[p1_trade_pair]['ask'] else 0)

    size_p1_bid1 =  float(ticker_data[p1_trade_pair]['bidsize'] if ticker_data[p1_trade_pair]['bidsize'] else 0)
    size_p1_ask1 =  float(ticker_data[p1_trade_pair]['asksize'] if ticker_data[p1_trade_pair]['asksize'] else 0)
   
    #print(price_p1_bid1, price_p1_ask1, size_p1_bid1,size_p1_ask1)
    # # P3
    price_p2_bid1 = float(ticker_data[p2_trade_pair]['bid'] if ticker_data[p2_trade_pair]['bid'] else 0)
    price_p2_ask1 = float(ticker_data[p2_trade_pair]['ask'] if ticker_data[p2_trade_pair]['ask'] else 0)

    size_p2_bid1 = float(ticker_data[p2_trade_pair]['bidsize'] if ticker_data[p2_trade_pair]['bidsize'] else 0)
    size_p2_ask1 = float(ticker_data[p2_trade_pair]['asksize'] if ticker_data[p2_trade_pair]['asksize'] else 0)
   
    # # P3
    price_p3_bid1 = float(ticker_data[p3_trade_pair]['bid'] if ticker_data[p3_trade_pair]['bid'] else 0)
    price_p3_ask1 = float(ticker_data[p3_trade_pair]['ask'] if ticker_data[p3_trade_pair]['ask'] else 0)

    size_p3_bid1 = float(ticker_data[p3_trade_pair]['bidsize'] if ticker_data[p3_trade_pair]['bidsize'] else 0)
    size_p3_ask1 = float(ticker_data[p3_trade_pair]['asksize'] if ticker_data[p3_trade_pair]['asksize'] else 0)
   

    if price_p1_bid1 == 0 or \
    price_p1_ask1 == 0 or \
    size_p1_bid1 == 0 or \
    size_p1_ask1 == 0:
        print("symbol not avilable", p1_trade_pair)
        return


    if price_p2_bid1 == 0 or \
    price_p2_ask1 == 0 or \
    size_p2_bid1 == 0 or \
    size_p2_ask1 == 0:
        print("symbol not avilable", p2_trade_pair)
        return

    if price_p3_bid1 == 0 or \
    price_p3_ask1 == 0 or \
    size_p3_bid1 == 0 or \
    size_p3_ask1 == 0:
          print("symbol not avilable", p3_trade_pair)
          return

    # if exchange.has['fetchTradingFees']:
    #     fees = exchange.fetchTradingFees(code, since, limit, params)
    # else:
    #     raise Exception (exchange.id + ' does not have the fetch_deposits method')
    #date_time = exchange.last_response_headers['Date']

    #检查正循环套利
    '''
        三角套利的基本思路是，用两个市场（比如BTC/USDT，EOS/USDT）的价格（分别记为P1，P2），
        计算出一个公允的EOS/BTC价格（P2/P1），如果该公允价格跟实际的EOS/BTC市场价格（记为P3）不一致，
        就产生了套利机会
        P3<P2/P1
        操作：买-卖/买
        价格条件提交：p2_ask1卖1 < p3_bid1买1/p1_ask1卖1
        交易量Q3:三者中取最小下单量，单位要统一为P3交易对的个数
        利润：Q3*P1*(P2/P1-P3)
    '''
    # try:
    #     balance = await exchange.fetch_balance()
    # except Exception as e:
    #     print('-------find_trade_object fetch_balance exception is {}'.format(e.args[0]))
    #     await exchange.close()
    #     return 
    # if  base not in  balance.keys():
    #     print("{} balance not exist".format(base))
    #     return

    # if  quote not in balance.keys():
    #     print("{} balance not exist".format(quote))
    #     return
        
    # if mid not in balance.keys():
    #     print("{} balance not exist".format(mid))
    #     return


    # free_base = balance[base]['free'] if balance[base]['free'] else 0
    # free_quote = balance[quote]['free'] if balance[quote]['free'] else 0
    # free_mid = balance[mid]['free'] if balance[mid]['free'] else 0

    #print(p1_trade_pair,p2_trade_pair, p3_trade_pair, "free:",free_base, free_quote,free_mid)
    positive_buy = (1 + slippage) * price_p1_ask1 * price_p2_ask1  * (1 + cost_P1) * (1 + cost_P2)
    positive_sell  =  price_p3_bid1 * (1 - slippage) * (1 - cost_P3)

    negative_sell = (1-slippage) * price_p1_bid1 * price_p2_bid1 / (1 + cost_P1) * (1 + cost_P2)
    negative_buy = price_p3_ask1 * (1 + slippage) * (1 + cost_P3)
    if positive_sell - positive_buy >0 or negative_sell - negative_buy >0:
        print(p1_trade_pair,p2_trade_pair, p3_trade_pair,"positive unit profit:", positive_sell - positive_buy)
        print(p1_trade_pair,p2_trade_pair, p3_trade_pair,"nagative unit profit", negative_sell - negative_buy)
    # if positive_buy < positive_sell:
    #     base_size = get_buy_size(free_base, free_quote, free_mid, size_p2_ask1, size_p1_ask1, 
    #                                 price_p2_ask1, price_p1_ask1)
    #     base_size = round(base_size ,2)
    #     #base_size 个eos 要拿这么多个btc来买
    #     quote_size = round(base_size * price_p2_ask1 * (1 + cost_P2)  ,6)
    #     # quote_size这么多个btc要拿这么多个usdt来买
    #     mid_size = quote_size *  price_p1_ask1 / (1 + cost_P1)

    #     # base_size 这么多个eos 卖出能得到这么多个usdt
    #     usdt_collect =  base_size * price_p3_bid1 *  (1 - cost_P3)

    #     print("p1:{}, size:{},amount:{} ,p2:{}, size:{} ,amount:{},p3: {} , size:{}".format(
    #     p1_trade_pair, quote_size, usdt_collect, 
    #     p2_trade_pair, base_size,base_size*price_p2_bid1,
    #     p3_trade_pair, mid_size
    #     ))

        
    #     if mid_size  <= min_notional:
    #         print("{} balance min_notional error: ,balance:{}".format(p1_trade_pair,mid_size))
    #         return
    #     if quote_size  <= 0.001:
    #         print("{} balance min_notional error: ,balance:{}".format(p2_trade_pair,quote_size * price_p2_bid1))
    #         return

    #     if base_size <= 0.001:
    #         print("{} balance min_notional error: ,balance:{}".format(p3_trade_pair,base_size * price_p3_ask1))
    #         return

    #     # 价格差值
    #     price_diff =  positive_sell - positive_buy
    #     profit = base_size * price_diff * price_p3_bid1

    #     print('++++++发现正套利机会 profit is {}(USDT), {} trade_size:{} ,{} trade_size: {} ,{} trade_size:{}, time: {}\n\n'.format(
    #         profit,mid, mid_size, quote, quote_size, base , base_size , date_time))
    #     # 开始正循环套利
    #     if order_flag:
    #         await postive_trade(exchange, p2_trade_pair_order, p3_trade_pair_order, p1_trade_pair_order,mid_size,quote_size, base_size, price_p2_ask1,
    #                     price_p3_bid1, price_p1_ask1)
    #     await exchange.close()
        # 检查逆循环套利
        # '''
        #     P3>P2/P1
        #     操作：卖-买/卖
        #     价格条件：p2_bid1买1 > p3_ask1卖1/p1_bid1买1
        #     交易量Q3:三者中取最小下单量
        #     利润：Q3*P1*(P3-P2/P1)
        # '''

    # if negative_sell > negative_buy:
    #     base_size = get_sell_size(free_base, free_quote, free_mid, size_p2_bid1, size_p3_ask1, price_p3_ask1, price_p2_ask1)
    #     base_size = round(base_size ,2)
    #     #base_size 个eos 卖出得到这么多个btc
    #     quote_size =round( base_size * price_p2_bid1 / (1 + cost_P2) , 6)
        

    #     #这么多个btc 卖掉能产生这么多个usdt
    #     usdt_collect =  quote_size * price_p1_bid1 /  (1 + cost_P1)


    #     # 要买 base_size 个 eos 需要这么多个usdt
    #     mid_size = base_size *  price_p3_ask1 * (1+ cost_P3)


    #     print("p1:{}, size:{},amount:{} ,p2:{}, size:{} ,amount:{},p3: {} , size:{}".format(
    #     p1_trade_pair, quote_size, usdt_collect, 
    #     p2_trade_pair, base_size,base_size*price_p2_bid1,
    #     p3_trade_pair, mid_size
    #     ))
        
    #     if mid_size  <= min_notional:
    #         print("{} balance min_notional error: ,balance:{}".format(p1_trade_pair,mid_size))
    #         return
    #     if quote_size  <= 0.0001:
    #         print("{} balance min_notional error: ,balance:{}".format(p2_trade_pair,quote_size * price_p1_ask1))
    #         return

    #     if base_size <= 0.01:
    #         print("{} balance min_notional error: ,balance:{}".format(p3_trade_pair,base_size * price_p3_ask1))
    #         return



    #     price_diff = negative_sell -  negative_buy
    #     # 单位usdt
    #     profit = base_size * price_diff * price_p3_ask1

    #     print('++++++发现负套利机会 profit is {}(USDT), {} trade_size:{} ,{} trade_size: {} ,{} trade_size:{}, time: {}\n\n'.format(
    #         profit,mid, mid_size, quote, quote_size, base , base_size , date_time))
    #     # 开始逆循环套利
    #     if order_flag:
    #         await negative_trade(exchange, p2_trade_pair_order, p3_trade_pair_order, p1_trade_pair_order, mid_size, quote_size, base_size, price_p2_bid1,price_p2_ask1,price_p3_ask1, price_p1_bid1)
    #     await exchange.close()
    # else:
    #     await exchange.close()

'''
    正循环套利
    正循环套利的顺序如下：
    先去EOS/BTC吃单买入EOS，卖出BTC，然后根据EOS/BTC的成交量，使用多线程，
    同时在EOS/USDT和BTC/USDT市场进行对冲。EOS/USDT市场吃单卖出EOS，BTC/USDT市场吃单买入BTC。
    P3<P2/P1
    p2<p1/p1
    操作：买-卖/买

'''


# 正循环套利
async def postive_trade(exchange, p2, p3, p1, mid_size, quote_size,base_size, price_p2_ask1, price_p3_bid1,price_p1_ask1):
    if not order_flag:
        return
    print('开始正向套利 postive_trade p2:{}, p3:{}, p1:{}, base_size:{}, '
          'price_p2_ask1:{}, price_p3_bid1:{}, price_p1_ask1:{}'
          .format(p2, p3, p1, base_size, price_p2_ask1, price_p3_bid1, price_p1_ask1))
    try:
        await hedge_buy(exchange, p2, base_size, price_p2_ask1) # TODO 三笔同时下单
         # 对冲卖P2 p3
        await hedge_sell(exchange, p3, base_size, price_p3_bid1)
        # 对冲买P1 p1
        await hedge_buy(exchange, p1, quote_size, price_p1_ask1)
    except Exception as e:
        print('create_order e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        await exchange.close()
        return

    print('结束正向套利 postive_trade,base_size{} is {}'.format(base,base_size))
    await exchange.close()


'''
    逆循环套利
    逆循环套利的顺序如下：
    先去EOS/BTC吃单卖出EOS，买入BTC，然后根据EOS/BTC的成交量，使用多线程，
    同时在EOS/USDT和BTC/USDT市场进行对冲。
    EOS/USDT市场吃单买入EOS，BTC/USDT市场吃单卖出BTC。
    P3>P2/P1
    p2>p3/p1
    操作：卖-买/卖
'''


# 逆循环套利
async def negative_trade(exchange, p2, p3, p1,mid_size, quote_size, base_size, price_p2_bid1,price_p2_ask1, price_p3_ask1,#TODO 交易失败撤单
                   price_p1_bid1):
    print('开始逆循环套利 negative_trade p2:{}, p3:{}, p1:{}, base_size:{}, '
          'price_p2_bid1:{}, price_p3_ask1:{}, price_p1_bid1:{}'
          .format(p2, p3, p1, base_size, price_p2_bid1, price_p3_ask1,
                  price_p1_bid1))
    # 卖出EOS 卖P3
    if not order_flag:
        await exchange.close()
        return
    # P1:BTC/USDT,P2:EOS/BTC,P3: EOS/USDT
    if base_size * price_p3_ask1 < min_notional:
        print('min_notional p2:{}, p3:{}, p1:{}, base_size:{},trade_price:{}'
        'price_p2_bid1:{}, price_p3_ask1:{}, price_p1_bid1:{}'
        .format(p2, p3, p1, base_size,base_size * price_p3_ask1, price_p2_bid1, price_p3_ask1,
                price_p1_bid1,base_size * price_p3_ask1))
        await exchange.close()
        return
    try:
        print("===>1")
        await hedge_sell(exchange,p2, base_size, price_p2_bid1)
        await hedge_buy(exchange, p3, base_size, price_p3_ask1)
        await hedge_sell(exchange, p1,quote_size , price_p1_bid1)
    except Exception as e:
        print('create_order e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        await exchange.close()
        return
    print('结束逆向套利 negative_trade ,base_size is {}'.format(base_size))
    await exchange.close()
        

# 对冲卖
async def hedge_sell(exchange, symbol, sell_size, price):# TODO 动态尝试不断加码, 而不是直接用市价单交易 
    print('开始对冲卖 hedge_sell symbol:{},sell_size:{},price:{} amount{}'.format(symbol, sell_size, price,sell_size * price))
    try:
        result = await exchange.create_order(symbol, 'limit', 'sell', sell_size, price)
    except Exception as e:
        print('create_order e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        await exchange.close()
        return
    # time.sleep(delay/10)
    await asyncio.sleep(delay)
    # # 延时delay/10秒后查询订单成交量
    # order = await exchange.fetch_order(result['id'], symbol)
    # filled = order['filled']
    # remaining = order['remaining']
    # # 未成交的市价交易
    # if filled < sell_size and filled >= min_notional:
    #     await exchange.create_order(symbol, 'market', 'sell', remaining)
    #     print('对冲卖---- hedge_sell filled < sell_size 市价交易 symbol:{},filled:{},sell_size:{},remaining:{}'.format(symbol, filled, sell_size, remaining))
    await exchange.close()


# 对冲买
async def hedge_buy(exchange, symbol, buy_size, price):# TODO 动态尝试不断加码, 而不是直接用市价单交易
    print('开始对冲买 hedge_buy symbol:{},buy_size:{},price:{} amount:{}'.format(symbol, buy_size, price,buy_size * price))
    try:
        result = await exchange.create_order(symbol, 'limit', 'buy', buy_size, price)
    except Exception as e:
        print('hedge_buy e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        await exchange.close()
        return
    # time.sleep(delay/10)
    await asyncio.sleep(delay/10)
    # 延时delay/10秒后查询订单成交量
    # order = await exchange.fetch_order(result['id'], symbol)
    # filled = order['filled']
    # remaining = order['remaining']
    # # 未成交的市价交易
    # if filled < buy_size and filled >= min_notional:
    #     await exchange.create_order(symbol, 'market', 'buy', remaining)
    #     print('对冲买---- hedge_buy filled < sell_size 市价交易 symbol:{},filled:{},buy_size:{},remaining:{}'.format(symbol, filled, buy_size, remaining))
    await exchange.close()


'''
        P3<P2/P1
        操作：买-卖/买
        base:EOS, quote:BTC, mid:USDT
        1.	EOS/BTC卖方盘口吃单数量：ltc_btc_sell1_quantity*order_ratio_ltc_btc，其中ltc_btc_sell1_quantity 代表EOS/BTC卖一档的数量，
            order_ratio_ltc_btc代表本策略在EOS/BTC盘口的吃单比例
        2.	EOS/USDT买方盘口吃单数量：ltc_usdt_buy1_quantity*order_ratio_ltc_usdt，其中order_ratio_ltc_usdt代表本策略在EOS/USDT盘口的吃单比例
        3.	EOS/BTC账户中可以用来买EOS的BTC额度及可以置换的EOS个数：
            btc_available - btc_reserve，可以置换成
            (btc_available – btc_reserve)/ltc_btc_sell1_price个EOS
            其中，btc_available表示该账户中可用的BTC数量，btc_reserve表示该账户中应该最少预留的BTC数量
            （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
        4.	EOS/USDT账户中可以用来卖的EOS额度：
            ltc_available – ltc_reserve
            其中，ltc_available表示该账户中可用的EOS数量，ltc_reserve表示该账户中应该最少预留的EOS数量
            （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
        5.	BTC/USDT账户中可以用来买BTC的USDT额度及可以置换的BTC个数和对应的EOS个数：
            usdt_available - usdt_reserve, 可以置换成
            (usdt_available-usdt_reserve)/btc_usdt_sell1_price个BTC，
            相当于
            (usdt_available-usdt_reserve)/btc_usdt_sell1_price/ltc_btc_sell1_price
            个EOS
            其中：usdt_available表示该账户中可用的人民币数量，usdt_reserve表示该账户中应该最少预留的人民币数量
            （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
'''


# 获取下单买入数量 需要跟账户可用余额结合起来，数量单位统一使用base(P3:EOS）来计算
def get_buy_size(free_base, free_quote, free_mid, size_p2_ask1, size_p3_bid1, price_p2_ask1, price_p1_ask1): #base quote 直接改成p1,p2,p3

    # 1. EOS/BTC卖方盘口吃单数量 P3 卖BTC得EOS
    p2_to_buy_size = size_p2_ask1 * order_ratio
    # 2. EOS/USDT买方盘口吃单数量 P2 卖EOS得USDT
    p3_to_sell_size = size_p3_bid1 * order_ratio



    # 3. EOS/BTC账户中可以用来买EOS的BTC额度及可以置换的EOS个数 P3 卖BTC得EOS
    p2_can_buy_size = free_quote * (1-reserve_ratio_quote) / price_p2_ask1
    p2_can_buy_size = p2_can_buy_size * (1 - cost_P2) #算上手续费只能买这些
   
    # 4. EOS/USDT账户中可以用来卖的EOS额度 P2 卖EOS得USDT
    p3_can_sell_size = free_base * (1-reserve_ratio_base)

    # 5. BTC/USDT账户中可以用来买BTC的USDT额度及可以置换的BTC个数和对应的EOS个数 P1 卖USDT得BTC
    p1_can_buy_size = free_mid * (1 - reserve_ratio_mid) / price_p1_ask1 / price_p2_ask1
    p1_can_buy_size = p1_can_buy_size * (1 - cost_P1) * ( 1- cost_P2)  #算上手续费只能买这些

    return min(p2_to_buy_size, p3_to_sell_size, p2_can_buy_size, p1_can_buy_size, 
               p3_can_sell_size)


'''
        P3>P2/P1
        操作：卖-买/卖
        base:EOS, quote:BTC, mid:USDT
        卖出的下单保险数量计算
        假设BTC/USDT盘口流动性好
        1. EOS/BTC买方盘口吃单数量：ltc_btc_buy1_quantity*order_ratio_ltc_btc，其中ltc_btc_buy1_quantity 代表EOS/BTC买一档的数量，
           order_ratio_ltc_btc代表本策略在EOS/BTC盘口的吃单比例
        2. EOS/USDT卖方盘口卖单数量：ltc_usdt_sell1_quantity*order_ratio_ltc_usdt，其中order_ratio_ltc_usdt代表本策略在EOS/USDT盘口的吃单比例
        3. EOS/BTC账户中可以用来卖EOS的数量：
           ltc_available - ltc_reserve，
           其中，ltc_available表示该账户中可用的EOS数量，ltc_reserve表示该账户中应该最少预留的EOS数量
          （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
        4.	EOS/USDT账户中可以用来卖的usdt额度：
            usdt_available – usdt_reserve，相当于
            (usdt_available – usdt_reserve) / ltc_usdt_sell1_price个EOS
            其中，usdt_available表示该账户中可用的人民币数量，usdt_reserve表示该账户中应该最少预留的人民币数量
            （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
        5.	BTC/USDT账户中可以用来卖BTC的BTC额度和对应的EOS个数：
            btc_available - btc_reserve, 可以置换成
            (btc_available-btc_reserve) / ltc_btc_sell1_price个EOS
            其中：btc_available表示该账户中可用的BTC数量，btc_reserve表示该账户中应该最少预留的BTC数量
           （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。

    '''


# 获取下单卖出数量 需要跟账户可用余额结合起来，数量单位统一使用base(P3:EOS）来计算 #TODO 最小下单金额10美元
def get_sell_size(free_base, free_quote, free_mid, size_p2_bid1, size_p3_ask1, price_p3_ask1, price_p2_ask1):
    # 1 EOS/BTC 买方盘口吃单数量P3 卖EOS得BTC
    p2_to_sell = size_p2_bid1 * order_ratio
    # 2 EOS/USDT 卖方盘口吃单数量P2 卖USDT得EOS
    p3_to_buy = size_p3_ask1 * order_ratio
    # 3 EOS/BTC 账户EOS中可以用来卖出EOS的数量P3，卖EOS得BTC
    p2_can_sell = free_base * (1-reserve_ratio_base) #有多少个eos能卖 换成btc
    # 4 EOS/USDT 账户USDT中可以用来购买EOS的数量P2，卖USDT得EOS
    p3_can_buy = free_mid * (1-reserve_ratio_mid) * (1- cost_P3) / price_p3_ask1 #拿usdt能换多少个eos
    # 5 BTC/USDT 账户中可以用来卖出BTC的数量，转换为EOS数量(卖BTC得EOS)P1，卖BTC得USDT
    p1_can_sell = free_quote * (1 - reserve_ratio_quote) *(1 - cost_P2)/ price_p2_ask1 #btc 能换到多少个eos

    print("get_sell_size====>",p2_to_sell,p3_to_buy, p2_can_sell, p3_can_buy, p1_can_sell)

    return min(p2_to_sell,p3_to_buy,p2_can_sell,p3_can_buy,p1_can_sell)


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
    loop =  asyncio.get_event_loop()
    global good_exchange_list
    good_exchange_list = get_exchange_list(good_exchange_name)
    while True:
        time.sleep(0.01)
        tick(loop)


def tick(loop):
    global good_exchange_list
    taskList = []  
    for symbol in good_coin:
        for exchange in good_exchange_list:
            taskList.append(find_trade_chance(exchange, symbol, default_quote_cur, default_mid_cur))
    loop.run_until_complete(asyncio.gather(*taskList))




worker_thread = threading.Thread(target=print_stream_data_from_stream_buffer, args=(binance_websocket_api_manager,))
worker_thread.start()


# print('before proxy ip is {}'.format(get_host_ip()))
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

import asyncio
import os
import time
import socket

import ccxt.async_support as ccxta
# TODO
# ws 推送行情 
# 加入frequency limit
# 跨交易所三角套利
# 多空双持 用来做套保的合约同时也用来做套利 或者加入合约平仓或者爆仓的停止机制,或者做平仓套利
# 自动均仓,平衡基础货币
# 被动挂单 
# 成交推送微信, 可视化资产
# ...


"""
    三角套利demo2：寻找三角套利空间，包含下单模块，异步请求处理版
    交易对：用一种资产（quote currency）去定价另一种资产（base currency）,比如用比特币（BTC）去定价莱特币（LTC），
    就形成了一个LTC/BTC的交易对，
    交易对的价格代表的是买入1单位的base currency（比如LTC）
    需要支付多少单位的quote currency（比如BTC），
    或者卖出一个单位的base currency（比如LTC）
    可以获得多少单位的quote currency（比如BTC）。
    中间资产mid currency可以是USDT等稳定币
"""
# quote_mid p1 BTC/USDT
# base_quote p2 LTC/BTC
# base_mid p3 LTC/USDT
default_base_cur = 'LTC'
default_quote_cur = 'BTC'
default_mid_cur = 'USDT'

cost_P1 = 0.03 #获取手续费
cost_P2 = 0.03
cost_P3 = 0.03

slippage = 0.01

# delay 2 second
delay = 2
# 轮询订单次数query_times 3
query_times = 3
# 最小下单价格 #TODO 必须全部大于10美元
min_notional = 10 

# good_exchange_name = ['binance', 'fcoin', 'gateio', 'huobipro', 'kucoin', 'okex']
# good_exchange_name = ['binance', 'fcoin', 'gateio', 'huobipro', 'kucoin', 'okex','bcex','bibox','bigone','bitfinex','bitforex',
#                       'bithumb','bitkk','cex','coinbase','coinex','cointiger','exx','gdax','gemini','hitbtc','rightbtc',
#                       'theocean','uex']
# good_coin = ['ETH', 'XRP', 'BCH', 'EOS', 'XLM', 'LTC', 'ADA', 'XMR', 'TRX', 'BNB', 'ONT', 'NEO', 'DCR']

good_exchange_name = ['binance']
good_coin = ['ETH', 'XRP', 'BCH', 'EOS', 'XLM', 'LTC', 'ADA', 'XMR', 'TRX', 'BNB', 'ONT', 'NEO', 'DCR', 'RATING']
#good_coin = ['BNB']


has_config_exchange = ['binance']
config_key = dict()
#config_key['binance'] = ['CSTMpyrOapOukNAABAQMuX0pyr4CgRiKbbznMIKkLYvDf7E9U3ROqNQKzEdwoEde','uwMXqTayKskkSpQiA9NJA1V9vESNZj1jdBFrGFNd9aWYlhLmzv6F3C7B3jhl5wtP']
config_key['binance'] = ['vaMCSPGdGTLdkcZKzyBtOkpGeVYPtb7F1OeI2gSPTHtjNh6Ze7qY7HLR2G2vmLte','sVpTMoJTZ0Bb21W73K6KpsNxt95MFn045V5jOjxVTQIyGM0zMeZnUkoiwlsuf7JT']
# 交易相关常量
# 订单交易量吃单比例
order_ratio = 0.5
# 账户资金保留比例
reserve_ratio_base = 0.3
reserve_ratio_quote = 0.3
reserve_ratio_mid = 0.3
slippage_ratio = 0.0005
service_ratio =0.0006

# 最小成交量比例设定
min_trade_percent = 0.2

# 是否真正下单
order_flag = False

sandbox_mode = True

proxy_flag = False


def set_proxy():
    if proxy_flag:
        os.environ.setdefault('http_proxy', 'http://127.0.0.1:1087')
        os.environ.setdefault('https_proxy', 'http://127.0.0.1:1087')


# 获取指定交易所列表
def get_exchange_list(good_list):
    exchange_list = []
    for exchange_name in good_list:
        exchange = getattr(ccxta,exchange_name)()
        if exchange:
            if sandbox_mode:
                exchange.set_sandbox_mode(True)
            exchange_list.append(exchange)
    return exchange_list


# 设置交易所key
def set_exchange_key(exchange):
    if exchange.id in has_config_exchange:
        exchange.apiKey = config_key[exchange.id][0]
        exchange.secret = config_key[exchange.id][1]
        print('set_exchange_key name is {},key is {},secret is {}'.format(exchange.name,exchange.apiKey,exchange.secret))
    else:
        print('set_exchange_key name is {} no key'.format(exchange.name))


# 在指定交易所寻找三角套利机会，根据P3与P2/P1大小关系进行套利，暂不考虑滑点和手续费，目标保持base,quote数量不变，使mid数量增多
async def find_trade_chance(exchange,base='LTC',quote='BTC',mid='USDT'):
    #print('-----find_trade_chance开始在交易所{}寻找三角套利机会,base:{},quote:{},mid:{}'.format(exchange.name,base,quote,mid))
    try:
        markets =  await exchange.load_markets()
        # for market in markets:
        #     print('+++++++++++',market)
    except Exception as e:
        print('load_markets e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        await exchange.close()
        return
    
    cur_p1 = quote + '/' + mid #P1 symbol
    cur_p2 = base + '/' + quote #P2 symbol
    cur_p3 = base+'/'+mid #P3 symbol

    print('P1:{},P2:{},P3: {}'.format(cur_p1,cur_p2,cur_p3))

    try:
        book_p1 = await exchange.fetch_order_book(cur_p1)
        # time.sleep(delay)
        await asyncio.sleep(delay)
        book_p2 = await exchange.fetch_order_book(cur_p2)
        # time.sleep(delay)
        await asyncio.sleep(delay)
        book_p3 = await exchange.fetch_order_book(cur_p3)
    except Exception as e:
        print('fetch_order_book e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        await exchange.close()
        return

    # P1
    price_p1_bid1 = book_p1['bids'][0][0] if len(book_p1['bids']) > 0 else None
    price_p1_ask1 = book_p1['asks'][0][0] if len(book_p1['asks']) > 0 else None
    size_p1_bid1 = book_p1['bids'][0][1] if len(book_p1['bids']) > 0 else None
    size_p1_ask1 = book_p1['asks'][0][1] if len(book_p1['asks']) > 0 else None
    # P3
    price_p2_bid1 = book_p2['bids'][0][0] if len(book_p2['bids']) > 0 else None
    price_p2_ask1 = book_p2['asks'][0][0] if len(book_p2['asks']) > 0 else None
    size_p2_bid1 = book_p2['bids'][0][1] if len(book_p2['bids']) > 0 else None
    size_p2_ask1 = book_p2['asks'][0][1] if len(book_p2['asks']) > 0 else None
    # P3
    price_p3_bid1 = book_p3['bids'][0][0] if len(book_p3['bids']) > 0 else None
    price_p3_ask1 = book_p3['asks'][0][0] if len(book_p3['asks']) > 0 else None
    size_p3_bid1 = book_p3['bids'][0][1] if len(book_p3['bids']) > 0 else None
    size_p3_ask1 = book_p3['asks'][0][1] if len(book_p3['asks']) > 0 else None


    date_time = exchange.last_response_headers['Date']

    #检查正循环套利
    '''
        三角套利的基本思路是，用两个市场（比如BTC/USDT，LTC/USDT）的价格（分别记为P1，P2），
        计算出一个公允的LTC/BTC价格（P2/P1），如果该公允价格跟实际的LTC/BTC市场价格（记为P3）不一致，
        就产生了套利机会
        P3<P2/P1
        操作：买-卖/买
        价格条件提交：p2_ask1卖1 < p3_bid1买1/p1_ask1卖1
        交易量Q3:三者中取最小下单量，单位要统一为P3交易对的个数
        利润：Q3*P1*(P2/P1-P3)
    '''
    try:
        balance = await exchange.fetch_balance()
    except Exception as e:
            print('-------find_trade_object fetch_balance exception is {}'.format(e.args[0]))
            await exchange.close()
            return 
    free_base = balance[base]['free'] if balance[base]['free'] else 0
    free_quote = balance[quote]['free'] if balance[quote]['free'] else 0
    free_mid = balance[mid]['free'] if balance[mid]['free'] else 0


    if (1-slippage) *(price_p1_ask1 * price_p2_ask1)/(1-cost_P1)(1-cost_P2) < price_p3_bid1*(1+slippage)(1-cost_P3):
        trade_size = get_buy_size(free_base, free_quote, free_mid, size_p2_ask1, size_p1_ask1, 
                                    price_p2_ask1, price_p1_ask1)
        if trade_size * price_p1_ask1 <= min_notional || trade_size * price_p2_ask1 <= min_notional || trade_size * price_p3_bid1 <= min_notional:
            print("balance not enough")
            return

        # 价格差值
        price_diff = price_p3_bid1*(1+slippage)(1-cost_P3) - (1-slippage) * (1-slippage) *(price_p1_ask1 * price_p2_ask1)/(1-cost_P1)(1-cost_P2)
        profit = trade_size*price_diff

        print('++++++发现正套利机会 profit is {} USDT,price_diff is {},trade_size is {},P3: {} < P2/P1: {},time:{}\n\n'.format(
            profit, price_diff, trade_size, price_p2_ask1, price_p3_bid1/price_p1_ask1, date_time))
        print('P1: buy1:{},{},sell1:{},{}'.format(price_p1_bid1,size_p1_bid1,price_p1_ask1,size_p1_ask1))
        print('P2: buy1:{},{},sell1:{},{}'.format(price_p3_bid1, size_p3_bid1, price_p3_ask1,size_p3_ask1))
        print('P3: buy1:{},{},sell1:{},{}'.format(price_p2_bid1, size_p2_bid1, price_p2_ask1,size_p2_ask1))
        # 开始正循环套利
        if order_flag:
            await postive_trade(exchange, cur_p2, cur_p3, cur_p1, trade_size, price_p2_ask1,
                        price_p3_bid1, price_p1_ask1)
        await exchange.close()
        # 检查逆循环套利
        '''
            P3>P2/P1
            操作：卖-买/卖
            价格条件：p2_bid1买1 > p3_ask1卖1/p1_bid1买1
            交易量Q3:三者中取最小下单量
            利润：Q3*P1*(P3-P2/P1)
        '''

    elif (1-slippage) *(price_p1_bid1 * price_p2_bid1)/(1-cost_P1)(1-cost_P2) > price_p3_ask1*(1 - slippage)(1-cost_P3):
        trade_size = get_sell_size(free_base, free_quote, free_mid, size_p2_bid1, size_p3_ask1, price_p3_ask1, price_p2_ask1)

        if trade_size * price_p1_bid1 <= min_notional || trade_size * price_p2_bid1 <= min_notional || trade_size * price_p3_ask1 <= min_notional:
            print("balance not enough")
            return

        price_diff = (1-slippage) *(price_p1_bid1 * price_p2_bid1)/(1-cost_P1)(1-cost_P2) > price_p3_bid1*(1 - slippage)(1-cost_P3)
        profit = trade_size*price_diff
        print('P1: buy1:{},{},sell1:{},{}'.format(price_p1_bid1,size_p1_bid1,price_p1_ask1,size_p1_ask1))
        print('P2: buy1:{},{},sell1:{},{}'.format(price_p3_bid1, size_p3_bid1, price_p3_ask1,size_p3_ask1))
        print('P3: buy1:{},{},sell1:{},{}'.format(price_p2_bid1, size_p2_bid1, price_p2_ask1,size_p2_ask1))
        print('++++++发现逆套利机会 profit is {},price_diff is {},trade_size is {},P3: {} > P2/P1: {},time:{}\n\n'.format(
        profit, price_diff, trade_size, price_p2_bid1, price_p3_ask1/price_p1_bid1, date_time))
        # 开始逆循环套利
        if order_flag:
            await negative_trade(exchange, cur_p2, cur_p3, cur_p1, trade_size, price_p2_bid1,
                        price_p3_ask1, price_p1_bid1)
        await exchange.close()
    else:
        #print('在交易所{}没有找到三角套利机会,time:{}\n\n'.format(exchange.name,date_time))
        await exchange.close()

'''
    正循环套利
    正循环套利的顺序如下：
    先去LTC/BTC吃单买入LTC，卖出BTC，然后根据LTC/BTC的成交量，使用多线程，
    同时在LTC/USDT和BTC/USDT市场进行对冲。LTC/USDT市场吃单卖出LTC，BTC/USDT市场吃单买入BTC。
    P3<P2/P1
    p2<p1/p1
    操作：买-卖/买

'''


# 正循环套利
async def postive_trade(exchange, p2, p3, p1, trade_size, price_p2_ask1, price_p3_bid1, #TODO 交易失败撤单
                  price_p1_ask1):
    print('开始正向套利 postive_trade p2:{}, p3:{}, p1:{}, trade_size:{}, '
          'price_p2_ask1:{}, price_p3_bid1:{}, price_p1_ask1:{}'
          .format(p2, p3, p1, trade_size, price_p2_ask1, price_p3_bid1, price_p1_ask1))
    # 买入P3 p2
    if order_flag:
        result = await exchange.create_order(p2, 'limit', 'buy', trade_size, price_p2_ask1) #TODO  同时下单 而不是串行下单

    retry = 0
    already_hedged_amount = 0
    while retry <= query_times:
        if retry == query_times:
            # cancel order
            print('正向套利 postive_trade，达到轮询上限仍未完成交易，取消订单,retry is {}'.format(retry))
            await exchange.cancel_order(result['id'], p2)
            break
        # time.sleep(delay)
        await asyncio.sleep(delay)
        # 延时delay后查询订单成交量
        order = await exchange.fetch_order(result['id'], p2)
        filled = order['filled']
        amount = order['amount']
        already_hedged_amount = filled
        # 实际成交比例小于设定比例
        if filled/amount < min_trade_percent:
            retry += 1
            continue
        # 对冲卖P2 p3
        await hedge_sell(exchange, p3, filled, price_p3_bid1)
        # 对冲买P1 p1
        await hedge_buy(exchange, p1, filled, price_p1_ask1)

        # 实际成交量完成目标，退出轮询
        if already_hedged_amount >= trade_size:
            print('正向套利 postive_trade 实际成交量完成目标，退出轮询')
            break
        else:
            retry += 1
    print('结束正向套利 postive_trade already_hedged_amount is {},trade_size is {}'.format(already_hedged_amount,trade_size))
    await exchange.close()


'''
    逆循环套利
    逆循环套利的顺序如下：
    先去LTC/BTC吃单卖出LTC，买入BTC，然后根据LTC/BTC的成交量，使用多线程，
    同时在LTC/USDT和BTC/USDT市场进行对冲。
    LTC/USDT市场吃单买入LTC，BTC/USDT市场吃单卖出BTC。
    P3>P2/P1
    p2>p3/p1
    操作：卖-买/卖

'''


# 逆循环套利
async def negative_trade(exchange, p2, p3, p1, trade_size, price_p2_bid1, price_p3_ask1,#TODO 交易失败撤单
                   price_p1_bid1):
    print('开始逆循环套利 negative_trade p2:{}, p3:{}, p1:{}, trade_size:{}, '
          'price_p2_bid1:{}, price_p3_ask1:{}, price_p1_bid1:{}'
          .format(p2, p3, p1, trade_size, price_p2_bid1, price_p3_ask1,
                  price_p1_bid1))
    # 卖出LTC 卖P3
    if order_flag:
        result = exchange.create_order(p2, 'limit', 'sell', trade_size, price_p2_bid1)
    
    retry = 0
    already_hedged_amount = 0
    while retry <= query_times:
        if retry == query_times:
            # cancel order
            print('逆向套利 negative_trade，达到轮询上限仍未完成交易，取消订单,retry is {}'.format(retry))
            await exchange.cancel_order(result['id'], p2)
            break
        # time.sleep(delay)
        await asyncio.sleep(delay)
        # 延时delay后查询订单成交量
        order = await exchange.fetch_order(result['id'], p2)
        filled = order['filled']
        amount = order['amount']
        already_hedged_amount = filled
        # 实际成交比例小于设定比例
        if filled / amount < min_trade_percent:
            retry += 1
            continue
        # 对冲买LTC P2
        await hedge_buy(exchange, p3, filled, price_p3_ask1)
        # 对冲卖BTC P1
        await hedge_sell(exchange, p1, filled, price_p1_bid1)
        # 实际成交量完成目标，退出轮询
        if already_hedged_amount >= trade_size:
            print('逆向套利 negative_trade 实际成交量完成目标，退出轮询')
            break
        else:
            retry += 1
    print('结束逆向套利 negative_trade already_hedged_amount is {},trade_size is {}'.format(already_hedged_amount, trade_size))
    await exchange.close()
        

# 对冲卖
async def hedge_sell(exchange, symbol, sell_size, price):# TODO 动态尝试不断加码, 而不是直接用市价单交易
    print('开始对冲卖 hedge_sell symbol:{},sell_size:{},price:{}'.format(symbol, sell_size, price))
    result = await exchange.create_order(symbol, 'limit', 'sell', sell_size, price)
    # time.sleep(delay/10)
    await asyncio.sleep(delay/10)
    # 延时delay/10秒后查询订单成交量
    order = await exchange.fetch_order(result['id'], symbol)
    filled = order['filled']
    remaining = order['remaining']
    # 未成交的市价交易
    if filled < sell_size:
        await exchange.create_order(symbol, 'market', 'sell', remaining)
        print('对冲卖---- hedge_sell filled < sell_size 市价交易 symbol:{},filled:{},sell_size:{},remaining:{}'.format(symbol, filled, sell_size, remaining))
    await exchange.close()


# 对冲买
async def hedge_buy(exchange, symbol, buy_size, price):# TODO 动态尝试不断加码, 而不是直接用市价单交易
    print('开始对冲买 hedge_buy symbol:{},buy_size:{},price:{}'.format(symbol, buy_size, price))
    result = await exchange.create_order(symbol, 'limit', 'buy', buy_size, price)
    # time.sleep(delay/10)
    await asyncio.sleep(delay/10)
    # 延时delay/10秒后查询订单成交量
    order = await exchange.fetch_order(result['id'], symbol)
    filled = order['filled']
    remaining = order['remaining']
    # 未成交的市价交易
    if filled < buy_size:
        await exchange.create_order(symbol, 'market', 'buy', remaining)
        print('对冲买---- hedge_buy filled < sell_size 市价交易 symbol:{},filled:{},buy_size:{},remaining:{}'.format(symbol, filled, buy_size, remaining))
    await exchange.close()


'''
        P3<P2/P1
        操作：买-卖/买
        base:LTC, quote:BTC, mid:USDT
        1.	LTC/BTC卖方盘口吃单数量：ltc_btc_sell1_quantity*order_ratio_ltc_btc，其中ltc_btc_sell1_quantity 代表LTC/BTC卖一档的数量，
            order_ratio_ltc_btc代表本策略在LTC/BTC盘口的吃单比例
        2.	LTC/USDT买方盘口吃单数量：ltc_usdt_buy1_quantity*order_ratio_ltc_usdt，其中order_ratio_ltc_usdt代表本策略在LTC/USDT盘口的吃单比例
        3.	LTC/BTC账户中可以用来买LTC的BTC额度及可以置换的LTC个数：
            btc_available - btc_reserve，可以置换成
            (btc_available – btc_reserve)/ltc_btc_sell1_price个LTC
            其中，btc_available表示该账户中可用的BTC数量，btc_reserve表示该账户中应该最少预留的BTC数量
            （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
        4.	LTC/USDT账户中可以用来卖的LTC额度：
            ltc_available – ltc_reserve
            其中，ltc_available表示该账户中可用的LTC数量，ltc_reserve表示该账户中应该最少预留的LTC数量
            （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
        5.	BTC/USDT账户中可以用来买BTC的USDT额度及可以置换的BTC个数和对应的LTC个数：
            usdt_available - usdt_reserve, 可以置换成
            (usdt_available-usdt_reserve)/btc_usdt_sell1_price个BTC，
            相当于
            (usdt_available-usdt_reserve)/btc_usdt_sell1_price/ltc_btc_sell1_price
            个LTC
            其中：usdt_available表示该账户中可用的人民币数量，usdt_reserve表示该账户中应该最少预留的人民币数量
            （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
'''


# 获取下单买入数量 需要跟账户可用余额结合起来，数量单位统一使用base(P3:LTC）来计算
def get_buy_size(free_base, free_quote, free_mid, size_p2_ask1, size_p3_bid1, price_p2_ask1, price_p1_ask1): #base quote 直接改成p1,p2,p3

    # 1. LTC/BTC卖方盘口吃单数量 P3 卖BTC得LTC
    p2_to_buy_size = size_p2_ask1 * order_ratio
    # 2. LTC/USDT买方盘口吃单数量 P2 卖LTC得USDT
    p3_to_sell_size = size_p3_bid1 * order_ratio
    # 3. LTC/BTC账户中可以用来买LTC的BTC额度及可以置换的LTC个数 P3 卖BTC得LTC
    p2_can_buy_size = free_quote * (1-reserve_ratio_quote) / price_p2_ask1
    # 4. LTC/USDT账户中可以用来卖的LTC额度 P2 卖LTC得USDT
    p3_can_sell_size = free_base * (1-reserve_ratio_base)
    # 5. BTC/USDT账户中可以用来买BTC的USDT额度及可以置换的BTC个数和对应的LTC个数 P1 卖USDT得BTC
    p1_can_buy_size = free_mid * (1 - reserve_ratio_mid) / price_p1_ask1 / price_p2_ask1
    return min(p2_to_buy_size, p3_to_sell_size, p2_can_buy_size, p1_can_buy_size, 
               p3_can_sell_size)


'''
        P3>P2/P1
        操作：卖-买/卖
        base:LTC, quote:BTC, mid:USDT
        卖出的下单保险数量计算
        假设BTC/USDT盘口流动性好
        1. LTC/BTC买方盘口吃单数量：ltc_btc_buy1_quantity*order_ratio_ltc_btc，其中ltc_btc_buy1_quantity 代表LTC/BTC买一档的数量，
           order_ratio_ltc_btc代表本策略在LTC/BTC盘口的吃单比例
        2. LTC/USDT卖方盘口卖单数量：ltc_usdt_sell1_quantity*order_ratio_ltc_usdt，其中order_ratio_ltc_usdt代表本策略在LTC/USDT盘口的吃单比例
        3. LTC/BTC账户中可以用来卖LTC的数量：
           ltc_available - ltc_reserve，
           其中，ltc_available表示该账户中可用的LTC数量，ltc_reserve表示该账户中应该最少预留的LTC数量
          （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
        4.	LTC/USDT账户中可以用来卖的usdt额度：
            usdt_available – usdt_reserve，相当于
            (usdt_available – usdt_reserve) / ltc_usdt_sell1_price个LTC
            其中，usdt_available表示该账户中可用的人民币数量，usdt_reserve表示该账户中应该最少预留的人民币数量
            （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。
        5.	BTC/USDT账户中可以用来卖BTC的BTC额度和对应的LTC个数：
            btc_available - btc_reserve, 可以置换成
            (btc_available-btc_reserve) / ltc_btc_sell1_price个LTC
            其中：btc_available表示该账户中可用的BTC数量，btc_reserve表示该账户中应该最少预留的BTC数量
           （这个数值由用户根据自己的风险偏好来设置，越高代表用户风险偏好越低）。

    '''


# 获取下单卖出数量 需要跟账户可用余额结合起来，数量单位统一使用base(P3:LTC）来计算 #TODO 最小下单金额10美元
def get_sell_size(free_base, free_quote, free_mid, size_p2_bid1, size_p3_ask1, price_p3_ask1, price_p2_ask1):
    # 1 LTC/BTC 买方盘口吃单数量P3 卖LTC得BTC
    p2_to_sell = size_p2_bid1 * order_ratio
    # 2 LTC/USDT 卖方盘口吃单数量P2 卖USDT得LTC
    p3_to_buy = size_p3_ask1 * order_ratio
    # 3 LTC/BTC 账户LTC中可以用来卖出LTC的数量P3，卖LTC得BTC
    p2_can_sell = free_base * (1-reserve_ratio_base)
    # 4 LTC/USDT 账户USDT中可以用来购买LTC的数量P2，卖USDT得LTC
    p3_can_buy = free_mid * (1-reserve_ratio_mid) / price_p3_ask1
    # 5 BTC/USDT 账户中可以用来卖出BTC的数量，转换为LTC数量(卖BTC得LTC)P1，卖BTC得USDT
    p1_can_sell = free_quote * (1-reserve_ratio_quote) / price_p2_ask1

    return min(p2_to_sell,p3_to_buy,p2_can_sell,p3_can_buy,p1_can_sell)


def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip
def tick():
 for symbol in good_coin:
        for exchange in good_exchange_list:
            # find_trade_chance(exchange, symbol, default_quote_cur, default_mid_cur)
            asyncio.get_event_loop().run_until_complete(
                find_trade_chance(exchange, symbol, default_quote_cur, default_mid_cur))
if __name__ == '__main__':
    # print('before proxy ip is {}'.format(get_host_ip()))
    set_proxy()
    # print('after proxy ip is {}'.format(get_host_ip()))
    good_exchange_list = get_exchange_list(good_exchange_name)
    for exchange in good_exchange_list:
        set_exchange_key(exchange)
    # 在good_coin作为base，quote=BTC,mid=USDT 在good_exchange_list交易所列表中寻找套利机会
   
    while True:
        time.sleep(delay)
        tick()
 
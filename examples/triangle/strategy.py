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
import time
import order
from datetime import datetime


cost_P1 = 0.00075
cost_P2 = 0.00075
cost_P3 = 0.00075


slippage = 0.00075
delay = 0.8
# 最小下单价格(usdt)
min_notional = 10



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
order_flag =  True 

sandbox_mode = False

#每次下单是最小下单金额的倍数
order_multiple = 2

#盈利点数 
profit_slippage = -0.00075





# 在指定交易所寻找三角套利机会，根据P3与P2/P1大小关系进行套利，暂不考虑滑点和手续费，目标保持base,quote数量不变，使mid数量增多
async def find_trade_chance(exchange,base='EOS',quote='BTC',mid='USDT', tickerData={}, orderData ={}):
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


    print('P1:{},P2:{},P3: {}'.format(p1_trade_pair,p2_trade_pair,p3_trade_pair))
    if len(tickerData) < 3:
        print("tickerData<3")
        return
    # P1
    if p1_trade_pair not in tickerData:
        return
    price_p1_bid1 = float(tickerData[p1_trade_pair]['bid'] if tickerData[p1_trade_pair]['bid'] else None)
    price_p1_ask1 = float(tickerData[p1_trade_pair]['ask'] if tickerData[p1_trade_pair]['ask'] else None)

    size_p1_bid1 =  float(tickerData[p1_trade_pair]['bidsize'] if tickerData[p1_trade_pair]['bidsize'] else None)
    size_p1_ask1 =  float(tickerData[p1_trade_pair]['asksize'] if tickerData[p1_trade_pair]['asksize'] else None)
   
    if p2_trade_pair not in tickerData:
        return
    print(price_p1_bid1, price_p1_ask1, size_p1_bid1,size_p1_ask1)
    # P2
    price_p2_bid1 = float(tickerData[p2_trade_pair]['bid'] if tickerData[p2_trade_pair]['bid'] else None)
    price_p2_ask1 = float(tickerData[p2_trade_pair]['ask'] if tickerData[p2_trade_pair]['ask'] else None)
    size_p2_bid1 = float(tickerData[p2_trade_pair]['bidsize'] if tickerData[p2_trade_pair]['bidsize'] else None)
    size_p2_ask1 = float(tickerData[p2_trade_pair]['asksize'] if tickerData[p2_trade_pair]['asksize'] else None)
   

    if p3_trade_pair not in tickerData:
        return
    # P3
    price_p3_bid1 = float(tickerData[p3_trade_pair]['bid'] if tickerData[p3_trade_pair]['bid'] else None)
    price_p3_ask1 = float(tickerData[p3_trade_pair]['ask'] if tickerData[p3_trade_pair]['ask'] else None)

    size_p3_bid1 = float(tickerData[p3_trade_pair]['bidsize'] if tickerData[p3_trade_pair]['bidsize'] else None)
    size_p3_ask1 = float(tickerData[p3_trade_pair]['asksize'] if tickerData[p3_trade_pair]['asksize'] else None)
   

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


    # TODO 手续费  
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
    
    
    mid_size = min_notional * 2

    positive_buy = (1 + slippage) * price_p1_ask1 * price_p2_ask1  * (1 + cost_P1) * (1 + cost_P2)
    positive_sell  =  price_p3_bid1 * (1 - slippage) * (1 - cost_P3)

    negative_sell = (1 - slippage) * price_p1_bid1 * price_p2_bid1 *  (1 - cost_P1) * (1 - cost_P2)
    negative_buy = price_p3_ask1 * (1 + slippage) * (1 + cost_P3)

    print("positive unit profit:", positive_sell - positive_buy)
    print("nagative unit profit", negative_sell - negative_buy)
    if positive_sell - positive_buy > profit_slippage:
        quote_size = mid_size / (price_p1_ask1 * (1+cost_P1) *  (1 + slippage) )
        base_size = quote_size / ( price_p2_ask1 * (1+cost_P2)  * (1 + slippage) )
        mid_collect = base_size * price_p3_bid1 * (1 - cost_P3) * (1 - slippage )

        print("p1:{}, size:{},amount:{} ,p2:{}, size:{} ,amount:{},p3: {} , size:{}".format(
        p1_trade_pair, quote_size, mid_size, 
        p2_trade_pair, base_size,base_size * price_p2_bid1,
        p3_trade_pair, mid_collect
        ))
      
        # 价格差值
        price_diff =  positive_sell - positive_buy
        profit  = mid_collect - mid_size

        print('++++++发现正套利机会 profit is {}(USDT), {} trade_size:{} ,{} trade_size: {} ,{} trade_size:{}\n\n'.format(
            profit,mid, mid_size, quote, quote_size, base , base_size))
        # 开始正循环套利
        if order_flag:
            await postive_trade(exchange,mid,quote,base, p1_trade_pair_order ,p2_trade_pair_order, p3_trade_pair_order , mid_size, quote_size, base_size,
            price_p1_ask1 *  (1 + cost_P1),
            price_p2_ask1 *  (1 + cost_P2) *  (1 + slippage),
            price_p3_bid1*(1 - cost_P3)*(1 - slippage),
            slippage,
            orderData)
        # 检查逆循环套利
        '''
            P3>P2/P1
            操作：卖-买/卖
            价格条件：p2_bid1买1 > p3_ask1卖1/p1_bid1买1
            交易量Q3:三者中取最小下单量
            利润：Q3*P1*(P3-P2/P1)
        '''

    if negative_sell - negative_buy > profit_slippage:
        base_size = mid_size /  (price_p3_ask1 * (1 + cost_P3)  * (1 + slippage) )
        quote_size = base_size * price_p2_bid1 * (1 - cost_P2) *  (1 - slippage) 
        mid_collect = quote_size * price_p1_bid1 * (1 - cost_P1) * (1 - slippage )        

        print("p1:{}, size:{},amount:{} ,p2:{}, size:{} ,amount:{},p3: {} , size:{}".format(
        p1_trade_pair, quote_size, mid_collect, 
        p2_trade_pair, base_size,base_size*price_p2_bid1,
        p3_trade_pair, mid_size
        ))
        

        price_diff = negative_sell -  negative_buy
        # 单位usdt
        profit = mid_collect - mid_size 

        print('++++++发现负套利机会 profit is {}(USDT), {} trade_size:{} ,{} trade_size: {} ,{} trade_size:{}\n\n'.format(
            profit,mid, mid_size, quote, quote_size, base , base_size))
        # 开始逆循环套利
        if order_flag:
            await negative_trade(exchange, mid, quote, base, p3_trade_pair_order, p2_trade_pair_order, p1_trade_pair_order, mid_size, quote_size, base_size,
            price_p3_ask1 * (1 + cost_P3),
            price_p2_bid1 * (1 - cost_P2) * (1 - slippage),
            price_p1_bid1*(1 - cost_P1)*(1 - slippage),
            slippage,
            orderData)
       

'''
    正循环套利
    正循环套利的顺序如下：
    先去EOS/BTC吃单买入EOS，卖出BTC，然后根据EOS/BTC的成交量，使用多线程，
    同时在EOS/USDT和BTC/USDT市场进行对冲。EOS/USDT市场吃单卖出EOS，BTC/USDT市场吃单买入BTC。
    P3<P2/P1
    p2<p1/p1
    操作：买-卖/买

'''
async def postive_trade(exchange,mid,quote,base,p1, p2, p3, mid_size, quote_size,base_size, price_p1_ask1, price_p2_ask1, price_p3_bid1, slippage,orderData):
    print('开始正向套利 postive_trade p2:{}, p3:{}, p1:{}, base_size:{}, '
          'price_p2_ask1:{}, price_p3_bid1:{}, price_p1_ask1:{}'
          .format(p2, p3, p1, base_size, price_p2_ask1, price_p3_bid1, price_p1_ask1))
    if not order_flag:
        return

    key = mid + quote + base
    if key not in orderData:
        orderData[key] = {} 
    try:
        await order.hedge_buy_step(exchange, p1, quote_size, price_p1_ask1,delay,slippage)
    except Exception as e:
        print('create_order e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        return

    result  = {}
    try:
        await order.hedge_buy(exchange, p2, base_size, price_p2_ask1,delay)
        result = await order.hedge_should_sell(exchange, p3, base_size, price_p3_bid1, delay)
    except Exception as e:
        print('create_order e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        fillOrderRecord(result, orderData)
        return

    fillOrderRecord(result, orderData)
    print('结束正向套利 postive_trade,base_size{} is {}'.format(base,base_size))


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
async def negative_trade(exchange,mid,quote,base, p3, p2, p1,mid_size, quote_size, base_size,price_p3_ask1 , price_p2_bid1 ,price_p1_bid1,slippage, orderData):
    print('开始逆循环套利 negative_trade p2:{}, p3:{}, p1:{}, base_size:{}, '
          'price_p2_bid1:{}, price_p3_ask1:{}, price_p1_bid1:{}'
          .format(p2, p3, p1, base_size, price_p2_bid1, price_p3_ask1,
                  price_p1_bid1))
    # 卖出EOS 卖P3
    if not order_flag:
        return
    key = mid + quote + base
    if key not in orderData:
            orderData[key] = {} 
    try:
        await order.hedge_buy_step(exchange, p3, base_size, price_p3_ask1, delay,slippage) # ① 第一笔失败不记录到dict
    except Exception as e:
        print('create_order e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        return
    result  = {}
    try:
        await order.hedge_sell(exchange, p2, base_size, price_p2_bid1, delay)
        result = await order.hedge_should_sell(exchange,p1, quote_size, price_p1_bid1, delay)  # 3
        # TODO 要不要sleep
    except Exception as e:
        fillOrderRecord(result, orderData)
        print('create_order e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        return
    fillOrderRecord(result, orderData)
    print('结束逆向套利 negative_trade ,base_size is {}'.format(base_size))



def fillOrderRecord(result={},orderData={}):
    if "id" in result and  (result["status"] == "closed" or result["status"] == "filled"): #第三步直接成功
        print('结束套利成功 negative_trade')
        return
    if "id" in result: # 第三步当时没成功
        orderData[key]["p3id"] = result["id"]
        orderData[key]["time"] = datetime.fromtimestamp(result["timestamp"] / 1000)
        orderData[key]["mid"] = mid
        orderData[key]["quote"]  = quote
        orderData[key]["quoteSize"] = quote_size
        orderData[key]["base"]  = base
        orderData[key]["baseSize"] = base_size
        print('create_order e is {} ,exchange is {}'.format(e.args[0],exchange.name))
        return
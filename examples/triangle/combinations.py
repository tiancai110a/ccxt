#求出所有三角交易组合

from itertools import combinations

import ccxt
import time
import asyncio
config_key={}
config_key['binance'] = ['i3bEQ2PECV68BDMRXuQO1nWvn8WNr2mXa1RCJs8MB1GK6Ge0qcxjrOomutR0QkU5','QlFZ6xbAQ6myXWXYoBKrwXwbuLM57tSRxNwxOWUqaSFsI3GJCzZ21BoI40trTknU']

exchange = getattr(ccxt,"binance")()
exchange.enableRateLimit = True
exchange.apiKey = config_key["binance"][0]
exchange.secret = config_key["binance"][1]



def isTriangle(trade_pair1, trade_pair2,pairMap):
    a1,b1  = trade_pair1.split("/")
    a2, b2 = trade_pair2.split("/")
    market1 = a1 +"/" + b2
    market2 = b2 + "/" + a1
    if market1 in pairMap:
        return market1
    if market2 in pairMap:
        return market2
    return ""


def get_all_triangles(exchange, midSymbol):
    totalMap = {}
    pairMap = {}
    result = []
    newMarket= []
    markets =  exchange.load_markets()
    for market in markets:
        pairMap[market] = 1
        totalMap[market] = [market]

    for base in markets:
        basea ,baseb = base.split("/")
        for market in markets:
            a, b = totalMap[market][len(totalMap[market]) - 1].split("/")
            if b == basea:
                totalMap[market].append(base)

    for market in markets:
        if market not in totalMap:
            continue
        if len(totalMap[market]) < 2:
            del totalMap[market]
            continue

        totalMap[market] = totalMap[market][:2]
        s = isTriangle(totalMap[market][0], totalMap[market][1], pairMap)
        if s=="":
            del totalMap[market]
            continue
        newMarket.append(market)
        a1,b1 = totalMap[market][0].split("/")
        a2,b2 = totalMap[market][1].split("/")
        pair = []
        if a1 != midSymbol and b1 != midSymbol and a2 != midSymbol and b2 != midSymbol:
            continue 
        if a1 != midSymbol:
            pair.append(a1)
        if b1 != midSymbol:
            pair.append(b1)
        if a2 != midSymbol:
            pair.append(a2)
        if b2 != midSymbol:
            pair.append(b2)
        newPair = list(dict.fromkeys(pair))
        result.append(newPair)
        totalMap[market].append(s)
        #print(totalMap[market][0],totalMap[market][1],totalMap[market][2]) #打印所有 三角组合
    print(totalMap)
    #print(newMarket) 打印所有有关usdt的交易对
    return result


get_all_triangles(exchange,"USDT")
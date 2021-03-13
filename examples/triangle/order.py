import asyncio
query_times = 3
#delay = 0.3


# hedge 必须成功 不成功就抛异常 并且取消订单
async def hedge(exchange, trade_string,symbol, size, price, delay):
    result = {}
    print('开始对冲%s hedge_sell symbol:{},size:{},price:{} amount{}'.format(trade_string, symbol, size, price,size * price))
    try:
        result = await exchange.create_order(symbol, 'limit', trade_string, size, price)
    except Exception as e:
        raise Exception("order error!",e)
        return
    retry = 0
    while retry < query_times:
        if "id" not in result:
            continue
        if result["status"] == "closed" or result["status"] == "filled":
            return result
        await asyncio.sleep(delay)
        try:
            result = exchange.fetch_order(result['id'], symbol)
        except Exception as e:
            continue

        if result["status"] == "open":
            retry += 1
            continue
        elif result["status"] == "filled" or result["status"] == "closed":
            return
        else:
            raise Exception("order status error!", result["status"])
    try:
        exchange.cancel_order(result['id'], symbol)
    except Exception as e:
        raise e
        return

    raise Exception("order not success!")
    return

# hedge_market  市价单必须成功 不成功就抛异常 并且取消订单
async def hedge_market(exchange, trade_string,symbol, size, price, delay):
    result = {}
    print('开始对冲{} hedge_sell symbol:{},size:{},price:{} amount{}'.format(trade_string , symbol, size, price,size * price))
    try:
        result = await exchange.create_order(symbol, 'market', trade_string, size, price)
    except Exception as e:
        await exchange.close()
        raise e
        return
    retry = 0
    while retry < query_times:
        if "id" not in result:
            continue
        if result["status"] == "closed" or result["status"] == "filled":
            return result
        await asyncio.sleep(delay)
        try:
            result = exchange.fetch_order(result['id'], symbol)
        except Exception as e:
            continue

        if result["status"] == "open":
            retry += 1
            continue
        elif result["status"] == "filled" or result["status"] == "closed":
            return
        else:
            raise Exception("order status error!", result["status"])
    try:
        exchange.cancel_order(result['id'], symbol)
    except Exception as e:
        raise e
        return

    raise Exception("order not success!")
    return


# hedge_should_trade 不成功就挂那等着, 并且返回result, 用以记录
async def hedge_should_trade(exchange,trade_string, symbol, size, price ,delay):
    result = {}
    print('开始对冲{} hedge_should_sell symbol:{},size:{},price:{} amount{}'.format(trade_string,symbol, size, price,size * price))
    try:
        result = await exchange.create_order(symbol, 'limit', trade_string, size, price)
    except Exception as e:
        raise e
        return
    retry = 0
    while retry < query_times:
        if "id" not in result:
            continue
        if result["status"] == "closed" or result["status"] == "filled":
            return result
        await asyncio.sleep(delay)
        try:
            result = exchange.fetch_order(result['id'], symbol)
        except Exception as e:
            continue
        
        if result["status"] == "open":
            retry += 1
            continue
        elif result["status"] == "filled" or result["status"] == "closed":
            return result
        else:
            return result
    return result


async def hedge_step(exchange, trade_string,symbol, size, origin_price, delay, slippage):
    step = slippage / 3
    price = origin_price
    while True:
        try:
            await hedge_sell(exchange,trade_string, symbol, size, price, delay)
            price = price + step
        except Exception as e:
            if price > origin_price + slippage:
                return
        if price > origin_price + slippage:
            return

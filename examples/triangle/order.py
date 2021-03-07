import asyncio
query_times = 3
#delay = 0.3


# hedge_sell 必须成功 不成功就抛异常 并且取消订单
async def hedge_sell(exchange, symbol, sell_size, price, delay):
    result = {}
    print('开始对冲卖 hedge_sell symbol:{},sell_size:{},price:{} amount{}'.format(symbol, sell_size, price,sell_size * price))
    try:
        result = await exchange.create_order(symbol, 'limit', 'sell', sell_size, price)
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

# hedge_should_sell 不成功就挂那等着, 并且返回result, 用以记录
async def hedge_should_sell(exchange, symbol, sell_size, price ,delay):
    result = {}
    print('开始对冲卖 hedge_should_sell symbol:{},sell_size:{},price:{} amount{}'.format(symbol, sell_size, price,sell_size * price))
    try:
        result = await exchange.create_order(symbol, 'limit', 'sell', sell_size, price)
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


# hedge_buy 必须成功 不成功就抛异常 并且取消订单
async def hedge_buy(exchange, symbol, buy_size, price ,delay):
    result = {}
    print('开始对冲买 hedge_buy symbol:{},buy_size:{},price:{} amount:{}'.format(symbol, buy_size, price,buy_size * price))
    try:
        result = await exchange.create_order(symbol, 'limit', 'buy', buy_size, price)
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
        elif result["status"] == "closed" or result["status"] == "filled":
            return
        else:
            raise Exception("order status error!", result["status"])
    try:
        exchange.cancel_order(result['id'], symbol)
    except Exception as e:
        raise Exception("order error!",e)
    raise Exception("order not success!")
    return



# hedge_should_buy 对冲买  不成功就挂那等着, 并且返回result, 用以记录
async def hedge_should_buy(exchange, symbol, buy_size, price, delay):
    result = {}
    print('开始对冲买 hedge_should_buy symbol:{},buy_size:{},price:{} amount:{}'.format(symbol, buy_size, price,buy_size * price))
    try:
        result = await exchange.create_order(symbol, 'limit', 'buy', buy_size, price)
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
        elif result["status"] == "closed" or result["status"] == "filled":
            return result
        else:
            return result
    return result



async def hedge_sell_step(exchange, symbol, sell_size, origin_price, delay, slippage):
    retry = 0
    step = slippage / 3
    price = origin_price
    while True:
        try:
            await hedge_sell(exchange, symbol, sell_size, price, delay)
        except Exception as e:
            price = price + step
            if price > origin_price + slippage:
                break



async def hedge_buy_step(exchange, symbol, buy_size, origin_price, delay, slippage):
    step = slippage / 3
    price = origin_price
    while True:
        try:
            await hedge_buy(exchange, symbol, buy_size, price, delay)
        except Exception as e:
            price = price + step
            if price > origin_price + slippage:
                    break

import time
import order
from datetime import datetime
wait_time_in_second  = 10 #s
# recycle 取消未成交的挂单,收回所有钱,把所钱转回usdt
order_data = {}
# 最小下单价格(usdt)
min_notional = 10
mid_size = min_notional * 2

def recycle(exchange, order_data={}):
    key_list = cancel_orders(exchange, order_data)
    time.sleep(1)
    recycling_money(exchange, order_data, key_list)
    if key_list is not None:
        for i in key_list:
            order_data.remove(i)


def cancel_orders(exchange, order_data={}):
    now = datetime.now()  # 获取当前时间
    recyleKeyList = []
    for i in list(order_data):
        order = order_data[i]
        if (now - order.time).seconds > wait_time_in_second:
            recyleKeyList.append(i)
            cancel_order(exchange, order)
        time.sleep(0.1)
    time.sleep(5)

#recycling_money 
# 正向, 第二步没成功 卖quote,第三步没成功 卖base
# 负向, 第二步没成功 卖base,第三步没成功 卖quote
def recycling_money(exchange, order_data={}, key_list=[]):
    if key_list is None:
        return
    for i in key_list:
        t = order_data[r]
        symbol = ""
        size = 0
        if "p3id" in t: #第三步没成功 第二步成功
            symbol = t["quote"] + "/" + t["mid"]
            size = t["quote_size"]
        else: #第二步没成功
            symbol = t["base"] + "/" + t["mid"]
            size = t["base_size"]
    
        try:
            exchange.create_order(symbol, 'market', 'sell',  size)
        except Exception as e:
            print(e)


def cancel_order(exchange, order):
    if "p3id" in order:
        try:
            exchange.cancel_order(order["p3id"])
        except Exception as e:
            print('cancel_orders e is {} ,exchange is {}'.format(e.args[0],exchange.name))
            return

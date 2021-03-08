import time
import threading

wait_time_in_second  = 180
# recycle 取消未成交的挂单,收回所有钱
orderData = {}
def recycle(exchange, orderData={}):
    while True:
        now = datetime.now()  # 获取当前时间
        for i in list(orderData):
            order = orderData[i]
            if (now - order.time).seconds > wait_time_in_second:
                cancel_orders(exchange, order)
            time.sleep(0.1)
         time.sleep(5)




def cancel_orders(exchange, order):
    exchange.cancel_order(order["id"])
    result = exchange.create_order(p1, 'market', 'sell', quote_size)


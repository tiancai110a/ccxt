import time
import threading
order_data = {}


def recycle(order_data={}):
    while True:
        for i in list(order_data):
            print("%s:%s" % (i, order_data[i]))
        time.sleep(0.1)

worker_thread1 = threading.Thread(target=recycle, args=(order_data,))
worker_thread1.start()
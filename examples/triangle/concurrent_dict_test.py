import time
import threading
orderData = {}


def recycle(orderData={}):
    while True:
        for i in list(orderData):
            print("%s:%s" % (i, orderData[i]))
        time.sleep(0.1)

worker_thread1 = threading.Thread(target=recycle, args=(orderData,))
worker_thread1.start()
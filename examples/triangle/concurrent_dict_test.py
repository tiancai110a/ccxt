import time
import threading
orderData = {}


def recycle(orderData={}):
    while True:
        for i in list(orderData):
            print("%s:%s" % (i, orderData[i]))
        time.sleep(0.1)

        
def write(orderData={}):
    i=0
    while True:
       i = i + 1
       orderData[i] = i
     # print("====",i)
       time.sleep(0.01)


worker_thread1 = threading.Thread(target=recycle, args=(orderData,))
worker_thread1.start()

worker_thread2 = threading.Thread(target=write, args=(orderData,))
worker_thread2.start()
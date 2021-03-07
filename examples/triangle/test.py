import ccxt
import time
from datetime import datetime
import asyncio
config_key={}
config_key['binance'] = ['i3bEQ2PECV68BDMRXuQO1nWvn8WNr2mXa1RCJs8MB1GK6Ge0qcxjrOomutR0QkU5','QlFZ6xbAQ6myXWXYoBKrwXwbuLM57tSRxNwxOWUqaSFsI3GJCzZ21BoI40trTknU']

exchange = getattr(ccxt,"binance")()
exchange.enableRateLimit = True
exchange.apiKey = config_key["binance"][0]
exchange.secret = config_key["binance"][1]

#result = exchange.create_order("ADA/BTC", 'limit', 'sell', 10, 0.00002238)



async def testFunc(i):
   print("==testFunc1",i)
   await asyncio.sleep(5)
   print("==testFunc2", i)
   
async def hello(i):
   print("==hello1",i)
   await asyncio.sleep(1)
   print("==hello2", i)
   
def testExeption():
    raise Exception("order error!")

def testFunc1():
    try:
        testExeption()
    except Exception as e:
        raise Exception("hello!",e)

    return {"id",12}
   
# # print(result)
# a = datetime.fromtimestamp(result["timestamp"]/1000)
# time.sleep(2)      #睡眠两秒
# b = datetime.now()  # 获取当前时间
# durn = (b-a).seconds  #两个时间差，并以秒显示出来
# print(durn)
# loop = asyncio.get_event_loop()
# taskList = []  
# taskList.append(testFunc(1))
# #taskList.append(hello(2))
# loop.run_until_complete(asyncio.gather(*taskList))

# result = {}
# try:
#     #testExeption()
#     result = testFunc1()
# except Exception as e:
#     if "id" not in result:
#         print("not in result",e)
#     else:
#         print("in result",result)

order = exchange.fetch_order(310002835, "ADA/BTC")
print(order)
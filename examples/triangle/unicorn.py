from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
import logging
import os
import time
import threading
import json


tickerData ={}

# https://docs.python.org/3/library/logging.html#logging-levels
logging.basicConfig(level=logging.DEBUG,
                    filename=os.path.basename(__file__) + '.log',
                    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
                    style="{")

binance_websocket_api_manager = BinanceWebSocketApiManager()


def print_stream_data_from_stream_buffer(binance_websocket_api_manager):
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        oldest_stream_data_from_stream_buffer = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()
        if oldest_stream_data_from_stream_buffer is False:
            time.sleep(0.01)
        else:
            try:
                data = json.loads(oldest_stream_data_from_stream_buffer)
                symbol = data['data']['s']
                tickerData[symbol] ={}
                tickerData[symbol]['bid'] = data['data']['b']
                tickerData[symbol]['bidsize'] = data['data']['B']
                tickerData[symbol]['ask'] = data['data']['a']
                tickerData[symbol]['asksize'] = data['data']['A']
            except Exception:
                binance_websocket_api_manager.add_to_stream_buffer(oldest_stream_data_from_stream_buffer)


def consumer():
   while True:
        print("==>",tickerData)
        time.sleep(1)





# start a worker process to process to move the received stream_data from the stream_buffer to a print function
worker_thread = threading.Thread(target=print_stream_data_from_stream_buffer, args=(binance_websocket_api_manager,))
worker_thread.start()
worker_thread1 = threading.Thread(target=consumer)
worker_thread1.start()


markets = ['btcusdt','eosbtc', 'eosusdt']



print("\r\n======================================== Starting ticker ==============================================\r\n")
ticker_stream_id = binance_websocket_api_manager.create_stream(["ticker"], markets)

while True:
    time.sleep(1)

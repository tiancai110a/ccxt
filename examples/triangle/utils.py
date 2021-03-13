import socket
import ccxt.async_support as ccxta

config_key = dict()
config_key['binance'] = ['i3bEQ2PECV68BDMRXuQO1nWvn8WNr2mXa1RCJs8MB1GK6Ge0qcxjrOomutR0QkU5','QlFZ6xbAQ6myXWXYoBKrwXwbuLM57tSRxNwxOWUqaSFsI3GJCzZ21BoI40trTknU']
proxy_flag = False


def set_proxy():
    if proxy_flag:
        os.environ.setdefault('http_proxy', 'http://127.0.0.1:1087')
        os.environ.setdefault('https_proxy', 'http://127.0.0.1:1087')

# 设置交易所key
def set_exchange_key(exchange,good_list):
    if exchange.id in good_list:
        exchange.apiKey = config_key[exchange.id][0]
        exchange.secret = config_key[exchange.id][1]
        print('set_exchange_key name is {},key is {},secret is {}'.format(exchange.name,exchange.apiKey,exchange.secret))
    else:
        print('set_exchange_key name is {} no key'.format(exchange.name))


def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


# 获取指定交易所列表
# 获取指定交易所列表
def get_exchange_list(good_list):
    exchange_list = []
    for exchange_name in good_list:
        exchange = getattr(ccxta,exchange_name)()
        if exchange:
            exchange.enableRateLimit = True
            exchange_list.append(exchange)
            set_exchange_key(exchange ,good_list)
    return exchange_list


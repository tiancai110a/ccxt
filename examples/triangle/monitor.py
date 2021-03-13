# from prometheus_client import CollectorRegistry, Gauge, push_to_gateway, Summary, Histogram
from time import sleep

# registry = CollectorRegistry()

# cpu_util_sum_metric = Summary('haha_util_summary111', 'haha_util_summary111', registry=registry)
# cpu_util_hist_metric = Summary('haha_util_hist111', 'haha_util_hist111', registry=registry)

# while True:
#   cpu_util = randint(0, 100)

#   cpu_util_sum_metric.observe(float(cpu_util))
#   cpu_util_hist_metric.observe(float(cpu_util))
#   print('cpu util is: {}'.format(cpu_util))
#   res = push_to_gateway('localhost:9091', job='cpu_stats', registry=registry)
#   print('push_to_gateway result is:', str(res))
#   sleep(0.01)



from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from random import randint, random
import  time
registry = CollectorRegistry()
g = Gauge('job_last_success_unixtime', 'Last time a batch job successfully finished', registry=registry)
while True:
    cpu_util = randint(0, 100)
    print(cpu_util)
    g.set(float(-cpu_util))
    res =push_to_gateway('localhost:9091', job='test_batchA', registry=registry)
    time.sleep(0.01)
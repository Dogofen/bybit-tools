import backtrader as bt
import datetime
import sys
from vwap_strategy import VwapStrategy

if '--Test' in sys.argv:
    data = bt.feeds.GenericCSVData(
        dataname='BTC_5m.csv',
        datetime=0,
        high=2,
        close=4,
        open=1,
        volume=5,
        dateformat='%Y-%m-%d %H:%M:%S',
        fromdate=datetime.datetime(2020, 12, 1, 2, 0, 0),
        todate=datetime.datetime(2020, 12, 7, 0, 0, 0),
        timeframe=bt.TimeFrame.Minutes,
        compression=5)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.broker.set_cash(200000)
    cerebro.addstrategy(VwapStrategy)
    print("Start Value {}".format(cerebro.broker.getvalue()))
    cerebro.run()
    print("End Value {}".format(cerebro.broker.getvalue()))
else:
    vwap = VwapStrategy()
    vwap.next()

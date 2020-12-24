from botlogger import Logger
import datetime
from time import sleep
from bybit_tools import BybitTools
import configparser


class VwapStrategy(BybitTools):
    old_position = False
    last_big_deal = False
    new_big_deal = False
    targets = []
    stop_px = False
    amount = False
    fill_thresh_hold = 1
    in_a_trade = False
    win = False
    wait = False
    wait_time = 0
    wait_time_limit = False
    price_above = False

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('conf.ini')
        self.targets = [
            float(self.config["Vwap"]["Target0"]),
            float(self.config["Vwap"]["Target1"]),
            float(self.config["Vwap"]["Target2"])
        ]
        self.stop_px = self.config["Vwap"]["StopPx"]
        self.wait_time_limit = int(self.config["Vwap"]["WaitTimeLimit"])
        self.amount = self.config["OTHER"]["Amount"]
        super(VwapStrategy, self).__init__()
        bot_logger = Logger()
        self.logger = bot_logger.init_logger()
        self.logger.info('Applying Big Deal Strategy')

    def next(self):
        symbol = "BTCUSD"
        while True:
            if datetime.datetime.now().second != 0:
                sleep(1)
                continue
            vwap = self.get_vwap(symbol)
            last_price = self.get_last_price_close(symbol)
            position = self.true_get_position(symbol)
            position_size = self.get_position_size(position)

            if position_size == 0 and self.in_a_trade:  # Finish Operations
                print("Trade was finished, win: {} cancelling Orders".format(self.win))
                self.logger.info("Trade was finished, win: {} cancelling Orders".format(
                    self.win
                    )
                )
                if not self.win:
                    self.wait = True
                self.cancel_all_orders(symbol)
                self.in_a_trade = False
                self.amount = self.config["OTHER"]["Amount"]
                self.win = False

            if position_size != 0 and self.in_a_trade:  # When in Trade, maintaining
                stop = self.orders[0]
                self.amount = self.maintain_trade(symbol, stop, self.amount)

            if position_size != 0 and not self.in_a_trade:  # When limit order just accepted
                self.in_a_trade = True
                if len(self.orders) == 1:
                    order = self.orders.pop()
                    if position_size < 0:
                        side = "Sell"
                    else:
                        side = "Buy"
                    self.initiate_trade(symbol, self.amount, side, self.targets, self.stop_px+'%')

            if not self.in_a_trade and len(self.orders) == 1:  # Editing Order every tick to fit vwap
                self.edit_orders_price(symbol, self.orders[0], vwap)

            if not self.in_a_trade and len(self.orders) == 0 and not self.wait:  # Send First Limit order
                if last_price > vwap:
                    self.orders.append(self.limit_order(symbol, "Buy", self.amount, vwap))
                else:
                    self.orders.append(self.limit_order(symbol, "Sell", self.amount, vwap))

            if self.wait:  # If waiting is needed between trades
                if last_price < vwap and self.price_above:  # Price just crossed vwap
                    self.wait_time = 0
                if last_price > vwap and not self.price_above:  # Price just crossed vwap
                    self.wait_time = 0
                self.wait_time += 1
                if self.wait_time == self.wait_time_limit:
                    self.wait = False
                    self.wait_time = 0
            if last_price > vwap:
                self.price_above = True
            else:
                self.price_above = False


vwap_strategy = VwapStrategy()
vwap_strategy.next()

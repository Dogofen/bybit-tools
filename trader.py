import bybit
import os
import configparser
import datetime
from time import sleep
from botlogger import Logger

class Trader (object):

    API_KEY = ''
    API_SECRET = ''

    logger = ''
    bybit  = ''
    symbol = ''
    targets= ''
    amount= ''
    stopPx = ''
    openOrders = ''
    env = ''
    leverage = ''
    price = ''
    side = ''
    last_big_deal = ''
    rate_limit_status = ''

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('conf.ini')
        self.API_KEY = config['API_KEYS']['api_key']
        self.API_SECRET = config['API_KEYS']['api_secret']
        self.leverage = config['OTHER']['leverage']
        self.env = config['OTHER']['env']
        botLogger = Logger()
        self.logger = botLogger.init_logger()
        self.logger.info('Boti Trading system initiated')

        if self.env == 'test':
            test = True
        elif self.env == 'prod':
            test = False
        self.bybit = bybit.bybit(test=test, api_key=self.API_KEY, api_secret=self.API_SECRET)
        #self.logger.info(self.bybit.Positions.Positions_saveLeverage(symbol=self.symbol, leverage=self.leverage).result())
        self.logger.info("Finished Trade construction, proceeding")


    def __destruct(self):
        self.logger.info('---------------------------------- End !!!!! ----------------------------------')

    def edit_orders_price(self, symbol, order_id, price):
        self.logger.info("editing order price={}.".format(price))
        self.logger.info(self.bybit.Order.Order_replace(symbol=symbol, order_id=order_id, p_r_price=price).result())

    def create_order(self, order_type, symbol, side, amount, price):
        self.logger.info("Sending a Create Order command type => {} side =>{} amount=>{} price=>{}".format(order_type, side, amount, price))
        try:
            order = self.bybit.Order.Order_new(side=side,symbol=symbol,order_type=order_type,qty=amount,price=price,time_in_force="GoodTillCancel").result()[0]['result']
        except Exception as e:
            self.logger.error("Create Trade Failed {}".format(e))
            quit()
        return order

    def true_get_position(self, symbol):
        position = False
        fault_counter = 0
        while position == False:
            if fault_counter > 5:
                self.logger.error("position Failed to retrieved fault counter has {} tries".format(fault_counter))
            position = self.bybit.Positions.Positions_myPosition(symbol=symbol).result()[0]
            fault_counter += 1
            sleep(1)
        self.rate_limit_status = position['rate_limit_status']
        return position['result']

    def get_open_position(self, symbol):
        return self.bybit.Positions.Positions_myPosition(symbol=symbol).result()[0]['result']

    def is_open_position(self):
        open_position = self.get_open_position();
        if(open_position['size'] == 0):
            return False
        return open_position

    def get_open_order_by_id(self, order_id):
        return self.bybit.Order.Order_getOrders(order_id=order_id).result()[0]['result']['data'][0]

    def get_order_book(self, symbol):
        return self.bybit.Market.Market_orderbook(symbol=symbol).result()[0]['result']

    def get_limit_price(self, symbol, side):
        order_book = self.get_order_book(symbol)
        if side == "Buy":
            return order_book[0]['price']
        for order in order_book:
            if order["side"] == side:
                return order['price']

    def limit_open_or_close_position(self, symbol, side, amount):
        limit_price = self.get_limit_price(side)
        order = self.create_order('Limit', symbol, side, amount, limit_price)
        sleep(1)
        if self.get_open_order_by_id(order['order_id'])['order_status'] == 'Filled':
            self.logger.info("Limit order was filled, price=>{}".format(limit_price))
            return
        while self.get_open_order_by_id(order['order_id'])['order_status'] != 'Filled':
            tmp_limit_price = self.get_limit_price(side)
            if tmp_limit_price != limit_price:
                limit_price = tmp_limit_price
                self.edit_orders_price(order["order_id"], limit_price)
            sleep(1)
        self.logger.info("Limit order was filled, price=>{}".format(limit_price))


    def limit_order(self, symbol, side, amount, price=False):
        if price == False:
            limit_price = self.get_limit_price(symbol, side)
        else:
            limit_price = price
        self.create_order('Limit', symbol, side, amount, limit_price)


    def create_stop(self, symbol, stop_px):
        position = self.true_get_position(symbol)
        base_price = int(float(position['entry_price']))
        if position['side'] == 'Buy':
            side = 'Sell'
            side_scelar = -1
        else:
            side = 'Buy'
            side_scelar = 1
        amount = str(position['size'])
        if '%' in stop_px:
            stop_px = base_price + side_scelar * float(stop_px.replace('%',''))*base_price/100
        elif '$' in stop_px:
            stop_px = base_price + side_scelar * int(stop_px.replace('$',''))/amount * base_price
        stop_px = int(stop_px)
        stop_px = str(stop_px)
        amount = str(amount)
        base_price = str(base_price)
        s = self.bybit.Conditional.Conditional_new(order_type="Market",side=side,symbol=symbol,qty=amount,stop_px=stop_px,base_price=base_price,time_in_force="GoodTillCancel").result()
        self.logger.info("Sending a Create Stop command side =>{} stop =>{}".format(side, stop_px))
        return s[0]['result']


    def print_bid_ask_summery(self, symbol):
        while(True):
            Sell_array = []
            Buy_array = []
            order_book = self.bybit.Market.Market_orderbook(symbol=symbol).result()[0]['result']
            for o in order_book:
                if o['side'] == 'Sell':
                    Sell_array.append(int(o['size']))
                else:
                    Buy_array.append(int(o['size']))
            sum_sell = sum(Sell_array)
            sum_buy = sum(Buy_array)
            total = sum_buy + sum_sell
            os.system('clear')
            print("Sell pressure: {} {}%".format(sum_sell, round(sum_sell/total*100,2)))
            print("Buy  pressure: {} {}%".format(sum_buy, round(sum_buy/total*100,2)))
            sleep(2)

    def update_last_big_deal(self,symbol):
        new_big_deal = False
        new_big_deal = self.bybit.Market.Market_bigDeal(symbol=symbol).result()[0]['result'][0]
        new_big_deal['timestamp']=datetime.datetime.fromtimestamp(new_big_deal['timestamp']).strftime("%d/%m/%Y, %H:%M:%S")
        if new_big_deal != self.last_big_deal:
            self.last_big_deal = new_big_deal


    def print_last_big_deal(self, symbol):
        new_big_deal = self.last_big_deal
        while(True):
            self.update_last_big_deal(symbol)
            if new_big_deal != self.last_big_deal:
                new_big_deal = self.last_big_deal
                print(new_big_deal)
            sleep(2)

    def wait_for_limit_order_fill(self, symbol):
        position = self.true_get_position(symbol)
        counter = 0
        while position['side'] == 'None' and counter < 605:
            position = self.true_get_position(symbol)
            counter += 1
            sleep(1)
        if counter > 60:
            self.logger.info("order did not met time constraints")
            self.bybit.Order.Order_cancelAll(symbol=symbol).result()
            return False
        else:
            return True

    def trade(self, symbol, quantity, side, targets, stop_px):
        self.logger.info('---------------------------------- New Trade ----------------------------------')
        self.limit_order(symbol, side, quantity)
        succes = self.wait_for_limit_order_fill(symbol)
        if not succes:
            return False
        stop = self.create_stop(symbol, stop_px)
        if side == 'Buy':
            opposite_side = 'Sell'
        else:
            opposite_side = 'Buy'

        for t in targets:
            self.limit_order(symbol, opposite_side, quantity/3, t)

        position = self.true_get_position(symbol)
        while position['side'] != 'None':
            if position['size'] != quantity:
                self.logger.info("Amending stop as limit was filled")
                quantity = position['size']
                self.bybit.Conditional.Conditional_replace(symbol=symbol, stop_order_id=stop['stop_order_id'],p_r_qty=str(quantity)).result()
            position = self.true_get_position(symbol)
            if self.rate_limit_status < 20:
                print('rate limit status is dangerously low {}'.format(self.rate_limit_status))
                self.logger.warning('rate limit status is dangerously low {}'.format(self.rate_limit_status))
            sleep(1)
        self.logger.info("Trade has finished")
        try:
            self.bybit.Conditional.Conditional_cancelAll(symbol=symbol).result()
        except Exception as e:
            self.logger.error("cncelling stop order failed")
            self.logger.error(e)
        try:
            self.bybit.Order.Order_cancelAll(symbol=symbol).result()
        except Exception as e:
            self.logger.error("cancelling limit orders failed")
            self.logger.error(e)









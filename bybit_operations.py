import bybit
import configparser
import datetime
from time import sleep
from botlogger import Logger


class BybitOperations(object):

    API_KEY = ''
    API_SECRET = ''

    logger = ''
    bybit  = ''
    env = ''
    day_open_dict = {
        '01': "02:00:00",
        '02': "02:00:00",
        '03': "02:00:00",
        '04': "03:00:00",
        '05': "03:00:00",
        '06': "03:00:00",
        '07': "03:00:00",
        '08': "03:00:00",
        '09': "03:00:00",
        '10': "03:00:00",
        '11': "02:00:00",
        '12': "02:00:00"
    }

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('conf.ini')
        self.API_KEY = config['API_KEYS']['api_key']
        self.API_SECRET = config['API_KEYS']['api_secret']
        self.env = config['OTHER']['env']
        bot_logger = Logger()
        self.logger = bot_logger.init_logger()

        if self.env == 'test':
            test = True
        elif self.env == 'prod':
            test = False
        self.bybit = bybit.bybit(test=test, api_key=self.API_KEY, api_secret=self.API_SECRET)
        self.logger.info("Finished BybitTools construction, proceeding")

    def edit_orders_price(self, symbol, order_id, price):
        order_id = order_id['order_id']
        self.logger.info("editing order:{} price:{}.".format(order_id, price))
        self.logger.info(self.bybit.Order.Order_replace(symbol=symbol, order_id=order_id, p_r_price=str(price)).result())

    def get_month(self):
        return datetime.datetime.now().strftime('%m')

    def get_day_open(self):
        date_now = datetime.datetime.now()
        date_from = datetime.datetime.strptime(date_now.strftime('%Y-%m-%d ' '%H:00:00'), '%Y-%m-%d ' '%H:%M:%S')
        day_open = self.day_open_dict[self.get_month()]
        while date_from.strftime('%H:%M:%S') != day_open:
            date_from = date_from - datetime.timedelta(hours=1)
        return date_from.timestamp()

    def get_big_deal(self, symbol):
        try:
            bd = self.bybit.Market.Market_bigDeal(symbol=symbol).result()[0]['result'][0]
        except Exception as e:
            self.logger.error("edit stop order Failed {}".format(e))
        return bd

    def edit_stop(self, symbol, stop_id, p_r_qty, p_r_trigger_price):
        stop_id = stop_id['stop_order_id']
        try:
            self.bybit.Conditional.Conditional_replace(
                symbol=symbol,
                stop_order_id=stop_id,
                p_r_qty=str(p_r_qty),
                p_r_trigger_price=str(p_r_trigger_price)
            ).result()
        except Exception as e:
            self.logger.error("edit stop order Failed {}".format(e))

    def create_order(self, order_type, symbol, side, amount, price):
        self.logger.info("Sending a Create Order command type => {} side =>{} amount=>{} price=>{}".format(order_type, side, amount, price))
        try:
            order = self.bybit.Order.Order_new(
                side=side,
                symbol=symbol,
                order_type=order_type,
                qty=amount,
                price=price,
                time_in_force="GoodTillCancel"
            ).result()[0]['result']
        except Exception as e:
            self.logger.error("Create Trade Failed {}".format(e))
            quit()
        return order

    def get_date(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def get_kline(self, symbol, interval, _from):
        kline = False
        fault_counter = 0
        while not kline:
            if fault_counter > 5:
                self.logger.error("Kline Failed to retrieved fault counter has {} tries".format(fault_counter))
            try:
                kline = self.bybit.Kline.Kline_get(
                    symbol=symbol, interval=interval, **{'from': _from}
                ).result()[0]['result']

            except Exception as e:
                self.logger.error("get Kline returned: {} error was: {}".format(kline, e))
                kline = False
                sleep(2)

            fault_counter += 1
            sleep(1)
        return kline

    def get_last_price_close(self, symbol):
        try:
            kline = self.get_kline(
                symbol,
                self.interval,
                (datetime.datetime.now() - datetime.timedelta(minutes=int(self.interval))).timestamp()
            )
        except Exception as e:
            self.logger.error("get Kline returned: {} error was: {}".format(kline, e))
        return int(float(kline[0]['close']))

    def cancel_all_orders(self, symbol):
        try:
            self.bybit.Conditional.Conditional_cancelAll(symbol=symbol).result()
        except Exception as e:
            self.logger.error("Failed cancelling Orders {}".format(e))
            return
        try:
            self.bybit.Order.Order_cancelAll(symbol=symbol).result()
        except Exception as e:
            self.logger.error("Failed cancelling Orders {}".format(e))
            return
        return True

    def true_get_position(self, symbol):
        position = False
        fault_counter = 0
        while position == False:
            if fault_counter > 5:
                self.logger.error("position Failed to retrieved fault counter has {} tries".format(fault_counter))
            position = self.bybit.Positions.Positions_myPosition(symbol=symbol).result()[0]
            try:
                self.rate_limit_status = position['rate_limit_status']
            except Exception as e:
                self.logger.error("get position returned: {} error was: {}".format(position, e))
                self.logger.info("self rate limit: {}".format(self.rate_limit_status))
                position = False
                sleep(2)

            fault_counter += 1
            sleep(1)
        return position['result']

    def get_position_size(self, position):
        return position['size']

    def get_position_price(self, position):
        return float(position['entry_price'])

    def is_open_position(self):
        open_position = self.true_get_position();
        if(open_position['size'] == 0):
            return False
        return open_position

    def get_order_book(self, symbol):
        return self.bybit.Market.Market_orderbook(symbol=symbol).result()[0]['result']

    def limit_order(self, symbol, side, amount, price=False):
        if price == False:
            limit_price = self.get_limit_price(symbol, side)
        else:
            limit_price = price
        return self.create_order('Limit', symbol, side, amount, limit_price)

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
        s = self.bybit.Conditional.Conditional_new(
            order_type="Market",
            side=side,
            symbol=symbol,
            qty=amount,
            stop_px=stop_px,
            base_price=base_price,
            time_in_force="GoodTillCancel"
        ).result()
        self.logger.info("Sending a Create Stop command side =>{} stop =>{}".format(side, stop_px))
        self.logger.info("Command's result: {}".format(s[0]['result']))
        return s[0]['result']










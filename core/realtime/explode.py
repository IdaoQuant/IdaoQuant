"""
@ File:     explode.py
@ Author:   pleiadesian
@ Datetime: 2020-01-16 20:51
@ Desc:     time share exploding detection
"""
import os
import datetime
import tushare as ts
import api.ts_map as tm
import api.storage as st

DEBUG = 0

# TODO: print more info in log for debug
# TODO: handle stocks with free share larger than 10,000,000,000

OPEN_UPPER_LIMIT = 0.1  # default 0.03
OPEN_LOWER_LIMIT = -0.05  # default -0.02 | -0.03

# TODO: CHANGE TO -0.05
# RUSH_LOWER_LIMIT = -0.09  # default -0.03

AMOUNT_THRESHOLD = 100  # 1,000,000 volume of transaction
TURNOVER_THRESHOLD = 8  # turnover rate 2.5%, default 0.6% | 2.5%
SMALL_TURNOVER_THRESHOLD = 8
VOLUME_RATIO_THRESHOLD = 0.6

EXPLODE_RISE_RATIO_THRESHOLD = 0.0158
ACCER_THRESHOLD = 0.01  # ￥0.01
LARGE_ACCER_THRESHOLD = 0.01  # %2
MORNING_ACCER_THRESHOLD = 0.005

RELATIVE_LARGE_VOLUME_THRESHOLD = 50  # default 58
SMALL_ABSOLUTE_LARGE_VOLUME_THRESHOLD = 3.5  # default 350% | 250%
ABSOLUTE_LARGE_VOLUME_THRESHOLD = 0.95  # default 127%
BIG_ABSOLUTE_LARGE_VOLUME_THRESHOLD = 0.9  # default 50%
SUPERBIG_ABSOLUTE_LARGE_VOLUME_THRESHOLD = 0.9  # default 40%

SMALL_FREE_SHARE = 26000  # default 12000
LARGE_FREE_SHARE = 50000
SUPERLARGE_FREE_SHARE = 200000

LOW_PRICE_BOUND = -0.01

path = os.getenv('PROJPATH')


class TimeShareExplosion:
    def __init__(self):
        self.deal_volume = dict()
        self.deal_price = dict()
        self.deal_bid = dict()
        self.deal_ask = dict()
        for code in tm.ts_mapping:
            self.deal_volume[code] = (0.0, datetime.datetime.now())
            self.deal_price[code] = 0.0
            self.deal_bid[code] = (0.0, 0.0)
            self.deal_ask[code] = (0.0, 0.0)

    def detect_timeshare_explode(self, storage, code):
        assert(isinstance(code, list) is False)
        basic_infos = storage.get_basicinfo_single(tm.ts_mapping[code])
        hist_data = storage.get_histdata_single(tm.ts_mapping[code])[-5:]
        info = storage.get_realtime_storage_single(code)

        volume = float(info[8]) / 100  # calculation by Lot
        volume_ma5 = sum(hist_data['vol']) / len(hist_data)
        volume_ma5_deal = sum(hist_data['vol']) / (len(hist_data) * 240 * 20)
        today_open = float(info[1])
        pre_close = float(info[2])
        price = float(info[3])
        high = float(info[4])
        low = float(info[5])
        amount = float(info[9])
        bid = float(info[20]) / 100
        bid_price = float(info[21])
        ask = float(info[10]) / 100
        ask_price = float(info[11])
        free_share = basic_infos['free_share']

        time = info[31]
        time = datetime.datetime.strptime(time, "%H:%M:%S")
        sec_delta = (time - self.deal_volume[code][1]).seconds
        # in case of re-fetch same data
        if sec_delta == 0:
            return False
        # in case of time delta
        curr_deal_volume = (volume - self.deal_volume[code][0]) / sec_delta * 3
        curr_deal_accer = (price - self.deal_price[code]) / sec_delta * 3
        curr_deal_accer_percent = (price - self.deal_price[code]) / sec_delta * 3 / pre_close
        curr_deal_positive_ask = self.deal_bid[code][0] - bid
        curr_deal_positive_bid = self.deal_ask[code][0] - ask

        if time <= datetime.datetime.strptime('11:30:00', "%H:%M:%S"):
            minutes_elapse = (time - datetime.datetime.strptime('9:30:00', "%H:%M:%S")).seconds / 60
        else:
            minutes_elapse = 120 + (time - datetime.datetime.strptime('13:00:00', "%H:%M:%S")).seconds / 60

        if minutes_elapse == 0:
            minutes_elapse = 1

        if self.deal_price[code] == 0.0:
            self.deal_volume[code] = (volume, time)
            self.deal_price[code] = price
            self.deal_bid[code] = (bid, bid_price)
            self.deal_ask[code] = (ask, ask_price)
            return False

        turnover_rate = volume * 240 / free_share / minutes_elapse  # customized turnover_rate
        volume_ratio = volume * 240 / volume_ma5 / minutes_elapse
        deal_volume_ratio = curr_deal_volume / volume_ma5_deal
        deal_turnover_rate = curr_deal_volume * 20 * 240 / free_share / 100

        open_ratio = (today_open - pre_close) / pre_close
        rise_ratio = (price - pre_close) / pre_close
        high_ratio = (high - pre_close) / pre_close
        low_ratio = (low - pre_close) / pre_close

        if free_share < SMALL_FREE_SHARE:
            absolute_large_volume = deal_turnover_rate > SMALL_ABSOLUTE_LARGE_VOLUME_THRESHOLD
            turnover_threshold = SMALL_TURNOVER_THRESHOLD
        elif free_share < LARGE_FREE_SHARE:
            absolute_large_volume = deal_turnover_rate > ABSOLUTE_LARGE_VOLUME_THRESHOLD
            turnover_threshold = SMALL_TURNOVER_THRESHOLD
        elif free_share < SUPERLARGE_FREE_SHARE:
            absolute_large_volume = deal_turnover_rate > BIG_ABSOLUTE_LARGE_VOLUME_THRESHOLD
            turnover_threshold = TURNOVER_THRESHOLD
        else:
            absolute_large_volume = deal_turnover_rate > SUPERBIG_ABSOLUTE_LARGE_VOLUME_THRESHOLD
            turnover_threshold = TURNOVER_THRESHOLD

        rush_not_broken = OPEN_LOWER_LIMIT <= open_ratio <= OPEN_UPPER_LIMIT
        # rush_not_broken &= low_ratio >= RUSH_LOWER_LIMIT

        active_stock = turnover_rate >= turnover_threshold and volume_ratio > VOLUME_RATIO_THRESHOLD
        relative_large_volume = deal_volume_ratio > RELATIVE_LARGE_VOLUME_THRESHOLD

        exploded = amount / 10000 > AMOUNT_THRESHOLD
        exploded &= active_stock

        exploded &= rush_not_broken
        # exploded &= rise_ratio >= EXPLODE_RISE_RATIO_THRESHOLD
        exploded &= curr_deal_accer >= ACCER_THRESHOLD or \
                    curr_deal_accer_percent >= LARGE_ACCER_THRESHOLD or \
                    (-0.01 < curr_deal_accer < 0.01 and
                     bid_price >= self.deal_bid[code][1] and
                     (bid_price > self.deal_bid[code][1] or
                      curr_deal_positive_ask >= 0.5 * (volume - self.deal_volume[code][0])))
                     # and
                     # ask_price >= self.deal_ask[code][1] and
                     # (ask_price > self.deal_ask[code][1] or
                     #  curr_deal_positive_bid <= 0.5 * (volume - self.deal_volume[code][0])))
        exploded &= (relative_large_volume or absolute_large_volume)
        # if code == '000955':
        #     print(str(time) + ' '+str(curr_deal_volume))

        self.deal_volume[code] = (volume, time)
        self.deal_price[code] = price
        self.deal_bid[code] = (bid, bid_price)
        self.deal_ask[code] = (ask, ask_price)

        # in case of booming
        if minutes_elapse <= 60:
            accer_percent_threshold = MORNING_ACCER_THRESHOLD
            if exploded and curr_deal_accer_percent >= accer_percent_threshold and \
                    curr_deal_accer > ACCER_THRESHOLD:
                return 2
        else:
            accer_percent_threshold = LARGE_ACCER_THRESHOLD
            if active_stock and rush_not_broken and curr_deal_accer_percent >= accer_percent_threshold and \
                    curr_deal_accer > ACCER_THRESHOLD and rise_ratio >= EXPLODE_RISE_RATIO_THRESHOLD:
                return 2

        # in case of low-price transaction
        if exploded and rise_ratio < LOW_PRICE_BOUND and curr_deal_accer_percent < LARGE_ACCER_THRESHOLD:
            print(code + ' too low')
            with open(path + 'stock.log', 'a') as f:
                f.write(code + ' too low' + "\n")
            return False
        return exploded


if __name__ == '__main__':
    storage = st.Storage()
    storage.update_realtime_storage()
    time_share_explotion = TimeShareExplosion()
    ret = time_share_explotion.detect_timeshare_explode(storage, '600804')
    storage.update_realtime_storage()
    ret = time_share_explotion.detect_timeshare_explode(storage, '600804')
    print(ret)



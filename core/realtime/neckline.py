"""
@ File:     neckline.py
@ Author:   pleiadesian
@ Datetime: 2020-01-17 07:20
@ Desc:     Maintaining the state of neckline of stock in time share
"""
import os
import datetime
import time
import numpy as np
import api.storage as st
import api.ts_map as tm

# TODO: print more info in log for debug

DEBUG = 1
TRUNCATE_TIME = 106
TRUNCATE = 0

NECKLINE_UPPER_BOUND = 1.005
NECKLINE_LOWER_BOUND = 0.99
NECKLINE_STEP = 20
NECKLINE_MINUS_STEP = 10

LOW_NECKLINE_INDEX = 17
LOW_NECKLINE_LENGTH_THRESHOLD = 50  # default 60
RECENT_NECKLINE_LENGTH_THRESHOLD = 19  # default 15 | 20
RECENT_GOOD_NECKLINE_LENGTH_THRESHOLD = 12
NECKLINE_LENGTH_THRESHOLD = 30  # default 35
SHORT_GENERAL_NECKLINE_LENGTH_PERCENT = 0.5
NECKLINE_GOOD_LENGTH_THRESHOLD = 90
LONG_NECKLINE_LENGTH_THRESHOLD = 70
SEPARATED_NECKLINE_MIN_GAP = 45
OUTLINER_THRESHOLD = 0.40  # default 0.55 | 0.65
RECENT_OUTLINER_THRESHOLD = 0.45
RECENT_GOOD_OUTLINER_THRESHOLD = 0.05

BOOM_LOWER_BOUND = 0.99  # default 98% | 99%
BOOM_UPPER_BOUND = 1.015  # default 103%
NORMAL_LOWER_BOUND = 0.99  # default 98%
NORMAL_UPPER_BOUND = 1.015  # default 101.5%
HIGH_LOWER_BOUND = 0.995
HIGH_UPPER_BOUND = 1.005

NORMAL_OPEN_HIGH_THRESHOLD = 0.02
LARGE_OPEN_HIGH_THRESHOLD = 0.005
SMALL_FREE_SHARE = 12000
LARGE_FREE_SHARE = 50000
RISE_HIGH_THRESHOLD = 0.025  # default 0.03
LARGE_RISE_HIGH_THRESHOLD = 0.02

MINUTE_ABSOLUTE_VOLUME_THRESHOLD = 1.12  # default 112%

HIGH_PRICE_PERCENT = 1.090  # default 9.5% rise ratio

RUSH_HIGH_THRESHOLD = 1.03

BOOMED_THRESHOLD = 1.005

path = os.getenv('PROJPATH')


class NeckLine:
    def __init__(self, storage):
        self.curr_price = dict()
        self.past_price = dict()
        self.pre_close = dict()
        self.curr_realtime_chart = None
        self.curr_realtime_chart_long = None
        self.storage = storage

    def detect_lower_neckline(self, boomed):
        """
        not used
        :param boomed: high speed rising
        :return: stock that broken high price
        """
        selected = []
        df_list = self.storage.get_realtime_chart(boomed)
        for df in df_list:
            # last 15 minutes rising do not count
            code = df.iloc[0]['code']
            df_hist = df.iloc[:-15]
            highest = max(df_hist['high'].values)
            price = float(self.storage.get_realtime_storage_single(code)[3])
            if price > highest:
                selected.append(code)
        return selected

    def detect_volume_neckline(self, matched, boomed):
        """
        not used
        :param matched: matched list by time share explosion filter
        :param boomed: high speed rising
        :return: filtered matched list by volume neckline detection
        """
        selected = []
        df_list = self.storage.get_realtime_chart(matched + boomed)
        for df in df_list:
            code = df.iloc[0]['code']
            close = df.iloc[-1]['close']
            open_price = df.iloc[0]['close']
            if code in boomed:
                lower_bound = BOOM_LOWER_BOUND
                upper_bound = BOOM_UPPER_BOUND
            else:
                lower_bound = NORMAL_LOWER_BOUND
                upper_bound = NORMAL_UPPER_BOUND
            df = df.iloc[11:]  # exclude yesterday data and morning data

            basic_infos = self.storage.get_basicinfo_single(tm.ts_mapping[code])
            free_share = basic_infos['free_share']
            # df_vol = df[df['volume'] * 240 / free_share / 100 > MINUTE_ABSOLUTE_VOLUME_THRESHOLD]
            # necklines = df_vol['high'].values
            # daytimes = df_vol['day'].values
            necklines = []
            # for daytime, neckline in zip(daytimes, necklines):
            for i in range(1, len(df)-1):
                # if df.iloc[i]['volume'] / 100 * 240 / free_share / 100 > MINUTE_ABSOLUTE_VOLUME_THRESHOLD and \
                #         df.iloc[i]['high'] > df.iloc[i-1]['high'] and df.iloc[i]['high'] > df.iloc[i+1]['high']:
                if df.iloc[i]['volume'] / 100 * 240 / free_share / 100 > MINUTE_ABSOLUTE_VOLUME_THRESHOLD:
                    necklines.append(df.iloc[i]['high'])

            selected_necklines = [0] * 20
            for neckline in necklines:
                neckline_idx = int(((neckline - open_price) / open_price) / 0.005) + 1
                if neckline_idx < 20:
                    selected_necklines[neckline_idx] += 1
            for i in range(0, 20):
                if selected_necklines[i] > 0:
                    neckline_price = open_price * (1 + i * 0.1 / 20)
                    if DEBUG == 1:
                        print(code + ':' + str(neckline_price))
                        with open(path + 'stock.log', 'a') as f:
                            f.write(code + ':' + str(neckline_price) + "\n")
                    if neckline_price * lower_bound <= close <= neckline_price * upper_bound:
                        selected.append(code)
                        if DEBUG == 1:
                            continue
                        else:
                            break
        return selected

    def detect_general_neckline(self, matched, boomed):
        """
        ONLY used after 10:30, recent neckline detection included
        :param matched: matched list by time share explosion filter
        :param boomed: high speed rising
        :return: filtered matched list by neckline detection
        """
        df_list = self.curr_realtime_chart
        selected = []
        selected_recent = self.detect_recent_neckline(matched, boomed)
        if TRUNCATE == 1:
            df_list = [df[:TRUNCATE_TIME] for df in df_list]
        for df in df_list:
            code = df.iloc[0]['code']
            close = self.curr_price[code]
            if TRUNCATE == 1:
                close = df.iloc[-1]['high']
            boom_close = df.iloc[-1]['open']
            open_price = self.pre_close[code]
            limit = round(open_price * 1.1, 2)
            rise_ratio = (close - open_price) / open_price
            basic_infos = self.storage.get_basicinfo_single(tm.ts_mapping[code])
            free_share = basic_infos['free_share']

            if close >= round(open_price * HIGH_PRICE_PERCENT, 2):
                continue

            if close < df.iloc[-1]['open']:
                print(code + "(general neckline): if falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(general neckline): is falling" + "\n")
                continue

            if free_share >= LARGE_FREE_SHARE:
                rise_threshold = LARGE_OPEN_HIGH_THRESHOLD
                rise_high_threshold = LARGE_RISE_HIGH_THRESHOLD
                if close < open_price:
                    if code not in boomed and close < df.iloc[-1]['open'] * BOOMED_THRESHOLD:
                        print(code + "(general neckline): too low and not boomed need: "
                              + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close))
                        with open(path + 'stock.log', 'a') as f:
                            f.write(code + "(general neckline): too low and not boomed" + "\n")
                        continue
            else:
                rise_threshold = NORMAL_OPEN_HIGH_THRESHOLD
                rise_high_threshold = RISE_HIGH_THRESHOLD
                if (close - open_price) / open_price < rise_threshold:
                    if code not in boomed and close < df.iloc[-1]['open'] * BOOMED_THRESHOLD:
                        print(code + "(general neckline): too low and not boomed need: "
                              + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close))
                        with open(path + 'stock.log', 'a') as f:
                            f.write(code + "(general neckline): too low and not boomed" + "\n")
                        continue
                if free_share < SMALL_FREE_SHARE:
                    if code not in boomed and close < df.iloc[-1]['open'] * BOOMED_THRESHOLD:
                        print(code + "(general neckline): too low and not boomed need: "
                              + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close))
                        with open(path + 'stock.log', 'a') as f:
                            f.write(code + "(general neckline): too low and not boomed" + "\n")
                        continue

            highest_recent = max(df.iloc[-5:])
            if len(df) > 5 and highest_recent > close: # and df.iloc[-5]['open'] > close:
                print(code + "(general neckline): is falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(general neckline): is falling" + "\n")
                continue

            # small platform is legal when price is high
            if rise_ratio > rise_high_threshold and code in selected_recent and code not in selected:
                selected.append(code)
                continue

            neckline_list = [open_price * (1 + ratio * 0.1 / NECKLINE_STEP) for ratio in
                             range(-NECKLINE_MINUS_STEP, NECKLINE_STEP)]
            neckline_select = []
            df = df.iloc[:-10]
            # df_recent = df.iloc[-45:] if len(df) > 45 else df[-25:]
            df = df.set_index('high')
            df = df.sort_index()
            # df_recent = df_recent.set_index('high')
            # df_recent = df_recent.sort_index()
            last_length = None
            for i in range(1, NECKLINE_STEP + NECKLINE_MINUS_STEP):
                df_temp = df[(df.index > neckline_list[i - 1]) & (df.index <= neckline_list[i])]
                # according to neckline definition
                if last_length is not None and last_length - len(df_temp) > 3:
                    neck_price = neckline_list[i - 1]
                    upper = neck_price * NECKLINE_UPPER_BOUND
                    lower = neck_price * NECKLINE_LOWER_BOUND
                    # general neckline
                    df_area = df[(df.index > lower) & (df.index < upper)]
                    df_area = df_area[df_area.index < limit]  # do not count limit price
                    # neckline should be longer than 35 minutes
                    if i <= LOW_NECKLINE_INDEX:
                        length_threshold = LOW_NECKLINE_LENGTH_THRESHOLD
                    else:
                        length_threshold = NECKLINE_LENGTH_THRESHOLD
                    if len(df_area) >= NECKLINE_GOOD_LENGTH_THRESHOLD:
                        neckline_select.append((i - 1, code))
                        continue
                    if len(df_area) >= length_threshold or \
                            len(df_area) / len(df) > SHORT_GENERAL_NECKLINE_LENGTH_PERCENT:
                        df_area = df_area.sort_values(by=['day'])
                        # calculate confidence coefficient of this neckline
                        days = df_area['day'].values
                        day_delta = np.array([(i - j).seconds / 60 for i, j in
                                              zip([datetime.datetime.strptime(k, '%Y-%m-%d %H:%M:%S') for k in
                                                   days[1:]],
                                                  [datetime.datetime.strptime(k, '%Y-%m-%d %H:%M:%S') for k in
                                                   days[:-1]])])
                        day_delta = day_delta[(day_delta <= SEPARATED_NECKLINE_MIN_GAP) & (day_delta > 1)]
                        day_delta = day_delta - 1
                        outliners = sum(day_delta)
                        # not too much outliners
                        if outliners / len(df_area) <= OUTLINER_THRESHOLD:
                            neckline_select.append((i - 1, code))
                last_length = len(df_temp)

            # for log
            if DEBUG == 1:
                print([k[1] + '(general neckline): '+str(neckline_list[k[0]]) for k in neckline_select])
                with open(path + 'stock.log', 'a') as f:
                    f.write(str([k[1] + '(general neckline): '+str(neckline_list[k[0]]) for k in neckline_select]) + '\n')
            if len(neckline_select) == 0:
                continue

            # detect neckline-crossing
            if code in self.past_price:
                past_deal = self.past_price[code]
                curr_deal = self.curr_price[code]
                for neckline in neckline_select:
                    if past_deal <= neckline_list[neckline[0]] <= curr_deal:
                        if code in selected_recent and code not in selected:
                            selected.append(code)
                            break
            # detect if price is in a box form
            if code in boomed and close > boom_close:
                lower_bound = BOOM_LOWER_BOUND
                upper_bound = BOOM_UPPER_BOUND
                close = boom_close
                if DEBUG == 1:
                    print(code + '(general neckline): boomed at' + str(boom_close))
                    with open(path + 'stock.log', 'a') as f:
                        f.write(code + '(general neckline): boomed at' + str(boom_close) + '\n')
            else:
                lower_bound = NORMAL_LOWER_BOUND
                upper_bound = NORMAL_UPPER_BOUND
            # boomed stock is over neckline
            for neckline in neckline_select:
                if neckline_list[neckline[0]] * lower_bound <= close <= neckline_list[neckline[0]] * upper_bound:
                    if code in selected_recent and code not in selected:
                        selected.append(code)
                        break
        return selected

    def detect_morning_neckline(self, matched, boomed):
        """
        ONLY used before 10:30, effective on high-open stock
        :param matched: matched list by time share explosion filter
        :param boomed: high speed rising
        :return: filtered matched list by morning neckline detection
        """
        selected = []
        df_list = self.curr_realtime_chart

        if TRUNCATE == 1:
            df_list = [df[:TRUNCATE_TIME] for df in df_list]
        for df in df_list:
            # neckline = [0] * 20
            code = df.iloc[0]['code']
            basic_infos = self.storage.get_basicinfo_single(tm.ts_mapping[code])
            free_share = basic_infos['free_share']
            open_price = self.pre_close[code]
            open_price_today = df.iloc[0]['open']
            limit = round(open_price * 1.1, 2)
            close = self.curr_price[code]
            boom_close = df.iloc[-1]['open']
            highest = max(df['high'].values)

            if close >= round(open_price * HIGH_PRICE_PERCENT, 2):
                continue

            if close < df.iloc[-1]['open']:
                print(code + "(morning neckline): if falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(morning neckline): is falling" + "\n")
                continue

            if close >= limit or highest >= limit:
                print(code + "(morning neckline): at limit")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(morning neckline): at limit" + "\n")
                continue

            highest_recent = max(df.iloc[-5:])
            if len(df) > 5 and highest_recent > close: # and df.iloc[-5]['open'] > close:
                print(code + "(morning neckline): is falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(morning neckline): is falling" + "\n")
                continue

            # morning neckline is effective on high-opened stock
            if free_share >= LARGE_FREE_SHARE:
                open_threshold = LARGE_OPEN_HIGH_THRESHOLD
            else:
                if code not in boomed and close < df.iloc[-1]['open'] * BOOMED_THRESHOLD:
                    print(code + '(morning neckline): not boomed, need: '
                          + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close))
                    with open(path + 'stock.log', 'a') as f:
                        f.write(code + '(morning neckline): not boomed' + '\n')
                    continue
                open_threshold = NORMAL_OPEN_HIGH_THRESHOLD
            if (open_price_today - open_price) / open_price < open_threshold or \
                    (close - open_price) / open_price < open_threshold:
                print(code + "(morning neckline): open too low")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(morning neckline): open too low" + "\n")
                continue

            # average price line can be an neckline for current price
            info = self.storage.get_realtime_storage_single(code)
            amount = float(info[9])
            volume = float(info[8])
            avl = amount / volume
            if code in boomed:
                lower_bound = BOOM_LOWER_BOUND
                upper_bound = BOOM_UPPER_BOUND
                close = boom_close
                if avl * lower_bound <= close <= avl * upper_bound:
                    print(code + "(morning avl):" + str(avl))
                    with open(path + 'stock.log', 'a') as f:
                        f.write(code + "(morning avl):" + str(avl) + "\n")
                    selected.append(code)
                    # if DEBUG == 1:
                    continue
            else:
                lower_bound = NORMAL_LOWER_BOUND
                upper_bound = NORMAL_UPPER_BOUND
            if code in self.past_price and \
                    self.past_price[code] <= avl <= self.curr_price[code]:
                print(code + "(morning avl): crossing " + str(avl))
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(morning avl): crossing " + str(avl) + "\n")
                selected.append(code)
                continue

            # find every peak point
            # highs = df['high'].values
            # neckline_idx = int(((highs[0] - open_price) / open_price) / 0.005) + 1
            # if neckline_idx < 20:
            #     neckline[int(((highs[0] - open_price) / open_price) / 0.005)+1] += 1
            # for i in range(1, len(highs)-1):
            #     if highs[i] >= highs[i-1] and highs[i] >= highs[i+1]:
            #         neckline_idx = int(((highs[i] - open_price) / open_price) / 0.005)+1
            #         if neckline_idx < 20:
            #             neckline[neckline_idx] += 1

            # use open price as a neckline
            # log and select
            # for i in range(0, 20):
            #     if neckline[i] > 0:
            #         neckline_price = open_price * (1 + i * 0.1 / 20)
            if open_price_today >= limit or \
                    highest >= ((open_price_today - open_price) / open_price + RUSH_HIGH_THRESHOLD) * open_price:
                print(code + "(morning): at limit or rush too high")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(morning): at limit or rush too high" + "\n")
                continue
            if DEBUG == 1:
                print(code + "(morning):" + str(open_price_today))
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(morning):" + str(open_price_today) + "\n")
            # detect neckline-crossing
            if code in self.past_price and self.past_price[code] <= open_price_today <= self.curr_price[code]:
                selected.append(code)
                # if DEBUG == 1:
                continue
                # else:
                #     break
            if open_price_today * lower_bound <= close <= open_price_today * upper_bound:
                selected.append(code)
                # if DEBUG == 1:
                continue
                # else:
                #     break
        return selected

    def detect_long_neckline(self, matched, boomed):
        """
        ONLY used before 10:30
        :param matched: matched list by time share explosion filter
        :param boomed: high speed rising
        :return: filtered matched list by long neckline detection
        """
        df_list = self.curr_realtime_chart_long
        selected = []

        if TRUNCATE == 1:
            df_list = [df[:-238+TRUNCATE_TIME] for df in df_list]
        for df in df_list:
            code = df.iloc[0]['code']
            open_price = self.pre_close[code]
            close = self.curr_price[code]
            if TRUNCATE == 1:
                close = df.iloc[-1]['high']
            boom_close = df.iloc[-1]['open']
            limit = round(open_price * 1.1, 2)
            rise_ratio = (close - open_price) / open_price
            basic_infos = self.storage.get_basicinfo_single(tm.ts_mapping[code])
            hist_data = self.storage.get_histdata_single(tm.ts_mapping[code])[-2:]
            free_share = basic_infos['free_share']

            if close >= round(open_price * HIGH_PRICE_PERCENT, 2):
                continue

            if close < df.iloc[-1]['open']:
                print(code + "(long neckline): if falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(long neckline): is falling" + "\n")
                continue

            if free_share >= LARGE_FREE_SHARE:
                rise_threshold = LARGE_OPEN_HIGH_THRESHOLD
            else:
                # if in_morning and code not in boomed and close < df.iloc[-1]['open'] * BOOMED_THRESHOLD:
                #     print(code + '(long neckline): not boomed in the morning need: '
                #           + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close))
                #     with open(path + 'stock.log', 'a') as f:
                #         f.write(code + '(long neckline): not boomed in the morning' + '\n')
                #     continue
                rise_threshold = NORMAL_OPEN_HIGH_THRESHOLD
                if free_share < SMALL_FREE_SHARE:
                    if code not in boomed and close < df.iloc[-1]['open'] * BOOMED_THRESHOLD:
                        print(code + "(long neckline): too low and not boomed need: "
                              + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close))
                        with open(path + 'stock.log', 'a') as f:
                            f.write(code + "(long neckline): too low and not boomed" + "\n")
                        continue
            if rise_ratio < rise_threshold:
                continue

            highest_recent = max(df.iloc[-5:])
            if len(df) > 5 and highest_recent > close: # and df.iloc[-5]['open'] > close:
                print(code + "(long neckline): is falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(long neckline): is falling" + "\n")
                continue

            neckline_list = [open_price * (1 + ratio * 0.1 / NECKLINE_STEP) for ratio in
                             range(-NECKLINE_MINUS_STEP, NECKLINE_STEP)]
            neckline_select = []
            df = df.iloc[:-10]
            df = df.set_index('high')
            df = df.sort_index()
            last_length = None
            for i in range(1, NECKLINE_STEP + NECKLINE_MINUS_STEP):
                df_temp = df[(df.index > neckline_list[i - 1]) & (df.index <= neckline_list[i])]
                # according to neckline defination
                if last_length is not None and last_length - len(df_temp) > 3:
                    neck_price = neckline_list[i - 1]
                    upper = neck_price * NECKLINE_UPPER_BOUND
                    lower = neck_price * NECKLINE_LOWER_BOUND
                    df_area = df[(df.index > lower) & (df.index < upper)]
                    df_area = df_area[df_area.index < limit]  # do not count limit price
                    # neckline should be longer than 35 minutes
                    if len(df_area) >= LONG_NECKLINE_LENGTH_THRESHOLD:
                        df_area = df_area.sort_values(by=['day'])
                        # calculate confidence coefficient of this neckline
                        days = df_area['day'].values
                        day_delta = np.array([(i - j).seconds / 60 for i, j in
                                     zip([datetime.datetime.strptime(k, '%Y-%m-%d %H:%M:%S') for k in days[1:]],
                                         [datetime.datetime.strptime(k, '%Y-%m-%d %H:%M:%S') for k in days[:-1]])])
                        day_delta = day_delta[(day_delta <= SEPARATED_NECKLINE_MIN_GAP) & (day_delta > 1)]
                        day_delta = day_delta - 1
                        outliners = sum(day_delta)
                        # too much outliner
                        if outliners / len(df_area) <= OUTLINER_THRESHOLD:
                            neckline_select.append((i-1, code))
                last_length = len(df_temp)

            if DEBUG == 1:
                print([k[1] + '(long neckline): '+str(neckline_list[k[0]]) for k in neckline_select])
                with open(path + 'stock.log', 'a') as f:
                    f.write(str([k[1] + '(long neckline): '+str(neckline_list[k[0]]) for k in neckline_select]) + '\n')
            if len(neckline_select) == 0:
                continue
            # detect neckline-crossing
            if code in self.past_price:
                past_deal = self.past_price[code]
                curr_deal = self.curr_price[code]
                for neckline in neckline_select:
                    if past_deal <= neckline_list[neckline[0]] <= curr_deal:
                        selected.append(code)
                        break
            # detect if price is in a box form
            if code in boomed and close > boom_close:
                lower_bound = BOOM_LOWER_BOUND
                upper_bound = BOOM_UPPER_BOUND
                close = boom_close
                if DEBUG == 1:
                    print(code + '(long neckline): boomed at' + str(boom_close))
                    with open(path + 'stock.log', 'a') as f:
                        f.write(code + '(long neckline): boomed at' + str(boom_close) + '\n')
            else:
                lower_bound = NORMAL_LOWER_BOUND
                upper_bound = NORMAL_UPPER_BOUND
            # boomed stock is over neckline
            for neckline in neckline_select:
                if neckline_list[neckline[0]] * lower_bound <= close <= neckline_list[neckline[0]] * upper_bound:
                    selected.append(code)
                    break
            # hist_peak_point = hist_data['high'].values
            # for neckline in hist_peak_point:
            #     if neckline * lower_bound <= close <= neckline * upper_bound:
            #         print(code + '(long neckline): select peak point yesterday')
            #         with open(path + 'stock.log', 'a') as f:
            #             f.write(code + '(long neckline): select peak point yesterday\n')
            #         selected.append(code)
            #         break
            # if in_morning:
            #     highest = max(df.index.values)
            #     if close >= highest:
            #         selected.append(code)
        return selected

    def detect_recent_neckline(self, matched, boomed, must_be_high=False):
        """
        used ONLY after 10:30. Detect neckline longer than 20 min.
        :param matched: matched list by time share explosion filter
        :param boomed: high speed rising
        :param must_be_high: is true in the morning
        :return:
        """
        selected = []
        df_list = self.curr_realtime_chart

        if TRUNCATE == 1:
            df_list = [df[:TRUNCATE_TIME] for df in df_list]
        for df in df_list:
            code = df.iloc[0]['code']
            close = self.curr_price[code]
            if TRUNCATE == 1:
                close = df.iloc[-1]['high']
            boom_close = df.iloc[-1]['open']
            open_price = self.pre_close[code]
            limit = round(open_price * 1.1, 2)
            rise_ratio = (close - open_price) / open_price
            basic_infos = self.storage.get_basicinfo_single(tm.ts_mapping[code])
            free_share = basic_infos['free_share']

            if close >= round(open_price * HIGH_PRICE_PERCENT, 2):
                continue

            if close < df.iloc[-1]['open']:
                print(code + "(recent neckline): if falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(recent neckline): is falling" + "\n")
                continue

            highest_recent = max(df.iloc[-5:])
            if len(df) > 5 and highest_recent > close: # and df.iloc[-5]['open'] > close:
                print(code + "(recent neckline): is falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(recent neckline): is falling" + "\n")
                continue

            if must_be_high:
                if free_share >= LARGE_FREE_SHARE:
                    open_threshold = LARGE_OPEN_HIGH_THRESHOLD
                else:
                    if code not in boomed and close < df.iloc[-1]['open'] * BOOMED_THRESHOLD:
                        print(code + '(recent neckline): not boomed in the morning need: '
                              + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close))
                        with open(path + 'stock.log', 'a') as f:
                            f.write(code + '(recent neckline): not boomed in the morning' + '\n')
                        continue
                    open_threshold = NORMAL_OPEN_HIGH_THRESHOLD
                if rise_ratio < open_threshold:
                    print(code + '(recent neckline): not open high in the morning')
                    with open(path + 'stock.log', 'a') as f:
                        f.write(code + '(recent neckline): not open high in the morning' + '\n')
                    continue

            neckline_list = [open_price * (1 + ratio * 0.1 / NECKLINE_STEP) for ratio in
                             range(-NECKLINE_MINUS_STEP, NECKLINE_STEP)]
            neckline_select = []
            df = df.iloc[-30:]
            df = df.set_index('high')
            df = df.sort_index()
            last_length = None
            for i in range(1, NECKLINE_STEP + NECKLINE_MINUS_STEP):
                df_temp = df[(df.index > neckline_list[i - 1]) & (df.index <= neckline_list[i])]
                # according to neckline definition
                if last_length is not None and last_length - len(df_temp) > 3:
                    neck_price = neckline_list[i - 1]
                    upper = neck_price * NECKLINE_UPPER_BOUND
                    lower = neck_price * NECKLINE_LOWER_BOUND
                    # general neckline
                    df_area = df[(df.index > lower) & (df.index < upper)]
                    df_area = df_area[df_area.index < limit]  # do not count limit price
                    # neckline should be longer than 15 minutes
                    # if len(df_area) >= RECENT_NECKLINE_LENGTH_THRESHOLD:
                    df_area = df_area.sort_values(by=['day'])
                    # calculate confidence coefficient of this neckline
                    days = df_area['day'].values
                    day_delta = np.array([(i - j).seconds / 60 for i, j in
                                          zip([datetime.datetime.strptime(k, '%Y-%m-%d %H:%M:%S') for k in
                                               days[1:]],
                                              [datetime.datetime.strptime(k, '%Y-%m-%d %H:%M:%S') for k in
                                               days[:-1]])])
                    day_delta = day_delta[(day_delta <= SEPARATED_NECKLINE_MIN_GAP) & (day_delta > 1)]
                    day_delta = day_delta - 1
                    outliners = sum(day_delta)
                    # not too much outliners
                    if (len(df_area) >= RECENT_NECKLINE_LENGTH_THRESHOLD and
                        outliners / len(df_area) < RECENT_OUTLINER_THRESHOLD) or \
                            (len(df_area) >= RECENT_GOOD_NECKLINE_LENGTH_THRESHOLD and
                             outliners / len(df_area) < RECENT_GOOD_OUTLINER_THRESHOLD):
                        neckline_select.append((i - 1, code))
                last_length = len(df_temp)

            # for log
            if DEBUG == 1:
                print([k[1] + '(recent neckline): '+str(neckline_list[k[0]]) for k in neckline_select])
                with open(path + 'stock.log', 'a') as f:
                    f.write(str([k[1] + '(recent neckline): '+str(neckline_list[k[0]]) for k in neckline_select]) + '\n')
            if len(neckline_select) == 0:
                continue

            # detect neckline-crossing
            if code in self.past_price:
                past_deal = self.past_price[code]
                curr_deal = self.curr_price[code]
                for neckline in neckline_select:
                    if past_deal <= neckline_list[neckline[0]] <= curr_deal:
                        selected.append(code)
                        break
            # detect if price is in a box form
            if code in boomed and close > boom_close:
                lower_bound = BOOM_LOWER_BOUND
                upper_bound = BOOM_UPPER_BOUND
                close = boom_close
                if DEBUG == 1:
                    print(code + '(recent neckline): boomed at ' + str(close))
                    with open(path + 'stock.log', 'a') as f:
                        f.write(code + '(recent neckline): boomed at ' + str(close) + '\n')
            else:
                lower_bound = NORMAL_LOWER_BOUND
                upper_bound = NORMAL_UPPER_BOUND
            # boomed stock is over neckline
            for neckline in neckline_select:
                if neckline_list[neckline[0]] * lower_bound <= close <= neckline_list[neckline[0]] * upper_bound:
                    print(code + '(recent neckline): select ' + str(neckline_list[neckline[0]])
                          + ' close ' + str(close))
                    with open(path + 'stock.log', 'a') as f:
                        f.write(code + '(recent neckline): select ' + str(neckline_list[neckline[0]])
                                + ' close ' + str(close) + '\n')
                    selected.append(code)
                    break
        return selected

    def detect_high_neckline(self, matched, boomed):
        """
        not used. Average success rate is low
        :param matched: matched list by time share explosion filter
        :param boomed: high speed rising
        :return: filtered matched list by high neckline detection
        """
        selected = []
        df_list = self.curr_realtime_chart

        if TRUNCATE == 1:
            df_list = [df[:TRUNCATE_TIME] for df in df_list]
        for df in df_list:
            code = df.iloc[0]['code']
            open_price = self.pre_close[code]
            close = self.curr_price[code]
            if TRUNCATE == 1:
                close = df.iloc[-1]['high']
            boom_close = df.iloc[-1]['open']
            open_price_today = df.iloc[0]['open']
            limit = round(open_price * 1.1, 2)
            basic_infos = self.storage.get_basicinfo_single(tm.ts_mapping[code])
            free_share = basic_infos['free_share']

            if close < df.iloc[-1]['open']:
                print(code + "(high neckline): if falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(high neckline): is falling" + "\n")
                continue

            highest_recent = max(df.iloc[-5:])
            if len(df) > 5 and highest_recent > close: # and df.iloc[-5]['open'] > close:
                print(code + "(high neckline): is falling")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(high neckline): is falling" + "\n")
                continue

            if free_share < SMALL_FREE_SHARE and code not in boomed and close < df.iloc[-1]['open'] * BOOMED_THRESHOLD:
                print(code + "(high neckline): small share and not boomed need: "
                      + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close))
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(high neckline): small share and not boomed need: "
                            + str(df.iloc[-1]['open'] * BOOMED_THRESHOLD) + ' close: ' + str(close) + "\n")
                continue

            # too early, should only use morning neckline
            if code not in self.past_price or len(df) <= 2:
                continue

            # too high
            if close >= limit:
                continue

            if close >= round(open_price * HIGH_PRICE_PERCENT, 2):
                continue

            # high neckline should be at a high price
            # if free_share >= LARGE_FREE_SHARE:
            #     rise_threshold = LARGE_OPEN_HIGH_THRESHOLD
            # else:
            #     rise_threshold = NORMAL_OPEN_HIGH_THRESHOLD
            if (close - open_price) / open_price <= RISE_HIGH_THRESHOLD:
                continue

            in_the_morning = False
            if len(df) > 120:
                df_recent = df[:-60]
                highest_recent = max(df[-10:-2]['high'].values)
            elif len(df) > 60:
                df_recent = df[:-30]
                highest_recent = max(df[-10:-2]['high'].values)
            elif len(df) > 30:
                df_recent = df[:-10]
                highest_recent = max(df[-10:-2]['high'].values)
            elif len(df) > 10:
                df_recent = df[:-5]
                highest_recent = max(df[-5:-2]['high'].values)
            else:
                in_the_morning = True
                df_recent = df
                highest_recent = 0
            # elif len(df) > 20:
            #     df_recent = df[:-20]
            # else:
            #     df_recent = df[:-5]
            # detect crossing
            past_deal = self.past_price[code]
            curr_deal = self.curr_price[code]
            highest = max(df_recent['high'].values)

            if in_the_morning and \
                    highest >= ((open_price_today - open_price) / open_price + RUSH_HIGH_THRESHOLD) * open_price:
                print(code + "(morning high neckline): rush too high")
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(morning high neckline): rush too high" + "\n")
                continue

            # too high
            if highest >= limit:
                continue

            # is rising
            if highest <= highest_recent:
                print(code + "(high neckline): is rising highest=" + str(highest))
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + "(high neckline): is rising highest=" + str(highest) + "\n")
                continue

            # log
            if DEBUG == 1:
                print(code + '(high neckline): ' + str(highest))
                with open(path + 'stock.log', 'a') as f:
                    f.write(code + '(high neckline): ' + str(highest) + '\n')

            if past_deal <= highest <= curr_deal:
                selected.append(code)
                continue

            # detect if price is in a box form
            if code in boomed and curr_deal > boom_close:
                lower_bound = BOOM_LOWER_BOUND
                upper_bound = BOOM_UPPER_BOUND
                curr_deal = boom_close
                if DEBUG == 1:
                    print(code + '(recent neckline): boomed at' + str(boom_close))
                    with open(path + 'stock.log', 'a') as f:
                        f.write(code + '(recent neckline): boomed at' + str(boom_close) + '\n')
            else:
                lower_bound = HIGH_LOWER_BOUND
                upper_bound = HIGH_UPPER_BOUND
            if highest * lower_bound <= curr_deal <= highest * upper_bound:
                selected.append(code)
                continue

        return selected

    def update_local_price(self, matched, boomed):
        """
        update current price and price 3 second ago
        :param matched: matched list by time share explosion filter
        :param boomed: high speed rising
        """
        self.past_price = self.curr_price
        self.curr_realtime_chart = self.storage.get_realtime_chart(matched + boomed)
        self.curr_realtime_chart_long = self.storage.get_realtime_chart_long(matched + boomed)
        for code in matched + boomed:
            info = self.storage.get_realtime_storage_single(code)
            self.curr_price[code] = float(info[3])
            self.pre_close[code] = float(info[2])

    def detect_neckline(self, matched, boomed):
        """
        :param matched: matched list by time share explosion filter
        :param boomed: high speed rising
        :return: filtered matched list by neckline detection
        """
        if TRUNCATE == 1:
            self.update_local_price(matched, boomed)
            selected_high = self.detect_high_neckline(matched, boomed)
            selected_morning = self.detect_morning_neckline(matched, boomed)
            selected_long = self.detect_long_neckline(matched, boomed)
            selected_recent = self.detect_recent_neckline(matched, boomed)
            selected_general = self.detect_general_neckline(matched, boomed)
            return selected_high + selected_long + selected_general + selected_morning + selected_recent
            # return selected_general
        self.update_local_price(matched, boomed)
        # if datetime.datetime.now().strftime('%H:%M:%S') < '09:32:00':
        #     selected = self.detect_long_neckline(matched, boomed)
        if datetime.datetime.now().strftime('%H:%M:%S') < '09:40:00':
            selected_long = self.detect_long_neckline(matched, boomed)
            selected_morning = self.detect_morning_neckline(matched, boomed)
            selected = list(set(selected_long) | set(selected_morning))
        elif datetime.datetime.now().strftime('%H:%M:%S') < '10:10:00':
            selected_morning = self.detect_morning_neckline(matched, boomed)
            selected_long = self.detect_long_neckline(matched, boomed)
            selected_recent = self.detect_recent_neckline(matched, boomed, True)
            selected = list(set(selected_morning) | set(selected_long) | set(selected_recent))
        else:
            selected = self.detect_general_neckline(matched, boomed)
        selected_high = self.detect_high_neckline(matched, boomed)
        selected = list(set(selected) | set(selected_high))
        return selected


if __name__ == '__main__':
    storage = st.Storage()
    storage.update_realtime_storage()
    neckline = NeckLine(storage)
    start = time.time()
    neckline.detect_neckline(['002436'], [])
    end = time.time()
    print('total: ' + str(end - start))


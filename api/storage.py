"""
@ File:     storage.py
@ Author:   pleiadesian
@ Datetime: 2020-01-17 07:47
@ Desc:     Scratching, cleaning and storing data
"""
import re
import time
import json
import datetime
import requests
import pandas as pd
from random import randint
from multiprocessing.pool import ThreadPool
from urllib.request import urlopen, Request
import tushare as ts
import api.ts_map as tm

DEBUG = 0

DATA_COLS = ['name', 'open', 'pre_close', 'price', 'high', 'low', 'bid', 'ask', 'volume', 'amount', 'b1_v', 'b1_p',
             'b2_v', 'b2_p', 'b3_v', 'b3_p', 'b4_v', 'b4_p', 'b5_v', 'b5_p', 'a1_v', 'a1_p', 'a2_v', 'a2_p', 'a3_v',
             'a3_p', 'a4_v', 'a4_p', 'a5_v', 'a5_p', 'date', 'time', 's']


def random(n=13):
    start = 10 ** (n - 1)
    end = (10 ** n) - 1
    return str(randint(start, end))


def process_plaintext(index, reg, reg_sym):
    """
    :param index: index for the bunch of stock
    :param reg: regular expression for data
    :param reg_sym: regular expression for symbols
    :return: data frame for a bunch of stock
    """
    # TODO: add index on code column
    realtime_info = dict()
    resp = None
    not_get = True
    while not_get:
        try:
            # text = urlopen(request, timeout=1).read()
            resp = requests.get('%shq.%s/rn=%s&list=%s' % ('http://', 'sinajs.cn',
                                random(), tm.code_list[index]), timeout=3)
            not_get = False
            if resp is None:
                not_get = True
        except requests.exceptions.RequestException as e:
            time.sleep(1)
            not_get = True

    text = resp.text
    # text = text.decode('GBK')
    data = reg.findall(text)
    syms = reg_sym.findall(text)
    # data_list = []
    # syms_list = []
    for index, row in enumerate(data):
        if len(row) > 1:
            # data_list.append([astr for astr in row.split(',')[:33]])
            # syms_list.append(syms[index])
            realtime_info[syms[index]] = [astr for astr in row.split(',')[:33]]
    # assert syms_list
    # df = pd.DataFrame(data_list, columns=DATA_COLS)
    # df = df.drop('s', axis=1)
    # df['code'] = syms_list
    # ls = [cls for cls in df.columns if '_v' in cls]  # bid and ask volume should / 100
    # for txt in ls:
    #     df[txt] = df[txt].map(lambda x: x[:-2])
    return realtime_info


def process_peak(df):
    """
    find the peak in the time share chart
    :param df: time share data frame
    :return: peak, peak time
    """
    if DEBUG == 1:
        start = time.time()
    df_sorted = df.sort_values(by=['high'])
    df_high = df[df.high == df_sorted.high[-1]]
    df_selected = df_high.sort_index()

    if DEBUG == 1:
        end = time.time()
        print(end - start)
    peak = df_selected['high'].values[0]
    peak_time = df_selected.index.values[0][-8:]
    rounddown_peak_time = (datetime.datetime.strptime(peak_time, "%H:%M:%S") - datetime.timedelta(minutes=5))\
        .strftime("%H:%M:%S")
    return peak, rounddown_peak_time


def process_json(codes):
    i = 0
    pro = ts.pro_api()
    df_date = pro.trade_cal(exchange='SSE', start_date=datetime.datetime.now().strftime('%Y') + '0101', is_open=1)
    pretrade_df = df_date[df_date.cal_date < datetime.datetime.now().strftime('%Y%m%d')]
    if len(pretrade_df) == 0:
        # consider the trade date after New Year's day
        df_date = pro.trade_cal(exchange='SSE', start_date='20200101',
                                is_open=1)
        pretrade_df = df_date[df_date.cal_date < datetime.datetime.now().strftime('%Y%m%d')]
    pretrade_date = pretrade_df['cal_date'].values[-1]
    pretrade_date = pretrade_date[:4] + '-' + pretrade_date[4:6] + '-' + pretrade_date[6:]

    peak_info = dict()
    # cols = ['date', 'open', 'high', 'close', 'low', 'volume', 'price_change', 'p_change', 'ma5', 'ma10', 'ma20',
    #         'v_ma5', 'v_ma10', 'v_ma20', 'turnover']  # only for K-5
    cols = ['date', 'open', 'high', 'close', 'low', 'volume', 'price_change', 'p_change',
            'ma5', 'ma10', 'ma20', 'v_ma5', 'v_ma10', 'v_ma20']  # only for daily
    df_curr = pd.DataFrame(columns=cols)
    for code in codes:
        if DEBUG == 1:
            start_time = time.time()
        # url = '%sapi.finance.%s/akmin?scode=%s&type=%s' % ('http://', 'ifeng.com', code, '5')
        url = '%sapi.finance.%s/%s/?code=%s&type=last' % ('http://', 'ifeng.com', 'akdaily', code)
        not_get = True
        resp = None
        while not_get:
            try:
                resp = requests.get(url, timeout=3)
                not_get = False
                if resp is None or len(resp.text) == 0:
                    time.sleep(1)
                    not_get = True
            except requests.exceptions.RequestException as e:
                time.sleep(1)
                not_get = True
        if DEBUG == 1:
            mid_time = time.time()
        text = resp.text
        js = json.loads(text)
        df = pd.DataFrame(js['record'], columns=cols)
        df = df[df.date >= pretrade_date]  # only for daily
        if len(df) > 1:
            # in case of replay
            df = df[df.date > pretrade_date]
        df.insert(0, 'code', code[2:])
        df['code'] = code[2:]
        df = df.applymap(lambda x: x.replace(u',', u''))  # only for daily
        df[df == ''] = 0  # only for daily
        for col in cols[1:]:
            df[col] = df[col].astype(float)
        df_curr = pd.concat([df_curr, df])
        # curr_date = df['date'].values[-1][0:10]    # only for K-5
        # df = df.drop('turnover', axis=1)  # only for K-5
        # df = df.set_index('date')
        # df = df.sort_index(ascending=False)
        # # TODO: calc the peak
        # peak, peak_time = process_peak(df)
        # peak_info[code[2:]] = (peak, peak_time)
        if DEBUG == 1:
            end_time = time.time()
            print("mid" + str(mid_time - start_time))
            print("final" + str(end_time - mid_time))
            i += 1
            print(str(i) + ' finished')
    return df_curr


class Storage:
    def __init__(self):
        if __name__ == '__main__':
            with open('token/token.txt', "r") as f:  # 设置文件对象
                token = f.read()
        elif __name__ == 'api.storage':
            with open('token/token.txt', "r") as f:  # 设置文件对象
                token = f.read()
        else:
            with open('api/token/token.txt', "r") as f:  # 设置文件对象
                token = f.read()
        self.pro = ts.pro_api(token)
        self.realtime_quotes = None
        self.stock_daily = None
        self.reg = re.compile(r'\="(.*?)\";')
        self.reg_sym = re.compile(r'(?:sh|sz)(.*?)\=')
        self.peak_info = dict()
        # self.basic_info = None
        # self.hist_data = None
        self.basic_info = dict()
        self.hist_data = dict()

        # self.init_neckline_storage()
        self.init_basicinfo()
        self.init_histdata()

    def update_realtime_storage(self):
        """
        scratch realtime data and store it locally
        """
        if DEBUG == 1:
            start_time = time.time()
        args = []
        for i in range(0, 5):
            args.append((i, self.reg, self.reg_sym))
        p = ThreadPool()
        # df_list = p.starmap(process_plaintext, args)
        dict_list = p.starmap(process_plaintext, args)

        args_remain = []
        for i in range(5, 8):
            args_remain.append((i, self.reg, self.reg_sym))
        # df_list_remain = p.starmap(process_plaintext, args_remain)
        dict_list_remain = p.starmap(process_plaintext, args_remain)
        # df_curr = pd.concat(df_list + df_list_remain)
        # df_curr = df_curr.set_index('code')
        dict_curr = {k:v for dic in dict_list for k,v in dic.items()}
        dict_curr_remain = {k:v for dic in dict_list_remain for k,v in dic.items()}
        # self.realtime_quotes = df_curr
        self.realtime_quotes = {**dict_curr, **dict_curr_remain}
        if DEBUG == 1:
            end_time = time.time()
            print("update_realtime_storage: "+str(end_time - start_time))

    def update_daily_storage(self):
        """
        scratch daily data and store it locally
        """

    def get_realtime_storage(self):
        """
        :return: realtime data
        """
        return self.realtime_quotes

    def get_realtime_storage_single(self, code):
        """
        :param code: stock code
        :return: realtime data for code
        """
        assert self.realtime_quotes is not None
        return self.realtime_quotes[code]
        # return self.realtime_quotes.loc[code]

    def get_basicinfo_single(self, ts_code):
        """
        :param ts_code: stock code
        :return: basic information for code
        """
        assert self.basic_info is not None
        # hit stock that suspended trading yesterday, load it
        # if ts_code not in self.basic_info.index:
        # TODO: prefetch data of suspended stock
        if ts_code not in self.basic_info:
            delta = 1
            suspended = True
            while suspended:
                df_basicinfo = self.pro.daily_basic(ts_code=ts_code,
                                                    trade_date=(datetime.datetime.now() -
                                                                datetime.timedelta(days=delta)).strftime('%Y%m%d'))
                if len(df_basicinfo) == 0:
                    delta += 1
                    continue
                # df_suspended = df_basicinfo.set_index('ts_code')
                # self.basic_info = pd.concat([self.basic_info, df_suspended])
                temp_series = df_basicinfo.loc[0]
                self.basic_info[ts_code] = temp_series
                return temp_series
                # suspended = False
        # return self.basic_info.loc[ts_code]
        return self.basic_info[ts_code]

    def get_histdata_single(self, ts_code):
        """
        :param ts_code: stock ts code
        :return:
        """
        assert self.hist_data is not None
        # return self.hist_data.loc[ts_code]
        return self.hist_data[ts_code]

    def init_basicinfo(self):
        """
        initialize stock basic info
        """
        # get daily basic information
        df_date = self.pro.trade_cal(exchange='SSE', start_date=datetime.datetime.now().strftime('%Y')+'0101', is_open=1)
        pretrade_df = df_date[df_date.cal_date < datetime.datetime.now().strftime('%Y%m%d')]
        if len(pretrade_df) == 0:
            # consider the trade date after New Year's day
            df_date = self.pro.trade_cal(exchange='SSE', start_date='20200101',
                                         is_open=1)
            pretrade_df = df_date[df_date.cal_date < datetime.datetime.now().strftime('%Y%m%d')]
        pretrade_date = pretrade_df['cal_date'].values[-1]
        # TODO: reconstruct timeout handling to a function
        not_get = True
        while not_get:
            try:
                df_basicinfo = self.pro.daily_basic(ts_code='', trade_date=pretrade_date)
                # self.basic_info = df_basicinfo.set_index('ts_code')
                for index, row in df_basicinfo.iterrows():
                    self.basic_info[row['ts_code']] = row
                not_get = False
            except requests.exceptions.RequestException as e:
                time.sleep(1)
                not_get = True

    def init_histdata(self):
        """
        initialize data in 5 days
        """
        df_date = self.pro.trade_cal(exchange='SSE', start_date=datetime.datetime.now().strftime('%Y')+'0101',
                                     is_open=1)
        df_pretrade = df_date[df_date.cal_date < datetime.datetime.now().strftime('%Y%m%d')]
        if len(df_pretrade) == 0:
            # consider the trade date after New Year's day
            df_date = self.pro.trade_cal(exchange='SSE', start_date='20200101',
                                         is_open=1)
            df_pretrade = df_date[df_date.cal_date < datetime.datetime.now().strftime('%Y%m%d')]
        df_pre5 = df_pretrade[-5:]
        pretrade_date = df_pre5['cal_date'].values
        df_list = list()
        for i in range(0, 5):
            not_get = True
            while not_get:
                try:
                    df = self.pro.daily(ts_code='', start_date=pretrade_date[i], end_date=pretrade_date[i])
                    df_list.append(df)
                    not_get = False
                except requests.exceptions.RequestException as e:
                    time.sleep(1)
                    not_get = True
        df_histdata = pd.concat(df_list)
        for index, row in df_histdata.iterrows():
            if row['ts_code'] not in self.hist_data:
                # self.hist_data[row['ts_code']] = pd.DataFrame().append(row, ignore_index=True)
                self.hist_data[row['ts_code']] = [row]
            else:
                # self.hist_data[row['ts_code']].append(row, ignore_index=True)
                self.hist_data[row['ts_code']].append(row)
        # self.hist_data = df_histdata.set_index('ts_code')

        # args = []
        # step = int(len(tm.detail_code_list) / 6)
        # for i in range(0, 6):
        #     if step * (i+1) > len(tm.detail_code_list):
        #         args.append(tm.detail_code_list[step * i:])
        #     else:
        #         args.append(tm.detail_code_list[step * i:step * (i+1)])
        # p = ThreadPool()
        # hist_datas = p.map(process_json, args)
        # df_histdata = pd.concat(hist_datas)
        # self.hist_data = df_histdata.set_index('code')

    def init_neckline_storage(self):
        """
        initialize neckline in time share chart
        """
        # TODO: this api cannot get current data, consider to check Wind api
        args = []
        step = int(len(tm.detail_code_list) / 12)
        for i in range(0, 12):
            if step * (i+1) > len(tm.detail_code_list):
                args.append(tm.detail_code_list[step * i:])
            else:
                args.append(tm.detail_code_list[step * i:step * (i+1)])
        p = ThreadPool()
        peak_infos = p.map(process_json, args)
        self.peak_info = {k:v for dic in peak_infos for k,v in dic.items()}

        # pro_bar need ￥1000 -_-
        # curr_date = self.get_realtime_storage_single('000001')[30]
        # curr_date = ''.join(curr_date.split('-'))
        # for ts_code in tm.ts_mapping.values():
        #     df = ts.pro_bar(ts_code='000001.SH,399365.SZ', freq='1min', start_date=curr_date)
        #     print(df)


if __name__ == '__main__':
    storage = Storage()
    while True:
        time.sleep(2)
        storage.update_realtime_storage()
        print(storage.get_realtime_storage())

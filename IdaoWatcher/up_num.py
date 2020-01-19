import tushare as ts
import datetime
import api.ts_map as tm


# 判断十字星
def judge_doji(i, open, high, close, low):
    if abs(open[i] - close[i]) <= (high[i] - low[i]) * 0.2:
            # and (open[i] > low[i] + 0.02) and (open[i] < high[i] - 0.02) and (close[i] > low[i] + 0.02) and (close[i] < high[i] - 0.02):
        return 1  # 收盘价与开盘价差的绝对值小于等于高低峰值差的0.1倍，且十字的一横不在最高或最低处，此时认为是十字星
    else:
        return 0


def calc_60_up_num(stock_ticker):
    """
    :param stock_ticker: stock code
    :return: the number of rising K60
    """
    hzsunmoon_num = 0  # 初始化阳线根数为0
    now_time = ts.get_realtime_quotes(stock_ticker).values[0][30]  # 今天的日期（年-月-日）
    delta = 4
    past_time = (datetime.datetime.strptime(now_time, '%Y-%m-%d') - datetime.timedelta(days=delta)).strftime(
        '%Y-%m-%d')  # 认为不可能连着16根阳线，只往前推4天

    all_info = ts.get_hist_data(stock_ticker, start=past_time, end=now_time, ktype='60')
    while all_info is None or len(all_info) < 16:
        # TODO: optimize this algorithm
        delta += 1
        past_time = (datetime.datetime.strptime(now_time, '%Y-%m-%d') - datetime.timedelta(days=delta)).strftime(
            '%Y-%m-%d')  # 遇到跨双休日、节假日的情况，持续往前推，直到获得4天的数据
        all_info = ts.get_hist_data(stock_ticker, start=past_time, end=now_time, ktype='60')
    open_price = all_info['open']
    high_price = all_info['high']
    close_price = all_info['close']
    low_price = all_info['low']

    # print(all_info)
    # limit_1_before = round(close_price[4] * 1.1, 2)  # 昨天的涨停limit
    # limit_2_before = round(close_price[8] * 1.1, 2)  # 前天的涨停limit
    # limit_3_before = round(close_price[12] * 1.1, 2)  # 大前天的涨停limit
    limit_set = []
    delta = 1
    pro = ts.pro_api()
    while len(limit_set) < 3:
        past_time = (datetime.datetime.strptime(now_time, '%Y-%m-%d') - datetime.timedelta(days=delta)).strftime(
            '%Y%m%d')
        pre_close = pro.daily(ts_code=tm.ts_mapping[stock_ticker], trade_date=past_time)['pre_close']
        if len(pre_close) == 1:
            data = round(pre_close[0] * 1.1, 2)
            if data is not None:
                limit_set.append(data)
        assert len(pre_close) == 0 or len(pre_close) == 1
        delta += 1

    for i in range(11):
        if ((close_price[i] > open_price[i] + 0.01) and (
                judge_doji(i, open_price, high_price, close_price, low_price) == 0) and (
                    close_price[i + 1] > open_price[i + 1] + 0.01)) or (
                close_price[i] >= limit_set[i // 4]):  # 某一小时正常阳线，或涨停；且前一小时也涨了。
            hzsunmoon_num += 1
        elif ((close_price[i] > open_price[i] + 0.01) and (
                judge_doji(i, open_price, high_price, close_price, low_price) == 0)) or (
                close_price[i] >= limit_set[i // 4]):  # 某小时正常阳线或涨停，前一小时不是阳线或涨停
            hzsunmoon_num += 1
        else:
            break

    return hzsunmoon_num


if __name__ == '__main__':
    num = calc_60_up_num('300703')
    print(num)

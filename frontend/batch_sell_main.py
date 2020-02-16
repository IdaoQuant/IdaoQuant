"""
@ File:     batch_sell_main.py
@ Author:   pleiadesian
@ Datetime: 2020-02-14 08:55
"""
import sys
import tushare as ts
import frontend.batch_sell as bs
import api.ts_map as tm
from frontend import setfocus
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget


def get_new_a1p(codes):
    infos = ts.get_realtime_quotes(codes).values
    a1ps = []
    for info in infos:
        # get ask price 1
        a1ps.append(float(info[21]))
    return a1ps


class BatchSellMain(QMainWindow, bs.Ui_MainWindow):
    def __init__(self, parent=None):
        super(BatchSellMain, self).__init__(parent)
        self.setupUi(self)
        self.window_info = setfocus.init_fs()
        self.codes = []
        self.price = dict()
        self.amount = dict()

    def confirm(self):
        price_text = self.lineEdit_price.text()
        code_text = self.lineEdit_stock.text()
        amount_text = self.lineEdit_amount.text()
        percent_text = self.lineEdit_percent.text()

        if price_text == '':
            QMessageBox.question(self, "警告", "卖出价格未设置！",
                                 QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
            return
        price = float(price_text)
        if price > 10.0:
            QMessageBox.question(self, "警告", "价格设置过低！",
                                 QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
            return
        if amount_text == '':
            amount_text = '全仓卖出'
            sell_amount = None
        else:
            amount = int(amount_text)
            if amount <= 0 or amount % 100 != 0:
                QMessageBox.question(self, "警告", "持仓数填写错误！",
                                     QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
                return
            if percent_text == '':
                percent = 1
            else:
                if float(percent_text) < 1:
                    QMessageBox.question(self, "警告", "卖出比例填写错误！",
                                         QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
                    return
                percent = 1 / float(percent_text)
            sell_amount = int(((amount * percent) // 100 + 1) * 100)
            amount_text = '持仓' + amount_text + '股 卖出' + str(sell_amount) + '股' + '(1/' + percent_text + '仓位）'
        if code_text not in tm.name_mapping:
            QMessageBox.question(self, "警告", "检测到股票代码输入错误，请重新输入（注意股票代码之间必须有且仅有1个空格）",
                                 QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
            return

        new_line = code_text + ' ' + tm.name_mapping[code_text] + ' 低' + price_text + '%   ' + amount_text + '\n'
        self.label_stock.setText(self.label_stock.text() + new_line)
        self.codes.append(code_text)
        self.price[code_text] = price_text
        if sell_amount is not None:
            self.amount[code_text] = str(sell_amount)

    def batch_sell_start(self):
        a1_ps = get_new_a1p(self.codes)
        if len(a1_ps) != len(self.codes) or len(self.codes) == 0:
            QMessageBox.question(self, "警告", "检测到股票代码输入错误，请重新输入（注意股票代码之间必须有且仅有1个空格）",
                                 QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
            return
        for code, ask_price in zip(self.codes, a1_ps):
            sell_price = str(round(ask_price * (1 - float(self.price[code]) / 100), 2))
            if code in self.amount:
                amt = self.amount[code]
            else:
                amt = None
            setfocus.sell_code(code, sell_price, amt, self.window_info)
        QMessageBox.question(self, "提示", "批量委托卖出完毕",
                             QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    batch_sell_main = BatchSellMain()
    batch_sell_main.show()
    app.exec_()

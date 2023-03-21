import yfinance as yf
from datetime import datetime, timedelta

class StockData:
    def __init__(self, stock_ids:list, exchange:str="USDTWD=X", n_day:int=14,start_date:str="", end_date:str="", candle_by:bool=False):
        # candle_by = True 代表以"收盤開盤價"作為計算方式
        # candle_by = False 代表以"最高最低價"作為計算方式
        self.stock_ids = [f"{id}.TW" for id in stock_ids]
        days_to_subtract = n_day + (n_day // 5 * 2)  # Add 2 weekend days for each week
        # Adjust for weekends if necessary
        current_weekday = datetime.today().weekday()
        days_to_subtract += 2 if current_weekday < n_day % 5 else 0
        previous_day = datetime.today() - timedelta(days=days_to_subtract)
        self.start_date = start_date if start_date else previous_day.strftime('%Y-%m-%d')
        self.end_date = end_date if end_date else datetime.now().strftime("%Y-%m-%d")
        self.candle_by = candle_by
        self.exchange = exchange
        # Type: {stock_id(str): data(pd.DataFrame)}
        self.stock_datas = dict()
        # 美元兌換台幣的匯率
        self.exchange_data = None
        # 儲存每個股票的價格漲跌幅度
        self.stock_price_extends = dict()
        # 儲存每個股票的成交量變化率
        self.stock_volume_extends = dict()
        # 標準化後股票價格漲跌幅度的平均值
        self.stock_avg_price_normalized = 0
        # 標準化後股票成交量變化率的平均值
        self.stock_avg_volume_normalized = 0
        # 標準化後外匯價格漲跌幅度的平均值
        self.exchange_rate_normalized = 0

        self.done = False

        self.download_data()
    
    def get_normalized_data(self):
        # return [stock_price_normalized, stock_volume_normalized, exchange_rate_normalized]
        if self.done:
            return [self.stock_avg_price_normalized, self.stock_avg_volume_normalized, self.exchange_rate_normalized]
        else:
            return [None,None,None]

    def download_data(self):
        # download stock data
        for id in self.stock_ids:
            data = yf.download(id,start=self.start_date, end=self.end_date)
            if not data.empty:
                data = data[data['Open'] != 0]
                data = data[data['High'] != 0]
                data = data[data['Low'] != 0]
                data = data[data['Close'] != 0]
                data = data[data['Volume'] != 0]
                self.stock_datas[id] = data
            else:
                self.stock_datas.pop(id, None)
        # download exchange data
        self.exchange_data = yf.download(self.exchange, start=self.start_date, end=self.end_date)

        self.normalized_extend()

    def normalized_extend(self):
        # 計算股價波動性、成交量變化率、外匯波動性
        # STOCK
        price_record = []
        volume_record = []

        for id in self.stock_datas.keys():
            data = self.stock_datas[id]

            close_price = data['Close'].tolist()
            high_price = data['High'].tolist()
            low_price = data['Low'].tolist()

            if self.candle_by:
                # 價格波動幅度 = (當日收盤價 - 昨日收盤價) / 昨日收盤價 * 100
                price_changes = [(close_price[i] - close_price[i-1]) / close_price[i-1] * 100 for i in range(1, len(data))]
            else:
                # 價格波動幅度 = (最高價 - 最低價) / 最低價 * 100
                price_changes = [(high_price[i] - low_price[i]) / low_price[i] * 100 for i in range(1, len(data))]
            
            # 找出最大最小值
            max_value = max(price_changes)
            min_value = min(price_changes)
            # 標準化每一個幅度
            price_extend = [(x - min_value) / (max_value - min_value) * 100 for x in price_changes]
            # 平均結果
            price_extend = sum(price_extend) / len(price_extend)
            
            self.stock_price_extends[id] = price_extend

            # 紀錄幅度
            price_record.append(price_extend)

            # 成交量變化率
            volume = data['Volume'].tolist()
            volume_changes = [(volume[i] - volume[i-1]) / volume[i-1] * 100 for i in range(1, len(data))]
            # 找出最大最小值
            max_value = max(volume_changes)
            min_value = min(volume_changes)
            # 標準化每一個變化
            volume_extend = [(x - min_value) / (max_value - min_value) * 100 for x in volume_changes]
            # 平均結果
            volume_extend = sum(volume_extend) / len(volume_extend)

            self.stock_volume_extends[id] = volume_extend

            # 紀錄變化
            volume_record.append(volume_extend)
            
        # 計算每個股票結果的平均值
        self.stock_avg_price_normalized = sum(price_record) / len(price_record)
        self.stock_avg_volume_normalized = sum(volume_record) / len(volume_record)

        # EXCHANGE
        # 外匯變化
        data = self.exchange_data
        close_price = data['Close'].tolist()
        high_price = data['High'].tolist()
        low_price = data['Low'].tolist()

        if self.candle_by:
            # 價格波動幅度 = (當日收盤價 - 昨日收盤價) / 昨日收盤價 * 100
            exchange_changes = [(close_price[i] / close_price[i-1] - 1) * 100 for i in range(1, len(data))]
        else:
            # 價格波動幅度 = (最高價 - 最低價) / 最低價 * 100
            exchange_changes = [(high_price[i] - low_price[i]) / low_price[i] * 100 for i in range(1, len(data))]

        # 找出最大最小值
        max_value = max(exchange_changes)
        min_value = min(exchange_changes)
        # 標準化每一個幅度
        price_extend = [(x - min_value) / (max_value - min_value) * 100 for x in exchange_changes]
        # 平均結果
        self.exchange_rate_normalized = 100 - sum(price_extend) / len(price_extend)

        self.done = True
        
if __name__ == "__main__":
    file_name = 'taiwan_nas99.csv'
    targets = [_.strip() for _ in open(file_name,'r')]
    # 下跌
    #'2021-12-07'
    sd = StockData(targets,start_date='2022-08-18',end_date='2022-10-26',candle_by=False)
    # 上升
    #sd = StockData(targets,start_date='2022-10-28',end_date='2022-12-01',candle_by=False)
    #sd = StockData(targets,n_day=14,candle_by=False)
    stock_price_normalized, stock_volume_normalized, exchange_rate_normalized = None, None, None
    while True:
        if sd.done:
            stock_price_normalized, stock_volume_normalized, exchange_rate_normalized = sd.get_normalized_data()
            break
    print('stock_price_normalized:',stock_price_normalized)
    print('stock_volume_normalized:',stock_volume_normalized)
    print('exchange_rate_normalized:',exchange_rate_normalized)
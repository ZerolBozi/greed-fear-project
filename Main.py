# -*- coding: utf-8 -*-
import asyncio
import random
from copy import deepcopy
from fastapi import FastAPI
from StockData import StockData
from threading import Thread, Lock
from datetime import datetime, timedelta
from CalculateNewsScore import CalculateNews
from Crawler import Proxy, LibertyTimes, MegaBankNews, YahooFinance_TW

app = FastAPI()

# 定義共用變數，保存貪婪恐懼指數
greed_fear_index = []
greed_fear_index_lock = Lock()
scores = {'news':[], 'stocks':{'stock_price':[],'stock_volume':[],'exchange':[]}}

# 權重比
greed_fear_ratio = {'news': 0.5, 'stock_price': 0.2, 'stock_volume': 0.15, 'exchange': 0.15}

"""Stock Parameter"""
stocks_file_name = 'taiwan_nas99.csv'
stocks = [_.strip() for _ in open(stocks_file_name,'r')]

save_len_limit = 20

n_day = 60
start_date = ""
end_data = ""
use_close_price = False
update_done = {'news': '', 'stocks': ''}

# 更新週期
update_time = 60 * 60 * 12

"""chatGPT API KEYS"""
api_keys = []

async def update_news(update_time:float=86400):
    first = True
    proxy = Proxy(proxy_count=5, use_timeout=False)

    keywords = [
        "半導體", "電子", "積體電路", "晶圓", "晶片", "晶片組","微控制器", "微處理器", "IC", "ASIC", "FPGA", "DRAM", "SRAM", 
        "快閃記憶體", "儲存器", "顯示器", "OLED", "LED","液晶顯示", "軟體", "硬體", "IoT", "物聯網", "5G","藍牙", "無線通信", 
        "射頻", "電池", "充電", "太陽能","光伏", "能源儲存", "電源管理", "電動汽車", "自動駕駛", "智慧家庭","半導體製程", "台積電",
        "三星", "英特爾", "高通", "美光","聯發科", "海力士", "蘋果", "華為", "富士康", "鴻海", "廣達", "瑞昱", "創意", "友達",
        "群創", "聯詠","微軟", "openai", "google", "mata", "人工智慧", "深度學習","模型","GPT", "聯準會", "美聯儲", "GDP", 
        "intel","顯示卡", "算力", "nvidia", "通貨膨脹", "通膨", "美元","特斯拉", "馬斯克", "Tesla", "Elon Musk", "Fed","AI"
    ]

    # trash website==
    # lbt = LibertyTimes(delay=1.5, proxy_valid_ips=proxy.get_valid_ips(),keywords=keywords)
    mbn = MegaBankNews(delay=1, keywords=keywords)
    yft = YahooFinance_TW(delay=0.5, keywords=keywords)

    while True:
        mbn.update_proxy(proxy.update_proxy(5))

        all_news = []
        news, news_with_keyword = await mbn.get_news([2, 5],date=mbn.get_today_date())
        
        news_k = 30 if len(news) > 30 else len(news)
        news_with_keyword_k = 80 if len(news) > 80 else len(news_with_keyword)
        all_news += random.sample(news, k=news_k)
        all_news += random.sample(news_with_keyword, k=news_with_keyword_k)

        yft.update_proxy(proxy.update_proxy(count=10))

        if first:
            news, news_with_keyword = await yft.get_news(['tw_market', 'intl_market', 'research'],is_today=False)
        else:
            news, news_with_keyword = await yft.get_news(['rss_news', 'rss_tw_market', 'rss_intl_market', 'rss_research'], False)

        news_k = 30 if len(news) > 30 else len(news)
        news_with_keyword_k = 80 if len(news) > 80 else len(news_with_keyword)
        all_news += random.sample(news, k=news_k)
        all_news += random.sample(news_with_keyword, k=news_with_keyword_k)

        # call chatGPT to calc the scores
        news_calc_obj = CalculateNews(api_keys,all_news,limit=200)
        news_score = await news_calc_obj.get_news_score()

        first = False
        # 當計算完成時，使用asyncio.create_task將貪婪恐懼指數更新的任務放入事件循環中
        asyncio.create_task(update_greed_fear_index(0,news_score=news_score))
        update_done['news'] = (datetime.now() + timedelta(seconds=update_time)).strftime("%Y-%m-%d %H:%M:%S")
        await asyncio.sleep(update_time)

async def update_stocks(stock_ids:list, n_day:int, start_date:str, end_data:str, use_close_price:bool, update_time:float=86400):
    while True:
        sd = StockData(stock_ids, n_day=n_day, start_date=start_date, end_date=end_data, candle_by=use_close_price)
        stock_price_normalized, stock_volume_normalized, exchange_rate_normalized = None, None, None

        while True:
            if sd.done:
                stock_price_normalized, stock_volume_normalized, exchange_rate_normalized = sd.get_normalized_data()
                break
            asyncio.sleep(0.5)

        print('stock_price_normalized:', stock_price_normalized)
        print('stock_volume_normalized:', stock_volume_normalized)
        print('exchange_rate_normalized:', exchange_rate_normalized)

        # 當計算完成時，使用asyncio.create_task將貪婪恐懼指數更新的任務放入事件循環中
        asyncio.create_task(update_greed_fear_index(1, stock_price=stock_price_normalized, stock_volume=stock_volume_normalized, exchange=exchange_rate_normalized))
        update_done['stocks'] = (datetime.now() + timedelta(seconds=update_time)).strftime("%Y-%m-%d %H:%M:%S")
        await asyncio.sleep(update_time)  # 等待12小時

async def update_greed_fear_index(update_type:int, **kwargs):
    # 由於這個函數會被多個任務共用，所以在更新共變數時需要使用鎖來保護資源
    greed_fear = 0
    # news update
    if update_type == 0:
        tmp_score = 0
        for key,value in kwargs.items():
            if len(scores['news']) > save_len_limit:
                scores['news'].pop(0)
            scores['news'].append(value)

        stock_price = scores['stocks']['stock_price'][-1] * greed_fear_ratio['stock_price'] if scores['stocks']['stock_price'] else 0
        stock_volume = scores['stocks']['stock_volume'][-1] * greed_fear_ratio['stock_volume'] if scores['stocks']['stock_volume'] else 0
        exchange = scores['stocks']['exchange'][-1] * greed_fear_ratio['exchange'] if scores['stocks']['exchange'] else 0
        tmp_score = scores['news'][-1] * greed_fear_ratio['news'] + stock_price + stock_volume + exchange
    
        total_ratio = 0
        for k in greed_fear_ratio.keys():
            total_ratio += greed_fear_ratio[k]

        greed_fear = tmp_score / total_ratio

    # stock update
    elif update_type == 1:
        for key, value in kwargs.items():
            if len(scores['stocks'][key]) > save_len_limit:
                scores['stocks'][key].pop(0)
            scores['stocks'][key].append(value)
        
    # 更新權重
    elif update_type == 2:
        if greed_fear_index:
            tmp_score = 0
            total_ratio = 0
            for key, value in kwargs.items():
                if key == 'news':
                    tmp_score += scores[key][-1] * value
                else:
                    tmp_score += scores['stocks'][key][-1] * value

                total_ratio += value
            
            greed_fear = tmp_score / total_ratio
            
    greed_fear = round(greed_fear,2)

    with greed_fear_index_lock:
        if len(greed_fear_index) > save_len_limit:
            # 刪除最早加入的數據
            greed_fear_index.pop(0)
        # 將新的貪婪恐懼指數加入列表中
        if update_type == 0:
            print('calculate done.\ngreed fear:', greed_fear)
            greed_fear_index.append(greed_fear)

    return greed_fear

@app.get('/greed_fear/{greed_fear_type}')
async def get_greed_fear(greed_fear_type:str):
    # loop = asyncio.get_running_loop()
    # loop.create_task(update_greed_fear_index())
    greed_fear_index_copy = deepcopy(greed_fear_index) # 複製共用變數
    tmp_greed_fear_his = []

    if len(greed_fear_index_copy) < 3:
        tmp_greed_fear_his = [-1]* (3-len(greed_fear_index_copy)) + greed_fear_index_copy[-len(greed_fear_index_copy):]

    if not tmp_greed_fear_his:
        tmp_greed_fear_his = greed_fear_index_copy[-3:]

    if not greed_fear_index_copy:
        return {'greed_fear': "no data!!", 'next_time': ''}
    
    if greed_fear_type == "now":
        return {'greed_fear':greed_fear_index_copy[-1], 'next_time': update_done['stocks'] if update_done['stocks'] else update_done['news']}
    
    if greed_fear_type == "history":
        return {'greed_fear_history': tmp_greed_fear_his, 'next_time': update_done['stocks'] if update_done['stocks'] else update_done['news']}
        
    if greed_fear_type == "all":
        return {'greed_fear':greed_fear_index_copy[-1], 'greed_fear_history': tmp_greed_fear_his, 'next_time': update_done['stocks'] if update_done['stocks'] else update_done['news']}
    
    return {'greed_fear': 'error', 'next_time': ''}

@app.get('/greed_fear_ratio')
async def get_greed_fear_ratio():
    return greed_fear_ratio

@app.post('/greed_fear_ratio')
async def change_greed_fear_ratio(new_ratios: dict):
    news = new_ratios.get('news', '')
    stock_price = new_ratios.get('stock_price', '')
    stock_volume = new_ratios.get('stock_volume', '')
    exchange = new_ratios.get('exchange', '')
    greed_fear = await update_greed_fear_index(2, news=news, stock_price=stock_price, stock_volume=stock_volume, exchange=exchange)
    return {'greed_fear': greed_fear}

def start_thread_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

async def main():
    # 創建新聞更新任務和股票更新任務
    update_news_task = asyncio.create_task(update_news(update_time=update_time))
    update_stocks_task = asyncio.create_task(update_stocks(stocks, n_day, start_date, end_data, use_close_price, update_time=update_time))

    # 等待所有任務完成
    await asyncio.gather(update_news_task, update_stocks_task)

if __name__ == "__main__":
    # 創建事件循環
    loop = asyncio.get_event_loop()

    # 創建用於提供FastAPI接口的線程
    thread = Thread(target=start_thread_loop, args=(loop,))
    thread.start()

    # 在主線程中啟動 FastAPI
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000) 

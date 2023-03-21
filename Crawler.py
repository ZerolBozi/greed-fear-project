# -*- coding: utf-8 -*-
from requests_html import AsyncHTMLSession, HTMLSession
# 爬蟲所使用的套件, 用於處理網頁前端html
from time import sleep, strftime, localtime, time
# 用於格式化時間、計算代理timeout及循環的延遲
from feedparser import parse
# RSS資料解析
import random
# 隨機取免費代理
import asyncio
# 異步處理
import threading
# 線程, 用於檢查proxy timeout

class Proxy:
    def __init__(self, proxy_count:int=5, use_timeout:bool=True ,proxy_timeout:int=600):
        """
        :param proxy_count: How many proxy you want?
        :type proxy_count: int
        :default = 5

        :param use_timeout: Do you want to use timeout to update the proxy?
        :type use_timeout: bool 
        :default = True

        :param proxy_timeout: your timeout is?
        :type proxy_timeout: int
        :default = 600(sec)
        """
        self.s = HTMLSession()
        self.s.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.53"}
        self.proxy_address='https://free-proxy-list.net/'
        self.proxy_count = proxy_count
        self.proxy_timeout = proxy_timeout
        self.valid_ips = []
        self.last_proxy_update = time()

        # 建立一個新的線程來運行 check_proxy_expiration 方法
        if use_timeout:
            self.timeout_thread = threading.Thread(target=self.check_proxy_expiration)
            self.timeout_thread.daemon = True
            self.timeout_thread.start()

    # 取得有效的IP
    def get_valid_ips(self):
        return self.valid_ips

    # 取得代理
    def get_proxy(self):
        """
        :rtype: list[str]
        """
        # reset
        self.valid_ips = []

        r = self.s.get(self.proxy_address)
        ip_list=[]
        for i in r.html.find('.container>.table-responsive .table.table-striped tbody tr'):
            Data=i.text.split('\n')
            ip_list.append(Data[0]+':'+Data[1])

        for ip in ip_list:
            try:
                result = self.s.get('http://api.ipify.org?format=json',proxies={'http': 'http://'+ip , 'https': 'https://'+ip},timeout=5)
                self.valid_ips.append({'http': f'http://{ip}'})
                print(result.json())
            except:
                continue
            if len(self.valid_ips) >= self.proxy_count:
                break

        return self.valid_ips

    # 更新代理
    def update_proxy(self, count:int = 0):
        """
        :param count: How many proxy you want?
        :type count: int
        :default = 0 (use init var)

        :rtype: list[str]
        """
        if count:
            self.proxy_count = count

        self.valid_ips = []
        self.last_proxy_update = time()
        valid_ips = self.get_proxy()
        return valid_ips

    # 檢查代理是否失效
    def check_proxy_expiration(self):
        while True:
            if time() - self.last_proxy_update > self.proxy_timeout:
                self.update_proxy()
                self.last_proxy_update = time()
            sleep(10)  # 每隔10秒檢查一次代理是否過期

class Crawler:
    # 爬蟲父類 存放共同參數、變數、函數
    def __init__(self, with_delay:bool=True, delay:float=1.5, with_proxy:bool=True, proxy_valid_ips:list=[], keywords:list=[], timeout:int=5):
        """
        :param with_delay: Do you want to use delay with each loop when you crawl the website?
        :type with_delay: bool
        :default = True

        :param delay: your delay is? (sec)
        :type delay: float 
        :default = 1.5

        :param with_proxy: Do you want to crawl with proxy? if you don't want to use, the program will use your local ip to crawl the website.
        :type with_proxy: bool
        :default = True

        :param proxy_valid_ips: a proxy pool
        :type proxy_valid_ips: list[str]
        :default = []

        :param keywords: a keyword list to split the news. 
        :type keywords: list
        :default = []

        :param timeout: your timeout is?
        :type timeout: int
        :default = 5(sec)
        """
        self.s = AsyncHTMLSession()
        self.s.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.53"}
        self.with_delay = with_delay
        self.delay = delay
        self.with_proxy = with_proxy
        self.valid_ips = proxy_valid_ips
        self.keywords = keywords
        self.timeout = timeout
        self.today = ""
        self.get_today_date()

        # API ADDRESS
        self.api_addresses = {
            'libertyTimes': "https://news.ltn.com.tw/ajax/breakingnews/business/",
            'megabank': {
                # TYPE = 1, 2, 4, 5, 6
                # 1 = 頭條, 2 = 國際股市, 4 = 外匯與債券, 5 = 國內外財經, 6 = 商品原物料
                # 每次查詢100筆, 從date前的100筆, 沒有設定date則返回最新100筆
                # 設定date參數 = 爬取某天"以前"的新聞
                'search': "https://fund.megabank.com.tw/ETFData/djjson/ETNEWSjson.djjson?a=",
                'content': "https://fund.megabank.com.tw/ETFData/djhtm/ETNEWSContentMega.djhtm?A="
            },
            'yahooFinanceTW': {
                'tw_market': 'https://tw.stock.yahoo.com/tw-market/',
                'intl_market': 'https://tw.stock.yahoo.com/intl-markets/',
                'funds': 'https://tw.stock.yahoo.com/funds-news/',
                'research': 'https://tw.stock.yahoo.com/research/',
                'rss_news': 'https://tw.stock.yahoo.com/rss?category=news',
                'rss_tw_market': 'https://tw.stock.yahoo.com/rss?category=tw-market',
                'rss_intl_market': 'https://tw.stock.yahoo.com/rss?category=intl-markets',
                'rss_funds': 'https://tw.stock.yahoo.com/rss?category=funds-news',
                'rss_research': 'https://tw.stock.yahoo.com/rss?category=research'
            }
        }
    
    # 更新proxy
    def update_proxy(self, proxy_valid_ips:list):
        """
        :param proxy_valid_ips: proxy pool
        :type proxy_valid_ips: list[str]
        """
        self.valid_ips = proxy_valid_ips

    def get_today_date(self):
        self.today = strftime("%Y/%m/%d",localtime())
        return self.today

class LibertyTimes(Crawler):
    async def get_news(self, is_today:bool=True ,limit:int=-1):
        """
        Inherited from Crawler class

        :param is_today: if you want to get today news then let this param to True.
        :type is_today: bool
        :default = True

        :param limit: crawl limit. How many news do you want?
        :type limit: int
        :default = -1

        :rtype: [news, news_with_keywords]
        """
        # is_today = True 代表取今天的新聞
        # 處理資料格式, 判斷時間是否為當日, 返回值 (data:dict, is_today:bool)
        async def process_data(item, proxy):
            try:
                r = await asyncio.wait_for(self.s.get(item['url'],proxies=proxy), timeout=self.timeout)
                div_p = r.html.find('.text p')[:-2]
                return {'title': item['title'], 'content': ''.join(cont.text for cont in div_p)}, "/" in item['time']
            except asyncio.TimeoutError:
                print(f"got the asyncio timeout error")
                return {}, False
            except Exception as e:
                print(f"got the error: {e}")
                return {}, False
        
        page = 1
        count = 0
        proxy = None
        valid_ips_cp = self.valid_ips.copy()
        news, news_with_keyword = [], []
        
        while True:

            if self.with_proxy:
                if len(valid_ips_cp) == 0:
                    valid_ips_cp = self.valid_ips.copy()
                proxy = random.choice(valid_ips_cp)
                valid_ips_cp.remove(proxy)
                print(f"proxy ip: {proxy['http']}")
            try:
                items = await asyncio.wait_for(self.s.get(f"{self.api_addresses['libertyTimes']}{page}",proxies=proxy), timeout=self.timeout)
            except asyncio.TimeoutError:
                print(f"got the asyncio timeout error")
                continue
            except Exception as e:
                print(f"got the error: {e}")
                continue
            items = items.json()['data']
            items = items if page == 1 else items.values()

            for item in items:
                tmp_struct, break_condition = process_data(item, proxy)

                if not tmp_struct:
                    continue

                if is_today and break_condition:
                    break
                
                haskeyword = False

                for keyword in self.keywords:
                    if keyword in tmp_struct['title'] or keyword in tmp_struct['content']:
                        haskeyword = True
                        break
                
                if haskeyword:
                    news_with_keyword.append(tmp_struct)
                else:
                    news.append(tmp_struct)
                
                count += 1

                if (not is_today) and count >= limit:
                    break_condition = True
                    break

                if self.with_delay:
                    await asyncio.sleep(self.delay)

            if break_condition:
                break

            page += 1
            # wait it if no wait it you will got the banned.
            if self.with_delay:
                await asyncio.sleep(self.delay)

        return [news, news_with_keyword]
    
class MegaBankNews(Crawler):
    def get_api_address_param(self, news_type:int, date:str):
        if date == '':
            return f"{news_type}&P1=mega&P2=&P3=true&P4=false&P5=false"
        else:
            # date type = yyyy-mm-dd
            return f"{news_type}&b={date}&P1=mega&P2=&P3=true&P4=false&P5=false"

    async def get_news(self, news_type: list=[1,2,4,5,6], date: str=""):
        """
        Inherited from Crawler class

        :param news_type: a news type list. 1 = top news, 2 = intl news, 4 = exchange, 5 = finance news, 6 = item ingredient
        :type news_type: list[int]
        :default = [1,2,4,5,6] (all type)

        :param date: When you want to start? if this value is empty, it will use today date (this value is back to search news. NOT IS START. For example: value is 2023-03-21, it will get the news before 2023-03-21.)
        :type date: str
        :default = ""

        :rtype: [news, news_with_keywords]
        """
        # 假設data沒有填 = 取得今日新聞
        # TYPE = 1, 2, 4, 5, 6
        # 1 = 頭條, 2 = 國際股市, 4 = 外匯與債券, 5 = 國內外財經, 6 = 商品原物料
        # 每次查詢100筆, 從date前的100筆, 沒有設定date則返回最新100筆
        # 設定date參數 = 爬取某天"以前"的新聞
        news, news_with_keyword = [], []
        valid_ips_cp = self.valid_ips.copy()

        for t in news_type:
            api_address = f"{self.api_addresses['megabank']['search']}{self.get_api_address_param(t, date)}"
            try:
                response = await asyncio.wait_for(self.s.get(api_address), timeout=self.timeout)
            except asyncio.TimeoutError:
                print(f"got the asyncio timeout error")
                continue
            except Exception as e:
                print(f"got the error: {e}")
                continue
            
            response = response.json()['ResultSet']['Result']

            for data in response:
                # V1 = News Date
                # V2 = News title
                # V3 = News link
                proxy = None
                if self.with_proxy:
                    if len(valid_ips_cp) == 0:
                        valid_ips_cp = self.valid_ips.copy()
                    proxy = random.choice(valid_ips_cp)
                    valid_ips_cp.remove(proxy)
                    print(f"proxy ip: {proxy['http']}")
                try:
                    p = await asyncio.wait_for(self.s.get(f"{self.api_addresses['megabank']['content']}{data['V3']}", proxies=proxy), timeout=self.timeout)
                except asyncio.TimeoutError:
                    print(f"got the asyncio timeout error")
                    continue
                except Exception as e:
                    print(f"got the error: {e}")
                    continue
                
                p = p.html.find('.NewsContent-Down p')
                content = ''.join(cont.text for cont in p)

                if not date:
                    if data['V1'] != self.today:
                        break

                haskeyword = False

                for keyword in self.keywords:
                    if keyword in data['V2'] or keyword in content:
                        haskeyword = True
                        break
                
                if haskeyword:
                    news_with_keyword.append({'date': data['V1'], 'title': data['V2'], 'content': content})
                else:
                    news.append({'date': data['V1'], 'title': data['V2'], 'content': content})

                if self.with_delay:
                    await asyncio.sleep(self.delay)

        return [news, news_with_keyword]
    
class YahooFinance_TW(Crawler):
    def get_all_news_type(self):
        return ['tw_market', 'intl_market', 'funds', 'research', 'rss_news', 'rss_tw_market', 'rss_intl_market', 'rss_funds', 'rss_research']
    
    def format_date(self, date_str: str):
        year = date_str[0:4]
        month = date_str[date_str.index('年')+1:date_str.index('月')]
        month = "0" + month if len(month) == 1 else month
        day = date_str[date_str.index('月')+1: date_str.index('日')]
        day = "0" + day if len(day) == 1 else day
        return f"{year}/{month}/{day}"
    
    async def process_link(self, addr:str):
        if 'rss' in addr:
            data = parse(addr)
            links = [news['links'][0]['href'] for news in data['entries']]
            await asyncio.sleep(0.01)
        else:
            try:
                links = await asyncio.wait_for(self.s.get(addr), timeout=self.timeout)
                links = links.html.find('#layout-col1 a')
                links = [list(link.absolute_links)[0] for link in links]
                # 過濾網址
                links = [link for link in links if "https://tw.stock.yahoo.com/news/%" in link]
            except asyncio.TimeoutError:
                print(f"got the asyncio timeout error")
                links = []
            except Exception as e:
                print(f"got the error: {e}")
                links = []
        return links
    
    async def get_news(self, news_type:list=['tw_market', 'intl_market', 'funds', 'research'], is_today:bool= True):
        """
        :param news_type: 'tw_market', 'intl_market', 'funds', 'research'
                            ,'rss_news', 'rss_tw_market', 'rss_intl_market', 'rss_funds', 'rss_research'
        :type news_type: list
        :if news_type list is None or [] then default = ['tw_market', 'intl_market', 'funds', 'research']

        :rtype: [news, news_with_keywords]
        """
        proxy = None
        valid_ips_cp = self.valid_ips.copy()
        news, news_with_keyword = [], []


        for t in news_type:
            address = self.api_addresses['yahooFinanceTW'][t]
            links = await self.process_link(address)

            if not links:
                continue

            for link in links:

                if self.with_proxy:
                    if len(valid_ips_cp) == 0:
                        valid_ips_cp = self.valid_ips.copy()
                    proxy = random.choice(valid_ips_cp)
                    valid_ips_cp.remove(proxy)
                    print(f"proxy ip: {proxy['http']}")
                try:
                    r = await asyncio.wait_for(self.s.get(link,proxies=proxy), timeout=self.timeout)
                except asyncio.TimeoutError:
                    print(f"got the asyncio timeout error")
                    continue
                except Exception as e:
                    print(f"got the error: {e}")
                    continue
                # date
                date = self.format_date(r.html.find('.caas-attr-time-style')[0].text)
                if is_today:
                    if date != self.today:
                        break
                # title
                title = r.html.find('.caas-title-wrapper')[0].text
                # content
                content = ''.join(cont.text for cont in r.html.find('.caas-body p'))

                haskeyword = False

                for keyword in self.keywords:
                    if keyword in title or keyword in content:
                        haskeyword = True
                        break

                if haskeyword:
                    news_with_keyword.append({'title':title,'content':content})
                else:
                    news.append({'title':title,'content':content})
                
                if self.with_delay:
                    await asyncio.sleep(self.delay)

            if self.with_delay:
                await asyncio.sleep(self.delay)
        
        return [news, news_with_keyword]
    
async def test():
    proxy = Proxy()
    keywords = [
        "半導體", "電子", "積體電路", "晶圓", "晶片", "晶片組",
        "微控制器", "微處理器", "IC", "ASIC", "FPGA", "DRAM", 
        "SRAM", "快閃記憶體", "儲存器", "顯示器", "OLED", "LED",
        "液晶顯示", "軟體", "硬體", "IoT", "物聯網", "5G",
        "藍牙", "無線通信", "射頻", "電池", "充電", "太陽能",
        "光伏", "能源儲存", "電源管理", "電動汽車", "自動駕駛", "智慧家庭",
        "半導體製程", "台積電", "三星", "英特爾", "高通", "美光",
        "聯發科", "海力士", "蘋果", "華為", "富士康", "鴻海", 
        "廣達", "瑞昱", "創意", "友達", "群創", "聯詠",
        "微軟", "openai", "google", "mata", "人工智慧", "深度學習",
        "模型", "GPT", "聯準會", "美聯儲", "GDP", "intel",
        "顯示卡", "算力", "nvidia", "通貨膨脹", "通膨", "美元",
        "特斯拉", "馬斯克", "Tesla", "Elon Musk", "Fed","AI"
    ]
    #mbn = MegaBankNews(delay=0.5, proxy_valid_ips=proxy.get_valid_ips(),keywords=keywords)
    #data = await mbn.get_news(2,"2023-03-17")
    #print(data)
    yft = YahooFinance_TW(delay=0.5, proxy_valid_ips=proxy.get_valid_ips(),keywords=keywords)
    data = await yft.get_news(is_today=False)
    print(data)
    
if __name__ == "__main__":
    asyncio.run(test())
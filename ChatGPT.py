# -*- coding: utf-8 -*-
import openai
import random
import asyncio
import re

class ChatBot:
    def __init__(self, api_keys:list):
        self.api_keys = api_keys
        self.api_keys_copy = self.api_keys.copy()

    def ask(self, message1:str, message2:str, model:str="gpt-3.5-turbo", temperature:float=0):
        """
        :message1 = 你要他做的事情
        :message2 = 問題
        """
        openai.api_key = self.get_api_key()
        message = [
            {"role": "system", "content": message1},
            {"role": "user", "content": message2}
        ]
        response = openai.ChatCompletion.create(
            model= model,
            messages = message,
            stream = False,
            temperature = temperature
        )

        return response['choices'][0]['message']['content']
    
    def ask_news_score(self, news_content:str, model:str="gpt-3.5-turbo", temperature:float=0):
        """
        :news_content = 新聞內容
        :model = 使用的模型
        :temperature = 是否採用隨機答案 (0-1的數) 0 = 固定, 1 = 隨機
        """
        openai.api_key = self.get_api_key()
        message = [
            {"role": "system", "content": '你現在是文章分析助手, 將我給的文章進行理解分析與判斷, 請返回兩個結果:1.範圍[0-100]的分數(分數0代表投資者恐慌, 分數100代表投資者貪婪) 2.範圍[0-100]的電子科技股票相關之百分比(如果會影響到台股大盤走勢或世界經濟使總體股價下跌也算是相關聯, 無法確定則為0%), 回答方式如下:"以簡潔的方式回答", 回答格式:0-100的分數,關聯之百分比'},
            {"role": "user", "content": news_content}
        ]
        response = openai.ChatCompletion.create(
            model= model,
            messages = message,
            stream = False,
            temperature = temperature
        )
        score, percentage = self.check_response_format(response['choices'][0]['message']['content'])

        return score, percentage
    
    async def ask_news_score_async(self, news_content:str, model:str="gpt-3.5-turbo", temperature:float=0, timeout:int = 5):
        """
        :news_content = 新聞內容
        :model = 使用的模型 (default = gpt-3.5-turbo)
        :temperature = 是否採用隨機答案 (0-1的數) 0 = 固定, 1 = 隨機
        """
        openai.api_key = self.get_api_key()
        message = [
            {"role": "system", "content": '你現在是文章分析助手, 將我給的文章進行理解分析與判斷, 請返回兩個結果:1.範圍[0-100]的分數(分數0代表投資者恐慌, 分數100代表投資者貪婪) 2.範圍[0-100]的電子科技股票相關之百分比(如果會影響到台股大盤走勢或世界經濟使總體股價下跌也算是相關聯, 無法確定則為0%), 回答方式如下:"以簡潔的方式回答", 回答格式:0-100的分數,關聯之百分比'},
            {"role": "user", "content": news_content}
        ]
        try:
            response = await asyncio.wait_for(openai.ChatCompletion.acreate(
                    model= model,
                    messages = message,
                    stream = False,
                    temperature = temperature
                ),
                timeout=timeout
            )
            score, percentage = self.check_response_format(response['choices'][0]['message']['content'])
       
        except asyncio.TimeoutError:
            print("asyncio timeout error")
            score, percentage = 0, 0
        except Exception as e:
            print(e)
            score, percentage = 0, 0

        return score, percentage
    
    def check_response_format(self, response:str):
        res = response.split(",")
        if len(res) != 2:
            return "",""
        
        # 有時候GPT會回答原因, 要排除掉
        finded_0 = re.findall(r"[-+]?\d*\.\d+|\d+", res[0])
        finded_1 = re.findall(r"[-+]?\d*\.\d+|\d+", res[1])
        
        # 從回答中找出分數及權重
        if finded_0 and finded_1:
            res[0] = float(finded_0[0])
            res[1] = float(finded_1[0].strip("%")) / 100
            return res[0], res[1]
        
        return 0, 0

    def get_api_key(self):
        if len(self.api_keys_copy) == 0:
            self.api_keys_copy = self.api_keys.copy()
        api_key = random.choice(self.api_keys_copy)
        self.api_keys_copy.remove(api_key)
        return api_key
    
async def test():
    chat_bot = ChatBot([])
    score, percentage = await chat_bot.ask_news_score_async('title:《國際金融》矽銀風暴 Fed一周借3,000億美元救命金, content: 【時報-台北電】美國聯準會（Fed）表示，自矽谷銀行與標誌銀行（Signature Bank）相繼倒閉後，過去一周美國銀行業透過緊急借貸機制，向Fed取得總計約3,000億美元資金，凸顯美國金融系統正面臨龐大壓力。受此影響，外界預測Fed在下周決策會議將暫緩激進升息腳步。根據芝商所Fedwatch tool最新數據顯示，交易商目前押注Fed下周升息1碼的機率將近85％、按兵不動為15.1％、至於押注2碼的機率則是降至零。聯準會提供約1,430億美元給聯邦存款保險公司（FDIC）接管、並對其設立控股公司的矽谷與標誌銀行。這兩家銀行的控股公司，將以債券為擔保品，把取得的貸款用來支付未投保的存戶。其他近1,650億美元資金則被其他銀行用來籌措現金，以因應存戶提款。這1,650億美元資金中，有1,530億美元是銀行經由Fed現有的緊急貸款計畫，也就是外界所稱的「貼現窗口」取得，該金額已超越2008年金融海嘯時期的1,110億美元，創下該計畫啟動以來的歷史新高。凱投宏觀北美經濟學家雅許沃斯（Paul Ashworth）表示，貼現窗口借出的融通金額激增，凸顯美國金融系統正處於嚴重危機，這將對實質經濟造成明顯的漣漪效應。另外，Fed在周日成立的銀行定期融資計畫（BTFP），也借出119億美元資金，該機制讓銀行可以應付存戶提款，而不用被迫出售資產。摩根大通預估，作為最新的緊急資金融通機制，BTFP最終向美國金融系統挹注的流動性資金上限約為2兆美元。(新聞來源 : 工商時報一蕭麗君／綜合外電報導)')
    print(score, percentage)
    
if __name__ == "__main__":
    # chat_bot = ChatBot(['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'])
    # msg1 = '你現在是文章分析助手, 將我給的文章進行理解分析與判斷, 請返回兩個結果:1.範圍[0-100]的分數(分數0代表投資者恐慌, 分數100代表投資者貪婪) 2.範圍[0-100]的電子科技股票相關之百分比(如果會影響到台股大盤走勢或世界經濟使總體股價下跌也算是相關聯, 無法確定則為0%), 回答方式如下:"以簡潔的方式回答", 回答格式:0-100的分數,關聯之百分比'
    # msg2 = 'title:《國際金融》矽銀風暴 Fed一周借3,000億美元救命金, content: 【時報-台北電】美國聯準會（Fed）表示，自矽谷銀行與標誌銀行（Signature Bank）相繼倒閉後，過去一周美國銀行業透過緊急借貸機制，向Fed取得總計約3,000億美元資金，凸顯美國金融系統正面臨龐大壓力。受此影響，外界預測Fed在下周決策會議將暫緩激進升息腳步。根據芝商所Fedwatch tool最新數據顯示，交易商目前押注Fed下周升息1碼的機率將近85％、按兵不動為15.1％、至於押注2碼的機率則是降至零。聯準會提供約1,430億美元給聯邦存款保險公司（FDIC）接管、並對其設立控股公司的矽谷與標誌銀行。這兩家銀行的控股公司，將以債券為擔保品，把取得的貸款用來支付未投保的存戶。其他近1,650億美元資金則被其他銀行用來籌措現金，以因應存戶提款。這1,650億美元資金中，有1,530億美元是銀行經由Fed現有的緊急貸款計畫，也就是外界所稱的「貼現窗口」取得，該金額已超越2008年金融海嘯時期的1,110億美元，創下該計畫啟動以來的歷史新高。凱投宏觀北美經濟學家雅許沃斯（Paul Ashworth）表示，貼現窗口借出的融通金額激增，凸顯美國金融系統正處於嚴重危機，這將對實質經濟造成明顯的漣漪效應。另外，Fed在周日成立的銀行定期融資計畫（BTFP），也借出119億美元資金，該機制讓銀行可以應付存戶提款，而不用被迫出售資產。摩根大通預估，作為最新的緊急資金融通機制，BTFP最終向美國金融系統挹注的流動性資金上限約為2兆美元。(新聞來源 : 工商時報一蕭麗君／綜合外電報導)'
    # chat_bot.ask_news_score(msg1,msg2)
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())

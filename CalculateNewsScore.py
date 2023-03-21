# -*- coding: utf-8 -*-
from ChatGPT import ChatBot
import asyncio

class CalculateNews:
    def __init__(self, api_keys:list, news:list, limit:int=50, roundto:int=-1):
        self.chat_bot = ChatBot(api_keys)
        self.news = news
        self.limit = limit
        self.roundto = roundto

    async def get_news_score(self):
        total_score = 0
        count = 0

        for n in self.news:

            if count > self.limit:
                break

            title = n.get('title', '')
            content = n.get('content', '')
            if title and content:
                score, percentage = await self.chat_bot.ask_news_score_async(f"title: {title}, content: {content}")
                # sum
                if score and percentage:
                    total_score += score * percentage
                    print(f"title: {title}, score: {score}, percentage: {percentage}")
                    count += 1
                    await asyncio.sleep(1)
        # avg
        return round(total_score / count, self.roundto) if self.roundto > -1 else total_score / count
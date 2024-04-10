
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite

from .models import RealTime
from constants import DEFAILT_GPT_ANSWER

class Ygosu(AbstractCommunityWebsite):
    def __init__(self):
        pass
    
    def get_daily_best(self):
        '''
        ygosu RealTimeBest post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        req = requests.get('https://ygosu.com/board/real_article')
        soup = BeautifulSoup(req.text, 'html.parser')

        result = []
        for tr in soup.select('tbody tr'):
            tit_element = tr.select_one('.tit a')
            if tit_element:
                title = tit_element.get_text(strip=True)
                url = tit_element['href']
                result.append({"title": title, "url": url})

        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data

    def get_real_time_best(self):
        '''
        ygosu RealTimeBest post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        req = requests.get('https://ygosu.com/board/real_article')
        soup = BeautifulSoup(req.text, 'html.parser')

        result = []
        for tr in soup.select('tbody tr'):
            tit_element = tr.select_one('.tit a')
            create_time_element = tr.select_one('.date') 
            if tit_element:
                # print(tit_element)
                title = tit_element.get_text(strip=True)
                create_time = create_time_element.get_text(strip=True) 
                if (create_time == '' or ':' not in create_time):
                    continue
                url = tit_element['href']
                url_parts = url.split('/')
                now = datetime.now()
                hour, minute, second = map(int, create_time.split(':'))
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)
                for board_id in url_parts:
                    if board_id.isdigit():
                        break

                RealTime.objects.get_or_create(
                            _id=board_id,
                            defaults={
                                'site' : 'ygosu',
                                'title': title,
                                'url': url,
                                'create_time': target_datetime,
                                'GPTAnswer': DEFAILT_GPT_ANSWER
                            }
                        )

        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data
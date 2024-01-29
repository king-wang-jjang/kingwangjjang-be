from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
from .models import RealTime
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite

class Dcinside(AbstractCommunityWebsite):
    def __init__(self):
        pass

    def GetDayBest(self):
        pass

    def GetRealTimeBest(self):
        headers = [
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
        ]

        req = requests.get('https://www.dcinside.com/', headers=headers[0])
        html_content = req.text

        soup = BeautifulSoup(html_content, 'html.parser')

        li_elements = soup.select('#dcbest_list_date li')
        
        real_time_instances = []

        for li in li_elements:
            p_element = li.select_one('.box.besttxt p')
            a_element = li.select_one('.main_log')
            time_element = li.select_one('.box.best_info .time')

            if p_element and a_element and time_element:
                p_text = p_element.get_text(strip=True)
                a_href = a_element['href']
                no_value = a_href.split('no=')[-1]
                time_text = time_element.get_text(strip=True)
                
                if(time_text.find('-') > 0): break # 어제껀 추가안함
                # 시간 13:40 -> 2024.01.29 13:40 로 수정
                now = datetime.now()
                hour, minute = map(int, time_text.split(':'))
                # 시간 설정 및 datetime 객체 생성
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)
                real_time_instance = RealTime(
                    _id=no_value,
                    title=p_text,
                    url=a_href,
                    create_time=target_datetime 
                )
                real_time_instances.append(real_time_instance)

        RealTime.objects.bulk_create(real_time_instances)
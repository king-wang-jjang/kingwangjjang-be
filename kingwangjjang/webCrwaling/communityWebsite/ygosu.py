
from datetime import datetime
import os
from bs4 import BeautifulSoup
from django.conf import settings
import requests
from utils import FTPClient
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite

from .models import Daily, RealTime
from constants import DEFAILT_GPT_ANSWER

class Ygosu(AbstractCommunityWebsite):
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime('%Y%m%d')
        
        try:
            self.ftp_client = FTPClient(
                                server_address=getattr(settings, 'FTP_SERVER', None),
                                username=getattr(settings, 'FTP_USER', None),
                                password=getattr(settings, 'FTP_PASSWORD', None))
            super().__init__(self.yyyymmdd, self.ftp_client)
            print("ready to today directory")
        except Exception as e:
            print("Dcinside error:", e)
            return None
    
    def get_daily_best(self):
        '''
        ygosu RealTimeBest post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        req = requests.get('https://ygosu.com/board/best_article/?type=daily')
        soup = BeautifulSoup(req.text, 'html.parser')
        already_exists_post = []

        for tr in soup.select('tbody tr'):
            tit_element = tr.select_one('.tit a')
            create_time_element = tr.select_one('.day')
            rank_element = tr.select_one('.num')
            if tit_element:
                title = tit_element.get_text(strip=True)
                rank = rank_element.get_text(strip=True)
                create_time = create_time_element.get_text(strip=True) 
                if (create_time == ''): # 광고 및 공지 제외
                    continue
                
                url = tit_element['href']
                url_parts = url.split('/')
                year, month, day = map(int, create_time.split('-'))
                target_datetime = datetime(year, month, day)
                for board_id in url_parts:
                    if board_id.isdigit():
                        break
                try:
                    existing_instance = Daily.objects.filter(board_id=board_id, site='ygosu').first() # 이미 있는 Board는 넘기기
                    if existing_instance:
                        already_exists_post.append(board_id)
                        continue
                    else:
                        Daily.objects.get_or_create(
                            board_id=board_id,
                            rank=rank,
                            site='ygosu',
                            title=title,
                            url=url,
                            create_time=target_datetime,
                            GPTAnswer=DEFAILT_GPT_ANSWER
                        )
                except Exception as e:
                    print(e)
                    
        print("already exists post", already_exists_post)

    def get_real_time_best(self):
        '''
        ygosu RealTimeBest post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        req = requests.get('https://ygosu.com/board/real_article')
        soup = BeautifulSoup(req.text, 'html.parser')
        already_exists_post = []

        for tr in soup.select('tbody tr'):
            tit_element = tr.select_one('.tit a')
            create_time_element = tr.select_one('.date')
            
            if tit_element:
                
                title = tit_element.get_text(strip=True)
                create_time = create_time_element.get_text(strip=True) 
                if (create_time == '' or ':' not in create_time): # 광고 및 공지 제외 및 금일만 추출
                    continue
                
                url = tit_element['href']
                url_parts = url.split('/')
                now = datetime.now()
                hour, minute, second = map(int, create_time.split(':'))
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)
                for board_id in url_parts:
                    if board_id.isdigit():
                        break
                try:
                    existing_instance = RealTime.objects.filter(board_id=board_id, site='ygosu').first() # 이미 있는 Board는 넘기기
                    if existing_instance:
                        already_exists_post.append(board_id)
                        continue
                    else:
                        RealTime.objects.get_or_create(
                            board_id=board_id,
                            site='ygosu',
                            title=title,
                            url=url,
                            create_time=target_datetime,
                            GPTAnswer=DEFAILT_GPT_ANSWER
                        )
                except Exception as e:
                    print(e)
                    
        print("already exists post", already_exists_post)

    def get_board_contents(self, board_id):
        abs_path = f'./{self.yyyymmdd}/{board_id}'
        self.download_path = os.path.abspath(abs_path) 
        daily_instance = Daily.objects.filter(board_id=board_id, site='ygosu').first()
        if daily_instance:
            response = requests.get(daily_instance.url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                board_body = soup.find('div', class_='container')
                paragraphs = board_body.find_all('p')


                for p in paragraphs:
                    # <p> 태그 안에 <img> 태그가 있는지 확인
                    if p.find('img'):
                        print(p)
                    else:
                        print(p)
            else:
                print("Failed to retrieve the webpage")
            
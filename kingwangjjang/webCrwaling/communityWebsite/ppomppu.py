import re
from bs4 import BeautifulSoup
import requests
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite
from datetime import datetime
from mongo import DBController
from utils import FTPClient
import logging
from django.conf import settings
from constants import DEFAULT_GPT_ANSWER, SITE_PPOMPPU
import os

logger = logging.getLogger("")
class Ppomppu(AbstractCommunityWebsite):
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime('%Y%m%d')
        self.db_controller = DBController()
        try:
            self.ftp_client = FTPClient(
                                server_address=getattr(settings, 'FTP_SERVER', None),
                                username=getattr(settings, 'FTP_USER', None),
                                password=getattr(settings, 'FTP_PASSWORD', None))
            super().__init__(self.yyyymmdd, self.ftp_client)

        except Exception as e:
            logger.info("Dcinside error:", e)
            return None
    
    def get_daily_best(self):
        pass        

    def get_real_time_best(self):
        '''
        ppomppu daily post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        num = 1
        _url = f"https://www.ppomppu.co.kr/hot.php?id=&page={num}&category=999&search_type=&keyword=&page_num=&del_flag=&bbs_list_category=0"
        response = requests.get(_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        now = datetime.now()
        already_exists_post = []

        result = []

        for tr in soup.find_all('tr', class_='line'):
            title_element = tr.find('a', class_='title')
            create_time_element = tr.find('td', class_='board_date')
            create_time = create_time_element.get_text(strip=True)
            # create_time = create_time_element.text.strip()  
            

            if title_element:
                # title = title_element.text.strip()  
                title = title_element.get_text(strip=True)
                domain = domain + "https://ppomppu.co.kr"
                url = title_element['href']
                # url_parts = url.split("/")
                board_id = self.extract_id_and_no_from_url(url)
                hour, minute, second = map(int, create_time.split(":"))
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)
                # contents_url = domain + url

                if ("/" in create_time): 
                    break

                try:
                    existing_instance = self.db_controller.select('RealTime', {'board_id': board_id, 'site': SITE_PPOMPPU})
                    if existing_instance:
                        already_exists_post.append(board_id)
                        continue
                    else:
                        gpt_exists = self.db_controller.select('GPT', {'board_id': board_id, 'site': SITE_PPOMPPU})
                        if gpt_exists:
                            gpt_obj_id = gpt_exists[0]['_id']
                        else :
                            gpt_obj = self.db_controller.insert('GPT', {
                                'board_id': board_id,
                                'site': SITE_PPOMPPU,
                                'answer': DEFAULT_GPT_ANSWER
                            })
                            gpt_obj_id = gpt_obj.inserted_id
                            
                        self.db_controller.insert('RealTime', {
                            'board_id': board_id,
                            'site': SITE_PPOMPPU,
                            'title': title,
                            'url': url,
                            'create_time': target_datetime,
                            'GPTAnswer': gpt_obj_id
                        })
                except Exception as e:
                    logger.info(e)
                    
        logger.info({"already exists post": already_exists_post})
        
        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data
    
    def extract_id_and_no_from_url(self, url):
        pattern = r"id=([^&]*)&no=([^&]*)"
        match = re.search(pattern, url)
        if match:
            id_value = match.group(1)
            no_value = match.group(2)
            return id_value + no_value
        else:
            return None
        
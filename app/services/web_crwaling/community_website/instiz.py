import re
from bs4 import BeautifulSoup
import requests
from services.web_crwaling.community_website.community_website import AbstractCommunityWebsite
from datetime import datetime
from mongo import DBController
from utils import FTPClient
import logging
from config import Config
from constants import DEFAULT_GPT_ANSWER, SITE_INSTIZ
from celery_app import celery_app

import os
logger = logging.getLogger("")
class Instiz(AbstractCommunityWebsite):
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime('%Y%m%d')
        self.db_controller = DBController()
        try:
            self.ftp_client = FTPClient(
                                server_address=Config().get('FTP_HOST'),
                                username=Config().get('FTP_USERNAME'),
                                password=Config().get('FTP_PASSWORD'))
            super().__init__(self.yyyymmdd, self.ftp_client)

        except Exception as e:
            logger.info("Instiz error:", e)
            return None
    
    def get_daily_best(self):
        pass        

    def get_real_time_best(self):
        '''
        ppomppu daily post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        _url = f"https://www.instiz.net/"
        response = requests.get(_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        now = datetime.now()
        already_exists_post = []

        result = []
        for tr in soup.find_all('a', class_='rank_href'):
            title_element = tr.find('span',)
            # create_time_element = tr.find('td', class_='board_date')
            # create_time = create_time_element.get_text(strip=True)
            link_element = tr
            link = link_element['href']
            # create_time = create_time_element.text.strip()


            if title_element:
                # title = title_element.text.strip()  
                title = tr.get_text(strip=True).replace(tr.find('span','itsme rank').get_text(strip=True)+tr.find('span','minitext').get_text(strip=True),'').replace(tr.find('span','cmt').get_text(strip=True),'')

                # print(title)
                domain = "https://instiz.co.kr"
                url = link.replace('//','https://')
                # url_parts = url.split("/")
                board_id = url.split('/')[-1]
                date_format = "%Y-%m-%dT%H:%M"
                target_datetime = datetime.strptime(self.extract_time(url), date_format)
                # contents_url = domain + url
                contents_url = url



                try:
                    existing_instance = self.db_controller.select('RealTime', {'board_id': board_id, 'site': SITE_INSTIZ})
                    if existing_instance:
                        already_exists_post.append(board_id)
                        continue
                    else:
                        gpt_exists = self.db_controller.select('GPT', {'board_id': board_id, 'site': SITE_INSTIZ})
                        if gpt_exists:
                            gpt_obj_id = gpt_exists[0]['_id']
                        else :
                            gpt_obj = self.db_controller.insert('GPT', {
                                'board_id': board_id,
                                'site': SITE_INSTIZ,
                                'answer': DEFAULT_GPT_ANSWER
                            })
                            gpt_obj_id = gpt_obj.inserted_id
                            
                        self.db_controller.insert('RealTime', {
                            'board_id': board_id,
                            'site': SITE_INSTIZ,
                            'title': title,
                            'url': contents_url,
                            'create_time': target_datetime,
                            'GPTAnswer': gpt_obj_id
                        })
                except Exception as e:
                    logger.info(e)
                    
        logger.info({"already exists post": already_exists_post})
        

    def extract_time(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.find('span',{'itemprop':'datePublished'}).get('content')
    def get_board_contents(self, board_id):
        abs_path = f'./{self.yyyymmdd}/{board_id}'
        self.download_path = os.path.abspath(abs_path) 
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
        daily_instance = self.db_controller.select('RealTime', {'board_id': board_id, 'site': 'ppomppu'})
        content_list = []
        if daily_instance:
            response = requests.get(daily_instance[0]['url'], headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                board_body = soup.find('div', class_='memo_content')
                paragraphs = board_body.find_all('p')

                for p in paragraphs:
                    # <p> 태그 안에 <img> 태그가 있는지 확인
                    if p.find('img'):
                        img_tag = p.find('img')
                        img_url = "https:" + img_tag['src']
                        try:
                            img_txt = super().img_to_text(self.save_img(img_url))
                            content_list.append({'type': 'image', 'url': img_url, 
                                                'content': img_txt})
                        except Exception as e:
                            logger.info(f'Instiz Error {e}')
                    elif p.find('video'):
                        video_tag = p.find('video')
                        video_url = "https:" + video_tag.find('source')['src']
                        try:
                            self.save_img(video_url)
                        except Exception as e:
                            logger.info(f'Instiz Error {e}')
                    else: 
                        content_list.append({'type': 'text', 'content': p.text.strip()})
            else:
                logger.info("Failed to retrieve the webpage")
        return content_list
    
            
    def save_img(self, url):
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        response = requests.get(url)
        img_name = os.path.basename(url)
        # 이미지를 파일로 저장
        with open(os.path.join( self.download_path, img_name), 'wb') as f:
            f.write(response.content)

        return self.download_path + "/" + img_name

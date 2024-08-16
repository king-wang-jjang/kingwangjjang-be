import re
from bs4 import BeautifulSoup
import requests
from datetime import datetime

from pygments.lexers import q
from app.utils.loghandler import catch_exception
import sys
sys.excepthook = catch_exception
from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.community_website import AbstractCommunityWebsite
from app.utils import FTPClient
import logging
from app.config import Config
from app.constants import DEFAULT_GPT_ANSWER, SITE_RULIWEB,DEFAULT_TAG
import os
from app.utils.loghandler import setup_logger

logger = setup_logger()
class Ruliweb(AbstractCommunityWebsite):
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime('%Y%m%d')
        self.db_controller = MongoController()
        try:
            self.ftp_client = FTPClient.FTPClient(
                                server_address=Config().get_env('FTP_HOST'),
                                username=Config().get_env('FTP_USERNAME'),
                                password=Config().get_env('FTP_PASSWORD'))
            super().__init__(self.yyyymmdd, self.ftp_client)

        except Exception as e:
            logger.info("ruliweb error:", e)
            return None
    
    def get_daily_best(self):
        '''
        ppomppu daily post

        :return: {rank: { {title: string, url: string}[]} }
        '''
        global tag_obj_id
        num = 1
        _url = f"https://bbs.ruliweb.com/best/humor_only/now?orderby=best_id&range=24h"
        response = requests.get(_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        now = datetime.now()
        already_exists_post = []

        result = []

        for tr in soup.find_all('li', class_='item blocktarget'):
            title_element = tr.find('a', class_='deco')

            # create_time = create_time_element.text.strip()

            if title_element:
                # title = title_element.text.strip()
                title = title_element.get_text(strip=True)
                domain = "https://bbs.ruliweb.co.kr"
                url = title_element['href']
                # url_parts = url.split("/")
                board_id = url.split('/')[-1]
                target_datetime = datetime(now.year, now.month, now.day)
                # contents_url = domain + url
                contents_url = url


                try:
                    existing_instance = self.db_controller.find('Daily',
                                                                  {'board_id': board_id, 'site': SITE_RULIWEB})
                    if existing_instance:
                        already_exists_post.append(board_id)
                        continue
                    else:
                        gpt_exists = self.db_controller.find('GPT', {'board_id': board_id, 'site': SITE_RULIWEB})
                        if gpt_exists:
                            gpt_obj_id = gpt_exists[0]['_id']
                        else:
                            gpt_obj = self.db_controller.insert_one('GPT', {
                                'board_id': board_id,
                                'site': SITE_RULIWEB,
                                'answer': DEFAULT_GPT_ANSWER
                            })
                            gpt_obj_id = gpt_obj.inserted_id
                        tag_exists = self.db_controller.find('TAG', {'board_id': board_id, 'site': SITE_RULIWEB})
                        if tag_exists:
                            tag_obj_id = tag_exists[0]['_id']
                        else:
                            tag_obj = self.db_controller.insert_one('TAG', {
                                'board_id': board_id,
                                'site': SITE_RULIWEB,
                                'Tag': DEFAULT_TAG
                            })
                            tag_obj_id = tag_obj.inserted_id
                        self.db_controller.insert_one('Daily', {
                            'board_id': board_id,
                            'site': SITE_RULIWEB,
                            'title': title,
                            'url': contents_url,
                            'create_time': target_datetime,
                            'GPTAnswer': gpt_obj_id,
                            'Tag': tag_obj_id
                        })
                except Exception as e:
                    logger.info(e)

        logger.info({"already exists post": already_exists_post})

        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data

    def get_real_time_best(self):
        pass
    

    def get_board_contents(self, board_id):
        abs_path = f'./{self.yyyymmdd}/{board_id}'
        self.download_path = os.path.abspath(abs_path) 
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
        daily_instance = self.db_controller.find('Daily', {'board_id': board_id, 'site': 'ruliweb'})
        content_list = []
        if daily_instance:
            response = requests.get(daily_instance[0]['url'], headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                board_body = soup.find('td', class_='board-contents')
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
                            logger.info(f'ruliweb Error {e}')
                    elif p.find('video'):
                        video_tag = p.find('video')
                        video_url = "https:" + video_tag.find('source')['src']
                        try:
                            self.save_img(video_url)
                        except Exception as e:
                            logger.info(f'ruliweb Error {e}')
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
Ruliweb().get_daily_best()
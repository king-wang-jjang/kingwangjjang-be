from datetime import datetime
import os
from bs4 import BeautifulSoup
import requests
from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.community_website import AbstractCommunityWebsite
from app.utils.FTPClient import FTPClient
from app.constants import DEFAULT_GPT_ANSWER, SITE_YGOSU, DEFAULT_TAG
import logging
from app.config import Config
from app.utils.loghandler import setup_logger, catch_exception
import sys
sys.excepthook = catch_exception

logger = setup_logger()

class Ygosu(AbstractCommunityWebsite):
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime('%Y%m%d')
        self.db_controller = MongoController()
        try:
            logger.info(f"Initializing Ygosu for date: {self.yyyymmdd}")
            self.ftp_client = FTPClient(
                server_address=Config().get_env('FTP_HOST'),
                username=Config().get_env('FTP_USERNAME'),
                password=Config().get_env('FTP_PASSWORD')
            )
            super().__init__(self.yyyymmdd, self.ftp_client)
            logger.info("Ygosu initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Ygosu: {e}")

    def get_daily_best(self):
        logger.info("Fetching daily best posts from Ygosu")
        try:
            req = requests.get('https://ygosu.com/board/best_article/?type=daily')
            req.raise_for_status()
            soup = BeautifulSoup(req.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching Ygosu daily best: {e}")
            return

        already_exists_post = []

        for tr in soup.find_all('tr'):
            try:
                tit_element = tr.select_one('.tit a')
                create_time_element = tr.select_one('.day')
                rank_element = tr.select_one('.num')

                if tit_element and create_time_element and rank_element:
                    title = tit_element.get_text(strip=True)
                    rank = rank_element.get_text(strip=True)
                    create_time = create_time_element.get_text(strip=True)

                    if not create_time:  # 광고 및 공지 제외
                        continue

                    url = tit_element['href']
                    year, month, day = map(int, create_time.split('-'))
                    target_datetime = datetime(year, month, day)

                    board_id = self._extract_board_id(url)
                    if self._post_already_exists(board_id, 'Daily'):
                        already_exists_post.append(board_id)
                        continue

                    gpt_obj_id = self._get_or_create_gpt_object(board_id)
                    tag_obj_id = self._get_or_create_tag_object(board_id)

                    self.db_controller.insert_one('Daily', {
                        'board_id': board_id,
                        'site': SITE_YGOSU,
                        'rank': rank,
                        'title': title,
                        'url': url,
                        'create_time': target_datetime,
                        'GPTAnswer': gpt_obj_id,
                        'Tag': tag_obj_id
                    })
                    logger.info(f"Post {board_id} inserted successfully")
            except Exception as e:
                logger.error(f"Error processing post: {e}")

        logger.info({"already exists post": already_exists_post})

    def get_real_time_best(self):
        logger.info("Fetching real-time best posts from Ygosu")
        try:
            req = requests.get('https://ygosu.com/board/real_article')
            req.raise_for_status()
            soup = BeautifulSoup(req.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching Ygosu real-time best: {e}")
            return

        already_exists_post = []

        for tr in soup.find_all('tr'):
            try:
                tit_element = tr.select_one('.tit a')
                create_time_element = tr.select_one('.date')

                if tit_element and create_time_element:
                    title = tit_element.get_text(strip=True)
                    create_time = create_time_element.get_text(strip=True)

                    if not create_time or ':' not in create_time:  # 광고 및 공지 제외
                        continue

                    url = tit_element['href']
                    now = datetime.now()
                    hour, minute = map(int, create_time.split(':'))
                    target_datetime = datetime(now.year, now.month, now.day, hour, minute)

                    board_id = self._extract_board_id(url)
                    if self._post_already_exists(board_id, 'RealTime'):
                        already_exists_post.append(board_id)
                        continue

                    gpt_obj_id = self._get_or_create_gpt_object(board_id)
                    tag_obj_id = self._get_or_create_tag_object(board_id)

                    self.db_controller.insert_one('RealTime', {
                        'board_id': board_id,
                        'site': SITE_YGOSU,
                        'title': title,
                        'url': url,
                        'create_time': target_datetime,
                        'GPTAnswer': gpt_obj_id,
                        'Tag': tag_obj_id
                    })
                    logger.info(f"Post {board_id} inserted successfully")
            except Exception as e:
                logger.error(f"Error processing real-time post: {e}")

        logger.info({"already exists post": already_exists_post})

    def get_board_contents(self, board_id):
        logger.info(f"Fetching contents for board_id: {board_id}")
        abs_path = f'./{self.yyyymmdd}/{board_id}'
        self.download_path = os.path.abspath(abs_path)
        daily_instance = self.db_controller.find('RealTime', {'board_id': board_id, 'site': SITE_YGOSU})

        content_list = []
        if daily_instance:
            try:
                response = requests.get(daily_instance[0]['url'])
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                board_body = soup.find('div', class_='container')
                paragraphs = board_body.find_all('p')

                for p in paragraphs:
                    if p.find('img'):
                        img_url = p.find('img')['src']
                        try:
                            img_txt = super().img_to_text(self.save_img(img_url))
                            content_list.append({'type': 'image', 'url': img_url, 'content': img_txt})
                        except Exception as e:
                            logger.error(f"Error processing image {img_url}: {e}")
                    elif p.find('video'):
                        video_url = p.find('video').find('source')['src']
                        self.save_img(video_url)
                    else:
                        content_list.append({'type': 'text', 'content': p.text.strip()})
            except Exception as e:
                logger.error(f"Error fetching board contents for {board_id}: {e}")

        return content_list

    def save_img(self, url):
        logger.info(f"Saving image from URL: {url}")
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        try:
            response = requests.get(url)
            response.raise_for_status()
            img_name = os.path.basename(url)

            with open(os.path.join(self.download_path, img_name), 'wb') as f:
                f.write(response.content)

            logger.info(f"Image saved successfully at {self.download_path}/{img_name}")
            return os.path.join(self.download_path, img_name)
        except Exception as e:
            logger.error(f"Error saving image {url}: {e}")
            return None

    def _extract_board_id(self, url):
        for part in url.split('/'):
            if part.isdigit():
                return part
        return None

    def _post_already_exists(self, board_id, collection):
        existing_instance = self.db_controller.find(collection, {'board_id': board_id, 'site': SITE_YGOSU})
        return existing_instance is not None

    def _get_or_create_gpt_object(self, board_id):
        gpt_exists = self.db_controller.find('GPT', {'board_id': board_id, 'site': SITE_YGOSU})
        if gpt_exists:
            return gpt_exists[0]['_id']
        else:
            gpt_obj = self.db_controller.insert_one('GPT', {
                'board_id': board_id,
                'site': SITE_YGOSU,
                'answer': DEFAULT_GPT_ANSWER
            })
            return gpt_obj.inserted_id

    def _get_or_create_tag_object(self, board_id):
        tag_exists = self.db_controller.find('TAG', {'board_id': board_id, 'site': SITE_YGOSU})
        if tag_exists:
            return tag_exists[0]['_id']
        else:
            tag_obj = self.db_controller.insert_one('TAG', {
                'board_id': board_id,
                'site': SITE_YGOSU,
                'Tag': DEFAULT_TAG
            })
            return tag_obj.inserted_id

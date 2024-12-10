import re
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.community_website import AbstractCommunityWebsite
from app.utils import FTPClient
import logging
from app.utils.loghandler import catch_exception
import sys

sys.excepthook = catch_exception
from app.config import Config
from app.constants import DEFAULT_GPT_ANSWER, SITE_PPOMPPU, DEFAULT_TAG
import os
from app.utils.loghandler import setup_logger

logger = setup_logger()


class Ppomppu(AbstractCommunityWebsite):
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime('%Y%m%d')
        self.db_controller = MongoController()
        try:
            logger.info("Initializing Ppomppu instance")
            self.ftp_client = FTPClient.FTPClient(
                server_address=Config().get_env('FTP_HOST'),
                username=Config().get_env('FTP_USERNAME'),
                password=Config().get_env('FTP_PASSWORD'))
            super().__init__(self.yyyymmdd, self.ftp_client)
            logger.info("Ppomppu initialized successfully")
        except Exception as e:
            logger.error("Error initializing Ppomppu: %s", e)

    def get_daily_best(self):
        pass

    def get_real_time_best(self):
        '''
        Fetches the real-time best posts from Ppomppu.
        '''
        logger.info("Fetching real-time best posts from Ppomppu")
        num = 1
        _url = f"https://www.ppomppu.co.kr/hot.php?id=&page={num}&category=999"
        try:
            response = requests.get(_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching page: {_url}, error: {e}")
            return {}

        now = datetime.now()
        already_exists_post = []

        result = []
        for tr in soup.find_all('tr', class_='line'):
            try:
                title_element = tr.find('a', class_='title')
                create_time_element = tr.find('td', class_='board_date')
                create_time = create_time_element.get_text(strip=True)

                if title_element:
                    title = title_element.get_text(strip=True)
                    domain = "https://ppomppu.co.kr"
                    url = title_element['href']
                    board_id = self.extract_id_and_no_from_url(url)

                    hour, minute, second = map(int, create_time.split(":"))
                    target_datetime = datetime(now.year, now.month, now.day, hour, minute)

                    if "/" in create_time:
                        logger.debug(f"Skipping older post: {create_time}")
                        break

                    # Check if the post already exists
                    if self._post_already_exists(board_id):
                        already_exists_post.append(board_id)
                        continue

                    gpt_obj_id = self._get_or_create_gpt_object(board_id)
                    tag_obj_id = self._get_or_create_tag_object(board_id)

                    self.db_controller.insert_one('RealTime', {
                        'board_id': board_id,
                        'site': SITE_PPOMPPU,
                        'title': title,
                        'url': domain + url,
                        'create_time': target_datetime,
                        'GPTAnswer': gpt_obj_id,
                        'Tag': tag_obj_id
                    })
                    logger.info(f"Post {board_id} inserted successfully")
            except Exception as e:
                logger.error(f"Error processing post: {e}")

        logger.info({"already exists post": already_exists_post})

        data = {"rank": {i + 1: item for i, item in enumerate(result)}}
        return data

    def extract_id_and_no_from_url(self, url):
        pattern = r"id=([^&]*)&no=([^&]*)"
        match = re.search(pattern, url)
        if match:
            return match.group(2)
        else:
            logger.warning(f"Could not extract board id from URL: {url}")
            return None

    def get_board_contents(self, board_id):
        logger.info(f"Fetching contents for board_id: {board_id}")
        abs_path = f'./{self.yyyymmdd}/{board_id}'
        self.download_path = os.path.abspath(abs_path)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }

        daily_instance = self.db_controller.find('RealTime', {'board_id': board_id, 'site': 'ppomppu'})
        content_list = []
        if daily_instance:
            try:
                response = requests.get(daily_instance[0]['url'], headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'lxml')
                board_body = soup.find('td', class_='board-contents')
                paragraphs = board_body.find_all('p')

                for p in paragraphs:
                    if p.find('img'):
                        img_url = "https:" + p.find('img')['src']
                        try:
                            img_txt = super().img_to_text(self.save_img(img_url))
                            content_list.append({'type': 'image', 'url': img_url, 'content': img_txt})
                        except Exception as e:
                            logger.error(f"Error processing image: {e}")
                    elif p.find('video'):
                        video_url = "https:" + p.find('video').find('source')['src']
                        try:
                            self.save_img(video_url)
                        except Exception as e:
                            logger.error(f"Error saving video: {e}")
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
            logger.error(f"Error saving image: {e}")
            return None

    def _post_already_exists(self, board_id):
        logger.debug(f"Checking if post {board_id} already exists in the database")
        existing_instance = self.db_controller.find('RealTime', {'board_id': board_id, 'site': SITE_PPOMPPU})
        return existing_instance is not None

    def _get_or_create_gpt_object(self, board_id):
        logger.debug(f"Fetching or creating GPT object for board_id: {board_id}")
        gpt_exists = self.db_controller.find('GPT', {'board_id': board_id, 'site': SITE_PPOMPPU})
        if gpt_exists:
            return gpt_exists[0]['_id']
        else:
            gpt_obj = self.db_controller.insert_one('GPT', {
                'board_id': board_id,
                'site': SITE_PPOMPPU,
                'answer': DEFAULT_GPT_ANSWER
            })
            return gpt_obj.inserted_id

    def _get_or_create_tag_object(self, board_id):
        logger.debug(f"Fetching or creating Tag object for board_id: {board_id}")
        tag_exists = self.db_controller.find('TAG', {'board_id': board_id, 'site': SITE_PPOMPPU})
        if tag_exists:
            return tag_exists[0]['_id']
        else:
            tag_obj = self.db_controller.insert_one('TAG', {
                'board_id': board_id,
                'site': SITE_PPOMPPU,
                'Tag': DEFAULT_TAG
            })
            return tag_obj.inserted_id

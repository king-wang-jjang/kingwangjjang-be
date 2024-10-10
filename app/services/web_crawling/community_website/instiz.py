import re
from bs4 import BeautifulSoup
import requests
from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.community_website import AbstractCommunityWebsite
from datetime import datetime
from app.utils import FTPClient
import logging
from app.config import Config
from app.constants import DEFAULT_GPT_ANSWER, SITE_INSTIZ, DEFAULT_TAG
from app.utils.loghandler import setup_logger, catch_exception
import sys
import os

# Set up logger and exception hook
sys.excepthook = catch_exception
logger = setup_logger()

class Instiz(AbstractCommunityWebsite):
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime('%Y%m%d')
        self.db_controller = MongoController()
        try:
            logger.info(f"Initializing Instiz with date: {self.yyyymmdd}")
            self.ftp_client = FTPClient.FTPClient(
                server_address=Config().get_env('FTP_HOST'),
                username=Config().get_env('FTP_USERNAME'),
                password=Config().get_env('FTP_PASSWORD')
            )
            super().__init__(self.yyyymmdd, self.ftp_client)
            logger.info("Instiz initialized successfully")
        except Exception as e:
            logger.error("Error during Instiz initialization: %s", e)

    def get_daily_best(self):
        # To be implemented if needed
        pass

    def get_real_time_best(self):
        logger.info("Fetching real-time best posts from Instiz")
        _url = "https://www.instiz.net/"
        try:
            response = requests.get(_url)
            response.raise_for_status()  # Check for HTTP errors
            soup = BeautifulSoup(response.text, 'html.parser')
            already_exists_post = []

            for tr in soup.find_all('a', class_='rank_href'):
                title_element = tr.find('span')
                link = tr['href']
                rank = tr.find('span', 'itsme rank').get_text(strip=True)
                cate = tr.find('span', 'minitext').get_text(strip=True)

                try:
                    cmt = tr.find('span', 'cmt').get_text(strip=True)
                except Exception as e:
                    cmt = ""
                    logger.debug(f"No comments found for post, continuing: {e}")

                title = tr.get_text(strip=True).replace(rank + cate, '').replace(cmt, '')
                url = link.replace('//', 'https://')
                board_id = url.split('/')[-1]

                try:
                    target_datetime = datetime.strptime(self.extract_time(url), "%Y-%m-%dT%H:%M")
                except Exception as e:
                    logger.error(f"Error parsing date for post {board_id}: {e}")
                    continue

                try:
                    existing_instance = self.db_controller.find('RealTime', {'board_id': board_id, 'site': SITE_INSTIZ})
                    if existing_instance:
                        already_exists_post.append(board_id)
                        continue

                    gpt_obj_id = self._get_or_create_gpt_object(board_id)
                    tag_obj_id = self._get_or_create_tag_object(board_id)

                    self.db_controller.insert_one('RealTime', {
                        'board_id': board_id,
                        'site': SITE_INSTIZ,
                        'title': title,
                        'url': url,
                        'create_time': target_datetime,
                        'GPTAnswer': gpt_obj_id,
                        'Tag': tag_obj_id
                    })
                    logger.info(f"Post {board_id} inserted successfully")

                except Exception as e:
                    logger.error(f"Error processing post {board_id}: {e}")

            logger.info({"already exists post": already_exists_post})

        except Exception as e:
            logger.error(f"Error fetching real-time best from Instiz: {e}")

    def extract_time(self, url):
        logger.debug(f"Extracting time from URL: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.find('span', {'itemprop': 'datePublished'}).get('content')
        except Exception as e:
            logger.error(f"Error extracting time from {url}: {e}")
            return None

    def get_board_contents(self, board_id):
        logger.info(f"Fetching board contents for board_id: {board_id}")
        abs_path = f'./{self.yyyymmdd}/{board_id}'
        self.download_path = os.path.abspath(abs_path)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }

        daily_instance = self.db_controller.find('RealTime', {'board_id': board_id, 'site': SITE_INSTIZ})
        content_list = []
        if daily_instance:
            try:
                response = requests.get(daily_instance[0]['url'], headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'lxml')
                board_body = soup.find('div', class_='memo_content')
                paragraphs = board_body.find_all('p')

                for p in paragraphs:
                    if p.find('img'):
                        img_url = "https:" + p.find('img')['src']
                        try:
                            img_txt = super().img_to_text(self.save_img(img_url))
                            content_list.append({'type': 'image', 'url': img_url, 'content': img_txt})
                        except Exception as e:
                            logger.error(f"Error processing image from {img_url}: {e}")
                    elif p.find('video'):
                        video_url = "https:" + p.find('video').find('source')['src']
                        try:
                            self.save_img(video_url)
                        except Exception as e:
                            logger.error(f"Error saving video from {video_url}: {e}")
                    else:
                        content_list.append({'type': 'text', 'content': p.text.strip()})
            except Exception as e:
                logger.error(f"Error fetching board contents for {board_id}: {e}")

        return content_list

    def save_img(self, url):
        logger.info(f"Saving image from {url}")
        try:
            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path)

            response = requests.get(url)
            response.raise_for_status()
            img_name = os.path.basename(url)
            img_path = os.path.join(self.download_path, img_name)

            with open(img_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Image saved successfully at {img_path}")
            return img_path
        except Exception as e:
            logger.error(f"Error saving image from {url}: {e}")
            return None

    def _get_or_create_gpt_object(self, board_id):
        logger.debug(f"Checking or creating GPT object for {board_id}")
        try:
            gpt_exists = self.db_controller.find('GPT', {'board_id': board_id, 'site': SITE_INSTIZ})
            if gpt_exists:
                return gpt_exists[0]['_id']
            else:
                gpt_obj = self.db_controller.insert_one('GPT', {
                    'board_id': board_id,
                    'site': SITE_INSTIZ,
                    'answer': DEFAULT_GPT_ANSWER
                })
                return gpt_obj.inserted_id
        except Exception as e:
            logger.error(f"Error creating GPT object for {board_id}: {e}")
            return None

    def _get_or_create_tag_object(self, board_id):
        logger.debug(f"Checking or creating Tag object for {board_id}")
        try:
            tag_exists = self.db_controller.find('TAG', {'board_id': board_id, 'site': SITE_INSTIZ})
            if tag_exists:
                return tag_exists[0]['_id']
            else:
                tag_obj = self.db_controller.insert_one('TAG', {
                    'board_id': board_id,
                    'site': SITE_INSTIZ,
                    'Tag': DEFAULT_TAG
                })
                return tag_obj.inserted_id
        except Exception as e:
            logger.error(f"Error creating Tag object for {board_id}: {e}")
            return None

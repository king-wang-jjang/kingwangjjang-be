import logging
import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from app.config import Config
from app.constants import DEFAULT_GPT_ANSWER, DEFAULT_TAG, SITE_RULIWEB
from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.community_website import \
    AbstractCommunityWebsite
from app.utils import FTPClient
from app.utils.loghandler import catch_exception, setup_logger

sys.excepthook = catch_exception

logger = setup_logger()


class Ruliweb(AbstractCommunityWebsite):
    """ """
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime("%Y%m%d")
        self.db_controller = MongoController()
        try:
            logger.info(f"Initializing Ruliweb crawler for date {self.yyyymmdd}")
            self.ftp_client = FTPClient.FTPClient(
                server_address=Config().get_env("FTP_HOST"),
                username=Config().get_env("FTP_USERNAME"),
                password=Config().get_env("FTP_PASSWORD"),
            )
            super().__init__(self.yyyymmdd, self.ftp_client)
            logger.info("Ruliweb initialized successfully")
        except Exception as e:
            logger.error("Error initializing Ruliweb: %s", e)

    def get_daily_best(self):
        """Ruliweb daily best posts
        
        :return: {rank: { {title: string, url: string}[]} }


        """
        logger.info("Fetching daily best posts from Ruliweb")
        num = 1
        _url = "https://bbs.ruliweb.com/best/humor_only/now?orderby=best_id&range=24h"
        try:
            response = requests.get(_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.error(f"Error fetching page {_url}: {e}")
            return {}

        now = datetime.now()
        already_exists_post = []
        result = []

        for tr in soup.find_all("li", class_="item blocktarget"):
            try:
                title_element = tr.find("a", class_="deco")
                if title_element:
                    title = title_element.get_text(strip=True)
                    url = title_element["href"]
                    board_id = url.split("/")[-1]
                    target_datetime = datetime(now.year, now.month, now.day)
                    contents_url = url

                    if self._post_already_exists(board_id):
                        already_exists_post.append(board_id)
                        continue

                    gpt_obj_id = self._get_or_create_gpt_object(board_id)
                    tag_obj_id = self._get_or_create_tag_object(board_id)

                    self.db_controller.insert_one(
                        "Daily",
                        {
                            "board_id": board_id,
                            "site": SITE_RULIWEB,
                            "title": title,
                            "url": contents_url,
                            "create_time": target_datetime,
                            "GPTAnswer": gpt_obj_id,
                            "Tag": tag_obj_id,
                        },
                    )
                    logger.info(f"Post {board_id} inserted successfully")
            except Exception as e:
                logger.error(f"Error processing post: {e}")

        logger.info({"already exists post": already_exists_post})

        data = {"rank": {i + 1: item for i, item in enumerate(result)}}
        return data

    def get_real_time_best(self):
        """Ruliweb daily best posts
        
        :return: {rank: { {title: string, url: string}[]} }


        """
        logger.info("Fetching Realtime best posts from Ruliweb")
        num = 1
        _url = "https://bbs.ruliweb.com/best/humor_only/now?orderby=best_id&range=all"
        try:
            response = requests.get(_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.error(f"Error fetching page {_url}: {e}")
            return {}

        now = datetime.now()
        already_exists_post = []
        result = []

        for tr in soup.find_all("li", class_="item blocktarget"):
            try:
                title_element = tr.find("a", class_="deco")
                if title_element:
                    title = title_element.get_text(strip=True)
                    url = title_element["href"]
                    board_id = url.split("/")[-1]
                    target_datetime = datetime(now.year, now.month, now.day)
                    contents_url = url

                    if self._post_already_exists(board_id):
                        already_exists_post.append(board_id)
                        continue

                    gpt_obj_id = self._get_or_create_gpt_object(board_id)
                    tag_obj_id = self._get_or_create_tag_object(board_id)

                    self.db_controller.insert_one(
                        "Daily",
                        {
                            "board_id": board_id,
                            "site": SITE_RULIWEB,
                            "title": title,
                            "url": contents_url,
                            "create_time": target_datetime,
                            "GPTAnswer": gpt_obj_id,
                            "Tag": tag_obj_id,
                        },
                    )
                    logger.info(f"Post {board_id} inserted successfully")
            except Exception as e:
                logger.error(f"Error processing post: {e}")

        logger.info({"already exists post": already_exists_post})

        data = {"rank": {i + 1: item for i, item in enumerate(result)}}
        return data

    def get_board_contents(self, board_id):
        """

        :param board_id: 

        """
        logger.info(f"Fetching board contents for board_id: {board_id}")
        abs_path = f"./{self.yyyymmdd}/{board_id}"
        self.download_path = os.path.abspath(abs_path)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        daily_instance = self.db_controller.find(
            "Daily", {"board_id": board_id, "site": SITE_RULIWEB}
        )
        content_list = []
        if daily_instance:
            try:
                response = requests.get(daily_instance[0]["url"], headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                board_body = soup.find("td", class_="board-contents")
                paragraphs = board_body.find_all("p")

                for p in paragraphs:
                    if p.find("img"):
                        img_url = "https:" + p.find("img")["src"]
                        try:
                            img_txt = super().img_to_text(self.save_img(img_url))
                            content_list.append(
                                {"type": "image", "url": img_url, "content": img_txt}
                            )
                        except Exception as e:
                            logger.error(f"Error processing image from {img_url}: {e}")
                    elif p.find("video"):
                        video_url = "https:" + p.find("video").find("source")["src"]
                        try:
                            self.save_img(video_url)
                        except Exception as e:
                            logger.error(f"Error saving video from {video_url}: {e}")
                    else:
                        content_list.append({"type": "text", "content": p.text.strip()})
            except Exception as e:
                logger.error(f"Error fetching board contents for {board_id}: {e}")
        return content_list

    def save_img(self, url):
        """

        :param url: 

        """
        logger.info(f"Saving image from URL: {url}")
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        try:
            response = requests.get(url)
            response.raise_for_status()
            img_name = os.path.basename(url)

            with open(os.path.join(self.download_path, img_name), "wb") as f:
                f.write(response.content)

            logger.info(f"Image saved successfully at {self.download_path}/{img_name}")
            return os.path.join(self.download_path, img_name)
        except Exception as e:
            logger.error(f"Error saving image from {url}: {e}")
            return None

    def _post_already_exists(self, board_id):
        """

        :param board_id: 

        """
        logger.debug(f"Checking if post {board_id} already exists in the database")
        existing_instance = self.db_controller.find(
            "Daily", {"board_id": board_id, "site": SITE_RULIWEB}
        )
        return existing_instance is not None

    def _get_or_create_gpt_object(self, board_id):
        """

        :param board_id: 

        """
        logger.debug(f"Fetching or creating GPT object for board_id: {board_id}")
        gpt_exists = self.db_controller.find(
            "GPT", {"board_id": board_id, "site": SITE_RULIWEB}
        )
        if gpt_exists:
            return gpt_exists[0]["_id"]
        else:
            gpt_obj = self.db_controller.insert_one(
                "GPT",
                {
                    "board_id": board_id,
                    "site": SITE_RULIWEB,
                    "answer": DEFAULT_GPT_ANSWER,
                },
            )
            return gpt_obj.inserted_id

    def _get_or_create_tag_object(self, board_id):
        """

        :param board_id: 

        """
        logger.debug(f"Fetching or creating Tag object for board_id: {board_id}")
        tag_exists = self.db_controller.find(
            "TAG", {"board_id": board_id, "site": SITE_RULIWEB}
        )
        if tag_exists:
            return tag_exists[0]["_id"]
        else:
            tag_obj = self.db_controller.insert_one(
                "TAG", {"board_id": board_id, "site": SITE_RULIWEB, "Tag": DEFAULT_TAG}
            )
            return tag_obj.inserted_id


# Run the get_daily_best function
Ruliweb().get_daily_best()

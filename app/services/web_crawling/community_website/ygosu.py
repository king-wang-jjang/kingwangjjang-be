import logging
import os
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from app.config import Config
from app.constants import DEFAULT_GPT_ANSWER
from app.constants import DEFAULT_TAG
from app.constants import SITE_YGOSU
from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.community_website import \
    AbstractCommunityWebsite
from app.utils.FTPClient import FTPClient
from app.utils.loghandler import catch_exception
from app.utils.loghandler import setup_logger

sys.excepthook = catch_exception
logger = setup_logger()


class Ygosu(AbstractCommunityWebsite):
    """ """
    def __init__(self):
        self.yyyymmdd = datetime.today().strftime("%Y%m%d")
        self.db_controller = MongoController()
        try:
            self.ftp_client = FTPClient(
                server_address=Config().get_env("FTP_HOST"),
                username=Config().get_env("FTP_USERNAME"),
                password=Config().get_env("FTP_PASSWORD"),
            )
            super().__init__(self.yyyymmdd, self.ftp_client)

        except Exception as e:
            logger.info("Dcinside error:", e)

    def get_daily_best(self):
        """ygosu RealTimeBest post
        
        :return: {rank: { {title: string, url: string}[]} }


        """
        req = requests.get("https://ygosu.com/board/best_article/?type=daily")
        soup = BeautifulSoup(req.text, "html.parser")
        already_exists_post = []

        for tr in soup.find("tbody tr"):
            tit_element = tr.find_one(".tit a")
            create_time_element = tr.find_one(".day")
            rank_element = tr.find_one(".num")
            if tit_element:
                title = tit_element.get_text(strip=True)
                rank = rank_element.get_text(strip=True)
                create_time = create_time_element.get_text(strip=True)
                if create_time == "":  # 광고 및 공지 제외
                    continue

                url = tit_element["href"]
                url_parts = url.split("/")
                year, month, day = map(int, create_time.split("-"))
                target_datetime = datetime(year, month, day)
                for board_id in url_parts:
                    if board_id.isdigit():
                        break
                    try:
                        existing_instance = self.db_controller.find(
                            # 이미 있는 Board는 넘기기
                            "Daily",
                            {"board_id": board_id, "site": "ygosu"},
                        )
                        if existing_instance:
                            already_exists_post.append(board_id)
                            continue
                        else:
                            gpt_exists = self.db_controller.find(
                                "GPT", {"board_id": board_id, "site": SITE_YGOSU}
                            )
                            if gpt_exists:
                                gpt_obj_id = gpt_exists[0]["_id"]
                            else:
                                gpt_obj = self.db_controller.insert_one(
                                    "GPT",
                                    {
                                        "board_id": board_id,
                                        "site": SITE_YGOSU,
                                        "answer": DEFAULT_GPT_ANSWER,
                                    },
                                )
                                gpt_obj_id = gpt_obj.inserted_id
                            tag_exists = self.db_controller.find(
                                "TAG", {"board_id": board_id, "site": SITE_YGOSU}
                            )
                            if tag_exists:
                                tag_obj_id = tag_exists[0]["_id"]
                            else:
                                tag_obj = self.db_controller.insert_one(
                                    "TAG",
                                    {
                                        "board_id": board_id,
                                        "site": SITE_YGOSU,
                                        "Tag": DEFAULT_TAG,
                                    },
                                )
                                tag_obj_id = tag_obj.inserted_id
                            self.db_controller.insert_one(
                                "Daily",
                                {
                                    "board_id": board_id,
                                    "site": SITE_YGOSU,
                                    "rank": rank,
                                    "title": title,
                                    "url": url,
                                    "create_time": target_datetime,
                                    "GPTAnswer": gpt_obj_id,
                                    "Tag": tag_obj_id,
                                },
                            )
                    except Exception as e:
                        logger.error(e)

        logger.info({"already exists post": already_exists_post})

    def get_real_time_best(self):
        """ygosu RealTimeBest post
        
        :return: {rank: { {title: string, url: string}[]} }


        """
        req = requests.get("https://ygosu.com/board/real_article")
        soup = BeautifulSoup(req.text, "html.parser")
        already_exists_post = []

        for tr in soup.find("tbody tr"):
            tit_element = tr.find_one(".tit a")
            create_time_element = tr.find_one(".date")

            if tit_element:

                title = tit_element.get_text(strip=True)
                create_time = create_time_element.get_text(strip=True)
                if (
                    create_time == "" or ":" not in create_time
                ):  # 광고 및 공지 제외 및 금일만 추출
                    continue

                url = tit_element["href"]
                url_parts = url.split("/")
                now = datetime.now()
                hour, minute, second = map(int, create_time.split(":"))
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)
                for board_id in url_parts:
                    if board_id.isdigit():
                        break
                    try:
                        existing_instance = self.db_controller.find(
                            "RealTime", {"board_id": board_id, "site": SITE_YGOSU}
                        )
                        if existing_instance:
                            already_exists_post.append(board_id)
                            continue
                        else:
                            gpt_exists = self.db_controller.find(
                                "GPT", {"board_id": board_id, "site": SITE_YGOSU}
                            )
                            if gpt_exists:
                                gpt_obj_id = gpt_exists[0]["_id"]
                            else:
                                gpt_obj = self.db_controller.insert_one(
                                    "GPT",
                                    {
                                        "board_id": board_id,
                                        "site": SITE_YGOSU,
                                        "answer": DEFAULT_GPT_ANSWER,
                                    },
                                )
                                gpt_obj_id = gpt_obj.inserted_id
                            tag_exists = self.db_controller.find(
                                "TAG", {"board_id": board_id, "site": SITE_YGOSU}
                            )
                            if tag_exists:
                                tag_obj_id = gpt_exists[0]["_id"]
                            else:
                                tag_obj = self.db_controller.insert_one(
                                    "TAG",
                                    {
                                        "board_id": board_id,
                                        "site": SITE_YGOSU,
                                        "Tag": DEFAULT_TAG,
                                    },
                                )
                                tag_obj_id = tag_obj.inserted_id
                            self.db_controller.insert_one(
                                "RealTime",
                                {
                                    "board_id": board_id,
                                    "site": SITE_YGOSU,
                                    "title": title,
                                    "url": url,
                                    "create_time": target_datetime,
                                    "GPTAnswer": gpt_obj_id,
                                    "Tag": tag_obj_id,
                                },
                            )
                    except Exception as e:
                        logger.error(e)

        logger.info({"already exists post": already_exists_post})

    def get_board_contents(self, board_id):
        """

        :param board_id: 

        """
        abs_path = f"./{self.yyyymmdd}/{board_id}"
        self.download_path = os.path.abspath(abs_path)
        daily_instance = self.db_controller.find(
            "RealTime", {"board_id": board_id, "site": "ygosu"}
        )
        content_list = []
        if daily_instance:
            response = requests.get(daily_instance[0]["url"])

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                board_body = soup.find("div", class_="container")
                paragraphs = board_body.find_all("p")

                for p in paragraphs:
                    # <p> 태그 안에 <img> 태그가 있는지 확인
                    if p.find("img"):
                        img_tag = p.find("img")
                        img_url = img_tag["src"]
                        try:
                            img_txt = super().img_to_text(self.save_img(img_url))
                            content_list.append(
                                {"type": "image", "url": img_url, "content": img_txt}
                            )
                        except Exception as e:
                            logger.info(f"Ygosu Error {e}")
                    elif p.find("video"):
                        video_tag = p.find("video")
                        video_url = video_tag.find("source")["src"]
                        try:
                            self.save_img(video_url)
                        except Exception as e:
                            logger.info(f"Ygosu Error {e}")
                    else:
                        content_list.append({"type": "text", "content": p.text.strip()})
            else:
                logger.info("Failed to retrieve the webpage")
        return content_list

    def save_img(self, url):
        """

        :param url: 

        """
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        response = requests.get(url)
        img_name = os.path.basename(url)
        # 이미지를 파일로 저장
        with open(os.path.join(self.download_path, img_name), "wb") as f:
            f.write(response.content)

        return self.download_path + "/" + img_name

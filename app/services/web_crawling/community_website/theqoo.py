from app.utils.loghandler import setup_logger
import logging
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from datetime import datetime
import os
from bs4 import BeautifulSoup
import requests
from app.db.mongo_controller import MongoController
from app.services.web_crawling.community_website.community_website import (
    AbstractCommunityWebsite,
)
from app.constants import DEFAULT_GPT_ANSWER, SITE_THEQOO, DEFAULT_TAG
from app.utils import FTPClient
from app.config import Config
from app.utils.loghandler import catch_exception
import sys

sys.excepthook = catch_exception

# selenium

logger = setup_logger()


class Theqoo(AbstractCommunityWebsite):
    g_headers = [
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    ]

    def __init__(self):
        self.yyyymmdd = datetime.today().strftime("%Y%m%d")
        self.db_controller = MongoController()
        try:
            logger.info(f"Initializing Theqoo crawler for date {self.yyyymmdd}")
            self.ftp_client = FTPClient.FTPClient(
                server_address=Config().get_env("FTP_HOST"),
                username=Config().get_env("FTP_USERNAME"),
                password=Config().get_env("FTP_PASSWORD"),
            )
            super().__init__(self.yyyymmdd, self.ftp_client)
            logger.info("Theqoo initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Theqoo: {e}")

    def get_daily_best(self):
        pass

    def get_real_time_best(self):
        logger.info("Fetching real-time best posts from Theqoo")
        try:
            req = requests.get("https://theqoo.net/hot", headers=self.g_headers[0])
            req.raise_for_status()
            html_content = req.text
            soup = BeautifulSoup(html_content, "html.parser")
            li_elements = soup.select(".hide_notice tr")
        except Exception as e:
            logger.error(f"Error fetching Theqoo hot page: {e}")
            return

        already_exists_post = []
        for li in li_elements:
            elements = li.find_all("td")
            if len(elements) > 1:
                try:
                    title = elements[2].get_text(strip=True)
                    url = "https://theqoo.net" + elements[2].find("a")["href"]
                    board_id = url.split("hot/")[-1]
                    time_text = elements[3].get_text(strip=True)

                    if "-" in time_text:
                        break  # Skip older posts

                    now = datetime.now()
                    hour, minute = map(int, time_text.split(":"))
                    target_datetime = datetime(
                        now.year, now.month, now.day, hour, minute
                    )

                    # Check if post already exists in DB
                    if self._post_already_exists(board_id, already_exists_post):
                        continue

                    gpt_obj_id = self._get_or_create_gpt_object(board_id)
                    tag_obj_id = self._get_or_create_tag_object(board_id)

                    self.db_controller.insert_one(
                        "RealTime",
                        {
                            "board_id": board_id,
                            "site": SITE_THEQOO,
                            "title": title,
                            "url": url,
                            "create_time": target_datetime,
                            "GPTAnswer": gpt_obj_id,
                            "Tag": tag_obj_id,
                        },
                    )
                    logger.info(f"Post {board_id} inserted successfully")
                except Exception as e:
                    logger.error(f"Error processing post {board_id}: {e}")

        logger.info({"already exists post": already_exists_post})

    def get_board_contents(self, board_id):
        logger.info(f"Fetching board contents for board_id: {board_id}")
        abs_path = f"./{self.yyyymmdd}/{board_id}"
        self.download_path = os.path.abspath(abs_path)

        _url = "https://theqoo.net/hot/" + board_id
        try:
            req = requests.get(_url, headers=self.g_headers[0])
            req.raise_for_status()
            html_content = req.text
            soup = BeautifulSoup(html_content, "html.parser")
            content_list = []
            write_div = soup.find("div", class_="rd_body clear")

            if write_div:
                find_all = write_div.find_all(["p", "div"])
                for element in find_all:
                    text_content = element.text.strip()
                    content_list.append({"type": "text", "content": text_content})
            return content_list
        except Exception as e:
            logger.error(f"Error fetching board contents for {board_id}: {e}")
            return []

    def set_driver_options(self):
        chrome_options = Options()
        prefs = {"download.default_directory": self.download_path}
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        self.driver = webdriver.Chrome(options=chrome_options)
        try:
            self.driver.get("https://www.theqoo.com/")
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//body"))
            )
            logger.info("Selenium driver initialized and page loaded")
        except Exception as e:
            logger.error(f"Error initializing Selenium driver: {e}")
        return True

    def save_img(self, url):
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        initial_file_count = len(os.listdir(self.download_path))
        try:
            script = f"""
                var link = document.createElement('a');
                link.href = "{url}";
                link.target = "_blank";
                link.click();
            """
            self.driver.execute_script(script)
            WebDriverWait(self.driver, 5).until(
                lambda x: len(os.listdir(self.download_path)) > initial_file_count
            )

            newest_file = max(
                os.listdir(self.download_path),
                key=lambda x: os.path.getctime(os.path.join(self.download_path, x)),
            )
            return os.path.join(self.download_path, newest_file)
        except Exception as e:
            logger.error(f"Error saving image from {url}: {e}")
            return None

    def _post_already_exists(self, board_id, already_exists_post):
        existing_instance = self.db_controller.find(
            "RealTime", {"board_id": board_id, "site": SITE_THEQOO}
        )
        if existing_instance:
            already_exists_post.append(board_id)
            return True
        return False

    def _get_or_create_gpt_object(self, board_id):
        gpt_exists = self.db_controller.find(
            "GPT", {"board_id": board_id, "site": SITE_THEQOO}
        )
        if gpt_exists:
            return gpt_exists[0]["_id"]
        else:
            gpt_obj = self.db_controller.insert_one(
                "GPT",
                {
                    "board_id": board_id,
                    "site": SITE_THEQOO,
                    "answer": DEFAULT_GPT_ANSWER,
                },
            )
            return gpt_obj.inserted_id

    def _get_or_create_tag_object(self, board_id):
        tag_exists = self.db_controller.find(
            "TAG", {"board_id": board_id, "site": SITE_THEQOO}
        )
        if tag_exists:
            return tag_exists[0]["_id"]
        else:
            tag_obj = self.db_controller.insert_one(
                "TAG", {"board_id": board_id, "site": SITE_THEQOO, "Tag": DEFAULT_TAG}
            )
            return tag_obj.inserted_id

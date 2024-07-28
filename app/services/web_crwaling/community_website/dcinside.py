import os
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from constants import DEFAULT_GPT_ANSWER, SITE_DCINSIDE
from db.mongo_controller import MongoController
from services.web_crwaling.community_website.community_website import AbstractCommunityWebsite
from utils import FTPClient
from config import Config

# selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger("")


class Dcinside(AbstractCommunityWebsite):
    g_headers = [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
    ]

    def __init__(self):
        self.yyyymmdd = datetime.today().strftime('%Y%m%d')
        self.db_controller = MongoController()
        try:
            self.ftp_client = FTPClient(
                server_address=Config().get_env('FTP_HOST'),
                username=Config().get_env('FTP_USERNAME'),
                password=Config().get_env('FTP_PASSWORD'))
            super().__init__(self.yyyymmdd, self.ftp_client)
        except Exception as e:
            logger.error("Dcinside initialization error: %s", e)
            raise

    def get_real_time_best(self):
        req = requests.get('https://www.dcinside.com/', headers=self.g_headers[0])
        html_content = req.text
        soup = BeautifulSoup(html_content, 'html.parser')
        li_elements = soup.select('#dcbest_list_date li')
        already_exists_post = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self._process_li_element, li) for li in li_elements]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    already_exists_post.append(result)

        logger.info("Already exists post: %s", already_exists_post)

    def _process_li_element(self, li):
        p_element = li.select_one('.box.besttxt p')
        a_element = li.select_one('.main_log')
        time_element = li.select_one('.box.best_info .time')

        if p_element and a_element and time_element:
            title = p_element.get_text(strip=True)
            url = a_element['href']
            board_id = url.split('no=')[-1]
            time_text = time_element.get_text(strip=True)
            if '-' in time_text:
                return None  # 오늘 것만 추가 (이전 글은 제외 (DB에서 확인))

            target_datetime = self._get_target_datetime(time_text)

            try:
                if self._post_exists(board_id):
                    return board_id

                gpt_obj_id = self._get_or_create_gpt_obj_id(board_id)

                self.db_controller.insert_one('RealTime', {
                    'board_id': board_id,
                    'site': SITE_DCINSIDE,
                    'title': title,
                    'url': url,
                    'create_time': target_datetime,
                    'GPTAnswer': gpt_obj_id
                })
            except Exception as e:
                logger.error('Error processing post: %s', e)
        return None

    def get_board_contents(self, board_id):
        abs_path = f'./{self.yyyymmdd}/{board_id}'
        self.download_path = os.path.abspath(abs_path)
        _url = "https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id
        req = requests.get(_url, headers=self.g_headers[0])
        html_content = req.text
        soup = BeautifulSoup(html_content, 'html.parser')

        content_list = self._parse_content(soup)
        return content_list

    def set_driver_options(self):
        '''
        Set Chrome driver options for Selenium.
        '''
        chrome_options = Options()
        prefs = {"download.default_directory": self.download_path}
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        os.makedirs(self.download_path, exist_ok=True)

        self.driver = webdriver.Chrome(options=chrome_options)

        try:
            self.driver.get("https://www.dcinside.com/")
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//body'))
            )
        except Exception as e:
            logger.error('Dcinside Error: %s', e)
            return False
        return True

    def save_img(self, url):
        os.makedirs(self.download_path, exist_ok=True)

        initial_file_count = len(os.listdir(self.download_path))
        script = f'''
            var link = document.createElement('a');
            link.href = "{url}";
            link.target = "_blank";
            link.click();
        '''
        self.driver.execute_script(script)

        WebDriverWait(self.driver, 5).until(
            lambda x: len(os.listdir(self.download_path)) > initial_file_count
        )

        newest_file = self._get_newest_file(self.download_path)
        return os.path.join(self.download_path, newest_file)

    def _get_target_datetime(self, time_text):
        now = datetime.now()
        hour, minute = map(int, time_text.split(':'))
        return datetime(now.year, now.month, now.day, hour, minute)

    def _post_exists(self, board_id):
        existing_instance = self.db_controller.find('RealTime', {'board_id': board_id, 'site': SITE_DCINSIDE})
        return existing_instance is not None

    def _get_or_create_gpt_obj_id(self, board_id):
        gpt_exists = self.db_controller.find('GPT', {'board_id': board_id, 'site': SITE_DCINSIDE})
        if gpt_exists:
            return gpt_exists[0]['_id']
        else:
            gpt_obj = self.db_controller.insert_one('GPT', {
                'board_id': board_id,
                'site': SITE_DCINSIDE,
                'answer': DEFAULT_GPT_ANSWER
            })
            return gpt_obj.inserted_id

    def _parse_content(self, soup):
        content_list = []
        write_div = soup.find('div', class_='write_div')
        find_all = write_div.find_all(['p']) if len(write_div.find_all(['p'])) > len(write_div.find_all(['div'])) else write_div.find_all(['div'])

        for element in find_all:
            text_content = element.text.strip()
            content_list.append({'type': 'text', 'content': text_content})
        return content_list

    def _get_newest_file(self, directory):
        files = os.listdir(directory)
        newest_file = max(files, key=lambda x: os.path.getctime(os.path.join(directory, x)))
        return newest_file

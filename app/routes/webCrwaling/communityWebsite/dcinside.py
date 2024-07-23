from datetime import datetime
import os
from bs4 import BeautifulSoup
import requests

from constants import DEFAULT_GPT_ANSWER, SITE_DCINSIDE
from mongo import DBController
from routes.webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite
from utils import FTPClient
from config import Config


# selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import logging

logger = logging.getLogger("")

class Dcinside(AbstractCommunityWebsite):
    g_headers = [
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
        ]
    
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
            logger.info("Dcinside error:", e)
            return None
            raise  # Directory 생성을 못 하면 일단 멈춤 나중에 Exception 처리 필요
    
    def get_daily_best(self):
        pass

    def get_real_time_best(self):
        req = requests.get('https://www.dcinside.com/', headers=self.g_headers[0])
        html_content = req.text
        soup = BeautifulSoup(html_content, 'html.parser')
        li_elements = soup.select('#dcbest_list_date li')
        already_exists_post = []

        for li in li_elements:
            p_element = li.select_one('.box.besttxt p')
            a_element = li.select_one('.main_log')
            time_element = li.select_one('.box.best_info .time')

            if p_element and a_element and time_element:
                title = p_element.get_text(strip=True)
                url = a_element['href']
                board_id = url.split('no=')[-1]
                time_text = time_element.get_text(strip=True)
                if(time_text.find('-') > 0): 
                    break  # 오늘 것만 추가 (이전 글은 제외 (DB에서 확인))

                # 시간 13:40 -> 2024.01.29 13:40 로 수정
                now = datetime.now()
                hour, minute = map(int, time_text.split(':'))
                # 시간 설정 및 datetime 객체 생성
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)

                try:
                    existing_instance = self.db_controller.select('RealTime', {'board_id': board_id, 'site': SITE_DCINSIDE})
                    if existing_instance:
                        already_exists_post.append(board_id)
                        continue
                    else:
                        gpt_exists = self.db_controller.select('GPT', {'board_id': board_id, 'site': SITE_DCINSIDE})
                        if gpt_exists:
                            gpt_obj_id = gpt_exists[0]['_id']
                        else :
                            gpt_obj = self.db_controller.insert('GPT', {
                                'board_id': board_id,
                                'site': SITE_DCINSIDE,
                                'answer': DEFAULT_GPT_ANSWER
                            })
                            gpt_obj_id = gpt_obj.inserted_id
                            
                        self.db_controller.insert('RealTime', {
                            'board_id': board_id,
                            'site': SITE_DCINSIDE,
                            'title': title,
                            'url': url,
                            'create_time': target_datetime,
                            'GPTAnswer': gpt_obj_id
                        })
                except Exception as e:
                    logger.error('error', e)
                    
        logger.info({"already exists post": already_exists_post})

    def get_board_contents(self, board_id):
        abs_path = f'./{self.yyyymmdd}/{board_id}'
        self.download_path = os.path.abspath(abs_path) 
        # self.set_driver_options()

        _url = "https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id
        req = requests.get(_url, headers=self.g_headers[0])
        html_content = req.text
        soup = BeautifulSoup(html_content, 'html.parser')

        second_article = soup.find_all('article')[1]
        title = second_article.find('h3').get_text(strip=True)
        content_list = []

        write_div = soup.find('div', class_='write_div')

        find_all = (
            write_div.find_all(['p'])
            if len(write_div.find_all(['p'])) > len(write_div.find_all(['div']))
            else write_div.find_all(['div'])
        )
     
        for element in find_all:
            text_content = element.text.strip()
            content_list.append({'type': 'text', 'content': text_content})
            # img_tags = element.find_all('img')
            # for img_tag in img_tags:
            #     image_url = img_tag['src']
            #     try:
            #         img_txt = super().img_to_text(self.save_img(image_url))
            #         content_list.append({'type': 'image', 'url': image_url, 
            #                             'content': img_txt})
            #     except Exception as e:
            #         logger.info(f'Dcinside Error {e}')

            # video_tags = element.find_all('video')
            # for video_tag in video_tags:
            #     source_tags = video_tag.find_all('source')
            #     for source_tag in source_tags:
            #         video_url = source_tag['src']
            #         content_list.append({'type': 'video', 'url': video_url})
        # 업로드
        # self.ftp_client.ftp_upload_folder(local_directory=self.download_path, remote_directory=board_id)
        
        # 업로드 후 삭제
        # shutil.rmtree(self.download_path)

        return content_list

    # 속도 개선 작업 (20s -> 2s)
    # https://www.notion.so/2-850bc2d1d98145bebcc89f3596798f05?pvs=4
    def set_driver_options(self):
        '''
            :option: download path
        '''
        chrome_options = Options()
        prefs = {"download.default_directory": self.download_path}
        chrome_options.add_experimental_option("prefs", prefs)
        # chrome_options.add_argument('headless')
        chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_argument('--incognito')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_experimental_option('excludeSwitches',['enable-logging'])

        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        self.driver = webdriver.Chrome(options=chrome_options)
        
        try:
            self.driver.get("https://www.dcinside.com/")
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//body'))
            )
        except Exception as e:
            logger.info('Dcinside Error', e)
        finally:
            return True
    
    def save_img(self, url):
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

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

        # 가장 최근에 다운로드된 파일 찾기
        files = os.listdir(self.download_path)
        newest_file = max(files, key=lambda x: os.path.getctime(os.path.join(self.download_path, x)))

        return self.download_path + "/" + newest_file
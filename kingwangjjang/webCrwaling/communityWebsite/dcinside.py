from datetime import datetime, timedelta
import os
from sqlite3 import IntegrityError
from bs4 import BeautifulSoup
from django.conf import settings
import requests

from utils import FTPClient
from .models import RealTime
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite

# selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class Dcinside(AbstractCommunityWebsite):
    g_headers = [
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
        ]
    
    def __init__(self, yyyymmddhhmm, board_id):
        self.download_path = os.path.abspath(f'./{yyyymmddhhmm}/{board_id}/')
        self.yyyymmddhhmm = yyyymmddhhmm
        self.board_id = board_id
        self.BASE_URL = 'https://www.dcinside.com/'
        self.set_driver_options()

    def get_daily_best(self):
        pass

    def get_real_time_best(self):
        req = requests.get('https://www.dcinside.com/', headers=self.g_headers[0])
        html_content = req.text

        soup = BeautifulSoup(html_content, 'html.parser')

        li_elements = soup.select('#dcbest_list_date li')
        
        real_time_instances = []

        for li in li_elements:
            p_element = li.select_one('.box.besttxt p')
            a_element = li.select_one('.main_log')
            time_element = li.select_one('.box.best_info .time')

            if p_element and a_element and time_element:
                p_text = p_element.get_text(strip=True)
                a_href = a_element['href']
                no_value = a_href.split('no=')[-1]
                time_text = time_element.get_text(strip=True)

                if(time_text.find('-') > 0): 
                    break  # 오늘 것만 추가 (이전 글은 제외 (DB에서 확인))

                # 시간 13:40 -> 2024.01.29 13:40 로 수정
                now = datetime.now()
                hour, minute = map(int, time_text.split(':'))
                # 시간 설정 및 datetime 객체 생성
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)

                try:
                    real_time_instance, created = RealTime.objects.get_or_create(
                        _id=no_value,
                        defaults={
                            'site' : 'dcinside',
                            'title': p_text,
                            'url': a_href,
                            'create_time': target_datetime,
                        }
                    )
                    if not created:
                        continue
                except IntegrityError:
                    continue
    
    def get_board_contents(self):
        _url = "https://gall.dcinside.com/board/view/?id=dcbest&no=" + self.board_id
        req = requests.get(_url, headers=self.g_headers[0])
        html_content = req.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        second_article = soup.find_all('article')[1]
        title = second_article.find('h3').get_text(strip=True)
        content_list = []

        write_div = soup.find('div', class_='write_div')

        # 총 경우는 3가지이나 두 가지의 경우가 많이 나와서 2개만 한다. 
        # https://www.notion.so/dcincide-f996acc8355e4f0d8320b6f7e06abd57?pvs=4
        find_all = (
            write_div.find_all(['p'])
            if len(write_div.find_all(['p'])) > len(write_div.find_all(['div']))
            else write_div.find_all(['div'])
        )
     
        for element in find_all:
            text_content = element.text.strip()
            content_list.append({'type': 'text', 'content': text_content})
            img_tags = element.find_all('img')
            for img_tag in img_tags:
                image_url = img_tag['src']
                content_list.append({'type': 'image', 'url': image_url})
                self.save_img(image_url)

            video_tags = element.find_all('video')
            for video_tag in video_tags:
                source_tags = video_tag.find_all('source')
                for source_tag in source_tags:
                    video_url = source_tag['src']
                    content_list.append({'type': 'video', 'url': video_url})

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

        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        self.driver = webdriver.Chrome(options=chrome_options)
        
        try:
            self.driver.get("https://www.dcinside.com/")
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//body'))
            )
        except Exception:
            print('Error', Exception)
        finally:
            return True
    
    def save_img(self, url):
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        initial_file_count = len(os.listdir(self.download_path))

        try:
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
            print("다운로드된 파일명:", newest_file)
        finally:
            return True
        
    def local_to_server(self, local_path):
        b = FTPClient(server_address=getattr(settings, 'DB_HOST', None),
                  username=getattr(settings, 'FTP_USER', None),
                  password=getattr(settings, 'FTP_PASSWORD', None))
    
        b.ftp_upload_file("C:/Users/nori/Envs/kingwangjjang-be/kingwangjjang/202402061210/203621/1706443238.png", "/home/17064433238.png")
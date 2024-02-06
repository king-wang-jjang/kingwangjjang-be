from datetime import datetime, timedelta
import os
from sqlite3 import IntegrityError
import time
from bs4 import BeautifulSoup
import requests
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
    
    def __init__(self):
        pass

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
                    break  # 어제껀 추가안함

                # 시간 13:40 -> 2024.01.29 13:40 로 수정
                now = datetime.now()
                hour, minute = map(int, time_text.split(':'))
                # 시간 설정 및 datetime 객체 생성
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)

                # Use get_or_create to avoid duplicates
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
                    
                    # If the instance was not created (already existed), skip it
                    if not created:
                        continue

                except IntegrityError:
                    # Handle any potential integrity error, such as a unique constraint violation
                    continue
    
    def get_board_contents(self, yyyymmddhhmm, board_id):
        _url = "https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id
        print(_url)
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
                print(img_tag)
                image_url = img_tag['src']
                content_list.append({'type': 'image', 'url': image_url})
                self.save_img(yyyymmddhhmm, board_id, image_url)

            video_tags = element.find_all('video')
            for video_tag in video_tags:
                source_tags = video_tag.find_all('source')
                for source_tag in source_tags:
                    video_url = source_tag['src']
                    content_list.append({'type': 'video', 'url': video_url})

        return content_list

    def save_img(self, yyyymmddhhmm, id, url):
        chrome_options = Options()
        download_path = os.path.abspath(f'./{yyyymmddhhmm}/{id}/')
        prefs = {"download.default_directory": download_path}
        chrome_options.add_experimental_option("prefs", prefs)

        if not os.path.exists(download_path):
            os.makedirs(download_path)
            
        initial_file_count = len(os.listdir(download_path))

        driver = webdriver.Chrome(options=chrome_options)

        try:
            driver.get("https://www.dcinside.com/")
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//body'))
            )
            script = f'''
                var link = document.createElement('a');
                link.href = "{url}";
                link.target = "_blank";
                link.click();
            '''
            driver.execute_script(script)
            
            time.sleep(3)
            WebDriverWait(driver, 5).until(
                lambda x: len(os.listdir(download_path)) > initial_file_count
            )

        finally:
            driver.quit()
            driver.close()
        return True

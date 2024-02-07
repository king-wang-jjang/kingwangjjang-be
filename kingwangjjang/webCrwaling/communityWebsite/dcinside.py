from datetime import datetime, timedelta
from bs4 import BeautifulSoup, NavigableString
import requests
from .models import RealTime
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite

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
                
                if(time_text.find('-') > 0): break # 어제껀 추가안함
                # 시간 13:40 -> 2024.01.29 13:40 로 수정
                now = datetime.now()
                hour, minute = map(int, time_text.split(':'))
                # 시간 설정 및 datetime 객체 생성
                target_datetime = datetime(now.year, now.month, now.day, hour, minute)
                real_time_instance = RealTime(
                    _id=no_value,
                    title=p_text,
                    url=a_href,
                    create_time=target_datetime 
                )
                real_time_instances.append(real_time_instance)

        RealTime.objects.bulk_create(real_time_instances)
    
    def get_board_contents(self, board_id):
        _url = "https://gall.dcinside.com/board/view/?id=dcbest&no=" + board_id
        req = requests.get(_url, headers=self.g_headers[0])
        html_content = req.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        second_article = soup.find_all('article')[1]
        title = second_article.find('h3').get_text(strip=True)
        content_list = []

        write_div = soup.find('div', class_='write_div')
        
        for element in write_div.find_all(['p']):
            text_content = element.text.strip()
            content_list.append({'type': 'text', 'content': text_content})

            # Check if there are img tags inside the p tag
            img_tags = element.find_all('img')
            for img_tag in img_tags:
                image_url = img_tag['src']
                content_list.append({'type': 'image', 'url': image_url})

              # Check for video tags inside the p tag
            video_tags = element.find_all('video')
            for video_tag in video_tags:
                # Check for source tags inside the video tag
                source_tags = video_tag.find_all('source')
                for source_tag in source_tags:
                    video_url = source_tag['src']
                    content_list.append({'type': 'video', 'url': video_url})
                    
        return content_list
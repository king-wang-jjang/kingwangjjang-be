from bs4 import BeautifulSoup
import requests
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite

class Dcinside(AbstractCommunityWebsite):
    def __init__(self):
        pass

    def GetDayBest(self):
        pass

    def GetRealTimeBest(self):
        '''
        dcinside RealTimeBest post 

        :return: {no: {title: string, url: string, createtime: date}[] }
        '''
        headers = [
            {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
        ]
        
        req = requests.get('https://www.dcinside.com/', headers=headers[0])
        html_content = req.text

        soup = BeautifulSoup(html_content, 'html.parser')
        
        li_elements = soup.select('#dcbest_list_date li')
        result = {}
        for li in li_elements:
            p_element = li.select_one('.box.besttxt p')
            a_element = li.select_one('.main_log')
            time_element = li.select_one('.box.best_info .time')

            if p_element and a_element and time_element:
                p_text = p_element.get_text(strip=True)
                a_href = a_element['href']
                no_value = a_href.split('no=')[-1]
                time_text = time_element.get_text(strip=True)
                result[no_value] = {"title": p_text, "url": a_href, "time": time_text}

        data = {"allRealtime": result}

        return data
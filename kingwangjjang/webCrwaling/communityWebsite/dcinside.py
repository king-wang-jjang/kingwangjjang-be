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

        :return: {rank: { {title: string, url: string}[]} }
        '''
        headers = [
            {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
        ]
        
        req = requests.get('https://www.dcinside.com/', headers=headers[0])
        html_content = req.text

        soup = BeautifulSoup(html_content, 'html.parser')
        
        li_elements = soup.select('#dcbest_list_date li')
        result = []
        for li in li_elements:
            p_element = li.select_one('.box.besttxt p')
            a_element = li.select_one('.main_log')
            if p_element and a_element:
                p_text = p_element.get_text(strip=True)
                a_href = a_element['href']
                result.append({"title": p_text, "url": a_href}) 
                
        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data

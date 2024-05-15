from bs4 import BeautifulSoup
import requests
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite

import logging

logger = logging.getLogger("")

class Ppompu(AbstractCommunityWebsite):
    def __init__(self):
        pass
    
    def get_daily_best(self):
        pass

    def get_real_time_best(self):
        '''
        ppomppu daily post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        req = requests.get('https://www.ppomppu.co.kr/hot.php?category=2')
        soup = BeautifulSoup(req.text, 'html.parser')
        result = []
        for tr in soup.select('tr.line'):
            title_element = tr.select_one('a.title')
            logger.info(title_element)
            if title_element:
                title = title_element.get_text(strip=True)
                url = title_element['href']
                result.append({"title": title, "url": url})

        logger.info(result)
        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data
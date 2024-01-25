
from bs4 import BeautifulSoup
import requests
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite


class Ygosu(AbstractCommunityWebsite):
    def __init__(self):
        pass
    
    def GetDayBest(self):
        '''
        ygosu RealTimeBest post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        req = requests.get('https://ygosu.com/board/real_article')
        soup = BeautifulSoup(req.text, 'html.parser')

        result = []
        for tr in soup.select('tbody tr'):
            tit_element = tr.select_one('.tit a')
            if tit_element:
                title = tit_element.get_text(strip=True)
                url = tit_element['href']
                result.append({"title": title, "url": url})

        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data

    def GetRealTimeBest(self):
        '''
        ygosu RealTimeBest post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        req = requests.get('https://ygosu.com/board/real_article')
        soup = BeautifulSoup(req.text, 'html.parser')

        result = []
        for tr in soup.select('tbody tr'):
            tit_element = tr.select_one('.tit a')
            if tit_element:
                title = tit_element.get_text(strip=True)
                url = tit_element['href']
                result.append({"title": title, "url": url})

        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data
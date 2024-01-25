from bs4 import BeautifulSoup
import requests
from webCrwaling.communityWebsite.communityWebsite import AbstractCommunityWebsite

class Ppompu(AbstractCommunityWebsite):
    def __init__(self):
        pass
    
    def GetDayBest(self):
        pass

    def GetRealTimeBest(self):
        '''
        ppomppu daily post 

        :return: {rank: { {title: string, url: string}[]} }
        '''
        req = requests.get('https://www.ppomppu.co.kr/hot.php?category=2')
        soup = BeautifulSoup(req.text, 'html.parser')
        result = []
        for tr in soup.select('tr.line'):
            title_element = tr.select_one('a.title')
            print(title_element)
            if title_element:
                title = title_element.get_text(strip=True)
                url = title_element['href']
                result.append({"title": title, "url": url})

        print(result)
        data = {"rank": {i + 1: item for i, item in enumerate(result)}}

        return data
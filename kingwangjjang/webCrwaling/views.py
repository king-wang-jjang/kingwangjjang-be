import json
import requests 
from bs4 import BeautifulSoup 
from django.http import JsonResponse
from selenium import webdriver
from urllib import request as urllib_request
from bson import json_util
from .communityWebsite.models import RealTime

from mongo import DBController  
from webCrwaling.communityWebsite.ppompu import Ppompu

from webCrwaling.communityWebsite.ygosu import Ygosu
from webCrwaling.communityWebsite.dcinside import Dcinside 

from djongo import models

# class RealTime(models.Model):

# Create your views here.

### 이미지가 많은 상황
# JPG -> Text 
# 댓글을 요약 ( 추천 수가 몇 개이상 )
def CommunitySiteCrawler(request):
    # DC
    dcincideCrwaller = Dcinside()
    a = dcincideCrwaller.GetRealTimeBest()

    return JsonResponse({})

def DBInsertTest():
    db_controller = DBController()
    collection_name = "pymongotest"
    data_to_insert = {
    "userName": "Bob",
    "age": 25,
    "sex": "male"
    }

    result = db_controller.insert(collection_name, data_to_insert)
    print(f"Insertion Result: {result}")
    return JsonResponse({"Insertion Result": "TEST"})

def test():
    # URL 설정
    BASE_URL = "https://gall.dcinside.com/board/view/?id=dcbest&no=2479&page=1"
    DOMAIN_URL = "https://gall.dcinside.com"

    # 헤더 설정
    headers = [
        {'User-Agent' : ''},
    ]

    html_list = requests.get(BASE_URL, headers=headers[0])
    soup = BeautifulSoup(html_list.content, 'html.parser')

    file_box = soup.find('div', class_='appending_file_box').find_all('li')

    num = 0
    for i in file_box:
        num += 1  # 넘버링
        img_URL = i.find('a', href=True)['href']  # 이미지 주소
        file_ext = i.find('a', href=True)['href'].split('.')[-1]  # 확장자 추출

        opener = urllib_request.build_opener()
        opener.addheaders = [('User-agent', ''), ('Referer', html_list.url)]
        urllib_request.install_opener(opener)
        urllib_request.urlretrieve(img_URL, "TEST" + str(num) + "." + file_ext)

    return JsonResponse({})

# Session Storage For dcinside

    # # DC
    # dcincideCrwaller = Dcinside()
    # a = dcincideCrwaller.GetRealTimeBest()
    
    # # yg
    # ygosuCrwaller = Ygosu()
    # a = ygosuCrwaller.GetRealTimeBest()
    
    # Pp
    PpomppuCrwaller = Ppompu()
    a = PpomppuCrwaller.GetDayBest()

    return JsonResponse(a)

# Session Storage For dcinside
def getSesstion():
    url = 'https://www.dcinside.com/'

    # Headless 모드로 Chrome 브라우저 열기
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    # 웹 페이지 열기
    driver.get(url)

    # 세션 스토리지 데이터 가져오기
    session_storage_data = json.loads(driver.execute_script('return window.sessionStorage.getItem("_dcbest_rank_hit");'))
    driver.execute_script(f'window.open("{session_storage_data[0]['thumb']}");') 
    # 브라우저 닫기
    driver.quit()

    return JsonResponse({'sessionStorage': session_storage_data})

#
# 실시간, 일간
def realtime():
    """이것은 함수입니다.

    :param request:
        0: 인기 글이 있는 url 
        1: li 
        2: class tag

    :return:
        {rank: { {title: string, url: string}[]} }
    """
    headers = [
        {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
    ]
    
    req = requests.get('https://www.dcinside.com/', headers=headers[0])
    html_content = req.text

    soup = BeautifulSoup(html_content, 'html.parser')
    
    li_elements = soup.select('#dcbest_list_date li')
    for li in li_elements:
        p_element = li.select_one('.box.besttxt p')
        a_element = li.select_one('.main_log')
        
        if p_element and a_element:
            p_text = p_element.get_text(strip=True)
            a_href = a_element['href']
            
            print(f"Text: {p_text}, URL: {a_href}")

    data = {"box_txt": [li.text for li in li_elements]}

    return data

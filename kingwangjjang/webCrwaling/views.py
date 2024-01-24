import json
import requests 
from bs4 import BeautifulSoup 
from django.http import JsonResponse
from selenium import webdriver
from urllib import request as urllib_request

from webCrwaling.communityWebsite.ygosu import Ygosu
from webCrwaling.communityWebsite.dcinside import Dcinside 

# Create your views here.

### 이미지가 많은 상황
# JPG -> Text 
# 댓글을 요약 ( 추천 수가 몇 개이상 )

def CommunitySiteCrawler(request):
    # # DC
    # dcincideCrwaller = Dcinside()
    # a = dcincideCrwaller.GetRealTimeBest()
    
    # # yg
    ygosuCrwaller = Ygosu()
    a = ygosuCrwaller.GetRealTimeBest()
    
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
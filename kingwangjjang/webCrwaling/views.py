import json
import time
import webbrowser
import requests 
from bs4 import BeautifulSoup 
from django.http import JsonResponse
from selenium import webdriver
from urllib import request as urllib_request
from bson import json_util
import urllib.request
from .communityWebsite.models import RealTime

from mongo import DBController  
from webCrwaling.communityWebsite.ppompu import Ppompu

from webCrwaling.communityWebsite.ygosu import Ygosu
from webCrwaling.communityWebsite.dcinside import Dcinside 

from djongo import models

from PIL import Image
from io import BytesIO
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\nori\AppData\Local\tesseract.exe'

# class RealTime(models.Model):

# Create your views here.

### 이미지가 많은 상황
# JPG -> Text 
# 댓글을 요약 ( 추천 수가 몇 개이상 )
def CommunitySiteCrawler(request):
    dcincideCrwaller = Dcinside()
    a = dcincideCrwaller.get_board_contents("203621")
    json_content = json.dumps(a, ensure_ascii=False, indent=2)
    json_object = json.loads(json_content)
    
    return JsonResponse({'data': json_object})

    return JsonResponse({})
    # 다운받을 이미지 url
    
    url = "https://image.dcinside.com/viewimage.php?id=&no=24b0d769e1d32ca73de985fa11d02831f8aadc88aabcff47e8021605d37bf1436ebb78a575eb9e18042afbf9848bfd403905acb77b9ac250540b76e4781bf2"
        # "https://dcimg3.dcinside.co.kr/viewimage.php?id=3dafdf35f5d73bb2&no=24b0d769e1d32ca73de985fa11d02831f8aadc88aabcff47e8021605d37bf1436ebb78a575eb9e18417faa9f8489fd48c473b37af0006de42028103fa06405e2a729ca"
    # url = "https://dcimg6.dcinside.co.kr/viewimage.php?id=3dafdf35f5d73bb2&no=24b0d769e1d32ca73de985fa11d02831f8aadc88aabcff47e8021605d37bf1436ebb78a575eb9e18417faa9f8489fd48c473b37af0006de42028103fa06405e2a729ca"
    # https://dcimg3.dcinside.co.kr/viewimage.php?id=3dafdf35f5d73bb2&no=24b0d769e1d32ca73de985fa11d02831f8aadc88aabcff47e8021605d37bf1436ebb78a575eb9e18417faaf2e98bfe4266db21f3aafbf2c8ab367ab72ef3366f3e4f8863
    # 헤더 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    BASE_URL = 'https://www.dcinside.com/'
    # webbrowser.open_new_tab(BASE_URL)
    webbrowser.open_new_tab(url)

    # 이미지 다운로드
    response = requests.get(url, headers=headers)
    
    return JsonResponse({})

    driver = webdriver.Chrome()
    # 이미지 다운로드
    try:
        # 해당 URL 열기
        driver.get(url)

        time.sleep(5)

        # 이미지가 로딩될 때까지 잠시 대기
    finally:
        # 브라우저 종료
        driver.quit()
    response = requests.get(url, headers=headers)
    print(response.content)
    
    img_data = BytesIO(response.content)
    
    # BytesIO 객체에서 이미지 열기
    img = Image.open(img_data)

    # 이미지 저장 (optional)
    img.save("downloaded_image.jpg")

    # 텍스트 추출
    # text = pytesseract.image_to_string(img, lang="kor")  # 영어로 추출

    # print(text)
    return JsonResponse({})
    # 이미지 파일의 URL
    image_url = "https://image.dcinside.com/viewimage.php?id=&no=24b0d769e1d32ca73de985fa11d02831f8aadc88aabcff47e8021605d37bf1436ebb78a575eb9e18042afbf9848bfd403905acb77b9ac250540b76e4781bf2"

    # 헤더 설정
    headers = [
        {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
    ]

    # 이미지 다운로드
    response = requests.get(image_url, headers=headers[0])
    image_data = BytesIO(response.content)
    # img = Image.open(BytesIO(response.content))
    # print(image_data)
    # # 로컬 파일로 저장 (optional)
    # image_data.save("downloaded_image.jpg")
    # BytesIO에서 이미지 열기
    img = Image.open(image_data)

    # 텍스트 추출
    # text = pytesseract.image_to_string(img)
    # # 텍스트 추출
    text = pytesseract.image_to_string(img)

    # print("추출된 텍스트:")
    print(text)
    return JsonResponse({})
    
    # DC
    dcincideCrwaller = Dcinside()
    # a = dcincideCrwaller.get_real_time_best()
    a = dcincideCrwaller.get_board_contents("203621")
    image_contents = [item for item in a if item['type'] == 'image']

    # json_content = json.dumps(a, ensure_ascii=False, indent=2, safe=False)
    json_content = json.dumps(a, ensure_ascii=False, indent=2)
    json_object = json.loads(json_content)
    
    return JsonResponse({'data': json_object})

def DBInsertTest():
    db_controller = DBController()
    collection_name = "realtimebest"

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
import requests 
from bs4 import BeautifulSoup 
from django.http import JsonResponse


# Create your views here.

### 이미지가 많은 상황
# JPG -> Text 
# 댓글을 요약 ( 추천 수가 몇 개이상 )

def CommunitySiteCrawler(request):
    headers = [
        {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
    ]
    
    req = requests.get('https://gall.dcinside.com/board/view/?id=dcbest&no=199651&_dcbest=1&page=1', headers=headers[0])
    html_content = req.text
    data = {"html_content": html_content}
    return JsonResponse(data)
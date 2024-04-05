from abc import abstractmethod
from django.conf import settings

# img to text
import pytesseract

from utils import FTPClient
from PIL import Image


class AbstractCommunityWebsite():
    dayBestUrl = ''
    realtimeBestUrl = ''

    def __init__(self, yyyymmdd, ftp_client: FTPClient) -> None:
        self.ftp_client = ftp_client
        if not self.ftp_client.create_today_directory(yyyymmdd):
            raise ValueError("Failed to create today's directory.")
        
    @abstractmethod
    def get_daily_best(self):
        return {}        

    @abstractmethod
    def get_real_time_best(self):
        return {} 
    
    @abstractmethod
    def get_board_contents(self, board_id):
        return {} 
    
    @abstractmethod
    def save_img(self, url):
        return {} 
    
    def img_to_text(self, img_path):
        img = Image.open(img_path)
        custom_config = r'--oem 3 --psm 6 -l kor+eng' 

        text = pytesseract.image_to_string(img, config=custom_config)
        print(text)
        return text
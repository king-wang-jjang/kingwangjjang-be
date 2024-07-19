from abc import abstractmethod
import os
from dotenv import load_dotenv

# img to text
import pytesseract

from utils import FTPClient
from PIL import Image
import logging

logger = logging.getLogger("")
load_dotenv()
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
        import cv2
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'   
        custom_config = r'--oem 3 --psm 6 -l kor'
        allowed_extensions = ['jpg', 'png', 'jpeg']

        if any(str in img_path for str in allowed_extensions):
            image = cv2.imread(img_path)
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            threshold_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

            text = pytesseract.image_to_string(threshold_image, config=custom_config)
        else:
            text = pytesseract.image_to_string(img_path, config=custom_config)

        return text
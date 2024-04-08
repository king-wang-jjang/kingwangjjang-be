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
        import cv2
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'   
        try:            
            image = cv2.imread(img_path)
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            threshold_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            custom_config = r'--oem 3 --psm 6 -l kor'

            text = pytesseract.image_to_string(threshold_image, config=custom_config)
        except Exception as e:
            text = pytesseract.image_to_string(img_path, config=custom_config)

        return text
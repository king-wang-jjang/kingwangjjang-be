from abc import abstractmethod

# img to text
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\nori\AppData\Local\tesseract.exe'
from PIL import Image
from io import BytesIO


class AbstractCommunityWebsite():
    dayBestUrl = ''
    realtimeBestUrl = ''
    
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
        text = pytesseract.image_to_string(img)

        return text

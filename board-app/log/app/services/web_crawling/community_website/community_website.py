import os
from abc import ABC, abstractmethod  # abc 모듈 추가
from app.config import Config
# img to text
import pytesseract
from app.utils import FTPClient
from PIL import Image
import logging
from app.utils.loghandler import setup_logger, catch_exception
import sys
import cv2

# Exception hook setup for catching unhandled exceptions
sys.excepthook = catch_exception

# Logger setup
logger = setup_logger()


class AbstractCommunityWebsite(ABC):  # ABC 클래스 상속 추가
    dayBestUrl = ''
    realtimeBestUrl = ''

    def __init__(self, yyyymmdd, ftp_client: FTPClient) -> None:
        logger.info(f"Initializing AbstractCommunityWebsite with date {yyyymmdd}")
        self.ftp_client = ftp_client

        # Try to create today's directory, log success or failure
        if not self.ftp_client.create_today_directory(yyyymmdd):
            logger.error("Failed to create today's directory.")
            raise ValueError("Failed to create today's directory.")
        else:
            logger.info(f"Successfully created directory for {yyyymmdd}")

    @abstractmethod
    def get_daily_best(self):
        logger.info("Getting daily best content.")
        return {}

    @abstractmethod
    def get_real_time_best(self):
        logger.info("Getting real-time best content.")
        return {}

    @abstractmethod
    def get_board_contents(self, board_id):
        logger.info(f"Fetching board contents for board_id: {board_id}")
        return {}

    @abstractmethod
    def save_img(self, url):
        logger.info(f"Saving image from URL: {url}")
        return {}

    def img_to_text(self, img_path):
        logger.info(f"Converting image to text from path: {img_path}")
        custom_config = r'--oem 3 --psm 6 -l kor'
        allowed_extensions = ['jpg', 'png', 'jpeg']

        try:
            # Check file extension and apply OCR accordingly
            if any(ext in img_path for ext in allowed_extensions):
                logger.info(f"Valid image extension detected for {img_path}. Proceeding with OCR.")

                # Load the image using OpenCV
                image = cv2.imread(img_path)
                if image is None:
                    logger.error(f"Failed to load image: {img_path}")
                    raise ValueError(f"Invalid image path or format: {img_path}")

                # Convert the image to grayscale
                gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                logger.debug(f"Image converted to grayscale.")

                # Apply thresholding to improve OCR accuracy
                threshold_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                logger.debug("Thresholding applied to the image.")

                # Extract text using Tesseract OCR
                text = pytesseract.image_to_string(threshold_image, config=custom_config)
                logger.info(f"OCR completed successfully on image {img_path}.")
            else:
                # If not an image file, directly process the file path
                logger.warning(f"No valid image extension detected for {img_path}. Attempting direct OCR.")
                text = pytesseract.image_to_string(img_path, config=custom_config)

            logger.info(f"Text extraction successful for {img_path}.")
        except Exception as e:
            logger.exception(f"Error during image-to-text conversion for {img_path}: {str(e)}")
            raise e

        return text

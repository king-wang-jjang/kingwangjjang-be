from django.shortcuts import render
from instagrapi import Client


class InstaPost:
    # instagrapi 클라이언트를 생성합니다.
    def __init__(self):
        self.client = Client()
        self.isLogined = False


    # 인스타그램 로그인
    def instaLogin(self, username, password):
        try:
            self.client.login(username, password)
            self.isLogined = True
            message = "로그인에 성공했습니다."
            print(message)
            return "로그인에 성공했습니다."
        
        except Exception as e:
            if "We couldn't find an account with the username" in str(e):
                print("아이디 혹은 비밀번호를 확인하세요.")
            else:
                print("로그인에 문제가 있습니다:", e)

    # 사용자 프로필 사진 가져오기(url로 get)
    def get_profile_image(self):
        if self.isLogined:
            profile_img = self.client.user_info_by_username(self.client.username).profile_pic_url
            return profile_img
                

    # 이미지 한 장 업로드
    def image_upload_one(self, media_path, caption):
        if self.isLogined:
            try:
                self.client.photo_upload(media_path, caption)
                message = "게시물 업로드를 완료했습니다."
                return message
            except Exception as e:
                print("게시물 업로드 중 문제가 생겼습니다.", e)
        else:
            message = "로그인 먼저 해주세요."
            return message      
        

    # 여러 개의 미디어 업로드(이미지 여러 장, 비디오 여러 개, 사진 + 비디오 등...)
    def album_upload(self, media_path, caption):
        if self.isLogined:
            try:
                self.client.album_upload(media_path, caption)
                message = "게시물 업로드를 완료했습니다."
                return message
            except Exception as e:
                print("게시물 업로드 중 문제가 생겼습니다.", e)
        else:
            message = "로그인 먼저 해주세요."
            return message        


    # 사용자 로그아웃
    def instaLogout(self):
        try:
            self.client.logout()
            return True
        except Exception as e:
            print(f"Logout failed: {e}")
            return False

import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .instaPost import InstaPost
from django import forms
from django.contrib import messages


class LoginForm(forms.Form):
    username = forms.CharField(label='Username', max_length=100)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class PhotoUploadForm(forms.Form):
    media_file = forms.ImageField()
    caption = forms.CharField(max_length=255, required=False, widget=forms.Textarea)    

def insta_post(request):
    if request.method == 'POST':
        # POST 요청일 때
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Instagram 로그인을 시도
            client = InstaPost()
            login_result = client.insta_login(username, password)

            if login_result:
                # 로그인 성공 시
                request.session['insta_login'] = True
                return redirect('upload_photo')
            else:
                # 로그인 실패 시
                return HttpResponse("Login failed. Please try again.")

    else:
        # GET 요청일 때
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def upload_photo(request):
    if not request.session.get('insta_login'):
        return HttpResponse("Login first!")

    if request.method == 'POST':
        # POST 요청일 때
        print(request.POST)

        form = PhotoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                media_file = form.cleaned_data['media_file']
                caption = form.cleaned_data['caption']
                print("media_file: ", media_file)
                print("caption: ", caption)

                # 이미지를 프로젝트의 image 폴더에 저장
                image_path = os.path.join(settings.BASE_DIR, 'image', media_file.name)
                print("image_path: ", image_path)
                with open(image_path, 'wb') as f:
                    for chunk in media_file.chunks():
                        f.write(chunk)
            except Exception as e:
                print("specify image path error: ", e)
                return HttpResponse(e)

            else:
                # 이미지의 경로를 media_path에 입력
                media_path = image_path

                # 미디어 업로드
                client = InstaPost()
                client.image_upload_one(media_path, caption)

                return HttpResponse("Upload success!")

    else:
        # GET 요청일 때
        form = PhotoUploadForm()

    return render(request, 'upload_photo.html', {'form': form})

def logout_view(request):
    # 로그아웃 처리
    if request.session.get('insta_login'):
        client = InstaPost()
        client.insta_logout()
        del request.session['insta_login']
        messages.info(request, "You have been logged out successfully.")
    
    return redirect('/') 
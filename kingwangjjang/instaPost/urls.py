from django.contrib import admin 
from django.urls import path 
from . import views 

urlpatterns = [ 
    
	path('post/', views.insta_post, name='instaPost'), 
    path('upload/', views.upload_photo, name='upload_photo'),
	path('logout/', views.logout_view, name='logout'),
] 
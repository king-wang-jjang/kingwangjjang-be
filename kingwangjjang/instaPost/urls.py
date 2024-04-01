from django.contrib import admin 
from django.urls import path 
from . import views 

urlpatterns = [ 
	path('post/', views.instaPost, name='instaPost'), 
    path('upload/', views.uploadPhoto, name='upload_photo'),
	path('logout/', views.logoutView, name='logout'),
]
from django.contrib import admin 
from django.urls import path 
from . import views 

urlpatterns = [ 
	path('board/summary', views.board_summary_rest, name='board_summary'), 
	path('test', views.ygosu_test, name='ygosu_test'),
    
]
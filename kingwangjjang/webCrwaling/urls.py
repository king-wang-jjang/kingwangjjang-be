from django.contrib import admin 
from django.urls import path 
from . import views 

urlpatterns = [ 
	path('board/summary', views.board_summary, name='board_summary'), 
    path('board/list', views.get_real_time_best, name='get_real_time_best'),
]
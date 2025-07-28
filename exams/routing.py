from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/exam_lobby/$', consumers.ExamLobbyConsumer.as_asgi()),
    re_path(r'ws/exam/(?P<exam_id>\w+)/$', consumers.ExamRoomConsumer.as_asgi()),
    # re_path(r'ws/exam/(?P<exam_id>\w+)/$', consumers.ExamConsumer.as_asgi()),
]

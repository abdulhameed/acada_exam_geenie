import logging
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Exam, StudentExam
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class ExamRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.exam_id = self.scope['url_route']['kwargs']['exam_id']
        self.exam_group_name = f'exam_{self.exam_id}'

        print(f"WebSocket connecting for exam {self.exam_id}")  # Debug print

        await self.channel_layer.group_add(
            self.exam_group_name,
            self.channel_name
        )

        await self.accept()

        # Send immediate confirmation of connection
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to exam room'
        }))

    async def disconnect(self, close_code):
        print(f"WebSocket disconnecting for exam {self.exam_id}")  # Debug print
        await self.channel_layer.group_discard(
            self.exam_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        print(f"Received WebSocket message: {text_data}")  # Debug print
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']

        if message_type == 'exam_end':
            student_id = text_data_json['student_id']
            await self.end_exam(student_id)
        elif message_type == 'exam_start':
            # Add handling for exam start
            await self.channel_layer.group_send(
                self.exam_group_name,
                {
                    'type': 'exam_start'
                }
            )

    async def exam_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'exam_start'
        }))

    async def exam_end(self, event):
        print("Sending exam_start event")  # Debug print
        await self.send(text_data=json.dumps({
            'type': 'exam_end'
        }))

    @database_sync_to_async
    def end_exam(self, student_id):
        try:
            student_exam = StudentExam.objects.get(student_id=student_id, exam_id=self.exam_id)
            student_exam.status = 'completed'
            student_exam.save()
            print(f"Successfully ended exam for student {student_id}")  # Debug print
        except Exception as e:
            print(f"Error ending exam: {str(e)}")  # Debug print


class ExamLobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'exam_lobby'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']

        if message_type == 'exam_start':
            exam_id = text_data_json['exam_id']
            await self.start_exam(exam_id)

    async def exam_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    @sync_to_async
    def start_exam(self, exam_id):
        student_exam = StudentExam.objects.get(student=self.scope["user"], exam_id=exam_id)
        if student_exam.status == 'waiting':
            student_exam.status = 'in_progress'
            student_exam.save()


class ExamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.exam_id = self.scope['url_route']['kwargs']['exam_id']
        self.exam_group_name = f'exam_{self.exam_id}'

        logger.info(f"Connecting to exam {self.exam_id}")

        await self.channel_layer.group_add(
            self.exam_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Connected to exam {self.exam_id}")

    async def disconnect(self, close_code):
        logger.info(f"Disconnecting from exam {self.exam_id}")
        await self.channel_layer.group_discard(
            self.exam_group_name,
            self.channel_name
        )
        logger.info(f"Disconnected from exam {self.exam_id}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        logger.info(f"Received message for exam {self.exam_id}: {data}")

        if data['type'] == 'start_exam':
            await self.start_exam()
        elif data['type'] == 'end_exam':
            await self.end_individual_exam(data['student_id'])
            # await self.end_exam()
            logger.info(f"Ended exam {self.exam_id}")

    async def exam_start(self, event):
        logger.info(f"Sending exam start message for exam {self.exam_id}")
        await self.send(text_data=json.dumps({
            'type': 'exam_start',
        }))

    async def exam_end(self, event):
        logger.info(f"Sending exam end message for exam {self.exam_id}")
        await self.send(text_data=json.dumps({
            'type': 'exam_end',
        }))

    @database_sync_to_async
    def start_exam(self):
        logger.info(f"Attempting to start exam {self.exam_id}")
        exam = Exam.objects.get(id=self.exam_id)
        if exam.date <= timezone.now():
            StudentExam.objects.filter(exam=exam, status='waiting').update(status='in_progress')
            logger.info(f"Exam {self.exam_id} started successfully")
            return True
        logger.warning(f"Failed to start exam {self.exam_id}: exam date is in the future")
        return False

    @database_sync_to_async
    def end_exam(self):
        logger.info(f"Ending exam {self.exam_id}")
        exam = Exam.objects.get(id=self.exam_id)
        StudentExam.objects.filter(exam=exam, status='in_progress').update(status='completed', end_time=timezone.now())
        logger.info(f"Exam {self.exam_id} ended")

    @database_sync_to_async
    def end_individual_exam(self, student_id):
        student_exam = StudentExam.objects.get(student_id=student_id, exam_id=self.exam_id)
        student_exam.status = 'completed'
        student_exam.individual_end_time = timezone.now()
        student_exam.save()
        # Trigger grading process for this student's exam

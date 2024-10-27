from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from exams.ai_utils import process_completed_exams
from exams.forms import ExamForm, QuestionForm, StudentExamForm
from exams.models import Answer, Exam, Question, StudentExam
from django.conf import settings
from django.contrib import messages
from .tasks import generate_exam_questions_task
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


@login_required
def exam_create(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            return redirect('exam_detail', exam_id=exam.pk)
    else:
        form = ExamForm()
    return render(request, 'exams/exam_form.html', {'form': form})


@login_required
def exam_list(request):
    exams = Exam.objects.filter(course__school=request.user.school)
    return render(request, 'exams/exam_list.html', {
        'exams': exams,
        'now': timezone.now()
    })


@login_required
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = exam.questions.all()

    if request.method == 'POST':
        if 'generate_questions' in request.POST:
            # Logging started...
            if 'generate_questions' in request.POST:
                logger.info(f"Generating questions for exam {exam_id}")
                task = generate_exam_questions_task.delay(exam.id)
                logger.info(f"Task {task.id} created for exam {exam_id}")
                messages.success(request, f"Question generation started using {settings.AI_PROVIDER}. Task ID: {task.id}")
            # Logging ended ...
            generate_exam_questions_task.delay(exam.id)
            messages.success(
                request,
                f"""Question generation started using {settings.AI_PROVIDER}.
                This may take a few minutes.
                """)
        elif 'switch_ai_provider' in request.POST:

            if settings.AI_PROVIDER == 'openai':
                new_provider = 'openai'
            else:
                new_provider = 'anthropic'
            # new_provider = 'anthropic' if settings.AI_PROVIDER == 'openai' else 'openai'
            settings.AI_PROVIDER = new_provider
            messages.success(request, f"Switched AI provider to {new_provider}")
        return redirect('exam_detail', exam_id=exam.id)

    return render(request, 'exams/exam_detail.html', {
        'exam': exam,
        'questions': questions,
        'ai_provider': settings.AI_PROVIDER,
    })


@login_required
def student_exam_create(request):
    if request.method == 'POST':
        form = StudentExamForm(request.POST)
        if form.is_valid():
            student_exam = form.save()
            return redirect('student_exam_detail', pk=student_exam.pk)
    else:
        form = StudentExamForm()
    return render(request, 'exams/student_exam_form.html', {'form': form})


# def exam_detail(request, pk):
#     exam = get_object_or_404(Exam, pk=pk)
#     return render(request, 'exams/exam_detail.html', {'exam': exam})


def student_exam_detail(request, pk):
    student_exam = get_object_or_404(StudentExam, pk=pk)
    context = {'student_exam': student_exam}
    return render(request, 'exams/student_exam_detail.html', context)


@login_required
def question_create(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.save()
            return redirect('exam_detail', exam_id=exam.id)
    else:
        form = QuestionForm()
    return render(request, 'exams/question_form.html', {'form': form, 'exam': exam})


@login_required
def start_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    student_exam = StudentExam.objects.create(
        student=request.user,
        exam=exam,
        start_time=timezone.now(),
        status='in_progress'
    )
    return redirect('take_exam', student_exam_id=student_exam.id)


# @login_required
# def take_exam(request, student_exam_id):
#     student_exam = get_object_or_404(
#         StudentExam,
#         id=student_exam_id,
#         student=request.user
#         )
#     if student_exam.status == 'completed':
#         return redirect('exam_results', student_exam_id=student_exam.id)

#     questions = student_exam.exam.questions.all()
#     if request.method == 'POST':
#         for question in questions:
#             answer_text = request.POST.get(f'question_{question.id}')
#             Answer.objects.create(
#                 student_exam=student_exam,
#                 question=question,
#                 text=answer_text
#             )
#         student_exam.status = 'completed'
#         student_exam.end_time = timezone.now()
#         student_exam.save()
#         return redirect('exam_results', student_exam_id=student_exam.id)

#     return render(
#         request,
#         'exams/take_exam.html',
#         {'student_exam': student_exam,
#          'questions': questions})


@login_required
def exam_results(request, student_exam_id):
    student_exam = get_object_or_404(
        StudentExam,
        id=student_exam_id,
        student=request.user)
    answers = student_exam.answers.all()
    return render(
        request,
        'exams/exam_results.html',
        {'student_exam': student_exam,
         'answers': answers})


@login_required
def take_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    student = request.user

    # Check if the student has already started this exam
    student_exam, created = StudentExam.objects.get_or_create(
        student=student,
        exam=exam,
        defaults={'start_time': timezone.now(), 'status': 'in_progress'}
    )

    if student_exam.status == 'completed':
        return redirect('exam_completed', exam_id=exam_id)

    if request.method == 'POST':
        for question in exam.questions.all():
            answer_text = request.POST.get(f'question_{question.id}')
            Answer.objects.create(
                student_exam=student_exam,
                question=question,
                text=answer_text
            )

        # Mark exam as completed
        student_exam.end_time = timezone.now()
        student_exam.status = 'completed'
        student_exam.save()

        # Trigger AI grading process
        process_completed_exams()

        return redirect('exam_completed', exam_id=exam_id)

    context = {
        'exam': exam,
        'student_exam': student_exam,
        'questions': exam.questions.all(),
        'time_remaining': (exam.duration - (timezone.now() - student_exam.start_time)).total_seconds()
    }
    return render(request, 'exams/take_exam.html', context)


@login_required
def exam_completed(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    student_exam = get_object_or_404(StudentExam, student=request.user, exam=exam)

    context = {
        'exam': exam,
        'student_exam': student_exam,
    }
    return render(request, 'exams/exam_completed.html', context)


@login_required
def exam_room(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    now = timezone.now()
    late_entry_deadline = exam.date + timedelta(hours=11)

    if now < exam.date:
        # Exam hasn't started yet
        return render(request, 'exams/exam_lobby.html', {'exam': exam})
    elif now <= late_entry_deadline:
        # Exam is in progress, allow entry
        student_exam, created = StudentExam.objects.get_or_create(
            student=request.user,
            exam=exam,
            defaults={
                'status': 'in_progress',
                'start_time': now,
                'end_time': now + exam.duration
            }
        )
        return render(request, 'exams/exam_room.html', {'student_exam': student_exam, 'exam': exam})
    else:
        # Too late to enter
        return render(request, 'exams/exam_closed.html', {'exam': exam})


def get_exam_content(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = Question.objects.filter(exam=exam).values('id', 'text', 'difficulty')

    content = {
        'exam_id': exam.id,
        'exam_title': exam.title,
        'questions': list(questions)
    }

    return JsonResponse(content)


@login_required
def save_answer(request, exam_id):
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        answer_text = request.POST.get('answer_text')

        student_exam = get_object_or_404(StudentExam, student=request.user, exam_id=exam_id)
        question = get_object_or_404(Question, id=question_id, exam_id=exam_id)

        answer, created = Answer.objects.update_or_create(
            student_exam=student_exam,
            question=question,
            defaults={'text': answer_text}
        )

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


def exam_lobby(request):
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    todays_exams = Exam.objects.filter(date__gte=today, date__lt=tomorrow).order_by('date')

    for exam in todays_exams:
        StudentExam.objects.get_or_create(
            student=request.user,
            exam=exam,
            defaults={
                'status': 'waiting',
                'start_time': exam.date,
            }
        )

    context = {
        'todays_exams': todays_exams,
    }
    return render(request, 'exams/exam_lobby.html', context)

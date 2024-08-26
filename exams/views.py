from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from exams.forms import ExamForm, StudentExamForm
from exams.models import Exam, StudentExam


@login_required
def exam_create(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            return redirect('exam_detail', pk=exam.pk)
    else:
        form = ExamForm()
    return render(request, 'exams/exam_form.html', {'form': form})


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


def exam_detail(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    return render(request, 'exams/exam_detail.html', {'exam': exam})


def student_exam_detail(request, pk):
    student_exam = get_object_or_404(StudentExam, pk=pk)
    context = {'student_exam': student_exam}
    return render(request, 'exams/student_exam_detail.html', context)

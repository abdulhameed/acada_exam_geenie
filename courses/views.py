from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from courses.forms import CourseContentForm, CourseForm
from courses.models import Course, CourseContent
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView
from django.views.generic.edit import CreateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy

from users.models import CustomUser
from .forms import CourseRegistrationForm


@login_required
def course_list(request):
    courses = Course.objects.filter(school=request.user.school)
    return render(request, 'courses/course_list.html', {'courses': courses})


@login_required
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            return redirect('course_detail', pk=course.pk)
    else:
        form = CourseForm()
    return render(request, 'courses/course_form.html', {'form': form})


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    contents = course.contents.all()
    return render(
        request,
        'courses/course_detail.html',
        {
            'course': course,
            'contents': contents
            }
            )


@login_required
def course_update(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_detail', course_id=course.id)
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/course_form.html', {'form': form})


@login_required
def course_content_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not request.user.can_create_course_content(course):
        raise PermissionDenied
    if request.method == 'POST':
        form = CourseContentForm(request.POST, request.FILES)
        if form.is_valid():
            content = form.save(commit=False)
            content.course = course
            content.save()
            return redirect('course_detail', course_id=course.id)
    else:
        form = CourseContentForm()
    return render(
        request,
        'courses/course_content_form.html',
        {'form': form, 'course': course}
        )


class CourseRegistrationView(LoginRequiredMixin, FormView):
    template_name = 'courses/course_registration.html'
    form_class = CourseRegistrationForm
    success_url = reverse_lazy('home')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        selected_courses = form.cleaned_data['courses']
        user.enrolled_courses.set(selected_courses)
        messages.success(self.request, 'Course registration successful!')
        return super().form_valid(form)


class CourseAssignmentView(LoginRequiredMixin, ListView):
    template_name = 'courses/course_assignment.html'
    # /Users/ChuzzyOfficial/PycharmProjects/exam_geenie/templates/courses/course_assignment.html
    context_object_name = 'students'

    def get_queryset(self):
        return CustomUser.objects.filter(school=self.request.user.school, role='student')

    def post(self, request, *args, **kwargs):
        student_id = request.POST.get('student')
        course_id = request.POST.get('course')
        if student_id and course_id:
            student = CustomUser.objects.get(id=student_id)
            course = Course.objects.get(id=course_id)
            student.enrolled_courses.add(course)
            messages.success(request, f'{student.username} has been assigned to {course.name}')
        return redirect('course_assignment')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = Course.objects.filter(school=self.request.user.school)
        return context


class ResearchContentCreateView(LoginRequiredMixin, CreateView):
    model = CourseContent
    fields = ['title', 'text_content', 'source_identifier']
    template_name = 'courses/research_content_form.html'
    
    def form_valid(self, form):
        form.instance.content_type = 'text'
        form.instance.research_mode = True
        form.instance.course = self.request.user.school.courses.first()  # Or specify
        return super().form_valid(form)
# 
# git push origin main
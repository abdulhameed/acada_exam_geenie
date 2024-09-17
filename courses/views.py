from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from courses.forms import CourseContentForm, CourseForm
from courses.models import Course
from django.core.exceptions import PermissionDenied


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

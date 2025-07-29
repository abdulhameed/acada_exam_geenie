from django.views.generic import TemplateView
from django.utils import timezone
# from django.contrib.auth.mixins import LoginRequiredMixin
from courses.models import Course
from exams.models import Exam
from django.shortcuts import render


def homepage(request):
    return render(request, 'core/homepage.html')


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()

        if user.is_authenticated:
            if user.role == 'student':
                # context['courses'] = Course.objects.filter(school=user.school)
                # Get courses the student is enrolled in
                context['enrolled_courses'] = user.enrolled_courses.all()
                # Get upcoming exams for these courses
                context['upcoming_exams'] = Exam.objects.filter(
                    course__in=user.enrolled_courses.all(),
                    date__gt=now
                ).order_by('date')[:9]
                # context['upcoming_exams'] = Exam.objects.filter(
                #     course__school=user.school,
                #     date__gt=now
                # ).order_by('date')[:5]
            elif user.role in ['lecturer', 'hod', 'school_admin']:
                context['courses_taught'] = Course.objects.filter(school=user.school, lecturer=user)
                context['upcoming_exams'] = Exam.objects.filter(
                    course__lecturer=user,
                    date__gt=now
                ).order_by('date')[:9]
        # else:
        #     context['courses'] = []
        #     context['upcoming_exams'] = []

        context['now'] = now

        return context


# class HomeView(
#         # LoginRequiredMixin,
#         TemplateView
#         ):
#     template_name = 'core/home.html'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user

#         if user.is_authenticated:

#             if user.role == 'student':
#                 context['courses'] = Course.objects.filter(school=user.school)
#                 context['upcoming_exams'] = Exam.objects.filter(course__school=user.school).order_by('date')[:5]
#             elif user.role in ['lecturer', 'hod', 'admin']:
#                 context['courses'] = Course.objects.filter(school=user.school, lecturer=user)
#                 context['upcoming_exams'] = Exam.objects.filter(course__lecturer=user).order_by('date')[:5]
#             else:  # User is anonymous, provide default or limited context
#                 context['courses'] = []  # or some default courses
#                 context['upcoming_exams'] = []  # or some default exams

#         return context

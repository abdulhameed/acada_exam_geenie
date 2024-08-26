from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
from schools.models import School
from users.forms import SchoolForm


def school_create(request):
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            school = form.save()
            return redirect('school_detail', pk=school.pk)
    else:
        form = SchoolForm()
    return render(request, 'schools/school_form.html', {'form': form})


def school_detail(request, pk):
    school = get_object_or_404(School, pk=pk)
    return render(
        request,
        'schools/school_detail.html',
        {'school': school})

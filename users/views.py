from django.shortcuts import (
    render,
    redirect,
    # get_object_or_404
    )
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView


from users.forms import CustomLoginForm, CustomUserCreationForm

# Create your views here.


def user_signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # login(request, user)
            CustomLoginView(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/signup.html', {'form': form})


class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'users/login.html'
    success_url = reverse_lazy('home')
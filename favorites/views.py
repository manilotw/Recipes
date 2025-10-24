from django.shortcuts import render
from .models import Dish

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .forms import UserUpdateForm, MealTariffForm
from django import forms
from .models import MealTariff
from .models import UserProfile


def index(request):
    return render(request, 'index.html')


def card1(request):
    return render(request, 'card1.html')


def card2(request):
    return render(request, 'card2.html')


def card3(request):
    return render(request, 'card3.html')


def order(request):
    # show order form (GET) and process tariff creation (POST)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Пожалуйста, войдите в систему, чтобы оформить тариф')
            return redirect('favorites:auth')

        form = MealTariffForm(request.POST)
        if form.is_valid():
            tariff = form.save(commit=False)
            # attach tariff to the authenticated User instance
            tariff.user = request.user
            tariff.save()
            messages.success(request, 'Тариф успешно создан и сохранён')
            return redirect('favorites:lk')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
            return render(request, 'order.html', {'form': form})

    # GET
    form = MealTariffForm()
    return render(request, 'order.html', {'form': form})


def registration(request):
    if request.user.is_authenticated:
        return redirect('favorites:lk')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.first_name}!')
                return redirect('favorites:lk')
            except forms.ValidationError as e:
                form.add_error(None, e)
            except Exception as e:
                form.add_error(None, f'Произошла непредвиденная ошибка: {str(e)}')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration.html', {'form': form})


def auth_view(request):
    if request.user.is_authenticated:
        return redirect('favorites:lk')

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.first_name}!')
                return redirect('favorites:lk')
        else:
            pass
    else:
        form = CustomAuthenticationForm()

    return render(request, 'auth.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('favorites:auth')


@login_required
def lk(request):
    if request.method == 'POST':
        new_first_name = request.POST.get('first_name')
        if new_first_name:
            request.user.first_name = new_first_name
            request.user.save()
            messages.success(request, 'Имя успешно изменено!')
            return redirect('favorites:lk')

    dishes = Dish.objects.filter(is_active=True)

    user_profile = UserProfile.objects.get_or_create(user=request.user)

    context = {
        'dishes': dishes,
        'user': request.user,
        'user_profile': user_profile
    }
    return render(request, 'lk.html', context)

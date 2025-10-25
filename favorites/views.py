from .models import Dish

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .forms import UserUpdateForm, MealTariffForm
from django import forms
from .models import MealTariff
from .models import UserProfile
from django.http import Http404


def index(request):
    return render(request, 'index.html')


def card(request, pk):
    try:
        dish = get_object_or_404(Dish, pk=pk)
    except Http404:

        return redirect('favorites:lk')  

    context = {
        'dish': dish
    }
    return render(request, 'card.html', context)


def order(request):

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Пожалуйста, войдите в систему, чтобы оформить тариф')
            return redirect('favorites:auth')

        if MealTariff.objects.filter(user=request.user).exists():
            messages.error(request, 'У вас уже есть тариф — нельзя создать ещё один.')
            return redirect('favorites:lk')

        form = MealTariffForm(request.POST)
        if form.is_valid():
            tariff = form.save(commit=False)
            tariff.user = request.user
            tariff.save()
            messages.success(request, 'Тариф успешно создан и сохранён')
            return redirect('favorites:lk')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
            return render(request, 'order.html', {'form': form})

    if request.user.is_authenticated and MealTariff.objects.filter(user=request.user).exists():
        messages.info(request, 'У вас уже есть активный тариф. Вы не можете создать новый.')
        return redirect('favorites:lk')

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

    if not  MealTariff.objects.filter(user=request.user).exists():
        
        return  redirect('favorites:order')
    else:
        if request.method == 'GET':
            max_price = request.GET.get('max_price')
            
            user_tariff = MealTariff.objects.get(user=request.user)

            dishes = Dish.objects.filter(is_active=True, diet_type=user_tariff.diet_type)

            if max_price:
                try:
                    max_price = float(max_price)
                    dishes = dishes.filter(total_price__lte=max_price)
                except ValueError:
                    pass
            if user_tariff.allergy_fish:
                dishes = dishes.exclude(name__icontains='Рыба')
            if user_tariff.allergy_meat:
                dishes = dishes.exclude(name__icontains='Мясо')
            if user_tariff.allergy_grains:
                dishes = dishes.exclude(name__icontains='Зерн')
            if user_tariff.allergy_honey:
                dishes = dishes.exclude(name__icontains='Мед')
            if user_tariff.allergy_nuts:
                dishes = dishes.exclude(name__icontains='Орех')
            if user_tariff.allergy_dairy:
                dishes = dishes.exclude(name__icontains='Молоко')
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)

            context = {
                'dishes': dishes,
                'user': request.user,
                'user_profile': user_profile,
                'user_tariff': user_tariff  
            }

            return render(request, 'lk.html', context)


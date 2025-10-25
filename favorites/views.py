from .models import Dish

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .forms import MealTariffForm
from django import forms
from .models import MealTariff
from .models import UserProfile
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
import random
from .models import UserDailyMenu


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


def get_or_create_daily_menu(user, user_tariff):
    today = timezone.now().date()

    daily_menus = UserDailyMenu.objects.filter(user=user, date=today)

    if daily_menus.exists():
        return daily_menus

    meal_types = []
    if user_tariff.breakfast:
        meal_types.append('BREAKFAST')
    if user_tariff.lunch:
        meal_types.append('LUNCH')
    if user_tariff.dinner:
        meal_types.append('DINNER')
    if user_tariff.desserts:
        meal_types.append('SNACK')

    dishes = get_filtered_dishes(user_tariff)

    for meal_type in meal_types:
        meal_dishes = dishes.filter(dish_ingredients__isnull=False).distinct()

        if meal_dishes.exists():
            random_dish = random.choice(list(meal_dishes))
            UserDailyMenu.objects.create(
                user=user,
                date=today,
                dish=random_dish,
                meal_type=meal_type
            )
    return UserDailyMenu.objects.filter(user=user, date=today)


def get_filtered_dishes(user_tariff):

    dishes = Dish.objects.filter(is_active=True, diet_type=user_tariff.diet_type)

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

    return dishes


def replace_dish(request, meal_type):
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)

        reset_user_swaps(user_profile)

        if user_profile.meal_swaps_remaining <= 0:
            messages.error(request, 'У вас не осталось доступных замен')
            return redirect('favorites:lk')

        today = timezone.now().date()
        user_tariff = MealTariff.objects.get(user=request.user)

        try:
            daily_menu = UserDailyMenu.objects.get(
                user=request.user,
                date=today,
                meal_type=meal_type
            )

            dishes = get_filtered_dishes(user_tariff)
            if dishes.exists():
                new_dish = random.choice(list(dishes))
                daily_menu.dish = new_dish
                daily_menu.save()

                user_profile.meal_swaps_remaining -= 1
                user_profile.save()
                messages.success(request, f'Блюдо для {daily_menu.get_meal_type_display()} успешно заменено!')
            else:
                messages.error(request, 'Не найдено подходящих блюд для замены')
        except UserDailyMenu.DoesNotExist:
            messages.error(request, 'Меню не найдено')
    return redirect('favorites:lk')


def reset_user_swaps(user_profile):
    return user_profile.reset_swaps_if_needed()


@login_required
def lk(request):
    if request.method == 'POST':
        new_first_name = request.POST.get('first_name')
        if new_first_name:
            request.user.first_name = new_first_name
            request.user.save()
            messages.success(request, 'Имя успешно изменено!')
        return redirect('favorites:lk')

    if not MealTariff.objects.filter(user=request.user).exists():
        return redirect('favorites:order')

    user_tariff = MealTariff.objects.get(user=request.user)
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]

    daily_menus = get_or_create_daily_menu(request.user, user_tariff)

    menu_by_meal_type = {}
    for menu in daily_menus:
        if menu.meal_type not in menu_by_meal_type:
            menu_by_meal_type[menu.meal_type] = []
        menu_by_meal_type[menu.meal_type].append(menu)

    max_price = request.GET.get('max_price')
    if max_price:
        try:
            max_price = float(max_price)
            for meal_type in menu_by_meal_type:
                menu_by_meal_type[meal_type] = [
                    menu for menu in menu_by_meal_type[meal_type]
                    if menu.dish.total_price <= max_price
                ]
        except ValueError:
            pass

    context = {
        'menu_by_meal_type': menu_by_meal_type,
        'user': request.user,
        'user_profile': user_profile,
        'user_tariff': user_tariff,
        'today': timezone.now().date()
    }
    return render(request, 'lk.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm, MealTariffForm
from django import forms
from .models import MealTariff, UserProfile, Dish, Allergy
from django.http import Http404
from django.utils import timezone
import random
from django.core.cache import cache
from decimal import Decimal


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


def get_daily_menu_for_user(user, user_tariff, max_price=None):
    today = timezone.now().date()
    cache_key = f"daily_menu_{user.id}_{today}"

    menu = cache.get(cache_key)
    if menu:
        return menu

    meal_types = []
    if user_tariff.breakfast:
        meal_types.append('BREAKFAST')
    if user_tariff.lunch:
        meal_types.append('LUNCH')
    if user_tariff.dinner:
        meal_types.append('DINNER')
    if user_tariff.desserts:
        meal_types.append('SNACK')

    menu = {}
    for meal_type in meal_types:
        dishes = get_filtered_dishes(user_tariff, meal_type, max_price)

        if hasattr(dishes, 'exists') and dishes.exists():
            selected_dish = random.choice(list(dishes))
            menu[meal_type] = selected_dish
            dishes_no_price_limit = get_filtered_dishes(user_tariff, meal_type, None)

            if hasattr(dishes_no_price_limit, 'exists') and dishes_no_price_limit.exists():
                selected_dish = random.choice(list(dishes_no_price_limit))
                menu[meal_type] = selected_dish
            else:
                fallback_dishes = Dish.objects.filter(
                    is_active=True,
                    diet_type=user_tariff.diet_type,
                    meal_type=meal_type
                )
                if fallback_dishes.exists():
                    selected_dish = random.choice(list(fallback_dishes))
                    menu[meal_type] = selected_dish

    cache.set(cache_key, menu, 60 * 60 * 24)
    return menu


def get_filtered_dishes(user_tariff, meal_type=None, max_price=None):
    try:
        dishes = Dish.objects.filter(is_active=True, diet_type=user_tariff.diet_type)

        if not hasattr(dishes, 'filter'):
            return Dish.objects.none()

        if meal_type:
            dishes = dishes.filter(meal_type=meal_type)

        if max_price is not None:
            try:
                max_price_decimal = Decimal(str(max_price))
                dishes = dishes.filter(total_price__lte=max_price_decimal)
            except (ValueError, TypeError) as e:
                print(f"Error converting max_price to Decimal: {e}")

        user_allergies = []
        if user_tariff.allergy_fish:
            user_allergies.append('fish')
        if user_tariff.allergy_meat:
            user_allergies.append('meat')
        if user_tariff.allergy_grains:
            user_allergies.append('grains')
        if user_tariff.allergy_honey:
            user_allergies.append('honey')
        if user_tariff.allergy_nuts:
            user_allergies.append('nuts')
        if user_tariff.allergy_dairy:
            user_allergies.append('dairy')

        if user_allergies:
            existing_allergies = Allergy.objects.filter(slug__in=user_allergies)
            if existing_allergies.exists():
                dishes = dishes.exclude(allergies__in=existing_allergies)

        return dishes
    except Exception as e:
        return Dish.objects.none()


def replace_dish_in_menu(user, user_tariff, meal_type, max_price=None):
    today = timezone.now().date()
    cache_key = f"daily_menu_{user.id}_{today}"

    menu = cache.get(cache_key) or {}

    dishes = get_filtered_dishes(user_tariff, meal_type, max_price)

    current_dish = menu.get(meal_type)
    if current_dish:
        dishes = dishes.exclude(pk=current_dish.pk)

    if dishes.exists():
        new_dish = random.choice(list(dishes))
        menu[meal_type] = new_dish
        cache.set(cache_key, menu, 60 * 60 * 24)
        return new_dish

    return None


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

        if 'reset_price' in request.POST:
            user_profile = UserProfile.objects.get(user=request.user)
            user_profile.max_dish_price = None
            user_profile.save()
            messages.success(request, 'Фильтр цены сброшен!')

            today = timezone.now().date()
            cache_key = f"daily_menu_{request.user.id}_{today}"
            cache.delete(cache_key)

            return redirect('favorites:lk')

        new_diet_type = request.POST.get('diet_type')
        if new_diet_type:
            user_tariff = MealTariff.objects.get(user=request.user)
            if user_tariff.diet_type != new_diet_type:
                user_tariff.diet_type = new_diet_type
                user_tariff.save()
                messages.success(request, f'Тип диеты изменен на {user_tariff.get_diet_type_display()}!')

                today = timezone.now().date()
                cache_key = f"daily_menu_{request.user.id}_{today}"
                cache.delete(cache_key)

            return redirect('favorites:lk')

        max_price = request.POST.get('max_price')
        if max_price is not None:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                if max_price.strip():
                    max_price_value = float(max_price)
                    user_profile.max_dish_price = max_price_value
                    messages.success(request, f'Настройки цены обновлены! Будут показаны блюда до {max_price_value} руб.')
                    print(f"DEBUG: Установлена максимальная цена: {max_price_value}")
                else:
                    user_profile.max_dish_price = None
                    messages.success(request, 'Фильтр цены сброшен!')
                user_profile.save()

                today = timezone.now().date()
                cache_key = f"daily_menu_{request.user.id}_{today}"
                cache.delete(cache_key)
                print(f"DEBUG: Кеш очищен для пользователя {request.user.id}")

            except ValueError:
                messages.error(request, 'Неверное значение цены')

        return redirect('favorites:lk')

    if not MealTariff.objects.filter(user=request.user).exists():
        return redirect('favorites:order')

    user_tariff = MealTariff.objects.get(user=request.user)
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]

    reset_user_swaps(user_profile)

    daily_menu = get_daily_menu_for_user(request.user, user_tariff, user_profile.max_dish_price)

    menu_by_meal_type = {}
    for meal_type, dish in daily_menu.items():
        if meal_type not in menu_by_meal_type:
            menu_by_meal_type[meal_type] = []

        menu_by_meal_type[meal_type].append({
            'dish': dish,
            'meal_type': meal_type
        })

    context = {
        'menu_by_meal_type': menu_by_meal_type,
        'user': request.user,
        'user_profile': user_profile,
        'user_tariff': user_tariff,
        'today': timezone.now().date(),
    }
    return render(request, 'lk.html', context)


def replace_dish(request, meal_type):
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        reset_user_swaps(user_profile)

        if user_profile.meal_swaps_remaining <= 0:
            messages.error(request, 'У вас не осталось доступных замен')
            return redirect('favorites:lk')

        user_tariff = MealTariff.objects.get(user=request.user)

        new_dish = replace_dish_in_menu(
            request.user,
            user_tariff,
            meal_type,
            user_profile.max_dish_price
        )

        if new_dish:
            user_profile.meal_swaps_remaining -= 1
            user_profile.save()
            messages.success(request, f'Блюдо успешно заменено!')
        else:
            messages.error(request, 'Не найдено подходящих блюд для замены')

    return redirect('favorites:lk')

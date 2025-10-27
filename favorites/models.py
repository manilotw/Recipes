from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    weekly_budget = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=2000.00,
        help_text='Недельный бюджет на продукты в рублях'
    )

    max_dish_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Макс. цена за блюдо',
        help_text='Если установлено, показываются только блюда дешевле этой цены'
    )

    meal_swaps_remaining = models.PositiveIntegerField(default=3, verbose_name='Количество замен')

    last_swap_reset = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Последнее обновление замен'
    )

    def __str__(self):
        return f'Профиль {self.user.username}'

    def reset_swaps_if_needed(self):
        now = timezone.now()
        time_since_reset = now - self.last_swap_reset

        if time_since_reset >= timedelta(hours=24):
            self.meal_swaps_remaining = 3
            self.last_swap_reset = now
            self.save()
            return True
        return False

    def get_daily_budget(self):
        return self.weekly_budget / 7

    def set_auto_max_price(self):
        daily_budget = self.get_daily_budget()

        self.max_dish_price = daily_budget / 3
        self.save()


class Allergy(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название аллергена')
    slug = models.SlugField(unique=True, verbose_name='Идентификатор')

    TARIFF_FIELD_MAPPING = {
        'fish': 'allergy_fish',
        'meat': 'allergy_meat',
        'grains': 'allergy_grains',
        'honey': 'allergy_honey',
        'nuts': 'allergy_nuts',
        'dairy': 'allergy_dairy',
    }

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Аллерген'
        verbose_name_plural = 'Аллергены'


class Dish(models.Model):
    MEAL_TYPES = [
        ('BREAKFAST', 'Завтрак'),
        ('LUNCH', 'Обед'),
        ('DINNER', 'Ужин'),
        ('SNACK', 'Перекус'),
    ]

    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    recipe = models.TextField(verbose_name='Рецепт')
    image = models.ImageField(upload_to='img/', verbose_name='Изображение')

    total_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Общая стоимость блюда',
        default=0,
        editable=False
    )

    DIET_CHOICES = [
        ('CLASSIC', 'Классическое'),
        ('LOW_CARB', 'Низкоуглеводное'),
        ('VEGETARIAN', 'Вегетарианское'),
        ('KETO', 'Кето'),
    ]

    allergies = models.ManyToManyField(
        Allergy, 
        blank=True, 
        verbose_name='Содержит аллергены',
        help_text='Аллергены, которые содержатся в этом блюде'
    )

    # which diet this dish belongs to — aligns with menu options a user can choose
    diet_type = models.CharField(max_length=20, choices=DIET_CHOICES, default='CLASSIC', verbose_name='Тип меню')

    total_calories = models.PositiveIntegerField(
        verbose_name='Общая калорийность (ккал)',
        default=0,
        help_text='Автоматически рассчитывается из ингредиентов',
        editable=False
    )

    meal_type = models.CharField(
        max_length=20,
        choices=MEAL_TYPES,
        verbose_name='Тип приема пищи',
        default='LUNCH'
    )

    is_active = models.BooleanField(default=True, verbose_name='Активно')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Когда создано')

    def __str__(self):
        return self.name

    def calculate_total_calories(self):
        total = 0
        for dish_ingredient in self.dish_ingredients.all():
            if dish_ingredient.ingredient.calories and dish_ingredient.quantity:
                total += dish_ingredient.ingredient.calories * dish_ingredient.quantity
        return int(total)

    def calculate_total_price(self):
        total = Decimal('0')
        for dish_ingredient in self.dish_ingredients.all():
            if dish_ingredient.ingredient.average_price and dish_ingredient.quantity:
                total += dish_ingredient.ingredient.average_price * dish_ingredient.quantity
        return total

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.total_calories = self.calculate_total_calories()
        self.total_price = self.calculate_total_price()
        Dish.objects.filter(pk=self.pk).update(
            total_calories=self.total_calories,
            total_price=self.total_price
        )


class Ingredient(models.Model):
    UNIT_TYPES = [
        ('GRAM', 'г'),
        ('KILOGRAM', 'кг'),
        ('PIECE', 'шт'),
        ('TABLESPOON', 'ст.л.'),
    ]

    name = models.CharField(max_length=100)
    average_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text='Средняя цена за 100 грамм (1 единицу) в рублях'
    )
    unit = models.CharField(
        max_length=15,
        choices=UNIT_TYPES,
        default='GRAM',
        verbose_name='Единица измерения'
    )
    calories = models.PositiveIntegerField(
        verbose_name='Калорийность на 100г (1 единицу)',
        help_text='Ккал на 100 грамм (1 единицу) продукта',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name


class DishIngredient(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='dish_ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Количество (в единицах)',
        help_text='Количество в единицах измерения (1 единица = 100г)'
    )

    class Meta:
        unique_together = ['dish', 'ingredient']

    def __str__(self):
        return f'{self.ingredient.name} для {self.dish.name}'


class MealTariff(models.Model):
    # enforce one tariff per user at DB level
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='meal_tariff')

    # Основные параметры
    name = models.CharField(max_length=100, default='Standard Plan', verbose_name='Название тарифа')

    DIET_CHOICES = [
        ('CLASSIC', 'Классическое'),
        ('LOW_CARB', 'Низкоуглеводное'),
        ('VEGETARIAN', 'Вегетарианское'),
        ('KETO', 'Кето'),
    ]

    # which menu type the user selected when creating this tariff
    diet_type = models.CharField(max_length=20, choices=DIET_CHOICES, default='CLASSIC', verbose_name='Тип меню')

    # Включенные приёмы пищи
    breakfast = models.BooleanField(default=False, verbose_name='Завтраки')
    lunch = models.BooleanField(default=False, verbose_name='Обеды')
    dinner = models.BooleanField(default=False, verbose_name='Ужины')
    desserts = models.BooleanField(default=False, verbose_name='Десерты')

    # Аллергии (чекбоксы)
    allergy_fish = models.BooleanField(default=False, verbose_name='Рыба и морепродукты')
    allergy_meat = models.BooleanField(default=False, verbose_name='Мясо')
    allergy_grains = models.BooleanField(default=False, verbose_name='Зерновые')
    allergy_honey = models.BooleanField(default=False, verbose_name='Продукты пчеловодства')
    allergy_nuts = models.BooleanField(default=False, verbose_name='Орехи и бобовые')
    allergy_dairy = models.BooleanField(default=False, verbose_name='Молочные продукты')

    def __str__(self):
        return f'{self.name} ({self.get_diet_type_display()})'


@receiver([post_save, post_delete], sender=DishIngredient)
def update_dish_nutrition(sender, instance, **kwargs):
    instance.dish.total_calories = instance.dish.calculate_total_calories()
    instance.dish.total_price = instance.dish.calculate_total_price()
    instance.dish.save()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Создает профиль пользователя автоматически при создании пользователя"""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Сохраняет профиль пользователя при сохранении пользователя"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
    else:
        UserProfile.objects.get_or_create(user=instance)


# invalidate cached daily menus when dishes or allergens change so users see updates immediately
@receiver([post_save, post_delete], sender=Dish)
def invalidate_cache_on_dish_change(sender, instance, **kwargs):
    try:
        cache.clear()
    except Exception:
        pass


@receiver([post_save, post_delete], sender=Allergy)
def invalidate_cache_on_allergy_change(sender, instance, **kwargs):
    try:
        cache.clear()
    except Exception:
        pass

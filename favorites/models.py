from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    diet_type = models.CharField(max_length=20, choices=[
        ('GLUTEN_FREE', 'Без глютена'),
        ('VEGAN', 'Веган'),
        ('VEGETARIAN', 'Вегетарианец'),
        ('NONE', 'Нет ограничений'),
    ], default='NONE', verbose_name='Тип диеты')

    weekly_budget = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=2000.00,
        help_text='Недельный бюджет на продукты в рублях'
    )

    meal_swaps_remaining = models.PositiveIntegerField(default=3, verbose_name='Количество замен')

    def __str__(self):
        return f'Профиль {self.user.username}'


class Dish(models.Model):
    MEAL_TYPES = [
        ('BREAKFAST', 'Завтрак'),
        ('LUNCH', 'Обед'),
        ('DINNER', 'Ужин'),
        ('SNACK', 'Перекус'),
    ]

    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    image = models.ImageField(upload_to='media/', verbose_name='Изображение')

    total_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Общая стоимость блюда',
        default=0,
        editable=False
    )

    is_gluten_free = models.BooleanField(default=False, verbose_name='Без глютена')
    is_vegan = models.BooleanField(default=False, verbose_name='Веганское')
    is_vegetarian = models.BooleanField(default=False, verbose_name='Вегетарианское')

    total_calories = models.PositiveIntegerField(
        verbose_name='Общая калорийность (ккал)',
        default=0,
        help_text='Автоматически рассчитывается из ингредиентов',
        editable=False
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


@receiver([post_save, post_delete], sender=DishIngredient)
def update_dish_nutrition(sender, instance, **kwargs):
    instance.dish.total_calories = instance.dish.calculate_total_calories()
    instance.dish.total_price = instance.dish.calculate_total_price()
    instance.dish.save()

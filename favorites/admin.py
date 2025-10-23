from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import UserProfile, Dish, Ingredient, DishIngredient


def format_currency(value):
    if value is None:
        return '0 ₽'

    value_float = float(value)

    if value_float == int(value_float):
        return f'{int(value_float)} ₽'
    else:
        return f'{value_float:.2f} ₽'


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Дополнительная информация'
    fields = ('diet_type', 'weekly_budget', 'meal_swaps_remaining')
    extra = 0


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_diet_type', 'get_weekly_budget', 'is_staff')
    list_filter = ('userprofile__diet_type', 'is_staff', 'is_active')

    def get_diet_type(self, obj):
        return obj.userprofile.diet_type
    get_diet_type.short_description = 'Диета'

    def get_weekly_budget(self, obj):
        return format_currency(obj.userprofile.weekly_budget)
    get_weekly_budget.short_description = 'Бюджет'


class DishIngredientInline(admin.TabularInline):
    model = DishIngredient
    extra = 1
    fields = ('ingredient', 'quantity', 'get_price_contribution', 'get_calories_contribution')
    readonly_fields = ('get_price_contribution', 'get_calories_contribution')

    def get_price_contribution(self, obj):
        if obj.pk and obj.ingredient.average_price and obj.quantity:
            price = obj.ingredient.average_price * obj.quantity
            return format_currency(price)
        return '0 ₽'
    get_price_contribution.short_description = 'Стоимость'

    def get_calories_contribution(self, obj):
        if obj.pk and obj.ingredient.calories and obj.quantity:
            calories = obj.ingredient.calories * obj.quantity
            return f'{int(calories)} ккал'
        return '0 ккал'
    get_calories_contribution.short_description = 'Калорийность'


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = (
        'image_preview',
        'name',
        'get_formatted_price',
        'total_calories',
        'is_active',
        'created_at'
    )
    list_display_links = ('name', 'image_preview')
    list_filter = ('is_gluten_free', 'is_vegan', 'is_vegetarian', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'total_calories', 'total_price', 'image_preview', 'get_formatted_price')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'image', 'image_preview', 'get_formatted_price', 'total_calories')
        }),
        ('Диетические свойства', {
            'fields': ('is_gluten_free', 'is_vegan', 'is_vegetarian'),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active', 'created_at')
        }),
    )
    inlines = (DishIngredientInline,)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        return 'Нет изображения'
    image_preview.short_description = 'Превью'

    def get_formatted_price(self, obj):
        return format_currency(obj.total_price)
    get_formatted_price.short_description = 'Стоимость'
    get_formatted_price.admin_order_field = 'total_price'

    actions = ['activate_dishes', 'deactivate_dishes', 'recalculate_nutrition']

    def activate_dishes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} блюд активировано')
    activate_dishes.short_description = 'Активировать выбранные блюда'

    def deactivate_dishes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} блюд деактивировано')
    deactivate_dishes.short_description = 'Деактивировать выбранные блюда'

    def recalculate_nutrition(self, request, queryset):
        for dish in queryset:
            dish.total_calories = dish.calculate_total_calories()
            dish.total_price = dish.calculate_total_price()
            dish.save()
        self.message_user(request, f'Показатели пересчитаны для {queryset.count()} блюд')
    recalculate_nutrition.short_description = 'Пересчитать стоимость и калорийность'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_formatted_price', 'unit', 'calories', 'get_dishes_count')
    list_filter = ('unit',)
    search_fields = ('name',)
    list_editable = ('unit', 'calories')

    def get_formatted_price(self, obj):
        '''Форматирует цену ингредиента без научной нотации'''
        return format_currency(obj.average_price)
    get_formatted_price.short_description = 'Цена'
    get_formatted_price.admin_order_field = 'average_price'

    def get_dishes_count(self, obj):
        return obj.dishingredient_set.count()
    get_dishes_count.short_description = 'Используется в блюдах'


@admin.register(DishIngredient)
class DishIngredientAdmin(admin.ModelAdmin):
    list_display = ('dish', 'ingredient', 'quantity', 'get_unit', 'get_price_contribution', 'get_calories_contribution')
    list_filter = ('dish', 'ingredient')
    search_fields = ('dish__name', 'ingredient__name')

    def get_unit(self, obj):
        return obj.ingredient.unit
    get_unit.short_description = 'Ед. изм.'

    def get_price_contribution(self, obj):
        if obj.ingredient.average_price and obj.quantity:
            price = obj.ingredient.average_price * obj.quantity
            return format_currency(price)
        return '0 ₽'
    get_price_contribution.short_description = 'Стоимость'

    def get_calories_contribution(self, obj):
        if obj.ingredient.calories and obj.quantity:
            calories = obj.ingredient.calories * obj.quantity
            return f'{int(calories)} ккал'
        return '0 ккал'
    get_calories_contribution.short_description = 'Калорийность'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
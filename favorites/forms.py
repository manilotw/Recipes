from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
from .models import MealTariff
from .models import UserProfile


class MealTariffForm(forms.ModelForm):
    class Meta:
        model = MealTariff
        fields = [
            'diet_type',
            'breakfast', 'lunch', 'dinner', 'desserts',
            'allergy_fish', 'allergy_meat', 'allergy_grains', 'allergy_honey', 'allergy_nuts', 'allergy_dairy'
        ]
        widgets = {
            'diet_type': forms.Select(attrs={'class': 'form-select'}),
        }


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'})
    )

    class Meta:
        model = User
        fields = ('first_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def save(self, commit=True):
        try:
            user = super().save(commit=False)
            email = self.cleaned_data['email']
            base_username = email.split('@')[0]
            username = base_username
            counter = 1

            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                if counter > 100:
                    import uuid
                    username = f"{base_username}_{uuid.uuid4().hex[:8]}"
                    break

            user.username = username
            user.email = email
            user.first_name = self.cleaned_data['first_name']
            if commit:
                user.save()
                UserProfile.objects.get_or_create(user=user)
            return user
        except Exception as e:
            raise forms.ValidationError(f"Ошибка при создании пользователя: {str(e)}")


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'})
    )

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    self.user_cache = user
                else:
                    raise forms.ValidationError("Неверный email или пароль")
            except User.DoesNotExist:
                raise forms.ValidationError("Неверный email или пароль")
        return self.cleaned_data


class UserUpdateForm(UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
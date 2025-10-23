from django.shortcuts import render
from .models import Dish

# Views that render templates in the project's templates/ directory.
def index(request):
	return render(request, 'index.html')


def auth_view(request):
	return render(request, 'auth.html')


def card1(request):
	return render(request, 'card1.html')


def card2(request):
	return render(request, 'card2.html')


def card3(request):
	return render(request, 'card3.html')


def lk(request):
	dishes = Dish.objects.all()
	return render(request, 'lk.html', {'dishes': dishes})


def order(request):
	return render(request, 'order.html')


def registration(request):
	return render(request, 'registration.html')

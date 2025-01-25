# reservations/forms.py

from django import forms
from .models import Reservation

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['boat', 'booking_date', 'time_slot', 'number_of_guests']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optionally, you can customize the form fields here (e.g., add help texts, labels, etc.)
        self.fields['booking_date'].widget.attrs.update({'class': 'datepicker'})  # Example if you want a specific class







#  urls.py

from django.urls import path
from . import views

# Custom 403 handler
def custom_permission_denied_view(request, exception=None):
    return render(request, 'reservations/403.html', status=403)

# Add this at the top level of your `urls.py`
handler403 = custom_permission_denied_view

urlpatterns = [
    # Homepage (Reservation page)
    path('', views.reservation_selection, name='reservation_selection'),  # /reservations

    # Dashboard page for logged-in users (customer dashboard)
    path('my-dashboard/', views.dashboard, name='dashboard'),  # /reservations/my-dashboard

    # Staff dashboard page for staff users
    path(
        'staff/dashboard/',
        views.StaffReservationListView.as_view(),
        name='staff_dashboard'
    ),
]







# views.py
from django.shortcuts import render, redirect
from django.views.generic import ListView
from .models import Reservation
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


# Reservation selection page (homepage)
def reservation_selection(request):
    return render(request, 'reservations/reservation_selection.html')


# Dashboard for logged-in users (customer dashboard)
@login_required
def dashboard(request):
    reservations = Reservation.objects.filter(user=request.user)
    return render(request, 'reservations/my_dashboard.html', {'reservations': reservations})


# Staff dashboard for logged-in staff users
class StaffReservationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Reservation
    template_name = 'reservations/staff_dashboard.html'  # Staff dashboard template
    context_object_name = 'reservations'

    def get_queryset(self):
        return Reservation.objects.all()  # Show all reservations for staff

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, 'reservations/403.html', status=403)
        raise PermissionDenied

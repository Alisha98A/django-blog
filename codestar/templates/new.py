from django.shortcuts import render, redirect
from django.views import generic
from django.views.generic.list import ListView
from .models import Reservation
from datetime import date
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .forms import ReservationForm
from django.contrib.auth.models import User
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView
from django.views.generic.edit import CreateView
from django.urls import reverse


# ---------------------------------
# View and Create Reservation
# ---------------------------------

@login_required
def reservation_view(request):
    if request.user.is_staff:
        # Staff members can make reservations for themselves or on behalf of others
        form = ReservationForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.save()
            return redirect('reservation_success')
        return render(request, 'reservation_form.html', {'form': form, 'user_type': 'staff'})

    else:
        # Guests can only make reservations for themselves
        form = ReservationForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.save()
            return redirect('reservation_success')
        return render(request, 'reservation_form.html', {'form': form, 'user_type': 'guest'})

def reservation_success(request):
    return render(request, 'reservation_success.html')

# ---------------------------------
# List of all reservations
# ---------------------------------


class ReservationListView(ListView):
    model = Reservation
    template_name = "reservation_list.html"  
    context_object_name = "reservations"

    def get_queryset(self):
        """Only show reservations for the logged-in user."""
        return Reservation.objects.filter(user=self.request.user).order_by("booking_date")


# ---------------------------------
# Create
# ---------------------------------


class ReservationCreateView(LoginRequiredMixin, CreateView):
    model = Reservation
    fields = ['booking_date', 'time_slot', 'number_of_guests', 'boat'] 

    def form_valid(self, form):
        # Assign the logged-in user to the reservation instance
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('reservations_list') 

# ---------------------------------
# Update
# ---------------------------------

class ReservationUpdateView(UpdateView):
    model = Reservation
    template_name = "reservation_form.html"
    fields = ["boat", "booking_date", "time_slot", "number_of_guests", "has_discount"]
    
    success_url = reverse_lazy('reservations_list')  # Redirect after success
    
    def form_valid(self, form):
        # Call the original form_valid method to save the form
        response = super().form_valid(form)
        
        # Add a success message
        messages.success(self.request, "Your reservation has been successfully updated!")
        
        return response

# ---------------------------------
# Delete
# ---------------------------------
class ReservationDeleteView(DeleteView):
    model = Reservation
    template_name = "reservation_confirm_delete.html"
    success_url = reverse_lazy("reservations_list")

# ---------------------------------
# Success & error page 
# ---------------------------------

@login_required
def reservation_success(request):
    # If the user is authenticated, show the reservation success page
    return render(request, 'reservation_success')






urls.py

from django.urls import path
from . import views 
from .views import (
    ReservationListView,
    ReservationCreateView,
    ReservationUpdateView,
    ReservationDeleteView,
)

app_name = 'reservations' 

urlpatterns = [
    # Create reservation and success page
    path("new/", ReservationCreateView.as_view(), name="reservation_create"),
    path('success/', views.reservation_success, name='reservation_success'),

    # List view, edit and delete
    path("reservations/", ReservationListView.as_view(), name="reservations_list"),
    path("reservations/<int:pk>/edit/", ReservationUpdateView.as_view(), name="reservation_edit"),
    path("reservations/<int:pk>/delete/", ReservationDeleteView.as_view(), name="reservation_delete"),
]




models.py


from datetime import timedelta, datetime, date
from django.utils.timezone import make_aware
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse


# Create your models here.

class Boat(models.Model):
    """
    The Boat model represents a dining boat used for reservations.
    It stores information about the boat's name, description, and capacity.
    This model is used to keep track of available boats for customer bookings.
    """
    name = models.CharField(max_length=255)
    description = models.TextField()  
    capacity = models.IntegerField()  

    def __str__(self):
        return self.name
    

class Reservation(models.Model):
    """
    The Reservation model represents a booking made by a user for a specific boat.
    It stores the user who made the reservation, the boat being reserved, the booking date, 
    the time slot, and the number of guests. It also includes an optional discount field.
    The model ensures that the number of guests is between 4 and 20 through the clean method.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    boat = models.ForeignKey(Boat, on_delete=models.CASCADE)  
    booking_date = models.DateField()  
    time_slot = models.TimeField()  
    number_of_guests = models.IntegerField() 
    has_discount = models.BooleanField(default=False, null=True, blank=True) 
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reservation for {self.user.username} on {self.booking_date}"

    def clean(self):
        """Validates the reservation details, including time slots, guest limits, and overlaps."""
        today = date.today()

        # Prevent past bookings and enforce 2-day advance notice
        if self.booking_date < today:
            raise ValidationError("Booking date cannot be in the past.")
        if self.booking_date < today + timedelta(days=2):
            raise ValidationError("Bookings must be made at least 2 days in advance.")

        # Validate guest count
        if not 4 <= self.number_of_guests <= 20:
            raise ValidationError("Number of guests must be between 4 and 20.")

        # Validate time slot within operational hours
        opening_time = datetime.strptime("10:00", "%H:%M").time()
        closing_time = datetime.strptime("22:00", "%H:%M").time()
        if not opening_time <= self.time_slot <= closing_time:
            raise ValidationError("Bookings must be between 10:00 and 22:00.")

        # Ensure last booking starts by 20:00
        latest_start_time = datetime.strptime("20:00", "%H:%M").time()
        if self.time_slot > latest_start_time:
            raise ValidationError("Last booking must start at 20:00 or earlier.")

        # Prevent overlapping reservations
        start_time = make_aware(datetime.combine(self.booking_date, self.time_slot))
        end_time = start_time + timedelta(hours=2)
        overlapping_reservations = Reservation.objects.filter(
            boat=self.boat,
            booking_date=self.booking_date,
        ).exclude(id=self.id)

        for reservation in overlapping_reservations:
            existing_start = make_aware(datetime.combine(reservation.booking_date, reservation.time_slot))
            existing_end = existing_start + timedelta(hours=2)
            if start_time < existing_end and end_time > existing_start:
                raise ValidationError(
                    f"This boat is already booked from {existing_start.time()} to {existing_end.time()}."
                )
            
    def get_absolute_url(self):
        # Redirect to the reservation list page after updating a reservation
        return reverse('reservations_list')
            
    def save(self, *args, **kwargs):
        """Overrides the save method to validate before saving."""
        self.clean()
        super().save(*args, **kwargs)






forms.py


from django import forms
from .models import Boat, Reservation
from django.contrib.auth.models import User


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['boat', 'booking_date', 'time_slot', 'number_of_guests', 'has_discount']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date'}),
            'time_slot': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit the boats to available boats
        self.fields['boat'].queryset = Boat.objects.all()

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

---------------

from django import forms
from .models import Reservation
from django.contrib.auth.models import User

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['booking_date', 'time_slot', 'number_of_guests']

    number_of_guests = forms.IntegerField(
        min_value=4,
        max_value=20,
        widget=forms.NumberInput(attrs={'min': 4, 'max': 20}),
    )

    def clean(self):
        cleaned_data = super().clean()
        booking_date_time = cleaned_data.get('booking_date_time')
        guests = cleaned_data.get('number_of_guests')

        # Split the date and time from the combined datetime field
        booking_date = booking_date_time.date()
        time_slot = booking_date_time.time()

        # Validate boat availability
        if not Reservation.check_availability(booking_date, time_slot, guests):
            raise forms.ValidationError(
                f"Selected time slot {time_slot} is not available for {guests} guests."
            )

        return cleaned_data






# Used previously
"""from django import forms
from .models import Reservation, Boat
from django.contrib.auth.models import User

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['boat', 'booking_date', 'time_slot', 'number_of_guests']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = kwargs.get('instance').user if 'instance' in kwargs else None
        
        # Fetch user's details if available
        if user:
            self.fields['first_name'] = forms.CharField(initial=user.first_name, required=True)
            self.fields['last_name'] = forms.CharField(initial=user.last_name, required=True)
            self.fields['phone_number'] = forms.CharField(initial=user.profile.phone_number if hasattr(user, 'profile') else '', required=True)
            self.fields['email'] = forms.EmailField(initial=user.email, required=True)
        else:
            self.fields['first_name'] = forms.CharField(required=True)
            self.fields['last_name'] = forms.CharField(required=True)
            self.fields['phone_number'] = forms.CharField(required=True)
            self.fields['email'] = forms.EmailField(required=True)

    def clean_booking_date(self):
        booking_date = self.cleaned_data.get('booking_date')
        if booking_date < datetime.date.today():
            raise forms.ValidationError("Booking date cannot be in the past.")
        return booking_date

    def clean_number_of_guests(self):
        num_guests = self.cleaned_data.get('number_of_guests')
        if not 4 <= num_guests <= 20:
            raise forms.ValidationError("Number of guests must be between 4 and 20.")
        return num_guests

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        time_slot = cleaned_data.get('time_slot')
        number_of_guests = cleaned_data.get('number_of_guests')

        # Validate available boats
        available_boats = Boat.objects.filter(
            capacity__gte=number_of_guests
        )

        if not available_boats:
            raise forms.ValidationError("No boats available for the number of guests selected.")
        
        # Check availability of the selected boat and time slot
        for boat in available_boats:
            conflicting_reservation = Reservation.objects.filter(
                boat=boat,
                booking_date=booking_date,
                time_slot=time_slot
            )
            if conflicting_reservation.exists():
                raise forms.ValidationError(f"Boat {boat.name} is already booked for this time slot.")

        return cleaned_data"""""


-----------------------------------------------------------------------------------------------------------------------


#  urls.py

from django.urls import path, include
from . import views

# Custom 403 handler
def custom_permission_denied_view(request, exception=None):
    return render(request, 'reservations/403.html', status=403)

handler403 = custom_permission_denied_view

urlpatterns = [
    # Reservation selection page (homepage)
    path('', views.reservation_selection, name='reservation_selection'),  

    # Dashboard page for logged-in users (customer dashboard)
    path('my-dashboard/', views.dashboard, name='dashboard'), 

    # Reservation form for users to make a reservation
    path('reservation/', views.reservation_form, name='reservation_form'),

    # List of reservations for logged-in users
    path('reservation/create/', views.create_reservation, name='create_reservation'),

    # Staff dashboard page for staff users
    path(
        'staff/dashboard/',
        views.StaffReservationListView.as_view(),
        name='staff_dashboard'
    ), 

    # Staff reservation management page to manage reservations
    path('staff/reservations/', views.staff_reservation_management, name='staff_reservation_management'),

    # Unavailable dates endpoint for AJAX calendar functionality
    path('unavailable-dates/', views.unavailable_dates, name='unavailable_dates'),

    # Allauth URLs for authentication
    path('accounts/', include('allauth.urls')),  # Includes login, logout, signup, password reset, etc.
]



USED BEFORE

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



-----------------------------------------------------------------------------------------------------------------------

views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.timezone import datetime
from django.http import JsonResponse
from .models import Reservation, Boat
from .forms import ReservationForm


# Predefined time slots
TIME_SLOTS = ['10-12', '12-14', '14-16', '16-18', '18-20', '20-22']

# ---------------------------------
# General Helper Functions
# ---------------------------------

def get_available_time_slots(booking_date):
    """Helper function to check available time slots for a given date."""
    available_time_slots = {}
    boats = Boat.objects.all()

    for time_slot in TIME_SLOTS:
        reservations_at_slot = Reservation.objects.filter(booking_date=booking_date, time_slot=time_slot)
        available_boats = len([boat for boat in boats if all(reservation.boat != boat for reservation in reservations_at_slot)])
        available_time_slots[time_slot] = available_boats

    return available_time_slots

def get_available_boats(booking_date, time_slot, number_of_guests):
    """Helper function to filter available boats based on date, time slot, and guest count."""
    boats = Boat.objects.filter(capacity__gte=number_of_guests)
    reservations_at_slot = Reservation.objects.filter(booking_date=booking_date, time_slot=time_slot)
    return [boat for boat in boats if all(reservation.boat != boat for reservation in reservations_at_slot)]

# ---------------------------------
# Views for Customers
# ---------------------------------

@login_required
def reservation_form(request):
    """Handles creating a reservation."""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            booking_date_time = form.cleaned_data['booking_date_time']
            number_of_guests = form.cleaned_data['number_of_guests']

            # Extract date and time from the combined field
            booking_date = booking_date_time.date()
            time_slot = booking_date_time.time()

            available_boats = get_available_boats(booking_date, time_slot, number_of_guests)

            if not available_boats:
                return render(request, 'reservations/reservation_form.html', {
                    'form': form,
                    'error': 'No available boats for the selected date and time slot.',
                    'available_time_slots': get_available_time_slots(booking_date),
                })

            # Save the reservation
            reservation = form.save(commit=False)
            reservation.user = request.user  # Associate the reservation with the logged-in user
            reservation.boat = available_boats[0]  # Assign the first available boat
            reservation.save()
            return redirect('dashboard')

    else:
        form = ReservationForm()

    return render(request, 'reservations/reservation_form.html', {
        'form': form,
        'available_time_slots': get_available_time_slots(datetime.today().date()),
    })


@login_required
def dashboard(request):
    """Displays reservations for the logged-in user."""
    reservations = Reservation.objects.filter(user=request.user)
    return render(request, 'reservations/my_dashboard.html', {'reservations': reservations})

# ---------------------------------
# Views for Staff
# ---------------------------------

class StaffReservationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Displays all reservations for staff users."""
    model = Reservation
    template_name = 'reservations/staff_dashboard.html'
    context_object_name = 'reservations'

    def get_queryset(self):
        return Reservation.objects.all()

    def test_func(self):
        return self.request.user.is_staff
    
@login_required
def staff_reservation_management(request):
    """View to manage reservations for staff."""
    if not request.user.is_staff:
        return redirect('permission_denied')  # Redirect to permission denied page if not staff

    reservations = Reservation.objects.all()  # Fetch all reservations or filter as needed
    return render(request, 'reservations/staff_reservation_management.html', {
        'reservations': reservations,
    })

# ---------------------------------
# AJAX for Calendar Validation
# ---------------------------------

def unavailable_dates(request):
    """Returns unavailable dates for the calendar in JSON format."""
    reservations = Reservation.objects.values_list('booking_date', flat=True)
    unavailable_dates = list(set(reservations))  # Unique list of unavailable dates
    return JsonResponse({'unavailable_dates': unavailable_dates})

# ---------------------------------
# CRUD Handling for Reservations
# ---------------------------------

# Create reservation using function-based view
@login_required
def create_reservation(request):
    """Handles creating a reservation."""
    if request.method == "POST":
        form = ReservationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('reservation_list')
    else:
        form = ReservationForm()
    return render(request, 'reservations/reservation_form.html', {'form': form})

# Update reservation using class-based view
class ReservationUpdateView(LoginRequiredMixin, UpdateView):
    """Handles updating a reservation."""
    model = Reservation
    form_class = ReservationForm
    template_name = 'reservations/reservation_form.html'

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

# Delete reservation using class-based view
class ReservationDeleteView(LoginRequiredMixin, DeleteView):
    """Handles deleting a reservation."""
    model = Reservation
    template_name = 'reservations/reservation_confirm_delete.html'
    success_url = '/dashboard/'

# ---------------------------------
# Reservation Selection for Staff
# ---------------------------------

@login_required
def reservation_selection(request):
    """Handles reservation selection logic for staff."""
    return render(request, 'reservations/reservation_selection.html')












USED BEFORE


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


-----------------------------------------------------------------------------------------------------------------------



models.py


from datetime import timedelta, datetime, date
from django.utils.timezone import make_aware
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

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
    


# Define the choices globally
TIME_SLOT_CHOICES = [
    ('10-12', '10:00 - 12:00'),
    ('12-14', '12:00 - 14:00'),
    ('14-16', '14:00 - 16:00'),
    ('16-18', '16:00 - 18:00'),
    ('18-20', '18:00 - 20:00'),
    ('20-22', '20:00 - 22:00'),
]

class Reservation(models.Model):
    """
    The Reservation model represents a booking made by a user for a specific boat.
    It stores the user who made the reservation, the boat being reserved, the booking date, 
    the time slot, and the number of guests. It also includes an optional discount field.
    The model ensures that the number of guests is between 4 and 20 through the clean method.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    booking_date = models.DateField()
    time_slot = models.CharField(max_length=5, choices=TIME_SLOT_CHOICES)
    boat = models.ForeignKey(Boat, on_delete=models.CASCADE)  
    booking_date = models.DateField()  
    models.CharField(max_length=5, choices=TIME_SLOT_CHOICES)
    number_of_guests = models.IntegerField() 
    has_discount = models.BooleanField(default=False, null=True, blank=True) 
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
            
    def save(self, *args, **kwargs):
        """Overrides the save method to validate before saving."""
        self.clean()
        super().save(*args, **kwargs)




-----------------------------------------------------------------------------------------------------------------------



forms.py


from django import forms
from .models import Reservation
from django.contrib.auth.models import User

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['booking_date', 'time_slot', 'number_of_guests']

    number_of_guests = forms.IntegerField(
        min_value=4,
        max_value=20,
        widget=forms.NumberInput(attrs={'min': 4, 'max': 20}),
    )

    def clean(self):
        cleaned_data = super().clean()
        booking_date_time = cleaned_data.get('booking_date_time')
        guests = cleaned_data.get('number_of_guests')

        # Split the date and time from the combined datetime field
        booking_date = booking_date_time.date()
        time_slot = booking_date_time.time()

        # Validate boat availability
        if not Reservation.check_availability(booking_date, time_slot, guests):
            raise forms.ValidationError(
                f"Selected time slot {time_slot} is not available for {guests} guests."
            )

        return cleaned_data






# Used previously
"""from django import forms
from .models import Reservation, Boat
from django.contrib.auth.models import User

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['boat', 'booking_date', 'time_slot', 'number_of_guests']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = kwargs.get('instance').user if 'instance' in kwargs else None
        
        # Fetch user's details if available
        if user:
            self.fields['first_name'] = forms.CharField(initial=user.first_name, required=True)
            self.fields['last_name'] = forms.CharField(initial=user.last_name, required=True)
            self.fields['phone_number'] = forms.CharField(initial=user.profile.phone_number if hasattr(user, 'profile') else '', required=True)
            self.fields['email'] = forms.EmailField(initial=user.email, required=True)
        else:
            self.fields['first_name'] = forms.CharField(required=True)
            self.fields['last_name'] = forms.CharField(required=True)
            self.fields['phone_number'] = forms.CharField(required=True)
            self.fields['email'] = forms.EmailField(required=True)

    def clean_booking_date(self):
        booking_date = self.cleaned_data.get('booking_date')
        if booking_date < datetime.date.today():
            raise forms.ValidationError("Booking date cannot be in the past.")
        return booking_date

    def clean_number_of_guests(self):
        num_guests = self.cleaned_data.get('number_of_guests')
        if not 4 <= num_guests <= 20:
            raise forms.ValidationError("Number of guests must be between 4 and 20.")
        return num_guests

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        time_slot = cleaned_data.get('time_slot')
        number_of_guests = cleaned_data.get('number_of_guests')

        # Validate available boats
        available_boats = Boat.objects.filter(
            capacity__gte=number_of_guests
        )

        if not available_boats:
            raise forms.ValidationError("No boats available for the number of guests selected.")
        
        # Check availability of the selected boat and time slot
        for boat in available_boats:
            conflicting_reservation = Reservation.objects.filter(
                boat=boat,
                booking_date=booking_date,
                time_slot=time_slot
            )
            if conflicting_reservation.exists():
                raise forms.ValidationError(f"Boat {boat.name} is already booked for this time slot.")

        return cleaned_data"""""




-----------------------------------------------------------------------------------------------------------------------

admin.py


from django.contrib import admin
from .models import Boat, Reservation

@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    """
    Customize the admin interface for the Boat model.
    """
    list_display = ('name', 'capacity')
    search_fields = ('name',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Customize the admin interface for the Reservation model.
    """
    list_display = ('user', 'user_email', 'boat', 'booking_date', 'time_slot', 'number_of_guests', 'has_discount')
    list_filter = ('booking_date', 'boat')
    search_fields = ('user__username', 'boat__name', 'user__email')  # Add email to search fields
    ordering = ('booking_date', 'time_slot')
    date_hierarchy = 'booking_date'

    # This method will display the user's email in the admin
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

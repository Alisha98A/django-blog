models.py


from datetime import timedelta, datetime, date
from django.utils.timezone import make_aware
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, EmailValidator
from django.urls import reverse


class Reservation(models.Model):
    """
    The Reservation model represents a booking made by a user.
    It stores details like booking date, time slot, number of guests, and contact information.
    The model ensures guest limits, time slot validation, and prevents overlapping bookings.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    staff_member = models.ForeignKey(User, related_name='staff_reservations', null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservations_created")
    booking_date = models.DateField()  
    time_slot = models.TimeField()  
    number_of_guests = models.IntegerField() 
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)   
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    email_address = models.EmailField(validators=[EmailValidator()])
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reservation for {self.user.username} on {self.booking_date}"

    def clean(self):
        """Validates the reservation details, including time slots, guest limits, and overlaps."""
        today = date.today()

        # **Booking Date Validation**
        if not self.booking_date:
            raise ValidationError("Booking date is required.")

        if self.booking_date < today:
            raise ValidationError("Booking date cannot be in the past.")
        
        if self.booking_date < today + timedelta(days=2):
            raise ValidationError("Bookings must be made at least 2 days in advance.")

        # Validate time slot is within allowed hours
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
            booking_date=self.booking_date,
        ).exclude(id=self.id)

        for reservation in overlapping_reservations:
            existing_start = make_aware(datetime.combine(reservation.booking_date, reservation.time_slot))
            existing_end = existing_start + timedelta(hours=2)
            if start_time < existing_end and end_time > existing_start:
                raise ValidationError(
                    f"The boat is already booked from {existing_start.time()} to {existing_end.time()}."
                )

    def save(self, *args, **kwargs):
        """Ensures validation runs before saving."""
        self.clean()
        super().save(*args, **kwargs)






forms.py


from django import forms
from .models import Reservation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class BaseReservationForm(forms.ModelForm):
    """Base form for reservations with shared fields."""
    
    booking_date = forms.DateField(
        required=True, 
        widget=forms.DateInput(attrs={'type': 'date', 'required': True}),
        error_messages={"required": "Please select a booking date."}
    )

    TIME_SLOTS = [
        ('10-12', '10:00 - 12:00'), ('12-14', '12:00 - 14:00'),
        ('14-16', '14:00 - 16:00'), ('16-18', '16:00 - 18:00'),
        ('18-20', '18:00 - 20:00'), ('20-22', '20:00 - 22:00'),
    ]

    time_slot = forms.ChoiceField(choices=TIME_SLOTS, required=True)
    
    number_of_guests = forms.ChoiceField(
        choices=[(str(i), str(i)) for i in range(4, 21)], required=True
    )

    class Meta:
        model = Reservation
        fields = ['booking_date', 'time_slot', 'number_of_guests', 
                  'first_name', 'last_name', 'phone_number', 'email_address']


class ReservationFormForUser(BaseReservationForm):
    """Form for regular users - Excludes 'user' field"""
    pass


class ReservationFormForStaff(BaseReservationForm):
    """Form for staff - Allows assigning bookings to other users"""
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=False),
        required=True,
        label="Guest User",
        error_messages={'required': 'Please select a user for the reservation.'}
    )

    class Meta(BaseReservationForm.Meta):
        fields = ['user'] + BaseReservationForm.Meta.fields




views.py

from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from .models import Reservation
from .forms import ReservationFormForUser, ReservationFormForStaff

@login_required
def reservation_view(request):
    if request.user.is_staff:
        form = ReservationFormForStaff(request.POST or None)
    else:
        form = ReservationFormForUser(request.POST or None)
    
    if request.method == 'POST':
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.save()
            messages.success(request, "Reservation successfully created!")
            return redirect('reservation_success')
        else:
            messages.error(request, "Please correct the errors below.")
    
    return render(request, 'reservation_form.html', {'form': form, 'user_type': 'staff' if request.user.is_staff else 'guest'})


def reservation_success(request):
    return render(request, 'reservation_success.html')


class ReservationListView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = "reservation_list.html"
    context_object_name = "reservations"

    def get_queryset(self):
        if self.request.user.is_staff:
            return Reservation.objects.all().order_by("booking_date", "time_slot")
        else:
            return Reservation.objects.filter(user=self.request.user).order_by("booking_date")


class StaffDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Reservation
    template_name = "staff_dashboard.html"
    context_object_name = "reservations"

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access this page.")
        return redirect("reservation_list")

    def get_queryset(self):
        return Reservation.objects.all().order_by("booking_date")


class ReservationCreateView(LoginRequiredMixin, CreateView):
    model = Reservation
    template_name = "reservations/reservation_form.html"
    success_url = reverse_lazy("reservation_list")

    def get_form_class(self):
        return ReservationFormForStaff if self.request.user.is_staff else ReservationFormForUser

    def form_invalid(self, form):
        messages.error(self.request, "There were errors in your submission. Please check your inputs.")
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        if self.request.user.is_staff and not form.cleaned_data.get("user"):
            messages.error(self.request, "You have to choose a user for the reservation.")
            return self.form_invalid(form)
        if not self.request.user.is_staff:
            form.instance.user = self.request.user
        messages.success(self.request, "Reservation successfully created!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('reservations:reservations_list')


class ReservationUpdateView(LoginRequiredMixin, UpdateView):
    model = Reservation
    template_name = "reservations/reservation_edit_form.html"

    def get_form_class(self):
        return ReservationFormForStaff if self.request.user.is_staff else ReservationFormForUser

    def form_valid(self, form):
        # Ensure user field is always set
        if not self.request.user.is_staff:
            form.instance.user = self.request.user  # Normal users can only update their own reservation

        if self.request.user.is_staff and not form.cleaned_data.get("user"):
            messages.error(self.request, "Staff must select a user for the reservation.")
            return self.form_invalid(form)

        messages.success(self.request, "Your reservation has been successfully updated!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('reservations:reservations_list')


class ReservationDeleteView(DeleteView):
    model = Reservation
    template_name = "reservations/reservation_confirm_delete.html"
    success_url = reverse_lazy("reservations:reservations_list")





decorators.py

from django.http import HttpResponseForbidden
from functools import wraps

def staff_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("You do not have permission to view this page.")
    return _wrapped_view

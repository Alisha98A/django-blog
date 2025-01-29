updated forms.py that works (29/1 kl 17)

from django import forms
from .models import Reservation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class ReservationFormForUser(forms.ModelForm):
    """Form for regular users - Excludes 'user' field"""
    
    booking_date = forms.DateField(
        required=True, 
        widget=forms.DateInput(attrs={'type': 'date', 'required': True}),
        error_messages={"required": "Please select a booking date."}
    )

    time_slot = forms.ChoiceField(choices=[
        ('10-12', '10:00 - 12:00'), ('12-14', '12:00 - 14:00'),
        ('14-16', '14:00 - 16:00'), ('16-18', '16:00 - 18:00'),
        ('18-20', '18:00 - 20:00'), ('20-22', '20:00 - 22:00'),
    ], required=True)
    
    number_of_guests = forms.ChoiceField(choices=[(str(i), str(i)) for i in range(4, 21)], required=True)
    
    class Meta:
        model = Reservation
        fields = ['booking_date', 'time_slot', 'number_of_guests', 'first_name', 'last_name', 'phone_number', 'email_address']


class ReservationFormForStaff(forms.ModelForm):
    """Form for staff - Allows assigning bookings to other users"""
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=False),
        required=True,
        label="Guest User",
        error_messages={'required': 'Please select a user for the reservation.'}
    )

    booking_date = forms.DateField(
        required=True, 
        widget=forms.DateInput(attrs={'type': 'date', 'required': True}),
        error_messages={"required": "Please select a booking date."}
    )

    time_slot = forms.ChoiceField(choices=[
        ('10-12', '10:00 - 12:00'), ('12-14', '12:00 - 14:00'),
        ('14-16', '14:00 - 16:00'), ('16-18', '16:00 - 18:00'),
        ('18-20', '18:00 - 20:00'), ('20-22', '20:00 - 22:00'),
    ], required=True)
    
    number_of_guests = forms.ChoiceField(choices=[(str(i), str(i)) for i in range(4, 21)], required=True)
    
    class Meta:
        model = Reservation
        fields = ['user', 'booking_date', 'time_slot', 'number_of_guests', 'first_name', 'last_name', 'phone_number', 'email_address']













forms.py

from django import forms
from .models import Reservation
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

#First code
"""class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['booking_date', 'time_slot', 'number_of_guests', 'first_name', 'last_name', 'phone_number', 'email_address']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date'}),
            'time_slot': forms.TimeInput(attrs={'type': 'time'}),
        }
"""


class ReservationFormForUser(forms.ModelForm):
    """Form for regular users - Excludes 'user' field"""
    
    time_slot = forms.ChoiceField(choices=[
        ('10-12', '10:00 - 12:00'), ('12-14', '12:00 - 14:00'),
        ('14-16', '14:00 - 16:00'), ('16-18', '16:00 - 18:00'),
        ('18-20', '18:00 - 20:00'), ('20-22', '20:00 - 22:00'),
    ], required=True)

    number_of_guests = forms.ChoiceField(choices=[(str(i), str(i)) for i in range(4, 21)], required=True)

    class Meta:
        model = Reservation
        fields = ['booking_date', 'time_slot', 'number_of_guests', 'first_name', 'last_name', 'phone_number', 'email_address']


class ReservationFormForStaff(forms.ModelForm):
    """Form for staff - Allows assigning bookings to other users"""
    
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=False), required=False, label="Guest User")

    class Meta:
        model = Reservation
        fields = ['user', 'booking_date', 'time_slot', 'number_of_guests', 'first_name', 'last_name', 'phone_number', 'email_address']



""""
class ReservationForm(forms.ModelForm):
    TIME_SLOT_CHOICES = [
        ('10-12', '10:00 - 12:00'),
        ('12-14', '12:00 - 14:00'),
        ('14-16', '14:00 - 16:00'),
        ('16-18', '16:00 - 18:00'),
        ('18-20', '18:00 - 20:00'),
        ('20-22', '20:00 - 22:00'),
    ]

    GUEST_CHOICES = [(str(i), str(i)) for i in range(4, 21)]  

    time_slot = forms.ChoiceField(choices=TIME_SLOT_CHOICES, required=True)
    number_of_guests = forms.ChoiceField(choices=GUEST_CHOICES, required=True)
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=False), required=False, label="Guest User")

    class Meta:
        model = Reservation
        fields = ['booking_date', 'time_slot', 'number_of_guests', 'first_name', 'last_name', 'phone_number', 'email_address']

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user

        if self.current_user and self.current_user.is_staff:
            self.fields['user'].queryset = User.objects.filter(is_staff=False)
        elif not self.current_user:
            # Fallback: Log and debug instead of erroring out
            import logging
            logging.warning("current_user is None in ReservationForm.")"""









views.py



from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from .models import Reservation
# from .forms import ReservationForm
from django.views.generic.list import ListView
from django.views.generic import CreateView, ListView
from django.views.generic.edit import CreateView
from .forms import ReservationFormForUser, ReservationFormForStaff

from django.shortcuts import redirect



# ---------------------------------
# View and Create Reservation
# ---------------------------------

@login_required
def reservation_view(request):
    if request.user.is_staff:
        # Staff members can make reservations for themselves or on behalf of others
        print(f"Logged in as staff: {request.user.username}")
        form = ReservationForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.save()
            return redirect('reservation_success')
        return render(request, 'reservation_form.html', {'form': form, 'user_type': 'staff'})

    else:
        # Guests can only make reservations for themselves
        print(f"Logged in as guest: {request.user.username}")
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

class ReservationListView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = "reservation_list.html"
    context_object_name = "reservations"

    def get_queryset(self):
        """Return reservations based on user type."""
        if self.request.user.is_staff:
            # Staff members see all reservations
            return Reservation.objects.all().order_by("booking_date", "time_slot")
        else:
            # Regular users see only their reservations
            return Reservation.objects.filter(user=self.request.user).order_by("booking_date")
        
# ---------------------------------
# Staff Dashboard View
# ---------------------------------

class StaffDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Reservation
    template_name = "staff_dashboard.html"
    context_object_name = "reservations"

    def test_func(self):
        """Ensure the user is a staff member."""
        return self.request.user.is_staff

    def handle_no_permission(self):
        """Redirect non-staff users to the reservation list."""
        messages.error(self.request, "You do not have permission to access this page.")
        return redirect("reservation_list")

    def get_queryset(self):
        """Show all reservations for staff."""
        return Reservation.objects.all().order_by("booking_date")
    
# ---------------------------------
# Create
# ---------------------------------
from django.contrib import messages
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .models import Reservation
from .forms import ReservationFormForUser, ReservationFormForStaff  

class ReservationCreateView(CreateView):
    model = Reservation
    template_name = "reservations/reservation_form.html"
    success_url = reverse_lazy("reservation_list")

    def get_form_class(self):
        if self.request.user.is_staff:
            return ReservationFormForStaff
        return ReservationFormForUser

    def form_valid(self, form):
        if self.request.user.is_staff and not form.cleaned_data.get("user"):
            messages.error(self.request, "You have to choose a user for the reservation.")
            return self.render_to_response(self.get_context_data(form=form))
        
        if not self.request.user.is_staff:
            form.instance.user = self.request.user

        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('reservations:reservations_list')
    

    
# First code that worked 
"""class ReservationCreateView(LoginRequiredMixin, CreateView):
    model = Reservation
    template_name = 'reservations/reservation_form.html'

    def get_form_class(self):
        #Use different forms for staff and normal users
        if self.request.user.is_staff:
            return ReservationFormForStaff
        return ReservationFormForUser

    def form_valid(self, form):
        reservation = form.save(commit=False)
        if not self.request.user.is_staff:
            reservation.user = self.request.user  # Normal users can only book for themselves
        reservation.save()
        messages.success(self.request, "Reservation successfully created!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('reservations:reservations_list')"""

# First code
"""""
class ReservationCreateView(LoginRequiredMixin, CreateView):
    model = Reservation
    form_class = ReservationForm 
    template_name = 'reservations/reservation_form.html'

    def get_success_url(self):
        return reverse('reservations:reservations_list')

    def form_valid(self, form):
        # Assign the logged-in user to the reservation instance
        form.instance.user = self.request.user
        form.instance.created_by = self.request.user  # who created the reservation
        if self.request.user.is_staff:
            # If the staff member creates this reservation, save their info as well
            form.instance.staff_member = self.request.user
        return super().form_valid(form)"""

# ---------------------------------
# Update
# ---------------------------------
class ReservationUpdateView(LoginRequiredMixin, UpdateView):
    model = Reservation
    template_name = "reservations/reservation_edit_form.html"

    def get_form_class(self):
        """Use different forms for staff and normal users"""
        if self.request.user.is_staff:
            return ReservationFormForStaff
        return ReservationFormForUser

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your reservation has been successfully updated!")
        return response

    def get_success_url(self):
        return reverse_lazy('reservations:reservations_list')
    
""""   
class ReservationUpdateView(UpdateView):
    model = Reservation
    template_name = "reservations/reservation_edit_form.html"
    form_class = ReservationForm 
    
    success_url = reverse_lazy('reservations:reservations_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Add a success message
        messages.success(self.request, "Your reservation has been successfully updated!")
        
        return response"""
    
# ---------------------------------
# Delete
# ---------------------------------

class ReservationDeleteView(DeleteView):
    model = Reservation
    template_name = "reservations/reservation_confirm_delete.html"
    success_url = reverse_lazy("reservations:reservations_list")

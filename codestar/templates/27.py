views.py


from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Reservation
from .forms import ReservationForm
from django.urls import reverse
from django.views.generic.list import ListView
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.views.generic import CreateView, ListView
from django.views.generic.edit import CreateView
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator

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
    fields = ['booking_date', 'time_slot', 'number_of_guests', 'first_name', 'last_name', 'phone_number', 'email_address']
    template_name = 'reservations/reservation_form.html' 

    def form_valid(self, form):
        # Assign the logged-in user to the reservation instance
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('reservations:reservations_list') 

# ---------------------------------
# Update
# ---------------------------------
    

class ReservationUpdateView(UpdateView):
    model = Reservation
    template_name = "reservations/reservation_edit_form.html"
    fields = ['booking_date', 'time_slot', 'number_of_guests', 'first_name', 'last_name', 'phone_number', 'email_address']
    
    success_url = reverse_lazy('reservations:reservations_list')

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
    template_name = "reservations/reservation_confirm_delete.html"
    success_url = reverse_lazy("reservations:reservations_list")



forms.py

from django import forms
from .models import Boat, Reservation
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model


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


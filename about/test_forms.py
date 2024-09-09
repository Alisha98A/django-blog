from django.test import TestCase
from .forms import CollaborateForm


class TestCollaborateForm(TestCase):

    def test_form_is_valid(self):
        form_data = {'name': 'John Doe', 'email': 'john@example.com', 'message': 'This is a collaboration request'}
        form = CollaborateForm(form_data)
        self.assertTrue(form.is_valid())
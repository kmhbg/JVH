from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, PuzzleOwnership, Friendship, PuzzleImage

class PuzzleSearchForm(forms.Form):
    search = forms.CharField(required=False, label='Sök pussel')

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone']

class PuzzleOwnershipForm(forms.ModelForm):
    class Meta:
        model = PuzzleOwnership
        fields = ['missing_pieces', 'notes', 'borrowed_by', 'borrowed_date', 'return_date']
        widgets = {
            'borrowed_date': forms.DateInput(attrs={'type': 'date'}),
            'return_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'missing_pieces': forms.NumberInput(attrs={'min': 0}),
        }
        labels = {
            'missing_pieces': 'Antal saknade bitar',
            'notes': 'Anteckningar',
            'borrowed_by': 'Utlånat till',
            'borrowed_date': 'Utlåningsdatum',
            'return_date': 'Återlämningsdatum'
        }

class FriendRequestForm(forms.Form):
    username = forms.CharField(max_length=150)

class PuzzleBorrowForm(forms.ModelForm):
    class Meta:
        model = PuzzleOwnership
        fields = ['borrowed_by', 'borrowed_date']
        widgets = {
            'borrowed_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'borrowed_by': 'Utlånad till',
            'borrowed_date': 'Utlåningsdatum',
        }

class PuzzleImageUploadForm(forms.ModelForm):
    class Meta:
        model = PuzzleImage
        fields = ['image']
        labels = {
            'image': 'Välj bild',
        } 
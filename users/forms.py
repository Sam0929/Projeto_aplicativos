from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import Profile


class RegisterForm(UserCreationForm):

    first_name = forms.CharField(max_length=100, required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'}))
    username = forms.CharField(max_length=100, required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'}))
    
    age = forms.IntegerField(required=True,
                              widget=forms.NumberInput(attrs={'placeholder': 'Age', 'class': 'form-control'}))
    weight = forms.IntegerField(required=True,
                                 widget=forms.NumberInput(attrs={'placeholder': 'Weight (kg)', 'class': 'form-control'}))
    date_of_birth = forms.DateField(required=True,
                                    widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    email = forms.EmailField(required=True,
                             widget=forms.TextInput(attrs={'placeholder': 'Email', 'class': 'form-control'}))
    password1 = forms.CharField(max_length=50, required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}))
    password2 = forms.CharField(max_length=50, required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}))

    

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'age', 'weight', 'date_of_birth', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()  
            user.profile.age = self.cleaned_data['age']
            user.profile.weight = self.cleaned_data['weight']
            user.profile.date_of_birth = self.cleaned_data['date_of_birth']
            user.profile.save()
            
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Username',
                                                             'class': 'form-control',
                                                             }))
    password = forms.CharField(max_length=50,
                               required=True,
                               widget=forms.PasswordInput(attrs={'placeholder': 'Password',
                                                                 'class': 'form-control',
                                                                 'data-toggle': 'password',
                                                                 'id': 'password',
                                                                 'name': 'password',
                                                                 }))
    remember_me = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


class UpdateUserForm(forms.ModelForm):
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email']


class UpdateProfileForm(forms.ModelForm):
    avatar = forms.ImageField(widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}))

    class Meta:
        model = Profile
        fields = ['avatar', 'bio']

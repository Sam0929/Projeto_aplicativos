# users/forms.py

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Profile

# --------------------------------------------------
# FORMULÁRIO DE CADASTRO (USER + PROFILE)
# --------------------------------------------------
class RegisterForm(UserCreationForm):
    # Campos do User
    first_name = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'placeholder':'Primeiro nome','class':'form-control'})
    )
    last_name = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'placeholder':'Sobrenome','class':'form-control'})
    )
    username = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'placeholder':'Username','class':'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder':'Email','class':'form-control'})
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder':'Senha','class':'form-control'})
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder':'Confirmar senha','class':'form-control'})
    )

    # Campos do Profile
    age = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'placeholder':'Idade','class':'form-control'})
    )
    weight = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={'placeholder':'Peso (kg)','class':'form-control','step':'0.1'})
    )
    height = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={'placeholder':'Altura (cm)','class':'form-control','step':'0.1'})
    )
    experience_years = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={'placeholder':'Anos de experiência','class':'form-control','step':'0.1'})
    )

    class Meta:
        model = User
        fields = [
            'first_name','last_name','username','email',
            'password1','password2',
            'age','weight','height','experience_years'
        ]

    def save(self, commit=True):
        # salva o User
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        user.email      = self.cleaned_data['email']
        if commit:
            user.save()
            # salva o Profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.age               = self.cleaned_data['age']
            profile.weight            = self.cleaned_data['weight']
            profile.height            = self.cleaned_data['height']
            profile.experience_years  = self.cleaned_data['experience_years']
            profile.save()
        return user


# --------------------------------------------------
# LOGIN COM REMEMBER ME
# --------------------------------------------------
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder':'Username','class':'form-control'})
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder':'Password','class':'form-control'})
    )
    remember_me = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ['username','password','remember_me']


# --------------------------------------------------
# ATUALIZAÇÃO DO USER BÁSICO
# --------------------------------------------------
class UpdateUserForm(forms.ModelForm):
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class':'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class':'form-control'})
    )

    class Meta:
        model = User
        fields = ['username','email']


# --------------------------------------------------
# ATUALIZAÇÃO DO PROFILE
# --------------------------------------------------
class UpdateProfileForm(forms.ModelForm):
    # Básicos
    age = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class':'form-control'}))
    weight = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'class':'form-control','step':'0.1'}))
    height = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'class':'form-control','step':'0.1'}))
    experience_years = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'class':'form-control','step':'0.1'}))

    # Mídias
    avatar = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class':'form-control-file'}))
    cover_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class':'form-control-file'}))

    # Rede social
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'class':'form-control','rows':3}))
    location = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control'}))
    gender = forms.ChoiceField(
        required=False,
        choices=[('','---------')] + Profile._meta.get_field('gender').choices,
        widget=forms.Select(attrs={'class':'form-control'})
    )
    relationship_status = forms.ChoiceField(
        required=False,
        choices=[('','---------')] + Profile._meta.get_field('relationship_status').choices,
        widget=forms.Select(attrs={'class':'form-control'})
    )
    interests = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control'}))

    # Privacidade
    show_age = forms.BooleanField(required=False)
    show_weight = forms.BooleanField(required=False)
    show_height = forms.BooleanField(required=False)
    show_experience = forms.BooleanField(required=False)

    class Meta:
        model = Profile
        fields = [
            'age','weight','height','experience_years',
            'avatar','cover_photo','bio','location','gender',
            'relationship_status','interests',
            'show_age','show_weight','show_height','show_experience'
        ]

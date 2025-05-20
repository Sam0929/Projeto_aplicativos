from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.contrib.auth import get_user_model


User = get_user_model()

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Campos existentes
    age = models.IntegerField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(default='default.png', upload_to='profile_images')
    bio = models.TextField(null=True, blank=True)

    # Novos campos “rede social”
    cover_photo = models.ImageField(
        upload_to='cover_images',
        default='cover_default.jpg',
        blank=True, null=True
    )
    location = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(
        max_length=1,
        choices=[('M','Masculino'),('F','Feminino'),('O','Outro')],
        blank=True, null=True
    )
    relationship_status = models.CharField(
        max_length=20,
        choices=[
            ('single','Solteiro(a)'),
            ('relationship','Em um relacionamento'),
            ('married','Casado(a)')
        ],
        blank=True, null=True
    )
    interests = models.CharField(
        max_length=200, blank=True, null=True,
        help_text='Separe por vírgula'
    )

    # Campos de academia
    height = models.FloatField(null=True, blank=True, help_text="Altura em cm")
    training_time = models.DurationField(
        null=True, blank=True,
        help_text="Duração média do treino (HH:MM:SS)"
    )
    experience_years = models.FloatField(
        null=True, blank=True,
        help_text="Anos de experiência"
    )

    # Flags de privacidade
    show_age = models.BooleanField(default=True)
    show_weight = models.BooleanField(default=True)
    show_height = models.BooleanField(default=True)
    show_training_time = models.BooleanField(default=True)
    show_experience = models.BooleanField(default=True)

    # timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True,     null=True)

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # redimensiona avatar
        img = Image.open(self.avatar.path)
        if img.height > 100 or img.width > 100:
            img.thumbnail((100, 100))
            img.save(self.avatar.path)
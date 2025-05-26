
from django.contrib import admin
from django.urls import path, include
from users.views import CustomLoginView, ResetPasswordView, ChangePasswordView, home
from users.forms import LoginForm
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', home, name='home'),  

    path('treinos/', include('treinos.urls', namespace='treinos')),
    path('amizades/', include('amizades.urls', namespace='amizades')),
    path('users/', include('users.urls', namespace='users')),

    path('login/', CustomLoginView.as_view(
        redirect_authenticated_user=True,
        template_name='users/login.html',
        authentication_form=LoginForm
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('password-reset/', ResetPasswordView.as_view(), name='password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
         name='password_reset_complete'),
    path('password-change/', ChangePasswordView.as_view(), name='password_change'),

    re_path(r'^oauth/', include('social_django.urls', namespace='social')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

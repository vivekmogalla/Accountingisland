from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, \
    PasswordResetConfirmView, PasswordResetCompleteView
from .forms import SignUpForm, LoginForm, CustomPasswordResetForm
from django.views import View
from django.contrib.auth import get_user_model
# Create your views here.


def generate_activation_token(user):
    # Generate activation token with timestamp
    timestamp = timezone.now() + timezone.timedelta(days=1)
    token = account_activation_token.make_token(user) + str(int(timestamp.timestamp()))
    return token


@method_decorator(csrf_protect, name='dispatch')
class SignupPageView(FormView):
    form_class = SignUpForm
    template_name = 'users/signup.html'

    def form_valid(self, form):
        # if model form validation is success, then follow below steps

        email = form.cleaned_data['email']
        user = form.save(commit=False)
        user.is_active = False  # creating user in inactive state, user is not activated at this stage
        # user cannot log in until his account is activated
        user.save()

        # Generate activation token with timestamp
        uid = urlsafe_base64_encode(str(user.pk).encode())
        token = generate_activation_token(user)

        current_site = get_current_site(self.request)
        mail_subject = 'Active your Accounting game'
        message = render_to_string('users/acc_active_email.html',
                                   {'user': user,
                                    'domain': current_site.domain,
                                    'uid': uid,
                                    'token': token, })
        to_email = form.cleaned_data.get('email')
        email = EmailMessage(mail_subject, message, to=[to_email])
        email.send()

        return render(self.request, 'users/registration_confirmation.html', {})

    def form_invalid(self, form):
        # Your form_invalid logic here to handle the case when the form is invalid
        # For example, you can log errors or display error messages to the user
        # Handle form validation errors
        return super().form_invalid(form)

    def get(self, request, *args, **kwargs):
        # if logged-in user tries to signup again. it redirects to dashboard as he is already authenticated
        if request.user.is_authenticated:
            return redirect('dashboard')
            # return redirect('dashboard')  # Redirect to the dashboard or another page
        return super().get(request, *args, **kwargs)


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()  # bytes to string
        user = get_user_model().objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # if user is not None and account_activation_token.check_token(user, token):
    if user is not None:
        token_length = 49  # Length of the token generated by account_activation_token.make_token() +
        # timestamp
        # Ensure that the token length is as expected before extracting the timestamp
        if len(token) != token_length:  # Each hexadecimal character represents 4 bits
            return HttpResponse('Activation link is invalid!')

        # Extract token and timestamp from the activation link
        actual_token = token
        token, timestamp_str = token[:39], token[39:]
        token = token.strip()  # Remove any whitespace characters
        timestamp = int(timestamp_str)
        #
        try:
            # Convert hexadecimal timestamp string to an integer timestamp
            timestamp = int(timestamp_str)
        except ValueError:
            timestamp = 0

        if (account_activation_token.check_token(user, token)) \
                and (timestamp >= timezone.now().timestamp()):
            user.is_active = True
            user.save()
            messages.success(request, 'Thank you for your email confirmation. Now you can log in to your account')
            return redirect('login')
        elif not (timestamp >= timezone.now().timestamp()):
            # return HttpResponse('Activation link is invalid or has expired. ')
            message = 'Activation link is invalid or has expired'
            context = {'message': message}
            return render(request, 'users/user_activation.html', context)
        else:
            # return HttpResponse('Activation link is invalid or has expired. ')
            message = 'Activation link is invalid or has expired'
            context = {'message': message}
            return render(request, 'users/user_activation.html', context)

    else:
        message = 'User is None'
        return render(request, 'users/user_activation.html', {'message': message})


@method_decorator(csrf_protect, name='dispatch')
class LoginPageView(FormView):
    form_class = LoginForm
    template_name = 'users/login.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']

        user = authenticate(username=username, password=password)

        # check for inactive existing user in the database
        existing_user_false = get_user_model().objects.filter(username=username, is_active=False).first()

        if existing_user_false:
            messages.error(self.request, f"user- {existing_user_false} is already existed and not activated, "
                                         f"please check your registered mail and activate!")
            return self.form_invalid(form)

        elif user is not None:
            login(self.request, user)
            return super().form_valid(form)
        else:
            messages.error(self.request, f"Username or password is incorrect!")
            return self.form_invalid(form)


class LogoutView(LoginRequiredMixin, View):
    def get(self, request):
        logout(request)
        return redirect('login')


@method_decorator(csrf_protect, name='dispatch')
class CustomPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset.html'
    success_url = reverse_lazy('password_reset_done')
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'

    # Specify the custom form to use
    form_class = CustomPasswordResetForm


# CustomPasswordResetDoneView extends the built-in PasswordResetDoneView
class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


# CustomPasswordResetConfirmView extends the built-in PasswordResetConfirmView
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


# CustomPasswordResetCompleteView extends the built-in PasswordResetCompleteView
class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'





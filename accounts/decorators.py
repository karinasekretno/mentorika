from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from accounts.models import UserProfile
from accounts.utils import get_user_profile



_EMAIL_VERIFY_EXEMPT = frozenset({
    'verify_email_pending',
    'resend_verification_email',
})


def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile = get_user_profile(request.user)
        url_name = getattr(request.resolver_match, 'url_name', None)
        if not profile.email_verified and url_name not in _EMAIL_VERIFY_EXEMPT:
            return redirect('verify_email_pending')
        return view_func(request, *args, **kwargs)
    return wrapper


def onboarding_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile = get_user_profile(request.user)
        if not profile.onboarding_completed:
            if profile.role == UserProfile.ROLE_MENTEE:
                return redirect('onboarding_mentee')
            return redirect('mentor_cabinet')
        return view_func(request, *args, **kwargs)
    return wrapper

def mentor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile = get_user_profile(request.user)
        if profile.role != UserProfile.ROLE_MENTOR:
            messages.error(request, 'Этот раздел доступен только менторам.')
            return redirect('mentee_cabinet')
        return view_func(request, *args, **kwargs)
    return wrapper

def mentee_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile = get_user_profile(request.user)
        if profile.role != UserProfile.ROLE_MENTEE:
            messages.error(request, 'Этот раздел доступен только менти.')
            return redirect('mentor_cabinet')
        return view_func(request, *args, **kwargs)
    return wrapper


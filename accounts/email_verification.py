from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile

VERIFICATION_MAX_AGE = 60 * 60 * 24 * 3
RESEND_COOLDOWN = timedelta(seconds=60)
SIGNER_SALT = 'accounts.email-verify'


def build_verification_url(user, request):
    signer = TimestampSigner(salt=SIGNER_SALT)
    token = signer.sign(str(user.pk))
    return request.build_absolute_uri(reverse('verify_email', args=[token]))


def send_verification_email(user, request):
    verification_url = build_verification_url(user, request)
    subject = 'Подтвердите email — Менторика'
    message = (
        f'Здравствуйте, {user.first_name or user.email}!\n\n'
        'Спасибо за регистрацию в Менторике. '
        'Подтвердите адрес почты, чтобы пользоваться сервисом:\n\n'
        f'{verification_url}\n\n'
        'Ссылка действует 3 дня. Если вы не регистрировались, просто проигнорируйте это письмо.'
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    UserProfile.objects.filter(user=user).update(
        email_verification_sent_at=timezone.now(),
    )


def can_resend_verification(profile):
    if not profile.email_verification_sent_at:
        return True
    return timezone.now() - profile.email_verification_sent_at >= RESEND_COOLDOWN


def verify_email_token(token):
    signer = TimestampSigner(salt=SIGNER_SALT)
    user_id = signer.unsign(token, max_age=VERIFICATION_MAX_AGE)
    return int(user_id)

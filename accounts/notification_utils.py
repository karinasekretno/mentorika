import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from accounts.anketa_utils import mentee_profile_completion, mentor_profile_completion
from accounts.chat_utils import format_booking_datetime
from accounts.models import MenteeProfile, MentorProfile, Notification, SessionBooking, UserProfile

logger = logging.getLogger(__name__)


def _absolute_link(link):
    if not link:
        return ''
    if link.startswith('http://') or link.startswith('https://'):
        return link
    path = link if link.startswith('/') else f'/{link}'
    return f'{settings.SITE_URL}{path}'


def _send_notification_email(user, title, body, link=''):
    email = (user.email or '').strip()
    if not email:
        return

    greeting = user.first_name or email
    lines = [
        f'Здравствуйте, {greeting}!',
        '',
        body,
    ]
    absolute_link = _absolute_link(link)
    if absolute_link:
        lines.extend(['', f'Перейти: {absolute_link}'])
    lines.extend(['', '— Менторика'])

    try:
        send_mail(
            f'{title} — Менторика',
            '\n'.join(lines),
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Не удалось отправить уведомление на почту: user=%s', user.pk)


def _booking_datetime_text(booking):
    date_part, time_part = format_booking_datetime(booking.slot)
    return f'{date_part}, {time_part}'


def _mentee_cabinet_link():
    return reverse('mentee_cabinet')


def _mentor_cabinet_link():
    return reverse('mentor_cabinet')


def _notification_sent_within(user, kind, *, hours=24, booking=None):
    since = timezone.now() - timedelta(hours=hours)
    qs = Notification.objects.filter(user=user, kind=kind, created_at__gte=since)
    if booking is not None:
        qs = qs.filter(booking=booking)
    else:
        qs = qs.filter(booking__isnull=True)
    return qs.exists()


def create_notification(
    user,
    kind,
    title,
    body,
    link='',
    booking=None,
    dedupe_unread=False,
    dedupe_within_hours=None,
    send_email=True,
):
    if dedupe_within_hours is not None:
        if _notification_sent_within(user, kind, hours=dedupe_within_hours, booking=booking):
            return None
    if dedupe_unread:
        exists = Notification.objects.filter(
            user=user,
            kind=kind,
            booking=booking,
            is_read=False,
        ).exists()
        if exists:
            return None
    notification = Notification.objects.create(
        user=user,
        kind=kind,
        title=title,
        body=body,
        link=link,
        booking=booking,
    )
    if send_email:
        _send_notification_email(user, title, body, link)
    return notification


def notify_booking_created(booking):
    when = _booking_datetime_text(booking)
    mentor_name = booking.mentor.display_name
    mentee_name = booking.mentee.get_full_name() or booking.mentee.first_name or booking.mentee.email

    create_notification(
        booking.mentee,
        Notification.KIND_BOOKING_CREATED,
        'Вы записались на сессию',
        f'Запись к {mentor_name} на {when} подтверждена.',
        link=_mentee_cabinet_link(),
        booking=booking,
    )
    create_notification(
        booking.mentor.user,
        Notification.KIND_BOOKING_CREATED,
        'Новая запись',
        f'{mentee_name} записался на сессию {when}.',
        link=_mentor_cabinet_link(),
        booking=booking,
    )


def notify_booking_cancelled(booking, cancelled_by):
    when = _booking_datetime_text(booking)
    mentor_name = booking.mentor.display_name
    mentee_name = booking.mentee.get_full_name() or booking.mentee.first_name or booking.mentee.email

    if cancelled_by == 'mentee':
        create_notification(
            booking.mentor.user,
            Notification.KIND_BOOKING_CANCELLED,
            'Запись отменена',
            f'{mentee_name} отменил запись на {when}.',
            link=_mentor_cabinet_link(),
            booking=booking,
        )
        create_notification(
            booking.mentee,
            Notification.KIND_BOOKING_CANCELLED,
            'Запись отменена',
            f'Вы отменили запись к {mentor_name} на {when}.',
            link=_mentee_cabinet_link(),
            booking=booking,
        )
    else:
        create_notification(
            booking.mentee,
            Notification.KIND_BOOKING_CANCELLED,
            'Запись отменена',
            f'Ментор {mentor_name} отменил сессию на {when}.',
            link=_mentee_cabinet_link(),
            booking=booking,
        )
        create_notification(
            booking.mentor.user,
            Notification.KIND_BOOKING_CANCELLED,
            'Запись отменена',
            f'Вы отменили сессию с {mentee_name} на {when}.',
            link=_mentor_cabinet_link(),
            booking=booking,
        )


def notify_booking_rescheduled(booking):
    when = _booking_datetime_text(booking)
    mentor_name = booking.mentor.display_name
    mentee_name = booking.mentee.get_full_name() or booking.mentee.first_name or booking.mentee.email

    create_notification(
        booking.mentee,
        Notification.KIND_BOOKING_RESCHEDULED,
        'Сессия перенесена',
        f'Сессия с {mentor_name} перенесена на {when}.',
        link=_mentee_cabinet_link(),
        booking=booking,
    )
    create_notification(
        booking.mentor.user,
        Notification.KIND_BOOKING_RESCHEDULED,
        'Сессия перенесена',
        f'Сессия с {mentee_name} перенесена на {when}.',
        link=_mentor_cabinet_link(),
        booking=booking,
    )


def notify_attendance_confirmed(booking):
    when = _booking_datetime_text(booking)
    mentee_name = booking.mentee.get_full_name() or booking.mentee.first_name or booking.mentee.email
    create_notification(
        booking.mentor.user,
        Notification.KIND_ATTENDANCE_CONFIRM,
        'Участие подтверждено',
        f'{mentee_name} подтвердил участие в сессии {when}.',
        link=_mentor_cabinet_link(),
        booking=booking,
    )


def _notify_session_started(booking):
    when = _booking_datetime_text(booking)
    mentor_name = booking.mentor.display_name
    mentee_name = booking.mentee.get_full_name() or booking.mentee.first_name or booking.mentee.email
    body = f'Сессия с {mentor_name} началась ({when}).'
    create_notification(
        booking.mentee,
        Notification.KIND_SESSION_STARTED,
        'Сессия началась',
        body,
        link=_mentee_cabinet_link(),
        booking=booking,
        dedupe_unread=True,
    )
    create_notification(
        booking.mentor.user,
        Notification.KIND_SESSION_STARTED,
        'Сессия началась',
        f'Сессия с {mentee_name} началась ({when}).',
        link=_mentor_cabinet_link(),
        booking=booking,
        dedupe_unread=True,
    )


def _notify_session_completed(booking):
    when = _booking_datetime_text(booking)
    mentor_name = booking.mentor.display_name
    mentee_name = booking.mentee.get_full_name() or booking.mentee.first_name or booking.mentee.email
    create_notification(
        booking.mentee,
        Notification.KIND_SESSION_COMPLETED,
        'Сессия завершена',
        f'Сессия с {mentor_name} завершена ({when}).',
        link=_mentee_cabinet_link(),
        booking=booking,
        dedupe_unread=True,
    )
    create_notification(
        booking.mentor.user,
        Notification.KIND_SESSION_COMPLETED,
        'Сессия завершена',
        f'Сессия с {mentee_name} завершена ({when}).',
        link=_mentor_cabinet_link(),
        booking=booking,
        dedupe_unread=True,
    )


def _notify_booking_reminder(booking, kind):
    when = _booking_datetime_text(booking)
    mentor_name = booking.mentor.display_name
    mentee_name = booking.mentee.get_full_name() or booking.mentee.first_name or booking.mentee.email

    if kind == Notification.KIND_BOOKING_REMINDER_24H:
        title = 'Напоминание о сессии'
        mentee_body = f'Менее чем через сутки сессия с {mentor_name} ({when}).'
        mentor_body = f'Менее чем через сутки сессия с {mentee_name} ({when}).'
    else:
        title = 'Напоминание: скоро сессия'
        mentee_body = f'Через час сессия с {mentor_name} ({when}).'
        mentor_body = f'Через час сессия с {mentee_name} ({when}).'

    create_notification(
        booking.mentee,
        kind,
        title,
        mentee_body,
        link=_mentee_cabinet_link(),
        booking=booking,
    )
    create_notification(
        booking.mentor.user,
        kind,
        title,
        mentor_body,
        link=_mentor_cabinet_link(),
        booking=booking,
    )


def _notify_attendance_needed(booking):
    when = _booking_datetime_text(booking)
    mentor_name = booking.mentor.display_name
    create_notification(
        booking.mentee,
        Notification.KIND_ATTENDANCE_CONFIRM,
        'Подтвердите участие',
        f'Сессия с {mentor_name} скоро ({when}). Подтвердите участие в личном кабинете.',
        link=_mentee_cabinet_link(),
        booking=booking,
        dedupe_unread=True,
    )


def _booking_queryset(mentor=None, mentee=None):
    qs = SessionBooking.objects.filter(
        status=SessionBooking.STATUS_CONFIRMED,
    ).select_related('slot', 'mentor', 'mentor__user', 'mentee')
    if mentor is not None:
        qs = qs.filter(mentor=mentor)
    if mentee is not None:
        qs = qs.filter(mentee=mentee)
    return qs


def process_booking_notifications(mentor=None, mentee=None):
    from accounts.chat_utils import process_booking_lifecycle_notifications

    process_booking_lifecycle_notifications(mentor=mentor, mentee=mentee)

    now = timezone.now()
    for booking in _booking_queryset(mentor=mentor, mentee=mentee):
        updates = []
        start = booking.slot_starts_at()

        if start > now:
            delta = start - now
            if (
                not booking.reminder_24h_sent
                and timedelta(hours=1) < delta <= timedelta(hours=24)
            ):
                _notify_booking_reminder(booking, Notification.KIND_BOOKING_REMINDER_24H)
                booking.reminder_24h_sent = True
                updates.append('reminder_24h_sent')
            if not booking.reminder_1h_sent and delta <= timedelta(hours=1):
                _notify_booking_reminder(booking, Notification.KIND_BOOKING_REMINDER_1H)
                booking.reminder_1h_sent = True
                updates.append('reminder_1h_sent')
            if booking.needs_attendance_confirmation:
                _notify_attendance_needed(booking)

        if updates:
            booking.save(update_fields=updates)


def ensure_account_notifications(user, profile=None):
    if profile is None:
        from accounts.utils import get_user_profile
        profile = get_user_profile(user)

    if not profile.onboarding_completed:
        if profile.role == UserProfile.ROLE_MENTEE:
            create_notification(
                user,
                Notification.KIND_ONBOARDING_INCOMPLETE,
                'Завершите регистрацию',
                'Заполните профиль менти, чтобы пользоваться сервисом.',
                link=reverse('onboarding_mentee'),
                dedupe_unread=True,
            )
        return

    if profile.role == UserProfile.ROLE_MENTEE:
        mentee = MenteeProfile.objects.filter(user=user).prefetch_related('interests').first()
        if not mentee:
            return
        completion = mentee_profile_completion(mentee)
        if completion['percent'] < 100:
            missing = ', '.join(completion['missing'][:3])
            create_notification(
                user,
                Notification.KIND_PROFILE_INCOMPLETE,
                'Заполните профиль',
                f'Добавьте в профиль: {missing}.',
                link=reverse('mentee_profile') + '?edit=1',
                dedupe_within_hours=24,
            )
    elif profile.role == UserProfile.ROLE_MENTOR:
        mentor = MentorProfile.objects.filter(user=user).prefetch_related(
            'skills', 'consultation_topics', 'work_experiences',
        ).first()
        if not mentor:
            return
        completion = mentor_profile_completion(mentor)
        if completion['percent'] < 100:
            missing = ', '.join(completion['missing'][:3])
            create_notification(
                user,
                Notification.KIND_PROFILE_INCOMPLETE,
                'Заполните анкету',
                f'Добавьте в анкету: {missing}.',
                link=reverse('mentor_anketa'),
                dedupe_within_hours=24,
            )


def get_unread_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()


def serialize_notification(notification):
    return {
        'id': notification.id,
        'kind': notification.kind,
        'title': notification.title,
        'body': notification.body,
        'link': notification.link,
        'is_read': notification.is_read,
        'created_at': notification.created_at.isoformat(),
        'time_ago': _time_ago(notification.created_at),
    }


def _time_ago(dt):
    now = timezone.now()
    delta = now - dt
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return 'только что'
    if minutes < 60:
        return f'{minutes} мин. назад'
    hours = minutes // 60
    if hours < 24:
        return f'{hours} ч. назад'
    days = hours // 24
    if days == 1:
        return 'вчера'
    return f'{days} дн. назад'

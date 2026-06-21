from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import reverse_lazy
from django.db import IntegrityError, transaction
from django.db.models import Avg, Prefetch, Q
import mimetypes
import os

from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import content_disposition_header, url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.anketa_utils import (
    mentee_profile_completion,
    mentor_profile_completion,
    mentor_profile_sections_context,
    save_education_from_post,
    save_interests_from_post,
    save_portfolio_social_from_post,
    save_skills_from_post,
    save_topics_from_post,
    save_work_from_post,
)
from accounts.interests_catalog import interests_from_mentee, standard_interest_names
from accounts.skills_catalog import (
    custom_skills_from_post,
    skill_choices_for,
    skill_level_from_post,
    skill_levels_from_mentor,
    standard_skill_names,
)
from accounts.chat_utils import (
    CHAT_MAX_ATTACHMENTS_PER_MESSAGE,
    CHAT_MESSAGE_MAX_LENGTH,
    active_messages_queryset,
    booking_cancelled_message,
    booking_rescheduled_message,
    create_message_attachments,
    get_deleted_message_ids,
    get_shared_media_items,
    notify_booking_event_in_chat,
    notify_booking_in_chat,
    serialize_message,
    soft_delete_message,
    user_can_access_conversation,
    user_can_delete_message,
)
from django.core.signing import BadSignature, SignatureExpired

from accounts.decorators import login_required, mentor_required, mentee_required, onboarding_required
from accounts.notification_utils import (
    ensure_account_notifications,
    get_unread_count,
    notify_attendance_confirmed,
    notify_booking_cancelled,
    notify_booking_created,
    notify_booking_rescheduled,
    process_booking_notifications,
    serialize_notification,
)
from accounts.email_verification import (
    can_resend_verification,
    send_verification_email,
    verify_email_token,
)
from accounts.forms import (
    AvailabilitySlotForm,
    BookingRescheduleForm,
    ChatMessageForm,
    LoginForm,
    PasswordResetRequestForm,
    MenteeOnboardingForm,
    MenteePhotoForm,
    MenteeProfileForm,
    MentorAnketaForm,
    MentorOnboardingForm,
    MentorPhotoForm,
    MentorSearchForm,
    SignUpForm,
)
from accounts.models import (
    AvailabilitySlot,
    Conversation,
    MenteeProfile,
    MentorProfile,
    Message,
    MessageAttachment,
    Notification,
    Review,
    SessionBooking,
    UserProfile,
)
from accounts.slot_utils import nearest_slots_by_mentor, sort_mentors_by_nearest_slot
from accounts.recommendation_events import (
    handle_profile_opened_from_recommendation,
    record_attendance_confirmed,
    record_booking_cancelled,
    record_booking_created,
    record_review_created,
)
from accounts.review_utils import (
    create_session_review,
    recalculate_mentor_rating,
    recalculate_mentor_stats,
)


from accounts.utils import get_user_profile


def _cabinet_redirect(profile):
    if profile.role == UserProfile.ROLE_MENTOR:
        return redirect('mentor_cabinet')
    return redirect('mentee_cabinet')


def _redirect_onboarding(profile):
    if profile.onboarding_completed:
        return _cabinet_redirect(profile)
    if profile.role == UserProfile.ROLE_MENTEE:
        return redirect('onboarding_mentee')
    return redirect('mentor_cabinet')


def _redirect_after_auth(profile):
    if not profile.email_verified:
        return redirect('verify_email_pending')
    return _redirect_onboarding(profile)


def _mentee_context(request, active_nav, mentee=None):
    profile = get_user_profile(request.user)
    if mentee is None:
        mentee, _ = MenteeProfile.objects.prefetch_related('interests').get_or_create(user=request.user)
    return {
        'profile': profile,
        'mentee': mentee,
        'active_nav': active_nav,
        'photo_form': MenteePhotoForm(instance=mentee),
    }


def _mentor_context(request, active_nav, mentor=None):
    profile = get_user_profile(request.user)
    if mentor is None:
        mentor, _ = MentorProfile.objects.prefetch_related(
            'skills',
            'consultation_topics',
        ).get_or_create(user=request.user)
    return {
        'profile': profile,
        'mentor': mentor,
        'active_nav': active_nav,
        'photo_form': MentorPhotoForm(instance=mentor),
    }


def signup(request):
    if request.user.is_authenticated:
        return _redirect_after_auth(get_user_profile(request.user))
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                send_verification_email(user, request)
                messages.info(
                    request,
                    f'Мы отправили письмо на {user.email}. Подтвердите email, чтобы продолжить.',
                )
            except Exception:
                messages.warning(
                    request,
                    'Аккаунт создан, но письмо не удалось отправить. '
                    'Нажмите «Отправить снова» на следующей странице.',
                )
            login(request, user)
            return redirect('verify_email_pending')
    else:
        form = SignUpForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_after_auth(get_user_profile(request.user))
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            profile = get_user_profile(request.user)
            if not profile.email_verified:
                messages.info(
                    request,
                    f'Подтвердите email {request.user.email}, чтобы войти в сервис.',
                )
                return redirect('verify_email_pending')
            return _redirect_onboarding(profile)
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def verify_email_pending(request):
    profile = get_user_profile(request.user)
    if profile.email_verified:
        return _redirect_onboarding(profile)
    return render(request, 'accounts/verify_email_pending.html', {
        'email': request.user.email,
        'can_resend': can_resend_verification(profile),
    })


@login_required
@require_POST
def resend_verification_email(request):
    profile = get_user_profile(request.user)
    if profile.email_verified:
        return _redirect_onboarding(profile)
    if not can_resend_verification(profile):
        messages.warning(request, 'Подождите минуту перед повторной отправкой письма.')
        return redirect('verify_email_pending')
    try:
        send_verification_email(request.user, request)
        messages.success(request, f'Письмо снова отправлено на {request.user.email}.')
    except Exception:
        messages.error(request, 'Не удалось отправить письмо. Попробуйте позже.')
    return redirect('verify_email_pending')


def verify_email(request, token):
    try:
        user_id = verify_email_token(token)
    except SignatureExpired:
        messages.error(request, 'Ссылка устарела. Войдите и запросите новое письмо.')
        return redirect('login')
    except BadSignature:
        messages.error(request, 'Некорректная ссылка подтверждения.')
        return redirect('login')

    user = get_object_or_404(User, pk=user_id)
    profile = get_user_profile(user)
    if profile.email_verified:
        messages.info(request, 'Email уже подтверждён. Можно войти в аккаунт.')
    else:
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        messages.success(request, 'Email подтверждён! Добро пожаловать в Менторику.')

    if request.user.is_authenticated and request.user.pk == user.pk:
        return _redirect_onboarding(profile)
    return redirect('login')


def logout_view(request):
    logout(request)
    return redirect('index')


def _run_user_notifications(request):
    profile = get_user_profile(request.user)
    if profile.role == UserProfile.ROLE_MENTOR:
        mentor = MentorProfile.objects.filter(user=request.user).first()
        process_booking_notifications(mentor=mentor)
    else:
        process_booking_notifications(mentee=request.user)
    ensure_account_notifications(request.user, profile)


@login_required
def notifications_list(request):
    _run_user_notifications(request)
    items = Notification.objects.filter(user=request.user).order_by('-created_at')[:40]
    return JsonResponse({
        'unread_count': get_unread_count(request.user),
        'notifications': [serialize_notification(item) for item in items],
    })


@login_required
@require_POST
def notification_mark_read(request, notification_id):
    updated = Notification.objects.filter(
        pk=notification_id,
        user=request.user,
        is_read=False,
    ).update(is_read=True)
    if not updated:
        return JsonResponse({'error': 'Уведомление не найдено.'}, status=404)
    return JsonResponse({'ok': True, 'unread_count': get_unread_count(request.user)})


@login_required
@require_POST
def notifications_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True, 'unread_count': 0})


class PasswordResetRequestView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    form_class = PasswordResetRequestForm
    email_template_name = 'accounts/email/password_reset_email.txt'
    subject_template_name = 'accounts/email/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


class PasswordResetSentView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class PasswordResetConfirmPageView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class PasswordResetCompletePageView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


@login_required
def onboarding_role(request):
    """Устаревший URL — роль выбирается только при регистрации."""
    return _redirect_onboarding(get_user_profile(request.user))


@login_required
def onboarding_mentee(request):
    profile = get_user_profile(request.user)
    if profile.onboarding_completed:
        return _cabinet_redirect(profile)
    mentee, _ = MenteeProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = MenteeOnboardingForm(request.POST, instance=mentee)
        if form.is_valid():
            form.save()
            profile.onboarding_completed = True
            profile.save()
            messages.success(request, 'Профиль менти сохранён!')
            return _cabinet_redirect(profile)
    else:
        form = MenteeOnboardingForm(instance=mentee)
    return render(request, 'accounts/onboarding_mentee.html', {'form': form, 'profile': profile})


@login_required
def onboarding_mentor(request):
    profile = get_user_profile(request.user)
    if profile.role != UserProfile.ROLE_MENTOR:
        return _cabinet_redirect(profile)
    if not profile.onboarding_completed:
        profile.onboarding_completed = True
        profile.save()
        return redirect('mentor_cabinet')
    if profile.onboarding_completed and request.method != 'POST':
        return redirect('dashboard')

    mentor, _ = MentorProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = MentorOnboardingForm(request.POST, instance=mentor)
        if form.is_valid():
            mentor = form.save(commit=False)
            mentor.save()
            form.save_m2m()
            profile.onboarding_completed = True
            profile.save()
            messages.success(request, 'Профиль ментора сохранён.')
            return redirect('mentor_cabinet')
    else:
        form = MentorOnboardingForm(instance=mentor)
    return render(request, 'accounts/onboarding_mentor.html', {'form': form})


@login_required
@onboarding_required
def dashboard(request):
    profile = get_user_profile(request.user)
    return _cabinet_redirect(profile)


@login_required
@onboarding_required
@mentee_required
def mentee_cabinet(request):
    mentee = get_object_or_404(
        MenteeProfile.objects.prefetch_related('interests'),
        user=request.user,
    )
    today = timezone.localdate()
    now = timezone.localtime()
    process_booking_notifications(mentee=request.user)
    ensure_account_notifications(request.user)
    upcoming_bookings_qs = (
        SessionBooking.objects.filter(
            mentee=request.user,
            status=SessionBooking.STATUS_CONFIRMED,
            attendance_status__in=(
                SessionBooking.ATTENDANCE_SCHEDULED,
                SessionBooking.ATTENDANCE_CONFIRMED,
            ),
        )
        .filter(
            Q(slot__date__gt=today)
            | Q(slot__date=today, slot__end_time__gt=now.time())
        )
        .select_related('mentor', 'mentor__user', 'slot')
        .order_by('slot__date', 'slot__start_time')
    )
    upcoming_bookings_count = upcoming_bookings_qs.count()
    upcoming_bookings = list(upcoming_bookings_qs)
    upcoming_bookings_has_more = upcoming_bookings_count > 4

    session_history_qs = (
        SessionBooking.objects.filter(mentee=request.user)
        .filter(
            Q(status=SessionBooking.STATUS_CONFIRMED) & (
                Q(slot__date__lt=now.date())
                | Q(slot__date=now.date(), slot__end_time__lte=now.time())
            )
            | Q(status=SessionBooking.STATUS_CANCELLED)
            | Q(attendance_status=SessionBooking.ATTENDANCE_DECLINED)
        )
        .select_related('mentor', 'mentor__user', 'slot')
        .order_by('-slot__date', '-slot__start_time')
    )
    session_history = list(session_history_qs)

    from accounts.review_utils import booking_needs_mentee_feedback

    completed_for_review_qs = (
        SessionBooking.objects.filter(
            mentee=request.user,
            status=SessionBooking.STATUS_CONFIRMED,
        )
        .filter(
            Q(slot__date__lt=now.date())
            | Q(slot__date=now.date(), slot__end_time__lte=now.time())
        )
        .select_related('mentor', 'mentor__user', 'slot', 'review')
        .order_by('-slot__date', '-slot__start_time')
    )
    pending_review_bookings = [
        booking for booking in completed_for_review_qs
        if booking_needs_mentee_feedback(booking)
    ]

    active_bookings_filter = {
        'mentee': request.user,
        'status': SessionBooking.STATUS_CONFIRMED,
        'attendance_status__in': (
            SessionBooking.ATTENDANCE_SCHEDULED,
            SessionBooking.ATTENDANCE_CONFIRMED,
        ),
    }
    completed_sessions = SessionBooking.objects.filter(
        **active_bookings_filter,
        attendance_status=SessionBooking.ATTENDANCE_CONFIRMED,
    ).filter(
        Q(slot__date__lt=now.date())
        | Q(slot__date=now.date(), slot__end_time__lte=now.time())
    ).count()
    mentors_count = (
        SessionBooking.objects.filter(**active_bookings_filter)
        .values('mentor')
        .distinct()
        .count()
    )
    context = _mentee_context(request, 'cabinet', mentee=mentee)
    context.update({
        'upcoming_bookings': upcoming_bookings,
        'upcoming_bookings_count': upcoming_bookings_count,
        'upcoming_bookings_has_more': upcoming_bookings_has_more,
        'session_history': session_history,
        'pending_review_bookings': pending_review_bookings,
        'completed_sessions': completed_sessions,
        'mentors_count': mentors_count,
        'interests_count': mentee.interests.count(),
        'profile_completion': mentee_profile_completion(mentee),
    })
    return render(request, 'accounts/mentee/cabinet.html', context)


@login_required
@onboarding_required
@mentee_required
def mentee_profile(request):
    mentee = get_object_or_404(
        MenteeProfile.objects.prefetch_related('interests'),
        user=request.user,
    )
    user = request.user
    editing = request.GET.get('edit') == '1'
    saved_interests = interests_from_mentee(mentee)

    if request.method == 'POST':
        form = MenteeProfileForm(
            request.POST,
            saved_interests=saved_interests,
        )
        editing = True
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name'].strip()
            user.last_name = form.cleaned_data['last_name'].strip()
            user.save(update_fields=['first_name', 'last_name'])
            mentee.bio = form.cleaned_data['bio'].strip()
            mentee.goals = form.cleaned_data['goals'].strip()
            mentee.save(update_fields=['bio', 'goals'])
            save_interests_from_post(mentee, request.POST)
            messages.success(request, 'Профиль сохранён.')
            return redirect('mentee_profile')
    else:
        form = MenteeProfileForm(
            initial={
                'first_name': user.first_name,
                'last_name': user.last_name,
                'bio': mentee.bio,
                'goals': mentee.goals,
                'interests': [name for name in saved_interests if name in standard_interest_names()],
            },
            saved_interests=saved_interests,
        )

    context = _mentee_context(request, 'profile', mentee=mentee)
    context.update({
        'form': form,
        'editing': editing,
        'profile_completion': mentee_profile_completion(mentee),
    })
    return render(request, 'accounts/mentee/profile.html', context)


@login_required
@onboarding_required
@mentee_required
@require_POST
def mentee_photo_upload(request):
    mentee = get_object_or_404(MenteeProfile, user=request.user)
    form = MenteePhotoForm(request.POST, request.FILES, instance=mentee)
    if form.is_valid():
        form.save()
        messages.success(request, 'Фото обновлено.')
    else:
        messages.error(request, 'Не удалось загрузить фото. Проверьте формат файла.')
    next_url = request.POST.get('next', 'mentee_cabinet')
    return redirect(next_url)


@login_required
@onboarding_required
@mentor_required
def mentor_cabinet(request):
    context = _mentor_context(request, 'cabinet')
    mentor = context['mentor']
    mentor = MentorProfile.objects.prefetch_related(
        'skills',
        'consultation_topics',
        'work_experiences',
        'reviews',
    ).get(pk=mentor.pk)
    recalculate_mentor_rating(mentor)
    today = timezone.localdate()
    now = timezone.localtime()
    process_booking_notifications(mentor=mentor)
    ensure_account_notifications(request.user)
    upcoming_bookings_qs = (
        SessionBooking.objects.filter(
            mentor=mentor,
            status=SessionBooking.STATUS_CONFIRMED,
            attendance_status__in=(
                SessionBooking.ATTENDANCE_SCHEDULED,
                SessionBooking.ATTENDANCE_CONFIRMED,
            ),
        )
        .filter(
            Q(slot__date__gt=today)
            | Q(slot__date=today, slot__end_time__gt=now.time())
        )
        .select_related('mentee', 'slot')
        .order_by('slot__date', 'slot__start_time')
    )
    upcoming_bookings_count = upcoming_bookings_qs.count()
    upcoming_bookings = list(upcoming_bookings_qs)
    upcoming_bookings_has_more = upcoming_bookings_count > 4
    chat_by_mentee = dict(
        Conversation.objects.filter(mentor=mentor).values_list('mentee_id', 'pk')
    )
    for booking in upcoming_bookings:
        booking.chat_id = chat_by_mentee.get(booking.mentee_id)

    session_history = list(
        SessionBooking.objects.filter(mentor=mentor)
        .filter(
            Q(status=SessionBooking.STATUS_CONFIRMED) & (
                Q(slot__date__lt=now.date())
                | Q(slot__date=now.date(), slot__end_time__lte=now.time())
            )
            | Q(status=SessionBooking.STATUS_CANCELLED)
            | Q(attendance_status=SessionBooking.ATTENDANCE_DECLINED)
        )
        .select_related('mentee', 'slot')
        .order_by('-slot__date', '-slot__start_time')
    )
    for booking in session_history:
        booking.chat_id = chat_by_mentee.get(booking.mentee_id)

    open_slots_count = mentor.slots.filter(
        date__gte=today,
        is_available=True,
    ).filter(
        Q(booking__isnull=True) | Q(booking__status=SessionBooking.STATUS_CANCELLED),
    ).count()
    context.update({
        'upcoming_bookings': upcoming_bookings,
        'upcoming_bookings_count': upcoming_bookings_count,
        'upcoming_bookings_has_more': upcoming_bookings_has_more,
        'session_history': session_history,
        'open_slots_count': open_slots_count,
        'reviews_count': mentor.reviews.count(),
        'profile_completion': mentor_profile_completion(mentor),
    })
    return render(request, 'accounts/mentor/cabinet.html', context)


@login_required
@onboarding_required
@mentor_required
def mentor_anketa(request):
    mentor = get_object_or_404(
        MentorProfile.objects.prefetch_related(
            'skills',
            'consultation_topics',
            'work_experiences',
            'education_entries',
            'profile_links',
        ),
        user=request.user,
    )
    recalculate_mentor_rating(mentor)
    user = request.user

    def _form_initial():
        skill_levels = skill_levels_from_mentor(mentor)
        standard = standard_skill_names()
        return {
            'headline': mentor.headline,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'bio': mentor.bio,
            'gender': mentor.gender,
            'languages': mentor.language_list,
            'skills': [name for name in skill_levels if name in standard],
            'portfolio_description': mentor.portfolio_text,
        }

    skill_levels = skill_levels_from_mentor(mentor)

    if request.method == 'POST':
        posted_languages = request.POST.getlist('languages')
        posted_skills = request.POST.getlist('skills')
        saved_skill_levels = {
            name: skill_level_from_post(request.POST, name) for name in posted_skills
        }
        for row in custom_skills_from_post(request.POST):
            saved_skill_levels[row['name']] = row['level']
        form = MentorAnketaForm(
            request.POST,
            saved_languages=posted_languages,
            saved_skill_levels=saved_skill_levels,
            saved_topics=list(mentor.consultation_topics.all()),
            saved_work_experiences=list(mentor.work_experiences.all()),
            saved_education=list(mentor.education_entries.all()),
            saved_mentor=mentor,
        )
        editing = True
        if form.is_valid():
            with transaction.atomic():
                user.first_name = form.cleaned_data['first_name'].strip()
                user.last_name = form.cleaned_data['last_name'].strip()
                user.save(update_fields=['first_name', 'last_name'])
                mentor.headline = form.cleaned_data['headline'].strip()
                mentor.bio = form.cleaned_data['bio'].strip()
                mentor.gender = form.cleaned_data.get('gender') or ''
                mentor.languages = ', '.join(form.cleaned_data['languages'])
                mentor.save(update_fields=['headline', 'bio', 'gender', 'languages'])
                save_skills_from_post(mentor, request.POST)
                save_topics_from_post(mentor, request.POST)
                save_work_from_post(mentor, request.POST)
                save_education_from_post(mentor, request.POST)
                save_portfolio_social_from_post(mentor, request.POST)
            messages.success(request, 'Профиль сохранён.')
            return redirect('mentor_anketa')
    else:
        form = MentorAnketaForm(
            initial=_form_initial(),
            saved_languages=mentor.language_list,
            saved_skill_levels=skill_levels,
            saved_topics=list(mentor.consultation_topics.all()),
            saved_work_experiences=list(mentor.work_experiences.all()),
            saved_education=list(mentor.education_entries.all()),
            saved_mentor=mentor,
        )
        editing = request.GET.get('edit') == '1'

    context = _mentor_context(request, 'anketa', mentor=mentor)
    context['form'] = form
    context['editing'] = editing
    context.update(mentor_profile_sections_context(mentor))
    return render(request, 'accounts/mentor/anketa.html', context)


def _conversations_with_preview(queryset):
    return queryset.prefetch_related(
        Prefetch(
            'messages',
            queryset=Message.objects.filter(is_deleted=False).prefetch_related('attachments').order_by('-created_at')[:1],
            to_attr='latest_messages',
        ),
    )


@login_required
@onboarding_required
@mentor_required
def mentor_chats(request):
    mentor = get_object_or_404(MentorProfile, user=request.user)
    conversations = _conversations_with_preview(
        Conversation.objects.filter(mentor=mentor).select_related('mentee', 'mentee__mentee_profile')
    )
    context = _mentor_context(request, 'chats', mentor=mentor)
    context['conversations'] = conversations
    return render(request, 'accounts/mentor/chats.html', context)


@login_required
@onboarding_required
@mentor_required
def mentee_detail(request, user_id):
    mentor = get_object_or_404(MentorProfile, user=request.user)
    mentee_user = get_object_or_404(User, pk=user_id)
    has_access = (
        Conversation.objects.filter(mentor=mentor, mentee=mentee_user).exists()
        or SessionBooking.objects.filter(mentor=mentor, mentee=mentee_user).exists()
    )
    if not has_access:
        raise Http404
    mentee = get_object_or_404(
        MenteeProfile.objects.prefetch_related('interests'),
        user=mentee_user,
    )
    context = _mentor_context(request, 'chats', mentor=mentor)
    context['mentee'] = mentee
    return render(request, 'accounts/mentee/detail.html', context)


@login_required
@onboarding_required
@mentor_required
def mentor_chat_detail(request, conversation_id):
    mentor = get_object_or_404(MentorProfile, user=request.user)
    conversation = get_object_or_404(
        Conversation.objects.select_related('mentee', 'mentor'),
        pk=conversation_id,
        mentor=mentor,
    )
    return _chat_detail_response(request, conversation, 'mentor')


@login_required
@onboarding_required
@mentee_required
def mentee_chats(request):
    conversations = _conversations_with_preview(
        Conversation.objects.filter(mentee=request.user).select_related('mentor', 'mentor__user')
    )
    context = _mentee_context(request, 'chats')
    context['conversations'] = conversations
    return render(request, 'accounts/mentee/chats.html', context)


@login_required
@onboarding_required
@mentee_required
def mentee_chat_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.select_related('mentor', 'mentor__user', 'mentee'),
        pk=conversation_id,
        mentee=request.user,
    )
    return _chat_detail_response(request, conversation, 'mentee')


@login_required
@onboarding_required
def chat_attachment_download(request, conversation_id, attachment_id):
    attachment = get_object_or_404(
        MessageAttachment.objects.select_related('message__conversation'),
        pk=attachment_id,
        message__conversation_id=conversation_id,
    )
    if not user_can_access_conversation(request.user, attachment.message.conversation):
        raise Http404

    mime_type = (
        attachment.mime_type
        or mimetypes.guess_type(attachment.file.name)[0]
        or 'application/octet-stream'
    )
    filename = attachment.name or os.path.basename(attachment.file.name)
    as_attachment = not attachment.is_image

    response = FileResponse(attachment.file.open('rb'), content_type=mime_type)
    response['Content-Disposition'] = content_disposition_header(as_attachment, filename)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@onboarding_required
@require_POST
def chat_message_delete(request, conversation_id, message_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if not user_can_access_conversation(request.user, conversation):
        raise Http404
    message = get_object_or_404(
        Message.objects.filter(conversation=conversation, is_deleted=False),
        pk=message_id,
    )
    if not user_can_delete_message(request.user, message):
        return JsonResponse({'error': 'Нельзя удалить это сообщение.'}, status=403)
    soft_delete_message(message)
    return JsonResponse({'ok': True, 'message_id': message.pk})


@login_required
@onboarding_required
def chat_shared_api(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if not user_can_access_conversation(request.user, conversation):
        raise Http404

    media_type = request.GET.get('type', 'images')
    try:
        items = get_shared_media_items(conversation, media_type)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)
    return JsonResponse({'items': items})


@login_required
@onboarding_required
def chat_messages_api(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if not user_can_access_conversation(request.user, conversation):
        raise Http404

    if request.method == 'GET':
        process_booking_notifications(
            mentor=conversation.mentor,
            mentee=conversation.mentee,
        )
        after = request.GET.get('after')
        qs = active_messages_queryset(conversation).select_related(
            'sender',
            'conversation',
            'booking',
            'booking__review',
            'reply_to',
            'reply_to__sender',
        ).prefetch_related('attachments', 'reply_to__attachments').order_by('created_at')
        if after:
            try:
                qs = qs.filter(pk__gt=int(after))
            except (TypeError, ValueError):
                pass
        response_data = {
            'messages': [serialize_message(message, request.user) for message in qs],
        }
        visible = request.GET.get('visible', '')
        if visible:
            visible_ids = [int(part) for part in visible.split(',') if part.strip().isdigit()]
            response_data['deleted_ids'] = get_deleted_message_ids(conversation, visible_ids)
        return JsonResponse(response_data)

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        uploaded_files = request.FILES.getlist('attachments')
        if not uploaded_files and request.FILES.get('attachment'):
            uploaded_files = [request.FILES['attachment']]
        if not text and not uploaded_files:
            return JsonResponse({'error': 'Напишите сообщение или прикрепите файл.'}, status=400)
        if len(text) > CHAT_MESSAGE_MAX_LENGTH:
            return JsonResponse({'error': f'Сообщение не длиннее {CHAT_MESSAGE_MAX_LENGTH} символов.'}, status=400)
        if len(uploaded_files) > CHAT_MAX_ATTACHMENTS_PER_MESSAGE:
            return JsonResponse({
                'error': f'Можно прикрепить не больше {CHAT_MAX_ATTACHMENTS_PER_MESSAGE} файлов за раз.',
            }, status=400)
        reply_to = None
        reply_to_raw = request.POST.get('reply_to', '').strip()
        if reply_to_raw:
            try:
                reply_to = active_messages_queryset(conversation).get(pk=int(reply_to_raw))
            except (TypeError, ValueError, Message.DoesNotExist):
                return JsonResponse({'error': 'Сообщение для ответа не найдено.'}, status=400)
            if reply_to.is_system:
                return JsonResponse({'error': 'Нельзя ответить на системное сообщение.'}, status=400)
        try:
            with transaction.atomic():
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    text=text,
                    reply_to=reply_to,
                )
                if uploaded_files:
                    create_message_attachments(message, uploaded_files)
        except ValidationError as exc:
            return JsonResponse({'error': exc.messages[0]}, status=400)
        message = Message.objects.select_related(
            'sender', 'reply_to', 'reply_to__sender',
        ).prefetch_related('attachments', 'reply_to__attachments').get(pk=message.pk)
        Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
        return JsonResponse({'message': serialize_message(message, request.user)})

    return JsonResponse({'error': 'Метод не поддерживается.'}, status=405)


def _chat_detail_response(request, conversation, role):
    process_booking_notifications(
        mentor=conversation.mentor,
        mentee=conversation.mentee,
    )
    form = ChatMessageForm()
    chat_messages = active_messages_queryset(conversation).select_related(
        'sender',
        'conversation',
        'booking',
        'booking__slot',
        'booking__review',
        'reply_to',
        'reply_to__sender',
    ).prefetch_related('attachments', 'reply_to__attachments').all()
    last_message = chat_messages.order_by('-pk').first()
    last_message_id = last_message.pk if last_message else 0
    if role == 'mentor':
        conversations = _conversations_with_preview(
            Conversation.objects.filter(mentor=conversation.mentor).select_related('mentee')
        )
        context = _mentor_context(request, 'chats', mentor=conversation.mentor)
        context.update({
            'conversation': conversation,
            'chat_messages': chat_messages,
            'conversations': conversations,
            'form': form,
            'active_conversation_id': conversation.pk,
            'last_message_id': last_message_id,
        })
        return render(request, 'accounts/mentor/chat_detail.html', context)

    conversations = _conversations_with_preview(
        Conversation.objects.filter(mentee=request.user).select_related('mentor', 'mentor__user')
    )
    context = _mentee_context(request, 'chats')
    context.update({
        'conversation': conversation,
        'chat_messages': chat_messages,
        'conversations': conversations,
        'form': form,
        'active_conversation_id': conversation.pk,
        'last_message_id': last_message_id,
        'session_rating_enabled': True,
    })
    return render(request, 'accounts/mentee/chat_detail.html', context)


@login_required
@onboarding_required
@mentor_required
@require_POST
def mentor_photo_upload(request):
    mentor = get_object_or_404(MentorProfile, user=request.user)
    form = MentorPhotoForm(request.POST, request.FILES, instance=mentor)
    if form.is_valid():
        form.save()
        messages.success(request, 'Фото обновлено.')
    else:
        messages.error(request, 'Не удалось загрузить фото. Проверьте формат файла.')
    next_url = request.POST.get('next', 'mentor_cabinet')
    return redirect(next_url)


def mentor_list(request):
    mentors = MentorProfile.objects.select_related('user').prefetch_related('skills')

    form = MentorSearchForm(request.GET or None)
    selected_skills = request.GET.getlist('skills')

    if form.is_valid():
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        min_rating = form.cleaned_data.get('min_rating', 0)
        max_rating = form.cleaned_data.get('max_rating', 5)
        sort = form.cleaned_data.get('sort') or 'popular'

        if first_name:
            mentors = mentors.filter(user__first_name__icontains=first_name)
        if last_name:
            mentors = mentors.filter(user__last_name__icontains=last_name)
        if min_rating > 0:
            mentors = mentors.filter(rating__gte=min_rating)
        if max_rating < 5:
            mentors = mentors.filter(rating__lte=max_rating)
        if selected_skills:
            mentors = mentors.filter(skills__name__in=selected_skills).distinct()

        if sort == 'rating':
            mentors = mentors.order_by('-rating', '-sessions_count')
        elif sort == 'nearest':
            mentors = mentors.distinct()
        else:
            mentors = mentors.order_by('-sessions_count', '-rating')
    else:
        mentors = mentors.order_by('-sessions_count', '-rating')
        sort = request.GET.get('sort', 'popular')
        if sort not in {'popular', 'rating', 'nearest'}:
            sort = 'popular'

    mentors = list(mentors.distinct())
    if sort == 'nearest':
        mentors = sort_mentors_by_nearest_slot(mentors)
    mentor_count = len(mentors)
    nearest_slots = nearest_slots_by_mentor([mentor.pk for mentor in mentors])
    for mentor in mentors:
        mentor.nearest_slots = nearest_slots.get(mentor.pk)

    catalog_skills = [label for _code, label in skill_choices_for()]
    custom_skills = sorted({
        name for name in MentorProfile.objects.values_list('skills__name', flat=True).distinct()
        if name and name not in catalog_skills
    })
    filter_skills = catalog_skills + custom_skills

    if form.is_valid():
        rating_min = form.cleaned_data['min_rating']
        rating_max = form.cleaned_data['max_rating']
    else:
        try:
            rating_min = max(0, min(5, int(request.GET.get('min_rating', 0))))
            rating_max = max(0, min(5, int(request.GET.get('max_rating', 5))))
        except (TypeError, ValueError):
            rating_min, rating_max = 0, 5
        if rating_min > rating_max:
            rating_max = rating_min

    return render(request, 'accounts/mentor_list.html', {
        'mentors': mentors,
        'mentor_count': mentor_count,
        'form': form,
        'filter_skills': filter_skills,
        'selected_skills': selected_skills,
        'sort': form.cleaned_data.get('sort') if form.is_valid() else 'popular',
        'rating_min': rating_min,
        'rating_max': rating_max,
    })


def mentor_detail(request, slug):
    mentor = get_object_or_404(
        MentorProfile.objects.select_related('user').prefetch_related(
            'skills',
            'consultation_topics',
            'work_experiences',
            'education_entries',
            'profile_links',
            'reviews__mentee',
        ),
        slug=slug,
    )

    tracking_token = (request.GET.get('rec') or '').strip()
    if tracking_token:
        handle_profile_opened_from_recommendation(request, tracking_token, mentor)

    return render(request, 'accounts/mentor_detail.html', {
        'mentor': mentor,
        **mentor_profile_sections_context(mentor),
    })


@login_required
@onboarding_required
@mentee_required
@require_POST
def book_session(request, slug):
    mentor = get_object_or_404(
        MentorProfile,
        slug=slug,
    )
    slot_id = request.POST.get('slot_id')
    if not slot_id:
        messages.error(request, 'Выберите временной слот.')
        return redirect('mentor_detail', slug=slug)

    try:
        with transaction.atomic():
            slot = (
                AvailabilitySlot.objects.select_for_update()
                .filter(pk=slot_id, mentor=mentor, is_available=True)
                .first()
            )
            if not slot:
                messages.error(request, 'Этот слот уже занят. Выберите другое время.')
                return redirect('mentor_detail', slug=slug)

            existing_booking = SessionBooking.objects.filter(slot=slot).select_for_update().first()
            if existing_booking and existing_booking.status != SessionBooking.STATUS_CANCELLED:
                messages.error(request, 'Этот слот уже занят. Выберите другое время.')
                return redirect('mentor_detail', slug=slug)

            if existing_booking:
                existing_booking.delete()

            booking = SessionBooking.objects.create(
                mentor=mentor,
                mentee=request.user,
                slot=slot,
                status=SessionBooking.STATUS_CONFIRMED,
            )
            slot.is_available = False
            slot.save(update_fields=['is_available'])
            conversation = notify_booking_in_chat(booking)
            notify_booking_created(booking)
            record_booking_created(request, booking)
    except Exception:
        messages.error(request, 'Не удалось забронировать слот. Попробуйте снова.')
        return redirect('mentor_detail', slug=slug)

    messages.success(request, 'Сессия успешно забронирована!')
    return redirect('mentee_chat_detail', conversation_id=conversation.pk)


@login_required
@onboarding_required
@mentee_required
@require_POST
def booking_attendance(request, booking_id):
    booking = get_object_or_404(
        SessionBooking.objects.select_related('slot'),
        pk=booking_id,
        mentee=request.user,
    )
    decision = request.POST.get('decision')

    if decision == 'confirm':
        if not booking.needs_attendance_confirmation:
            messages.error(request, 'Подтверждение участия сейчас недоступно для этой сессии.')
            return redirect('mentee_cabinet')
        booking.confirm_attendance()
        notify_attendance_confirmed(booking)
        record_attendance_confirmed(booking)
        messages.success(request, 'Вы подтвердили участие в сессии.')
    elif decision == 'decline':
        if not booking.can_cancel_booking:
            messages.error(request, 'Эту запись нельзя отменить.')
            return redirect('mentee_cabinet')
        booking.cancel_booking()
        notify_booking_event_in_chat(booking, booking_cancelled_message(booking))
        notify_booking_cancelled(booking, cancelled_by='mentee')
        record_booking_cancelled(booking)
        messages.info(request, 'Запись на сессию отменена.')
    else:
        messages.error(request, 'Некорректный ответ.')
        return redirect('mentee_cabinet')

    return redirect('mentee_cabinet')


@login_required
@onboarding_required
@mentee_required
@require_POST
def booking_rate(request, booking_id):
    booking = get_object_or_404(
        SessionBooking.objects.select_related('slot', 'mentor'),
        pk=booking_id,
        mentee=request.user,
    )
    if booking.status != SessionBooking.STATUS_CONFIRMED:
        return JsonResponse({'error': 'Нельзя оценить эту сессию.'}, status=400)
    if not booking.slot_has_ended():
        return JsonResponse({'error': 'Сессия ещё не завершена.'}, status=400)
    from accounts.review_utils import review_feedback_complete

    review = Review.objects.filter(booking=booking).first()
    text = (request.POST.get('text') or '').strip()[:2000]
    try:
        rating = int(request.POST.get('rating', 0))
    except (TypeError, ValueError):
        rating = 0

    if review:
        if review_feedback_complete(review):
            return JsonResponse({'error': 'Отзыв уже отправлен.'}, status=400)
        if rating >= 1 and rating <= 5:
            review.rating = rating
        elif not review.rating:
            return JsonResponse({'error': 'Выберите от 1 до 5 звёзд.'}, status=400)
        review.text = text
        review.save(update_fields=['rating', 'text'])
        recalculate_mentor_stats(booking.mentor)
        return JsonResponse({
            'ok': True,
            'rating': review.rating,
            'text': review.text,
            'complete': review_feedback_complete(review),
        })

    if rating < 1 or rating > 5:
        return JsonResponse({'error': 'Выберите от 1 до 5 звёзд.'}, status=400)
    review = create_session_review(booking, request.user, rating, text=text)
    record_review_created(booking, review)
    return JsonResponse({
        'ok': True,
        'rating': review.rating,
        'text': review.text,
        'complete': review_feedback_complete(review),
    })


def _redirect_after_booking_manage(request, default_view='mentor_cabinet'):
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(default_view)


@login_required
@onboarding_required
@mentor_required
@require_POST
def mentor_booking_manage(request, booking_id):
    booking = get_object_or_404(
        SessionBooking.objects.select_related('slot', 'mentee', 'mentor'),
        pk=booking_id,
        mentor__user=request.user,
    )
    action = request.POST.get('action')
    redirect_response = _redirect_after_booking_manage

    if action == 'cancel':
        if not booking.can_mentor_manage_booking:
            messages.error(request, 'Эту запись нельзя отменить.')
            return redirect_response(request)
        booking.cancel_booking()
        notify_booking_event_in_chat(booking, booking_cancelled_message(booking))
        notify_booking_cancelled(booking, cancelled_by='mentor')
        record_booking_cancelled(booking)
        messages.info(request, 'Запись отменена. Слот снова доступен для записи.')
    elif action == 'reschedule':
        if not booking.can_mentor_manage_booking:
            messages.error(request, 'Эту запись нельзя изменить.')
            return redirect_response(request)
        form = BookingRescheduleForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Проверьте дату и время.')
            return redirect_response(request)
        try:
            booking.reschedule_slot(
                date=form.cleaned_data['date'],
                start_time=form.cleaned_data['start_time'],
                end_time=form.cleaned_data['end_time'],
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect_response(request)
        notify_booking_event_in_chat(booking, booking_rescheduled_message(booking))
        notify_booking_rescheduled(booking)
        messages.success(request, 'Время сессии обновлено.')
    else:
        messages.error(request, 'Некорректное действие.')
    return redirect_response(request)


@login_required
@onboarding_required
def booking_confirm(request, booking_id):
    booking = get_object_or_404(
        SessionBooking.objects.select_related('mentor', 'mentee', 'slot'),
        pk=booking_id,
    )
    if booking.mentee != request.user and booking.mentor.user != request.user:
        raise Http404
    conversation = Conversation.objects.filter(mentor=booking.mentor, mentee=booking.mentee).first()
    return render(request, 'accounts/booking_confirm.html', {
        'booking': booking,
        'conversation': conversation,
    })


@login_required
@onboarding_required
@mentor_required
def mentor_schedule(request):
    mentor = get_object_or_404(MentorProfile, user=request.user)

    if request.method == 'POST':
        form = AvailabilitySlotForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.mentor = mentor
            slot.save()
            messages.success(request, 'Слот добавлен.')
            return redirect('mentor_schedule')
    else:
        form = AvailabilitySlotForm()

    context = _mentor_context(request, 'schedule', mentor=mentor)
    context.update({'form': form})
    return render(request, 'accounts/mentor/schedule.html', context)


@login_required
@onboarding_required
@mentor_required
def mentor_schedule_api(request):
    mentor = get_object_or_404(MentorProfile, user=request.user)
    today = timezone.localdate()
    month_str = request.GET.get('month')
    date_str = request.GET.get('date')

    base_qs = (
        mentor.slots.filter(date__gte=today)
        .select_related('booking', 'booking__mentee')
        .order_by('start_time')
    )

    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
        except (TypeError, ValueError):
            return JsonResponse({'dates': []})
        dates = (
            base_qs.filter(date__year=year, date__month=month)
            .values_list('date', flat=True)
            .distinct()
            .order_by('date')
        )
        return JsonResponse({'dates': [d.isoformat() for d in dates]})

    if date_str:
        process_booking_notifications(mentor=mentor)
        ensure_account_notifications(request.user)
        slots = base_qs.filter(date=date_str)
        payload = []
        for slot in slots:
            item = {
                'id': slot.pk,
                'date': slot.date.isoformat(),
                'start': slot.start_time.strftime('%H:%M'),
                'end': slot.end_time.strftime('%H:%M'),
                'booked': slot.has_active_booking,
            }
            if slot.has_active_booking:
                booking = slot.booking
                mentee = booking.mentee
                item['mentee'] = mentee.get_full_name() or mentee.username
                item['booking_id'] = booking.pk
                item['can_manage'] = booking.can_mentor_manage_booking
                if booking.slot_is_in_progress():
                    item['session_state'] = 'started'
                else:
                    item['session_state'] = 'booked'
            payload.append(item)
        return JsonResponse({'slots': payload})

    return JsonResponse({'dates': [], 'slots': []})


@login_required
@onboarding_required
@mentor_required
@require_POST
def edit_slot(request, slot_id):
    mentor = get_object_or_404(MentorProfile, user=request.user)
    slot = get_object_or_404(AvailabilitySlot, pk=slot_id, mentor=mentor)
    if slot.has_active_booking:
        messages.error(request, 'Нельзя изменить забронированный слот.')
        return redirect('mentor_schedule')
    form = AvailabilitySlotForm(request.POST, instance=slot)
    if form.is_valid():
        try:
            form.save()
            messages.success(request, 'Слот обновлён.')
        except IntegrityError:
            messages.error(request, 'Слот с таким временем уже существует.')
    else:
        messages.error(request, 'Проверьте дату и время.')
    return redirect('mentor_schedule')


@login_required
@onboarding_required
@mentor_required
@require_POST
def delete_slot(request, slot_id):
    mentor = get_object_or_404(MentorProfile, user=request.user)
    slot = get_object_or_404(AvailabilitySlot, pk=slot_id, mentor=mentor)
    if slot.has_active_booking:
        messages.error(request, 'Нельзя удалить забронированный слот.')
    else:
        SessionBooking.objects.filter(slot=slot, status=SessionBooking.STATUS_CANCELLED).delete()
        slot.delete()
        messages.success(request, 'Слот удалён.')
    return redirect('mentor_schedule')


def api_slots(request, slug):
    mentor = get_object_or_404(MentorProfile, slug=slug)
    today = timezone.localdate()
    month_str = request.GET.get('month')
    date_str = request.GET.get('date')

    base_qs = AvailabilitySlot.objects.filter(
        mentor=mentor,
        is_available=True,
        date__gte=today,
    ).filter(
        Q(booking__isnull=True) | Q(booking__status=SessionBooking.STATUS_CANCELLED),
    )

    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
        except (TypeError, ValueError):
            return JsonResponse({'dates': []})
        dates = (
            base_qs.filter(date__year=year, date__month=month)
            .values_list('date', flat=True)
            .distinct()
            .order_by('date')
        )
        return JsonResponse({'dates': [d.isoformat() for d in dates]})

    if date_str:
        slots = base_qs.filter(date=date_str).order_by('start_time')
        return JsonResponse({
            'slots': [
                {'id': s.pk, 'start': s.start_time.strftime('%H:%M'), 'end': s.end_time.strftime('%H:%M')}
                for s in slots
            ],
        })

    return JsonResponse({'dates': [], 'slots': []})

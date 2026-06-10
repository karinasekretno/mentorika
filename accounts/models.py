import os
from datetime import datetime, timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class UserProfile(models.Model):
    ROLE_MENTEE = 'mentee'
    ROLE_MENTOR = 'mentor'
    ROLE_BOTH = 'both'  # устаревшее значение, только для старых записей
    ROLE_CHOICES = [
        (ROLE_MENTEE, 'Менти (ученик)'),
        (ROLE_MENTOR, 'Ментор'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField('Роль', max_length=10, choices=ROLE_CHOICES)
    active_role = models.CharField(
        'Активная роль (служебное)',
        max_length=10,
        choices=ROLE_CHOICES,
        editable=False,
    )
    onboarding_completed = models.BooleanField('Онбординг завершён', default=False)
    email_verified = models.BooleanField('Email подтверждён', default=False)
    email_verification_sent_at = models.DateTimeField(
        'Письмо подтверждения отправлено',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Роль пользователя'
        verbose_name_plural = 'Роли пользователей'

    def __str__(self):
        return f'{self.user.username} — {self.get_role_display()}'

    def save(self, *args, **kwargs):
        if self.pk:
            previous_role = (
                UserProfile.objects.filter(pk=self.pk)
                .values_list('role', flat=True)
                .first()
            )
            if previous_role and self.role != previous_role:
                self.role = previous_role
        if self.role == self.ROLE_BOTH:
            self.role = self.active_role or self.ROLE_MENTEE
        self.active_role = self.role
        super().save(*args, **kwargs)

    @property
    def can_be_mentor(self):
        return self.role == self.ROLE_MENTOR

    @property
    def can_be_mentee(self):
        return self.role == self.ROLE_MENTEE


class MenteeProfile(models.Model):
    LEVEL_JUNIOR = 'junior'
    LEVEL_MIDDLE = 'middle'
    LEVEL_SENIOR = 'senior'
    LEVEL_LEAD = 'lead'
    LEVEL_CHOICES = [
        (LEVEL_JUNIOR, 'Junior'),
        (LEVEL_MIDDLE, 'Middle'),
        (LEVEL_SENIOR, 'Senior'),
        (LEVEL_LEAD, 'Lead'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mentee_profile',
    )
    photo = models.ImageField('Фото', upload_to='mentees/photos/', blank=True)
    bio = models.TextField('О себе', blank=True)
    goals = models.TextField('Цели обучения', blank=True)
    level = models.CharField('Уровень', max_length=10, choices=LEVEL_CHOICES, blank=True)

    class Meta:
        verbose_name = 'Анкета менти'
        verbose_name_plural = 'Анкеты менти'

    def __str__(self):
        return f'Менти: {self.user.get_full_name() or self.user.username}'

    @property
    def display_name(self):
        full = self.user.get_full_name()
        return full if full else self.user.username

    @property
    def initials(self):
        parts = self.display_name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return self.display_name[:2].upper()

    @property
    def headline(self):
        parts = []
        interest = self.interests.first()
        if interest:
            parts.append(interest.name)
        return ' · '.join(parts)


class MenteeInterest(models.Model):
    mentee = models.ForeignKey(MenteeProfile, on_delete=models.CASCADE, related_name='interests')
    name = models.CharField('Интерес', max_length=80)

    class Meta:
        verbose_name = 'Интерес менти'
        verbose_name_plural = 'Интересы менти'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['mentee', 'name'], name='unique_mentee_interest'),
        ]

    def __str__(self):
        return self.name


class MentorProfile(models.Model):
    GENDER_MALE = 'male'
    GENDER_FEMALE = 'female'
    GENDER_CHOICES = [
        (GENDER_MALE, 'Мужской'),
        (GENDER_FEMALE, 'Женский'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mentor_profile',
    )
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    photo = models.ImageField('Фото', upload_to='mentors/photos/', blank=True)
    headline = models.CharField('Краткое описание', max_length=200, blank=True)
    bio = models.TextField('О себе', blank=True)
    gender = models.CharField('Пол', max_length=10, choices=GENDER_CHOICES, blank=True)
    languages = models.CharField('Языки', max_length=255, blank=True, help_text='Через запятую')
    company = models.CharField('Компания', max_length=120, blank=True)
    job_title = models.CharField('Должность', max_length=120, blank=True)
    portfolio_url = models.URLField('Портфолио (URL)', blank=True)
    portfolio_text = models.TextField('Портфолио (описание)', blank=True)
    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=2, default=0)
    sessions_count = models.PositiveIntegerField('Проведено сессий', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Анкета ментора'
        verbose_name_plural = 'Менторы'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = self.user.username
            self.slug = slugify(base, allow_unicode=True) or f'mentor-{self.user_id}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def rating_display(self):
        from accounts.review_utils import calculate_mentor_rating

        return float(calculate_mentor_rating(self))

    @property
    def has_real_rating(self):
        return self.rating_display > 0

    @property
    def completed_sessions_count(self):
        from accounts.review_utils import calculate_completed_sessions_count

        return calculate_completed_sessions_count(self)

    @property
    def star_states(self):
        rating = max(0.0, min(5.0, self.rating_display))
        states = []
        for index in range(1, 6):
            if rating >= index:
                states.append('full')
            elif rating >= index - 0.5:
                states.append('half')
            else:
                states.append('empty')
        return states

    @property
    def display_name(self):
        full = self.user.get_full_name()
        return full if full else self.user.username

    @property
    def initials(self):
        parts = self.display_name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return self.display_name[:2].upper()

    @property
    def language_list(self):
        if not self.languages:
            return []
        return [lang.strip() for lang in self.languages.split(',') if lang.strip()]

    @property
    def bio_display(self):
        return self.bio.strip() if self.bio else ''

    @property
    def short_display_name(self):
        first = self.user.first_name.strip()
        last = self.user.last_name.strip()
        if first and last:
            return f'{first} {last[0]}.'
        return self.display_name

    @property
    def list_headline(self):
        if self.headline:
            return self.headline
        parts = []
        if self.job_title:
            parts.append(self.job_title)
        if self.company:
            parts.append(f'в компании {self.company}')
        return ' '.join(parts)


class MentorSkill(models.Model):
    LEVEL_JUNIOR = 'junior'
    LEVEL_MIDDLE = 'middle'
    LEVEL_SENIOR = 'senior'
    LEVEL_LEAD = 'lead'
    LEVEL_CHOICES = [
        (LEVEL_JUNIOR, 'Junior'),
        (LEVEL_MIDDLE, 'Middle'),
        (LEVEL_SENIOR, 'Senior'),
        (LEVEL_LEAD, 'Lead'),
    ]

    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField('Навык', max_length=80)
    level = models.CharField('Уровень', max_length=10, choices=LEVEL_CHOICES, default=LEVEL_MIDDLE)

    class Meta:
        verbose_name = 'Скилл ментора'
        verbose_name_plural = 'Скиллы ментора'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} — {self.get_level_display()}'


class MentorConsultationTopic(models.Model):
    mentor = models.ForeignKey(
        MentorProfile,
        on_delete=models.CASCADE,
        related_name='consultation_topics',
    )
    title = models.CharField('Заголовок', max_length=200)
    description = models.TextField('Описание')
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Запрос ментора'
        verbose_name_plural = 'Запросы ментора'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title


class MentorWorkExperience(models.Model):
    mentor = models.ForeignKey(
        MentorProfile,
        on_delete=models.CASCADE,
        related_name='work_experiences',
    )
    company = models.CharField('Компания', max_length=200)
    period = models.CharField('Период', max_length=120, blank=True)
    start_date = models.DateField('Начало', null=True, blank=True)
    end_date = models.DateField('Окончание', null=True, blank=True)
    is_current = models.BooleanField('По настоящее время', default=False)
    job_title = models.CharField('Должность', max_length=120, blank=True)
    description = models.TextField('Описание', blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Место работы'
        verbose_name_plural = 'Места работы'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.company

    @property
    def period_display(self):
        from accounts.work_period import format_work_period

        formatted = format_work_period(self.start_date, self.end_date, self.is_current)
        return formatted or self.period


class MentorEducation(models.Model):
    mentor = models.ForeignKey(
        MentorProfile,
        on_delete=models.CASCADE,
        related_name='education_entries',
    )
    institution = models.CharField('Учебное заведение', max_length=200)
    specialization = models.CharField('Специальность', max_length=200, blank=True)
    graduation_year = models.PositiveSmallIntegerField('Год окончания', null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Образование'
        verbose_name_plural = 'Образование'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.institution

    @property
    def graduation_display(self):
        if not self.graduation_year:
            return ''
        return f'Окончил в {self.graduation_year} г.'


class MentorProfileLink(models.Model):
    TYPE_PORTFOLIO = 'portfolio'
    TYPE_SOCIAL = 'social'
    TYPE_CHOICES = [
        (TYPE_PORTFOLIO, 'Портфолио'),
        (TYPE_SOCIAL, 'Социальная сеть'),
    ]

    mentor = models.ForeignKey(
        MentorProfile,
        on_delete=models.CASCADE,
        related_name='profile_links',
    )
    link_type = models.CharField('Тип', max_length=10, choices=TYPE_CHOICES)
    platform = models.CharField('Платформа', max_length=20, blank=True)
    url = models.URLField('Ссылка', max_length=500)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Ссылка профиля'
        verbose_name_plural = 'Ссылки профиля'
        ordering = ['link_type', 'sort_order', 'id']

    def __str__(self):
        return self.url

    @property
    def platform_display(self):
        from accounts.social_catalog import SOCIAL_PLATFORM_LABELS

        return SOCIAL_PLATFORM_LABELS.get(self.platform, self.platform)


class MentorProject(models.Model):
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)

    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'


class Review(models.Model):
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='reviews')
    mentee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_written')
    booking = models.OneToOneField(
        'SessionBooking',
        on_delete=models.CASCADE,
        related_name='review',
        null=True,
        blank=True,
        verbose_name='Бронирование',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField('Отзыв', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']


class AvailabilitySlot(models.Model):
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField('Дата')
    start_time = models.TimeField('Начало')
    end_time = models.TimeField('Конец')
    is_available = models.BooleanField('Доступен', default=True)

    class Meta:
        verbose_name = 'Слот доступности'
        verbose_name_plural = 'Слоты доступности'
        ordering = ['date', 'start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['mentor', 'date', 'start_time'],
                name='unique_mentor_slot',
            ),
        ]

    def __str__(self):
        return f'{self.mentor} — {self.date} {self.start_time:%H:%M}'

    @property
    def has_active_booking(self):
        try:
            return self.booking.status == SessionBooking.STATUS_CONFIRMED
        except SessionBooking.DoesNotExist:
            return False

    def is_open_for_booking(self):
        if not self.is_available:
            return False
        try:
            return self.booking.status == SessionBooking.STATUS_CANCELLED
        except SessionBooking.DoesNotExist:
            return True


class SessionBooking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_CONFIRMED, 'Подтверждено'),
        (STATUS_CANCELLED, 'Отменено'),
    ]

    ATTENDANCE_SCHEDULED = 'scheduled'
    ATTENDANCE_CONFIRMED = 'confirmed'
    ATTENDANCE_DECLINED = 'declined'
    ATTENDANCE_CHOICES = [
        (ATTENDANCE_SCHEDULED, 'Записан'),
        (ATTENDANCE_CONFIRMED, 'Подтвердил участие'),
        (ATTENDANCE_DECLINED, 'Отказался'),
    ]

    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='bookings')
    mentee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    slot = models.OneToOneField(
        AvailabilitySlot,
        on_delete=models.PROTECT,
        related_name='booking',
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    attendance_status = models.CharField(
        'Подтверждение участия',
        max_length=12,
        choices=ATTENDANCE_CHOICES,
        default=ATTENDANCE_SCHEDULED,
    )
    notes = models.TextField('Заметки', blank=True)
    session_started_notified = models.BooleanField(
        'Уведомление о начале отправлено',
        default=False,
    )
    session_completed_notified = models.BooleanField(
        'Уведомление о завершении отправлено',
        default=False,
    )
    reminder_24h_sent = models.BooleanField(
        'Напоминание за сутки отправлено',
        default=False,
    )
    reminder_1h_sent = models.BooleanField(
        'Напоминание за час отправлено',
        default=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.mentee} → {self.mentor} ({self.slot.date})'

    def slot_starts_at(self):
        return timezone.make_aware(
            datetime.combine(self.slot.date, self.slot.start_time),
            timezone.get_current_timezone(),
        )

    def slot_ends_at(self):
        return timezone.make_aware(
            datetime.combine(self.slot.date, self.slot.end_time),
            timezone.get_current_timezone(),
        )

    def slot_is_in_progress(self):
        if self.status != self.STATUS_CONFIRMED:
            return False
        now = timezone.now()
        return self.slot_starts_at() <= now < self.slot_ends_at()

    @property
    def needs_attendance_confirmation(self):
        if self.status != self.STATUS_CONFIRMED:
            return False
        if self.attendance_status != self.ATTENDANCE_SCHEDULED:
            return False
        now = timezone.now()
        start = self.slot_starts_at()
        if start <= now:
            return False
        return (start - now) <= timedelta(hours=24)

    @property
    def mentee_attendance_ui(self):
        if self.status == self.STATUS_CANCELLED or self.attendance_status == self.ATTENDANCE_DECLINED:
            return 'cancelled'
        if self.slot_is_in_progress():
            return 'started'
        if self.attendance_status == self.ATTENDANCE_CONFIRMED:
            return 'confirmed'
        if self.needs_attendance_confirmation:
            return 'confirm_action'
        return 'booked'

    @property
    def mentor_session_ui(self):
        if self.status == self.STATUS_CANCELLED:
            return 'cancelled'
        if self.slot_is_in_progress():
            return 'started'
        if self.attendance_status == self.ATTENDANCE_CONFIRMED:
            return 'confirmed'
        if self.needs_attendance_confirmation:
            return 'awaiting'
        return 'booked'

    @property
    def can_cancel_booking(self):
        return (
            self.status == self.STATUS_CONFIRMED
            and self.attendance_status == self.ATTENDANCE_SCHEDULED
            and not self.slot_has_ended()
        )

    @property
    def can_mentor_manage_booking(self):
        return self.status == self.STATUS_CONFIRMED and not self.slot_has_ended()

    def slot_has_ended(self):
        return timezone.now() >= self.slot_ends_at()

    @property
    def session_history_ui(self):
        if self.status == self.STATUS_CANCELLED or self.attendance_status == self.ATTENDANCE_DECLINED:
            return 'cancelled'
        if self.status == self.STATUS_CONFIRMED and self.slot_has_ended():
            return 'completed'
        return None

    @property
    def mentee_history_ui(self):
        return self.session_history_ui

    def confirm_attendance(self):
        self.attendance_status = self.ATTENDANCE_CONFIRMED
        self.save(update_fields=['attendance_status'])

    def cancel_booking(self):
        self.attendance_status = self.ATTENDANCE_DECLINED
        self.status = self.STATUS_CANCELLED
        self.save(update_fields=['attendance_status', 'status'])
        slot = self.slot
        slot.is_available = True
        slot.save(update_fields=['is_available'])

    def decline_attendance(self):
        self.cancel_booking()

    def reschedule_slot(self, date, start_time, end_time):
        if not self.can_mentor_manage_booking:
            raise ValueError('Запись нельзя перенести.')
        if end_time <= start_time:
            raise ValueError('Время окончания должно быть позже начала.')
        slot = self.slot
        conflict = (
            AvailabilitySlot.objects.filter(
                mentor_id=slot.mentor_id,
                date=date,
                start_time=start_time,
            )
            .exclude(pk=slot.pk)
            .exists()
        )
        if conflict:
            raise ValueError('У вас уже есть слот на это время.')
        slot.date = date
        slot.start_time = start_time
        slot.end_time = end_time
        slot.is_available = False
        slot.save(update_fields=['date', 'start_time', 'end_time', 'is_available'])
        self.reminder_24h_sent = False
        self.reminder_1h_sent = False
        self.save(update_fields=['reminder_24h_sent', 'reminder_1h_sent'])


class Notification(models.Model):
    KIND_BOOKING_CREATED = 'booking_created'
    KIND_BOOKING_CANCELLED = 'booking_cancelled'
    KIND_BOOKING_RESCHEDULED = 'booking_rescheduled'
    KIND_BOOKING_REMINDER_24H = 'booking_reminder_24h'
    KIND_BOOKING_REMINDER_1H = 'booking_reminder_1h'
    KIND_ATTENDANCE_CONFIRM = 'attendance_confirm'
    KIND_SESSION_STARTED = 'session_started'
    KIND_SESSION_COMPLETED = 'session_completed'
    KIND_PROFILE_INCOMPLETE = 'profile_incomplete'
    KIND_ONBOARDING_INCOMPLETE = 'onboarding_incomplete'
    KIND_CHOICES = [
        (KIND_BOOKING_CREATED, 'Запись создана'),
        (KIND_BOOKING_CANCELLED, 'Запись отменена'),
        (KIND_BOOKING_RESCHEDULED, 'Запись перенесена'),
        (KIND_BOOKING_REMINDER_24H, 'Напоминание за сутки'),
        (KIND_BOOKING_REMINDER_1H, 'Напоминание за час'),
        (KIND_ATTENDANCE_CONFIRM, 'Подтверждение участия'),
        (KIND_SESSION_STARTED, 'Сессия началась'),
        (KIND_SESSION_COMPLETED, 'Сессия завершена'),
        (KIND_PROFILE_INCOMPLETE, 'Профиль не заполнен'),
        (KIND_ONBOARDING_INCOMPLETE, 'Онбординг не завершён'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    kind = models.CharField('Тип', max_length=40, choices=KIND_CHOICES)
    title = models.CharField('Заголовок', max_length=200)
    body = models.TextField('Текст')
    link = models.CharField('Ссылка', max_length=500, blank=True)
    booking = models.ForeignKey(
        SessionBooking,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'{self.title} → {self.user}'


def chat_attachment_upload_to(instance, filename):
    from django.utils import timezone

    safe_name = os.path.basename(filename)
    now = timezone.now()
    conversation_id = instance.message.conversation_id
    return (
        f'chat/attachments/conversation_{conversation_id}/'
        f'{now:%Y}/{now:%m}/{safe_name}'
    )


class Conversation(models.Model):
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='conversations')
    mentee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mentee_conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Диалог'
        verbose_name_plural = 'Диалоги'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['mentor', 'mentee'], name='unique_mentor_mentee_conversation'),
        ]

    def __str__(self):
        return f'{self.mentee} ↔ {self.mentor}'

    @property
    def other_party_for_mentee(self):
        return self.mentor.display_name

    @property
    def other_party_for_mentor(self):
        mentee = self.mentee
        return mentee.get_full_name() or mentee.username


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_messages',
    )
    text = models.TextField('Текст', blank=True)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Ответ на',
    )
    is_system = models.BooleanField('Системное', default=False)
    booking = models.ForeignKey(
        SessionBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_messages',
    )
    is_deleted = models.BooleanField('Удалено', default=False, db_index=True)
    deleted_at = models.DateTimeField('Удалено в', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']

    @property
    def system_variant(self):
        if not self.is_system or not self.text:
            return 'default'
        if ' началась (' in self.text:
            return 'started'
        if ' завершена (' in self.text:
            return 'completed'
        if ' отменена.' in self.text:
            return 'cancelled'
        return 'default'

    def __str__(self):
        if self.is_deleted:
            return f'Удалённое сообщение #{self.pk}'
        if self.text:
            return self.text[:50]
        attachment = self.attachments.first()
        if attachment:
            return attachment.name[:50]
        return f'Сообщение #{self.pk}'


class MessageAttachment(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='Сообщение',
    )
    file = models.FileField('Файл', upload_to=chat_attachment_upload_to)
    name = models.CharField('Имя файла', max_length=255)
    mime_type = models.CharField('MIME-тип', max_length=127, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Вложение в чате'
        verbose_name_plural = 'Вложения в чате'
        ordering = ['pk']

    def __str__(self):
        return self.name

    @property
    def is_image(self):
        name = (self.name or self.file.name).lower()
        return name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))

    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)

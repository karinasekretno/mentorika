import mimetypes
import os
import re
from pathlib import Path

from django.core.exceptions import ValidationError
from django.template.defaultfilters import date as format_date
from django.urls import reverse
from django.utils import timezone

from accounts.models import Conversation, Message, MessageAttachment, Review, SessionBooking

CHAT_MESSAGE_MAX_LENGTH = 2000
CHAT_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
CHAT_MAX_ATTACHMENTS_PER_MESSAGE = 10
CHAT_ATTACHMENT_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.rtf',
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.zip', '.rar', '.7z',
    '.xls', '.xlsx', '.ppt', '.pptx',
    '.csv',
}
CHAT_URL_PATTERN = re.compile(r'https?://[^\s<>"\'\]\)]+', re.IGNORECASE)
CHAT_SHARED_MEDIA_TYPES = {'images', 'files', 'links'}
CHAT_ATTACHMENT_MIME_TYPES = {
    '.pdf': {'application/pdf'},
    '.doc': {'application/msword'},
    '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
    '.txt': {'text/plain'},
    '.rtf': {'text/rtf', 'application/rtf'},
    '.png': {'image/png'},
    '.jpg': {'image/jpeg'},
    '.jpeg': {'image/jpeg'},
    '.gif': {'image/gif'},
    '.webp': {'image/webp'},
    '.zip': {'application/zip', 'application/x-zip-compressed'},
    '.rar': {'application/vnd.rar', 'application/x-rar-compressed'},
    '.7z': {'application/x-7z-compressed'},
    '.xls': {'application/vnd.ms-excel'},
    '.xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
    '.ppt': {'application/vnd.ms-powerpoint'},
    '.pptx': {'application/vnd.openxmlformats-officedocument.presentationml.presentation'},
    '.csv': {'text/csv', 'application/csv', 'text/plain'},
}


def sanitize_attachment_filename(filename):
    safe_name = Path(filename).name.strip()
    if not safe_name or safe_name in {'.', '..'}:
        raise ValidationError('Некорректное имя файла.')
    return safe_name[:255]


def resolve_attachment_mime_type(uploaded_file, ext):
    content_type = (getattr(uploaded_file, 'content_type', '') or '').split(';', 1)[0].strip().lower()
    allowed = CHAT_ATTACHMENT_MIME_TYPES.get(ext, set())
    if content_type and content_type != 'application/octet-stream':
        if allowed and content_type not in allowed:
            raise ValidationError('Содержимое файла не соответствует расширению.')
        return content_type
    guessed, _encoding = mimetypes.guess_type(f'name{ext}')
    if guessed:
        return guessed
    if allowed:
        return next(iter(allowed))
    return 'application/octet-stream'


def validate_chat_attachment(uploaded_file):
    if uploaded_file.size > CHAT_ATTACHMENT_MAX_BYTES:
        raise ValidationError('Файл слишком большой. Максимум — 10 МБ.')
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in CHAT_ATTACHMENT_EXTENSIONS:
        raise ValidationError('Этот тип файла не поддерживается.')
    sanitize_attachment_filename(uploaded_file.name)
    resolve_attachment_mime_type(uploaded_file, ext)


def prepare_chat_attachment(uploaded_file):
    validate_chat_attachment(uploaded_file)
    name = sanitize_attachment_filename(uploaded_file.name)
    ext = os.path.splitext(name)[1].lower()
    mime_type = resolve_attachment_mime_type(uploaded_file, ext)
    return {
        'file': uploaded_file,
        'name': name,
        'mime_type': mime_type,
    }


def attachment_download_url(attachment):
    return reverse('chat_attachment_download', kwargs={
        'conversation_id': attachment.message.conversation_id,
        'attachment_id': attachment.pk,
    })


def extract_links_from_text(text):
    if not text:
        return []
    links = []
    for match in CHAT_URL_PATTERN.findall(text):
        cleaned = match.rstrip('.,;:!?)')
        if cleaned:
            links.append(cleaned)
    return links


def shared_media_month_label(dt):
    from django.utils.formats import date_format

    return date_format(dt, 'F Y', use_l10n=True).upper()


def serialize_shared_attachment(attachment):
    created_at = attachment.message.created_at
    return {
        'id': f'attachment-{attachment.pk}',
        'type': 'image' if attachment.is_image else 'file',
        'url': attachment_download_url(attachment),
        'name': attachment.name or os.path.basename(attachment.file.name),
        'message_id': attachment.message_id,
        'created_at': created_at.isoformat(),
        'month_key': created_at.strftime('%Y-%m'),
        'month_label': shared_media_month_label(created_at),
    }


def get_shared_media_items(conversation, media_type):
    if media_type not in CHAT_SHARED_MEDIA_TYPES:
        raise ValidationError('Некорректный тип вложений.')

    if media_type in {'images', 'files'}:
        attachments = MessageAttachment.objects.filter(
            message__conversation=conversation,
            message__is_deleted=False,
        ).select_related('message').order_by('-message__created_at', '-pk')
        items = []
        for attachment in attachments:
            if media_type == 'images' and not attachment.is_image:
                continue
            if media_type == 'files' and attachment.is_image:
                continue
            items.append(serialize_shared_attachment(attachment))
        return items

    items = []
    messages = active_messages_queryset(conversation).exclude(text='').order_by('-created_at')
    for message in messages:
        for index, url in enumerate(extract_links_from_text(message.text)):
            created_at = message.created_at
            items.append({
                'id': f'link-{message.pk}-{index}',
                'type': 'link',
                'url': url,
                'name': url,
                'message_id': message.pk,
                'created_at': created_at.isoformat(),
                'month_key': created_at.strftime('%Y-%m'),
                'month_label': shared_media_month_label(created_at),
            })
    return items


def serialize_attachment(attachment):
    return {
        'id': attachment.pk,
        'url': attachment_download_url(attachment),
        'name': attachment.name or os.path.basename(attachment.file.name),
        'is_image': attachment.is_image,
    }


def user_can_delete_message(user, message):
    return (
        not message.is_system
        and not message.is_deleted
        and message.sender_id == user.id
    )


def active_messages_queryset(conversation):
    return conversation.messages.filter(is_deleted=False)


def get_deleted_message_ids(conversation, visible_ids):
    if not visible_ids:
        return []
    existing_ids = set(
        conversation.messages.filter(
            pk__in=visible_ids,
            is_deleted=False,
        ).values_list('pk', flat=True)
    )
    return [message_id for message_id in visible_ids if message_id not in existing_ids]


def soft_delete_message(message):
    for attachment in list(message.attachments.all()):
        attachment.delete()
    message.text = ''
    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.save(update_fields=['text', 'is_deleted', 'deleted_at'])


def message_sender_label(message, user):
    if message.sender_id == user.id:
        return 'Вы'
    if message.sender:
        return message.sender.get_full_name() or message.sender.username
    return 'Участник'


def message_preview(message):
    if message.is_deleted:
        return 'Сообщение удалено'
    if message.text:
        text = message.text.strip().replace('\n', ' ')
        return text[:120] + ('…' if len(text) > 120 else '')
    attachment = message.attachments.first()
    if attachment:
        return attachment.name
    return 'Вложение'


def serialize_reply(message, user):
    if not message.reply_to_id:
        return None
    reply = message.reply_to
    return {
        'id': reply.pk,
        'sender_name': message_sender_label(reply, user),
        'text': message_preview(reply),
    }


def get_session_rating_prompt(message, user):
    if not message.is_system or message.system_variant != 'completed':
        return None
    if not message.booking_id:
        return None
    if not getattr(user, 'mentee_profile', None):
        return None
    if message.conversation.mentee_id != user.id:
        return None
    booking = message.booking
    if booking.status != SessionBooking.STATUS_CONFIRMED:
        return None
    if not booking.slot_has_ended():
        return None
    review = Review.objects.filter(booking=booking).first()
    return {
        'booking_id': booking.pk,
        'rating': review.rating if review else None,
        'can_rate': review is None,
    }


def serialize_message(message, user):
    return {
        'id': message.pk,
        'is_system': message.is_system,
        'system_variant': message.system_variant if message.is_system else None,
        'rating_prompt': get_session_rating_prompt(message, user),
        'is_own': bool(message.sender_id and message.sender_id == user.id),
        'can_delete': user_can_delete_message(user, message),
        'sender_name': message_sender_label(message, user),
        'preview': message_preview(message),
        'text': message.text,
        'reply_to': serialize_reply(message, user),
        'attachments': [serialize_attachment(attachment) for attachment in message.attachments.all()],
        'created_at': message.created_at.isoformat(),
    }


def create_message_attachments(message, uploaded_files):
    attachments = []
    for uploaded_file in uploaded_files:
        payload = prepare_chat_attachment(uploaded_file)
        attachments.append(MessageAttachment.objects.create(
            message=message,
            file=payload['file'],
            name=payload['name'],
            mime_type=payload['mime_type'],
        ))
    return attachments


def format_booking_datetime(slot):
    date_part = format_date(slot.date, 'j E Y')
    time_part = f'{slot.start_time:%H:%M}–{slot.end_time:%H:%M}'
    return date_part, time_part


def booking_system_message(booking):
    mentor_name = booking.mentor.display_name
    date_part, time_part = format_booking_datetime(booking.slot)
    return f'Вы записаны к {mentor_name} на {date_part}, {time_part}.'


def booking_cancelled_message(booking):
    mentor_name = booking.mentor.display_name
    date_part, time_part = format_booking_datetime(booking.slot)
    return f'Запись к {mentor_name} на {date_part}, {time_part} отменена.'


def booking_rescheduled_message(booking):
    mentor_name = booking.mentor.display_name
    date_part, time_part = format_booking_datetime(booking.slot)
    return f'Сессия с {mentor_name} перенесена на {date_part}, {time_part}.'


def booking_session_started_message(booking):
    mentor_name = booking.mentor.display_name
    date_part, time_part = format_booking_datetime(booking.slot)
    return f'Сессия с {mentor_name} началась ({date_part}, {time_part}).'


def booking_session_completed_message(booking):
    mentor_name = booking.mentor.display_name
    date_part, time_part = format_booking_datetime(booking.slot)
    return f'Сессия с {mentor_name} завершена ({date_part}, {time_part}).'


def process_booking_lifecycle_notifications(mentor=None, mentee=None):
    qs = SessionBooking.objects.filter(
        status=SessionBooking.STATUS_CONFIRMED,
    ).select_related('slot', 'mentor', 'mentor__user', 'mentee')
    if mentor is not None:
        qs = qs.filter(mentor=mentor)
    if mentee is not None:
        qs = qs.filter(mentee=mentee)

    now = timezone.now()
    for booking in qs:
        updates = []
        if not booking.session_started_notified and now >= booking.slot_starts_at():
            notify_booking_event_in_chat(booking, booking_session_started_message(booking))
            from accounts.notification_utils import _notify_session_started
            _notify_session_started(booking)
            booking.session_started_notified = True
            updates.append('session_started_notified')
        if not booking.session_completed_notified and booking.slot_has_ended():
            notify_booking_event_in_chat(booking, booking_session_completed_message(booking))
            from accounts.notification_utils import _notify_session_completed
            _notify_session_completed(booking)
            booking.session_completed_notified = True
            updates.append('session_completed_notified')
            from accounts.review_utils import recalculate_mentor_stats
            recalculate_mentor_stats(booking.mentor)
        if updates:
            booking.save(update_fields=updates)


def notify_booking_in_chat(booking):
    conversation, _created = Conversation.objects.get_or_create(
        mentor=booking.mentor,
        mentee=booking.mentee,
    )
    Message.objects.create(
        conversation=conversation,
        is_system=True,
        text=booking_system_message(booking),
        booking=booking,
    )
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    return conversation


def notify_booking_event_in_chat(booking, text):
    conversation, _created = Conversation.objects.get_or_create(
        mentor=booking.mentor,
        mentee=booking.mentee,
    )
    Message.objects.create(
        conversation=conversation,
        is_system=True,
        text=text,
        booking=booking,
    )
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    return conversation


def user_can_access_conversation(user, conversation):
    if conversation.mentee_id == user.id:
        return True
    if hasattr(user, 'mentor_profile') and conversation.mentor_id == user.mentor_profile.id:
        return True
    return False

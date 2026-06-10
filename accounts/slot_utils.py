from collections import defaultdict
from datetime import date, time, timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.formats import date_format

from accounts.models import AvailabilitySlot, SessionBooking

MAX_NEAREST_SLOTS = 3


def open_slots_queryset(mentor_ids=None):
    today = timezone.localdate()
    now = timezone.localtime().time()
    qs = (
        AvailabilitySlot.objects.filter(
            is_available=True,
            date__gte=today,
        )
        .filter(
            Q(booking__isnull=True) | Q(booking__status=SessionBooking.STATUS_CANCELLED),
        )
        .filter(Q(date__gt=today) | Q(date=today, end_time__gt=now))
        .order_by('mentor_id', 'date', 'start_time')
    )
    if mentor_ids is not None:
        qs = qs.filter(mentor_id__in=mentor_ids)
    return qs


def format_slot_date_label(slot_date, today=None):
    today = today or timezone.localdate()
    if slot_date == today:
        return 'сегодня'
    if slot_date == today + timedelta(days=1):
        return 'завтра'
    return date_format(slot_date, 'j E')


def nearest_slot_datetime_by_mentor(mentor_ids):
    nearest = {}
    for slot in open_slots_queryset(mentor_ids):
        if slot.mentor_id not in nearest:
            nearest[slot.mentor_id] = (slot.date, slot.start_time)
    return nearest


def sort_mentors_by_nearest_slot(mentors):
    if not mentors:
        return mentors

    nearest = nearest_slot_datetime_by_mentor([mentor.pk for mentor in mentors])
    far_future = (date.max, time.max)

    def sort_key(mentor):
        slot_when = nearest.get(mentor.pk)
        if slot_when is None:
            return (1, far_future)
        return (0, slot_when)

    return sorted(mentors, key=sort_key)


def nearest_slots_by_mentor(mentor_ids):
    if not mentor_ids:
        return {}

    today = timezone.localdate()
    slots_by_mentor = defaultdict(list)
    for slot in open_slots_queryset(mentor_ids):
        slots_by_mentor[slot.mentor_id].append(slot)

    result = {}
    for mentor_id, mentor_slots in slots_by_mentor.items():
        nearest_date = mentor_slots[0].date
        day_slots = [
            slot for slot in mentor_slots if slot.date == nearest_date
        ][:MAX_NEAREST_SLOTS]
        result[mentor_id] = {
            'date_label': format_slot_date_label(nearest_date, today),
            'slots': [
                {
                    'id': slot.pk,
                    'time': slot.start_time.strftime('%H:%M'),
                    'date': slot.date.isoformat(),
                }
                for slot in day_slots
            ],
        }
    return result

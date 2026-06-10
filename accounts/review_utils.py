from decimal import Decimal

from django.db.models import Avg, Q
from django.utils import timezone

from accounts.models import MentorProfile, Review, SessionBooking

RATING_SESSION_WINDOW = 40


def recent_session_review_ids(mentor, limit=RATING_SESSION_WINDOW):
    return list(
        Review.objects.filter(mentor=mentor, booking__isnull=False)
        .order_by('-booking__slot__date', '-booking__slot__start_time', '-pk')
        .values_list('pk', flat=True)[:limit]
    )


def calculate_mentor_rating(mentor):
    recent_ids = recent_session_review_ids(mentor)
    if not recent_ids:
        return Decimal('0')
    agg = Review.objects.filter(pk__in=recent_ids).aggregate(avg=Avg('rating'))
    if agg['avg'] is None:
        return Decimal('0')
    return Decimal(str(round(float(agg['avg']), 2)))


def calculate_completed_sessions_count(mentor):
    now = timezone.localtime()
    return SessionBooking.objects.filter(
        mentor=mentor,
        status=SessionBooking.STATUS_CONFIRMED,
    ).filter(
        Q(slot__date__lt=now.date())
        | Q(slot__date=now.date(), slot__end_time__lte=now.time())
    ).count()


def recalculate_mentor_stats(mentor):
    mentor.rating = calculate_mentor_rating(mentor)
    mentor.sessions_count = calculate_completed_sessions_count(mentor)
    mentor.save(update_fields=['rating', 'sessions_count'])


def recalculate_mentor_rating(mentor):
    recalculate_mentor_stats(mentor)


def recalculate_all_mentor_ratings():
    updated = 0
    for mentor in MentorProfile.objects.all().iterator():
        recalculate_mentor_stats(mentor)
        updated += 1
    return updated


def review_feedback_complete(review):
    return bool(review and review.text.strip())


def booking_needs_mentee_feedback(booking):
    try:
        review = booking.review
    except Review.DoesNotExist:
        return True
    return not review_feedback_complete(review)


def create_session_review(booking, mentee, rating, text=''):
    review = Review.objects.create(
        mentor=booking.mentor,
        mentee=mentee,
        booking=booking,
        rating=rating,
        text=(text or '').strip(),
    )
    recalculate_mentor_stats(booking.mentor)
    return review

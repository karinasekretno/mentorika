from accounts.models import RecommendationEvent, RecommendationExposure, SessionBooking

SESSION_EXPOSURE_TOKEN = 'recommendation_tracking_token'
SESSION_EXPOSURE_MENTOR_SLUG = 'recommendation_mentor_slug'


def _store_active_recommendation(request, exposure):
    request.session[SESSION_EXPOSURE_TOKEN] = str(exposure.tracking_token)
    request.session[SESSION_EXPOSURE_MENTOR_SLUG] = exposure.mentor.slug
    request.session.modified = True


def get_active_exposure(request, mentor):
    if not request.user.is_authenticated:
        return None
    token = request.session.get(SESSION_EXPOSURE_TOKEN)
    slug = request.session.get(SESSION_EXPOSURE_MENTOR_SLUG)
    if not token or slug != mentor.slug:
        return None
    try:
        return RecommendationExposure.objects.get(
            tracking_token=token,
            mentee=request.user,
            mentor=mentor,
        )
    except (RecommendationExposure.DoesNotExist, ValueError):
        return None


def find_exposure_for_booking(booking):
    linked = RecommendationEvent.objects.filter(
        booking=booking,
        event_type=RecommendationEvent.EVENT_BOOKING_CREATED,
    ).select_related('exposure').first()
    if linked:
        return linked.exposure

    return (
        RecommendationExposure.objects.filter(
            mentee=booking.mentee,
            mentor=booking.mentor,
            created_at__lte=booking.created_at,
        )
        .order_by('-created_at')
        .first()
    )


def record_event_once(exposure, event_type, *, booking=None, review=None):
    if exposure is None:
        return None, False

    lookup = {
        'exposure': exposure,
        'event_type': event_type,
    }
    if booking is not None:
        lookup['booking'] = booking
    if review is not None:
        lookup['review'] = review

    event, created = RecommendationEvent.objects.get_or_create(**lookup)
    return event, created


def handle_profile_opened_from_recommendation(request, tracking_token, mentor):
    if not tracking_token or not request.user.is_authenticated:
        return None

    try:
        exposure = RecommendationExposure.objects.get(
            tracking_token=tracking_token,
            mentee=request.user,
            mentor=mentor,
        )
    except (RecommendationExposure.DoesNotExist, ValueError):
        return None

    record_event_once(exposure, RecommendationEvent.EVENT_PROFILE_OPENED)
    _store_active_recommendation(request, exposure)
    return exposure


def has_prior_confirmed_or_completed_session(mentee, mentor, exclude_booking_id=None):
    bookings = SessionBooking.objects.filter(
        mentor=mentor,
        mentee=mentee,
        status=SessionBooking.STATUS_CONFIRMED,
    )
    if exclude_booking_id is not None:
        bookings = bookings.exclude(pk=exclude_booking_id)

    for booking in bookings.select_related('slot'):
        if booking.attendance_status == SessionBooking.ATTENDANCE_CONFIRMED:
            return True
        if booking.slot_has_ended():
            return True
    return False


def record_booking_created(request, booking):
    exposure = get_active_exposure(request, booking.mentor)
    if exposure is None:
        return None, False

    event, created = record_event_once(
        exposure,
        RecommendationEvent.EVENT_BOOKING_CREATED,
        booking=booking,
    )

    if has_prior_confirmed_or_completed_session(
        booking.mentee,
        booking.mentor,
        exclude_booking_id=booking.pk,
    ):
        record_event_once(
            exposure,
            RecommendationEvent.EVENT_REPEAT_BOOKING,
            booking=booking,
        )

    return event, created


def record_attendance_confirmed(booking):
    exposure = find_exposure_for_booking(booking)
    record_event_once(
        exposure,
        RecommendationEvent.EVENT_ATTENDANCE_CONFIRMED,
        booking=booking,
    )


def record_booking_cancelled(booking):
    exposure = find_exposure_for_booking(booking)
    record_event_once(
        exposure,
        RecommendationEvent.EVENT_BOOKING_CANCELLED,
        booking=booking,
    )


def record_session_completed(booking):
    exposure = find_exposure_for_booking(booking)
    record_event_once(
        exposure,
        RecommendationEvent.EVENT_SESSION_COMPLETED,
        booking=booking,
    )


def record_review_created(booking, review):
    exposure = find_exposure_for_booking(booking)
    record_event_once(
        exposure,
        RecommendationEvent.EVENT_REVIEW_CREATED,
        booking=booking,
        review=review,
    )

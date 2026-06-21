import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef

from accounts.models import RecommendationEvent, RecommendationExposure


class Command(BaseCommand):
    help = 'Export pseudonymized recommendation dataset to CSV for future model training.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default='recommendation_dataset.csv',
            help='Path to output CSV file',
        )

    def handle(self, *args, **options):
        output_path = Path(options['output']).resolve()
        event_types = {
            RecommendationEvent.EVENT_PROFILE_OPENED: 'profile_opened',
            RecommendationEvent.EVENT_BOOKING_CREATED: 'booking_created',
            RecommendationEvent.EVENT_ATTENDANCE_CONFIRMED: 'attendance_confirmed',
            RecommendationEvent.EVENT_BOOKING_CANCELLED: 'booking_cancelled',
            RecommendationEvent.EVENT_SESSION_COMPLETED: 'session_completed',
            RecommendationEvent.EVENT_REVIEW_CREATED: 'review_created',
            RecommendationEvent.EVENT_REPEAT_BOOKING: 'repeat_booking',
        }

        exposures = RecommendationExposure.objects.order_by('created_at')

        for event_type in event_types:
            exposures = exposures.annotate(**{
                f'has_{event_types[event_type]}': Exists(
                    RecommendationEvent.objects.filter(
                        exposure=OuterRef('pk'),
                        event_type=event_type,
                    )
                ),
            })

        headers = [
            'exposure_id',
            'mentee_id',
            'mentor_id',
            'rank',
            'content_score',
            'rating_score',
            'experience_score',
            'final_score',
            'profile_opened',
            'booking_created',
            'attendance_confirmed',
            'booking_cancelled',
            'session_completed',
            'review_created',
            'review_rating',
            'repeat_booking',
            'exposure_created_at',
            'algorithm_version',
        ]

        with output_path.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)
            for exposure in exposures.iterator():
                review_rating_value = ''
                review_event = exposure.events.filter(
                    event_type=RecommendationEvent.EVENT_REVIEW_CREATED,
                    review__isnull=False,
                ).select_related('review').first()
                if review_event and review_event.review:
                    review_rating_value = review_event.review.rating

                writer.writerow([
                    exposure.pk,
                    exposure.mentee_id,
                    exposure.mentor_id,
                    exposure.rank,
                    exposure.content_score,
                    exposure.rating_score,
                    exposure.experience_score,
                    exposure.final_score,
                    int(getattr(exposure, f'has_{event_types[RecommendationEvent.EVENT_PROFILE_OPENED]}', False)),
                    int(getattr(exposure, f'has_{event_types[RecommendationEvent.EVENT_BOOKING_CREATED]}', False)),
                    int(getattr(exposure, f'has_{event_types[RecommendationEvent.EVENT_ATTENDANCE_CONFIRMED]}', False)),
                    int(getattr(exposure, f'has_{event_types[RecommendationEvent.EVENT_BOOKING_CANCELLED]}', False)),
                    int(getattr(exposure, f'has_{event_types[RecommendationEvent.EVENT_SESSION_COMPLETED]}', False)),
                    int(getattr(exposure, f'has_{event_types[RecommendationEvent.EVENT_REVIEW_CREATED]}', False)),
                    review_rating_value,
                    int(getattr(exposure, f'has_{event_types[RecommendationEvent.EVENT_REPEAT_BOOKING]}', False)),
                    exposure.created_at.isoformat(),
                    exposure.algorithm_version,
                ])

        self.stdout.write(self.style.SUCCESS(f'Exported dataset to {output_path}'))

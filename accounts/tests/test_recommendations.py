import csv
import io
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase

from accounts.models import (
    AvailabilitySlot,
    MenteeInterest,
    MenteeProfile,
    MentorConsultationTopic,
    MentorProfile,
    MentorSkill,
    RecommendationEvent,
    RecommendationExposure,
    SessionBooking,
    UserProfile,
)
from accounts.recommendation_events import (
    handle_profile_opened_from_recommendation,
    record_booking_created,
    record_event_once,
)
from accounts.recommendation_utils import (
    _compute_tfidf_scores,
    build_mentee_profile_text,
    landing_mentors_for_request,
    recommend_mentors_for_mentee,
)


class RecommendationAlgorithmTests(TestCase):
    def setUp(self):
        self.mentee_user = User.objects.create_user(
            username='mentee1',
            email='mentee1@example.com',
            password='pass12345',
        )
        UserProfile.objects.create(
            user=self.mentee_user,
            role=UserProfile.ROLE_MENTEE,
            onboarding_completed=True,
            email_verified=True,
        )
        self.mentee = MenteeProfile.objects.create(
            user=self.mentee_user,
            goals='Хочу прокачать Python и Django для backend-разработки',
        )
        MenteeInterest.objects.create(mentee=self.mentee, name='Python')
        MenteeInterest.objects.create(mentee=self.mentee, name='Django')

        self.python_user = User.objects.create_user(username='python_mentor', password='pass12345')
        self.python_mentor = MentorProfile.objects.create(
            user=self.python_user,
            bio='Backend-разработчик, Python Django FastAPI',
            job_title='Python Developer',
            company='TechCo',
            rating=3.5,
            sessions_count=2,
        )
        MentorSkill.objects.create(mentor=self.python_mentor, name='Python')
        MentorSkill.objects.create(mentor=self.python_mentor, name='Django')
        MentorConsultationTopic.objects.create(
            mentor=self.python_mentor,
            title='Backend на Django',
            description='Архитектура REST API и ORM',
        )

        self.design_user = User.objects.create_user(username='design_mentor', password='pass12345')
        self.design_mentor = MentorProfile.objects.create(
            user=self.design_user,
            bio='UX/UI дизайн и исследования',
            job_title='UX Lead',
            company='DesignCo',
            rating=5.0,
            sessions_count=50,
        )
        MentorSkill.objects.create(mentor=self.design_mentor, name='UI/UX')
        MentorConsultationTopic.objects.create(
            mentor=self.design_mentor,
            title='Продуктовый дизайн',
            description='Пользовательские интерфейсы',
        )

    def test_python_mentee_prefers_matching_mentor_over_high_rating(self):
        cards, _interests, personalized, scored_items = recommend_mentors_for_mentee(self.mentee)

        self.assertTrue(personalized)
        self.assertGreaterEqual(len(cards), 1)
        self.assertEqual(cards[0]['slug'], self.python_mentor.slug)
        self.assertGreater(scored_items[0]['content_score'], 0)

    def test_empty_interests_and_goals_use_popular_fallback(self):
        empty_user = User.objects.create_user(username='empty_mentee', password='pass12345')
        UserProfile.objects.create(
            user=empty_user,
            role=UserProfile.ROLE_MENTEE,
            onboarding_completed=True,
        )
        empty_mentee = MenteeProfile.objects.create(user=empty_user)

        cards, _interests, personalized, scored_items = recommend_mentors_for_mentee(empty_mentee)

        self.assertFalse(personalized)
        self.assertEqual(scored_items, [])
        self.assertGreaterEqual(len(cards), 1)

    def test_incomplete_mentor_profile_does_not_break_algorithm(self):
        sparse_user = User.objects.create_user(username='sparse', password='pass12345')
        MentorProfile.objects.create(user=sparse_user, bio='Ментор')

        cards, _interests, personalized, _scored = recommend_mentors_for_mentee(self.mentee)

        self.assertTrue(personalized)
        self.assertGreaterEqual(len(cards), 1)

    def test_high_rating_does_not_replace_topic_match(self):
        mentee_text = build_mentee_profile_text(self.mentee)
        scores = _compute_tfidf_scores(mentee_text, [self.python_mentor, self.design_mentor])

        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[0], 0)


class RecommendationTrackingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.mentee_user = User.objects.create_user(
            username='track_mentee',
            email='track@example.com',
            password='pass12345',
        )
        UserProfile.objects.create(
            user=self.mentee_user,
            role=UserProfile.ROLE_MENTEE,
            onboarding_completed=True,
            email_verified=True,
        )
        self.mentee = MenteeProfile.objects.create(
            user=self.mentee_user,
            goals='Python backend',
        )
        MenteeInterest.objects.create(mentee=self.mentee, name='Python')

        mentor_user = User.objects.create_user(username='track_mentor', password='pass12345')
        self.mentor = MentorProfile.objects.create(
            user=mentor_user,
            bio='Python mentor',
            job_title='Developer',
        )
        MentorSkill.objects.create(mentor=self.mentor, name='Python')

        other_user = User.objects.create_user(username='other_mentee', password='pass12345')
        UserProfile.objects.create(user=other_user, role=UserProfile.ROLE_MENTEE, onboarding_completed=True)

    def _create_exposure(self):
        return RecommendationExposure.objects.create(
            mentee=self.mentee_user,
            mentor=self.mentor,
            rank=1,
            content_score=0.8,
            rating_score=0.4,
            experience_score=0.1,
            final_score=0.7,
        )

    def test_personalized_landing_creates_exposure(self):
        self.client.login(username='track_mentee', password='pass12345')
        context = landing_mentors_for_request(self.mentee_user)

        self.assertTrue(context['mentors_personalized'])
        self.assertEqual(RecommendationExposure.objects.filter(mentee=self.mentee_user).count(), 1)
        self.assertTrue(context['mentors'][0]['recommendation_tracking_token'])

    def test_profile_opened_event_created_once(self):
        exposure = self._create_exposure()
        request = self.client.request().wsgi_request
        request.user = self.mentee_user
        request.session = self.client.session

        handle_profile_opened_from_recommendation(request, str(exposure.tracking_token), self.mentor)
        handle_profile_opened_from_recommendation(request, str(exposure.tracking_token), self.mentor)

        self.assertEqual(
            RecommendationEvent.objects.filter(
                exposure=exposure,
                event_type=RecommendationEvent.EVENT_PROFILE_OPENED,
            ).count(),
            1,
        )

    def test_invalid_token_does_not_create_event(self):
        exposure = self._create_exposure()
        request = self.client.request().wsgi_request
        request.user = self.mentee_user
        request.session = self.client.session

        result = handle_profile_opened_from_recommendation(
            request,
            str(exposure.tracking_token),
            self.mentor,
        )
        self.assertIsNotNone(result)

        other_exposure = RecommendationExposure.objects.create(
            mentee=User.objects.create_user(username='intruder', password='pass12345'),
            mentor=self.mentor,
            rank=1,
            content_score=0.1,
            rating_score=0.1,
            experience_score=0.1,
            final_score=0.1,
        )
        blocked = handle_profile_opened_from_recommendation(
            request,
            str(other_exposure.tracking_token),
            self.mentor,
        )
        self.assertIsNone(blocked)

    def test_booking_created_event_without_duplicates(self):
        exposure = self._create_exposure()
        slot = AvailabilitySlot.objects.create(
            mentor=self.mentor,
            date=date.today() + timedelta(days=3),
            start_time=time(15, 0),
            end_time=time(16, 0),
            is_available=False,
        )
        booking = SessionBooking.objects.create(
            mentor=self.mentor,
            mentee=self.mentee_user,
            slot=slot,
        )

        request = self.client.request().wsgi_request
        request.user = self.mentee_user
        request.session = self.client.session
        request.session['recommendation_tracking_token'] = str(exposure.tracking_token)
        request.session['recommendation_mentor_slug'] = self.mentor.slug

        record_booking_created(request, booking)
        record_booking_created(request, booking)

        self.assertEqual(
            RecommendationEvent.objects.filter(
                exposure=exposure,
                event_type=RecommendationEvent.EVENT_BOOKING_CREATED,
                booking=booking,
            ).count(),
            1,
        )

    def test_record_event_once_is_idempotent(self):
        exposure = self._create_exposure()
        record_event_once(exposure, RecommendationEvent.EVENT_PROFILE_OPENED)
        record_event_once(exposure, RecommendationEvent.EVENT_PROFILE_OPENED)
        self.assertEqual(RecommendationEvent.objects.filter(exposure=exposure).count(), 1)


class RecommendationExportTests(TestCase):
    def test_export_command_writes_csv_without_pii(self):
        mentee_user = User.objects.create_user(
            username='export_mentee',
            email='secret@example.com',
            password='pass12345',
        )
        mentor_user = User.objects.create_user(username='export_mentor', password='pass12345')
        mentor = MentorProfile.objects.create(user=mentor_user, bio='Python', job_title='Dev')
        exposure = RecommendationExposure.objects.create(
            mentee=mentee_user,
            mentor=mentor,
            rank=1,
            content_score=0.5,
            rating_score=0.2,
            experience_score=0.1,
            final_score=0.45,
        )
        RecommendationEvent.objects.create(
            exposure=exposure,
            event_type=RecommendationEvent.EVENT_PROFILE_OPENED,
        )

        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            tmp_path = tmp.name
        try:
            call_command('export_recommendation_dataset', f'--output={tmp_path}')
            with open(tmp_path, encoding='utf-8') as csv_file:
                content = csv_file.read()
        finally:
            os.unlink(tmp_path)

        self.assertIn('exposure_id', content)
        self.assertNotIn('secret@example.com', content)
        self.assertNotIn('export_mentee', content)
        self.assertNotIn('Python', content)

        reader = csv.DictReader(io.StringIO(content))
        row = next(reader)
        self.assertEqual(row['mentee_id'], str(mentee_user.pk))
        self.assertEqual(row['profile_opened'], '1')

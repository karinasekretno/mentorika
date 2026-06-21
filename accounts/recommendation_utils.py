import math
import uuid

from django.db.models import Q
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from accounts.interests_catalog import interests_from_mentee
from accounts.models import MenteeProfile, MentorProfile, RecommendationExposure, UserProfile

ALGORITHM_VERSION = 'tfidf-v1'
INTEREST_WEIGHT_REPEAT = 3
SKILL_TOPIC_WEIGHT_REPEAT = 3
GOALS_WEIGHT_REPEAT = 2

CONTENT_WEIGHT = 0.7
RATING_WEIGHT = 0.2
EXPERIENCE_WEIGHT = 0.1


def _landing_mentors_base_qs():
    return (
        MentorProfile.objects.select_related('user')
        .prefetch_related('skills', 'consultation_topics', 'work_experiences')
        .filter(
            Q(job_title__gt='') | Q(headline__gt='') | Q(bio__gt=''),
        )
    )


def landing_mentor_count():
    return _landing_mentors_base_qs().count()


def _repeat_fragment(text, times):
    cleaned = (text or '').strip()
    if not cleaned:
        return ''
    return ' '.join([cleaned] * times)


def _join_parts(parts):
    return ' '.join(part.strip() for part in parts if part and str(part).strip())


def build_mentee_profile_text(mentee):
    parts = []
    for interest in mentee.interests.all():
        parts.append(_repeat_fragment(interest.name, INTEREST_WEIGHT_REPEAT))
    if mentee.goals:
        parts.append(_repeat_fragment(mentee.goals, GOALS_WEIGHT_REPEAT))
    if mentee.level:
        parts.append(mentee.get_level_display())
    if mentee.bio:
        parts.append(mentee.bio.strip())
    return _join_parts(parts)


def build_mentor_profile_text(mentor):
    parts = []
    for skill in mentor.skills.all():
        parts.append(_repeat_fragment(skill.name, SKILL_TOPIC_WEIGHT_REPEAT))
    for topic in mentor.consultation_topics.all():
        topic_text = _join_parts([topic.title, topic.description])
        parts.append(_repeat_fragment(topic_text, SKILL_TOPIC_WEIGHT_REPEAT))
    for value in (
        mentor.headline,
        mentor.bio,
        mentor.job_title,
        mentor.company,
        mentor.portfolio_text,
        mentor.languages,
    ):
        if value:
            parts.append(str(value).strip())
    for experience in mentor.work_experiences.all():
        parts.append(
            _join_parts([
                experience.company,
                experience.job_title,
                experience.description,
                experience.period_display,
            ])
        )
    return _join_parts(parts)


def mentee_has_recommendation_content(mentee):
    if interests_from_mentee(mentee):
        return True
    return bool((mentee.goals or '').strip())


def _normalize_rating(rating):
    return max(0.0, min(1.0, float(rating) / 5.0))


def _normalize_sessions(sessions_count, max_sessions):
    if max_sessions <= 0:
        return 0.0
    return math.log1p(max(0, sessions_count)) / math.log1p(max_sessions)


def _mentor_skill_names(mentor):
    return {skill.name.lower(): skill.name for skill in mentor.skills.all()}


def _find_matched_skills(mentor, interest_names):
    matched = []
    skill_names = _mentor_skill_names(mentor)
    topic_texts = [
        f'{topic.title} {topic.description}'.lower()
        for topic in mentor.consultation_topics.all()
    ]

    for interest in interest_names:
        key = interest.lower()
        if key in skill_names:
            matched.append(skill_names[key])
            continue
        for skill_lower, skill_name in skill_names.items():
            if key in skill_lower or skill_lower in key:
                matched.append(skill_name)
                break
        else:
            for text in topic_texts:
                if key in text:
                    matched.append(interest)
                    break

    return sorted(set(matched), key=str.lower)


def _build_recommendation_reason(mentee, mentor, matched_skills):
    if matched_skills:
        shown = matched_skills[:3]
        return f'Подходит по интересам: {", ".join(shown)}'

    goals = (mentee.goals or '').strip().lower()
    if goals:
        for topic in mentor.consultation_topics.all():
            title = topic.title.lower()
            if title and title in goals:
                return 'Совпадают цели обучения и темы консультаций'
            for word in title.split():
                if len(word) > 3 and word in goals:
                    return 'Совпадают цели обучения и темы консультаций'

    return 'Рекомендован с учётом компетенций и опыта'


def _mentor_summary(mentor):
    if mentor.list_headline:
        return mentor.list_headline
    if mentor.bio_display:
        text = mentor.bio_display
        if len(text) > 150:
            return f'{text[:147].rstrip()}…'
        return text
    return ''


def mentor_to_landing_card(
    mentor,
    *,
    matched_skills=None,
    recommended=False,
    recommendation_score=None,
    recommendation_reason='',
    recommendation_tracking_token='',
):
    all_skills = [skill.name for skill in mentor.skills.all()]
    tags = all_skills[:3]
    extra = max(0, len(all_skills) - len(tags))
    matched = matched_skills or []
    card = {
        'slug': mentor.slug,
        'name': mentor.short_display_name,
        'full_name': mentor.display_name,
        'role': mentor.job_title,
        'company': mentor.company,
        'avatar': mentor.initials,
        'photo_url': mentor.photo.url if mentor.photo else '',
        'summary': _mentor_summary(mentor),
        'rating': float(mentor.rating),
        'sessions': mentor.sessions_count,
        'tags': tags,
        'skills_extra': extra,
        'matched_skills': matched,
        'recommended': recommended,
    }
    if recommendation_score is not None:
        card['recommendation_score'] = recommendation_score
    if recommendation_reason:
        card['recommendation_reason'] = recommendation_reason
    if recommendation_tracking_token:
        card['recommendation_tracking_token'] = recommendation_tracking_token
    return card


def popular_mentors_for_landing():
    mentors = _landing_mentors_base_qs().order_by('-sessions_count', '-rating')
    return [mentor_to_landing_card(mentor) for mentor in mentors]


def hero_mentors_for_landing(limit=3):
    qs = _landing_mentors_base_qs().order_by('-sessions_count', '-rating')
    with_photo = [mentor for mentor in qs if mentor.photo]
    chosen = with_photo[:limit]
    if len(chosen) < limit:
        seen = {mentor.pk for mentor in chosen}
        for mentor in qs:
            if mentor.pk in seen:
                continue
            chosen.append(mentor)
            if len(chosen) >= limit:
                break
    return [mentor_to_landing_card(mentor) for mentor in chosen]


def _compute_tfidf_scores(mentee_text, mentors):
    mentor_texts = [build_mentor_profile_text(mentor) for mentor in mentors]
    corpus = [mentee_text] + mentor_texts
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        token_pattern=r'(?u)\b[\w\-]+\b',
        lowercase=True,
    )
    matrix = vectorizer.fit_transform(corpus)
    return cosine_similarity(matrix[0:1], matrix[1:]).flatten()


def recommend_mentors_for_mentee(mentee):
    interest_names = interests_from_mentee(mentee)
    mentors = list(_landing_mentors_base_qs())
    if not mentors:
        return [], interest_names, False, []

    if not mentee_has_recommendation_content(mentee):
        return popular_mentors_for_landing(), interest_names, False, []

    mentee_text = build_mentee_profile_text(mentee)
    if not mentee_text.strip():
        return popular_mentors_for_landing(), interest_names, False, []

    content_scores = _compute_tfidf_scores(mentee_text, mentors)
    max_sessions = max((mentor.sessions_count for mentor in mentors), default=0)

    scored_items = []
    for index, mentor in enumerate(mentors):
        content_score = float(content_scores[index])
        rating_score = _normalize_rating(mentor.rating_display)
        experience_score = _normalize_sessions(mentor.sessions_count, max_sessions)
        final_score = (
            CONTENT_WEIGHT * content_score
            + RATING_WEIGHT * rating_score
            + EXPERIENCE_WEIGHT * experience_score
        )
        matched = _find_matched_skills(mentor, interest_names)
        scored_items.append({
            'mentor': mentor,
            'content_score': content_score,
            'rating_score': rating_score,
            'experience_score': experience_score,
            'final_score': final_score,
            'matched_skills': matched,
            'recommendation_reason': _build_recommendation_reason(mentee, mentor, matched),
        })

    if not any(item['content_score'] > 0 for item in scored_items):
        return popular_mentors_for_landing(), interest_names, False, []

    positive_items = [item for item in scored_items if item['content_score'] > 0]
    positive_items.sort(
        key=lambda item: (
            -item['final_score'],
            -item['content_score'],
            -float(item['mentor'].rating),
            -item['mentor'].sessions_count,
        )
    )

    cards = [
        mentor_to_landing_card(
            item['mentor'],
            matched_skills=item['matched_skills'],
            recommended=True,
            recommendation_score=item['final_score'],
            recommendation_reason=item['recommendation_reason'],
        )
        for item in positive_items
    ]
    return cards, interest_names, True, positive_items


def create_recommendation_exposures(user, scored_items):
    exposures = []
    for rank, item in enumerate(scored_items, start=1):
        token = uuid.uuid4()
        exposure = RecommendationExposure.objects.create(
            tracking_token=token,
            mentee=user,
            mentor=item['mentor'],
            rank=rank,
            content_score=item['content_score'],
            rating_score=item['rating_score'],
            experience_score=item['experience_score'],
            final_score=item['final_score'],
            algorithm_version=ALGORITHM_VERSION,
        )
        exposures.append(exposure)
    return exposures


def attach_tracking_tokens(cards, exposures):
    for card, exposure in zip(cards, exposures):
        card['recommendation_tracking_token'] = str(exposure.tracking_token)
    return cards


def landing_mentors_for_request(user):
    if not user.is_authenticated:
        return {
            'mentors': popular_mentors_for_landing(),
            'mentors_personalized': False,
            'mentors_has_interests': False,
        }

    profile = getattr(user, 'profile', None)
    if profile is None or profile.role != UserProfile.ROLE_MENTEE:
        return {
            'mentors': popular_mentors_for_landing(),
            'mentors_personalized': False,
            'mentors_has_interests': False,
        }

    mentee = (
        MenteeProfile.objects.filter(user=user)
        .prefetch_related('interests')
        .first()
    )
    if mentee is None:
        return {
            'mentors': popular_mentors_for_landing(),
            'mentors_personalized': False,
            'mentors_has_interests': False,
        }

    cards, interest_names, personalized, scored_items = recommend_mentors_for_mentee(mentee)
    has_interests = mentee_has_recommendation_content(mentee)

    if personalized and scored_items and has_interests:
        exposures = create_recommendation_exposures(user, scored_items)
        cards = attach_tracking_tokens(cards, exposures)

    return {
        'mentors': cards,
        'mentors_personalized': personalized,
        'mentors_has_interests': has_interests,
        'mentee_interests': interest_names[:5],
    }

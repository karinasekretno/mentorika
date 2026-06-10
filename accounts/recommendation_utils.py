from django.db.models import Q

from accounts.interests_catalog import interests_from_mentee
from accounts.models import MenteeProfile, MentorProfile, UserProfile


def _landing_mentors_base_qs():
    return (
        MentorProfile.objects.select_related('user')
        .prefetch_related('skills', 'consultation_topics')
        .filter(
            Q(job_title__gt='') | Q(headline__gt='') | Q(bio__gt=''),
        )
    )


def landing_mentor_count():
    return _landing_mentors_base_qs().count()


def _mentor_skill_names(mentor):
    return {skill.name.lower() for skill in mentor.skills.all()}


def _topic_texts(mentor):
    texts = []
    for topic in mentor.consultation_topics.all():
        texts.append(f'{topic.title} {topic.description}'.lower())
    return texts


def score_mentor_for_mentee(mentor, interest_names):
    interests = [name.strip() for name in interest_names if name and name.strip()]
    if not interests:
        return 0, []

    skill_names = _mentor_skill_names(mentor)
    matched = []
    score = 0

    for interest in interests:
        key = interest.lower()
        if key in skill_names:
            matched.append(interest)
            score += 12
            continue
        for skill in skill_names:
            if key in skill or skill in key:
                matched.append(interest)
                score += 8
                break
        else:
            for text in _topic_texts(mentor):
                if key in text:
                    matched.append(interest)
                    score += 5
                    break

    if mentor.bio_display:
        bio = mentor.bio_display.lower()
        for interest in interests:
            if interest.lower() in bio and interest not in matched:
                score += 2

    score += float(mentor.rating) * 1.5
    score += min(mentor.sessions_count, 100) * 0.05

    return score, sorted(set(matched), key=str.lower)


def _mentor_summary(mentor):
    if mentor.list_headline:
        return mentor.list_headline
    if mentor.bio_display:
        text = mentor.bio_display
        if len(text) > 150:
            return f'{text[:147].rstrip()}…'
        return text
    return ''


def mentor_to_landing_card(mentor, *, matched_skills=None, recommended=False):
    all_skills = [skill.name for skill in mentor.skills.all()]
    tags = all_skills[:3]
    extra = max(0, len(all_skills) - len(tags))
    matched = matched_skills or []
    return {
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


def popular_mentors_for_landing():
    mentors = _landing_mentors_base_qs().order_by('-sessions_count', '-rating')
    return [mentor_to_landing_card(mentor) for mentor in mentors]


def hero_mentors_for_landing(limit=3):
    qs = _landing_mentors_base_qs().order_by('-sessions_count', '-rating')
    with_photo = [m for m in qs if m.photo]
    chosen = with_photo[:limit]
    if len(chosen) < limit:
        seen = {m.pk for m in chosen}
        for mentor in qs:
            if mentor.pk in seen:
                continue
            chosen.append(mentor)
            if len(chosen) >= limit:
                break
    return [mentor_to_landing_card(mentor) for mentor in chosen]


def recommend_mentors_for_mentee(mentee):
    interest_names = interests_from_mentee(mentee)
    mentors = list(_landing_mentors_base_qs())
    if not mentors:
        return [], interest_names

    if not interest_names:
        return popular_mentors_for_landing(), interest_names

    scored = []
    for mentor in mentors:
        score, matched = score_mentor_for_mentee(mentor, interest_names)
        if score > 0 and matched:
            scored.append((score, mentor, matched))

    scored.sort(key=lambda row: (-row[0], -row[1].rating, -row[1].sessions_count))

    if not scored:
        return popular_mentors_for_landing(), interest_names

    cards = [
        mentor_to_landing_card(mentor, matched_skills=matched, recommended=True)
        for _score, mentor, matched in scored
    ]
    return cards, interest_names


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

    cards, interest_names = recommend_mentors_for_mentee(mentee)
    has_interests = bool(interest_names)
    personalized = has_interests and any(card.get('recommended') for card in cards)

    return {
        'mentors': cards,
        'mentors_personalized': personalized,
        'mentors_has_interests': has_interests,
        'mentee_interests': interest_names[:5],
    }

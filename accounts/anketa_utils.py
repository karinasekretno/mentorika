from accounts.models import (
    MentorConsultationTopic,
    MentorEducation,
    MentorProfile,
    MentorProfileLink,
    MentorSkill,
    MentorWorkExperience,
    MenteeInterest,
)
from accounts.interests_catalog import (
    MAX_CUSTOM_INTERESTS,
    custom_interests_from_post,
    standard_interest_names,
)
from accounts.skills_catalog import custom_skills_from_post, skill_level_from_post
from accounts.social_catalog import (
    MAX_PORTFOLIO_LINKS,
    MAX_SOCIAL_LINKS,
    SOCIAL_MAIN_PLATFORMS,
    SOCIAL_OTHER_START_INDEX,
    SOCIAL_PLATFORM_INDEX,
)
from accounts.work_period import format_work_period, month_value, parse_month

MAX_CONSULTATION_TOPICS = 20
MAX_WORK_EXPERIENCES = 20
MAX_EDUCATION_ENTRIES = 20


def _topic_text(topic):
    return (topic.description or topic.title or '').strip()


def topics_from_saved(topics):
    rows = []
    for index, topic in enumerate(topics[:MAX_CONSULTATION_TOPICS]):
        rows.append({
            'index': index,
            'text': _topic_text(topic),
        })
    if not rows:
        rows.append({'index': 0, 'text': ''})
    return rows


def topics_from_post(post_data, include_empty=False):
    rows = []
    for index in range(MAX_CONSULTATION_TOPICS):
        key = f'consultation_topic_{index}'
        if key not in post_data:
            break
        text = post_data.get(key, '').strip()
        if text or include_empty:
            rows.append({'index': index, 'text': text})
    return rows


def save_topics_from_post(mentor, post_data):
    mentor.consultation_topics.all().delete()
    for index, row in enumerate(topics_from_post(post_data)):
        text = row['text']
        MentorConsultationTopic.objects.create(
            mentor=mentor,
            title=text[:200],
            description=text,
            sort_order=index,
        )


def empty_work_row(index=0):
    return {
        'index': index,
        'company': '',
        'start': '',
        'end': '',
        'is_current': False,
        'job_title': '',
        'description': '',
    }


def _work_period_fields(post_data, index):
    start = post_data.get(f'work_experience_{index}_start', '').strip()
    end = post_data.get(f'work_experience_{index}_end', '').strip()
    is_current = post_data.get(f'work_experience_{index}_is_current') == '1'
    start_date = parse_month(start)
    end_date = None if is_current else parse_month(end)
    return start, end, is_current, start_date, end_date


def work_from_saved(experiences):
    rows = []
    for index, exp in enumerate(experiences[:MAX_WORK_EXPERIENCES]):
        rows.append({
            'index': index,
            'company': exp.company,
            'start': month_value(exp.start_date),
            'end': month_value(exp.end_date),
            'is_current': exp.is_current,
            'job_title': exp.job_title,
            'description': exp.description,
        })
    if not rows:
        rows.append(empty_work_row())
    return rows


def work_from_post(post_data, include_empty=False):
    rows = []
    for index in range(MAX_WORK_EXPERIENCES):
        company_key = f'work_experience_{index}_company'
        if company_key not in post_data:
            break
        company = post_data.get(company_key, '').strip()
        start, end, is_current, _, _ = _work_period_fields(post_data, index)
        job_title = post_data.get(f'work_experience_{index}_job_title', '').strip()
        description = post_data.get(f'work_experience_{index}_description', '').strip()
        if company or include_empty:
            rows.append({
                'index': index,
                'company': company,
                'start': start,
                'end': end,
                'is_current': is_current,
                'job_title': job_title,
                'description': description,
            })
    return rows


def save_work_from_post(mentor, post_data):
    mentor.work_experiences.all().delete()
    for index, row in enumerate(work_from_post(post_data)):
        _, _, is_current, start_date, end_date = _work_period_fields(post_data, row['index'])
        MentorWorkExperience.objects.create(
            mentor=mentor,
            company=row['company'],
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            period=format_work_period(start_date, end_date, is_current),
            job_title=row['job_title'],
            description=row['description'],
            sort_order=index,
        )


def _parse_graduation_year(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        year = int(value)
    except ValueError:
        return None
    if 1950 <= year <= 2100:
        return year
    return None


def empty_education_row(index=0):
    return {
        'index': index,
        'institution': '',
        'graduation_year': '',
        'specialization': '',
    }


def education_from_saved(entries):
    rows = []
    for index, entry in enumerate(entries[:MAX_EDUCATION_ENTRIES]):
        rows.append({
            'index': index,
            'institution': entry.institution,
            'graduation_year': entry.graduation_year or '',
            'specialization': entry.specialization,
        })
    if not rows:
        rows.append(empty_education_row())
    return rows


def education_from_post(post_data, include_empty=False):
    rows = []
    for index in range(MAX_EDUCATION_ENTRIES):
        institution_key = f'education_{index}_institution'
        if institution_key not in post_data:
            break
        institution = post_data.get(institution_key, '').strip()
        graduation_year = post_data.get(f'education_{index}_graduation_year', '').strip()
        specialization = post_data.get(f'education_{index}_specialization', '').strip()
        if institution or include_empty:
            rows.append({
                'index': index,
                'institution': institution,
                'graduation_year': graduation_year,
                'specialization': specialization,
            })
    return rows


def save_education_from_post(mentor, post_data):
    mentor.education_entries.all().delete()
    for index, row in enumerate(education_from_post(post_data)):
        MentorEducation.objects.create(
            mentor=mentor,
            institution=row['institution'],
            specialization=row['specialization'],
            graduation_year=_parse_graduation_year(row['graduation_year']),
            sort_order=index,
        )


def empty_portfolio_row(index=0):
    return {'index': index, 'url': ''}


def empty_social_row(index=0):
    return {'index': index, 'platform': 'telegram', 'url': ''}


def empty_social_other_row(index=SOCIAL_OTHER_START_INDEX):
    return {'index': index, 'platform': 'other', 'url': ''}


def social_form_slots(rows):
    """Split saved/posted social rows into fixed platform slots and optional «other» links."""
    main_urls = {value: '' for value, _label in SOCIAL_MAIN_PLATFORMS}
    others = []

    for row in rows:
        platform = row.get('platform') or 'other'
        url = (row.get('url') or '').strip()
        if not url:
            continue
        if platform in main_urls:
            main_urls[platform] = url
        elif platform == 'other':
            others.append({'platform': 'other', 'url': url})

    main_platforms = []
    for value, label in SOCIAL_MAIN_PLATFORMS:
        main_platforms.append({
            'value': value,
            'label': label,
            'index': SOCIAL_PLATFORM_INDEX[value],
            'url': main_urls[value],
        })

    other_rows = []
    for offset, row in enumerate(others):
        other_rows.append({
            'index': SOCIAL_OTHER_START_INDEX + offset,
            'platform': 'other',
            'url': row['url'],
        })

    return main_platforms, other_rows


def _portfolio_links_from_mentor(mentor):
    links = list(
        mentor.profile_links.filter(link_type=MentorProfileLink.TYPE_PORTFOLIO).order_by('sort_order', 'id')
    )
    if not links and mentor.portfolio_url:
        return [{'index': 0, 'url': mentor.portfolio_url}]
    return [{'index': i, 'url': link.url} for i, link in enumerate(links[:MAX_PORTFOLIO_LINKS])]


def portfolio_from_saved(mentor):
    rows = _portfolio_links_from_mentor(mentor)
    if not rows:
        rows.append(empty_portfolio_row())
    return rows


def portfolio_from_post(post_data, include_empty=False):
    rows = []
    for index in range(MAX_PORTFOLIO_LINKS):
        key = f'portfolio_link_{index}'
        if key not in post_data:
            break
        url = post_data.get(key, '').strip()
        if url or include_empty:
            rows.append({'index': index, 'url': url})
    return rows


def social_from_saved(mentor):
    rows = []
    for index, link in enumerate(
        mentor.profile_links.filter(link_type=MentorProfileLink.TYPE_SOCIAL).order_by('sort_order', 'id')[:MAX_SOCIAL_LINKS]
    ):
        rows.append({
            'index': index,
            'platform': link.platform or 'other',
            'url': link.url,
        })
    if not rows:
        rows.append(empty_social_row())
    return rows


def social_from_post(post_data, include_empty=False):
    rows = []
    for index in range(MAX_SOCIAL_LINKS):
        url_key = f'social_link_{index}_url'
        platform_key = f'social_link_{index}_platform'
        if url_key not in post_data and platform_key not in post_data:
            break
        url = post_data.get(url_key, '').strip()
        platform = post_data.get(platform_key, 'other').strip() or 'other'
        if url or include_empty:
            rows.append({'index': index, 'platform': platform, 'url': url})
    return rows


def save_portfolio_social_from_post(mentor, post_data):
    mentor.profile_links.all().delete()
    portfolio_rows = [row for row in portfolio_from_post(post_data) if row['url']]
    social_rows = [row for row in social_from_post(post_data) if row['url']]

    for index, row in enumerate(portfolio_rows):
        MentorProfileLink.objects.create(
            mentor=mentor,
            link_type=MentorProfileLink.TYPE_PORTFOLIO,
            url=row['url'],
            sort_order=index,
        )

    for index, row in enumerate(social_rows):
        MentorProfileLink.objects.create(
            mentor=mentor,
            link_type=MentorProfileLink.TYPE_SOCIAL,
            platform=row['platform'],
            url=row['url'],
            sort_order=index,
        )

    first_portfolio = portfolio_rows[0]['url'] if portfolio_rows else ''
    mentor.portfolio_url = first_portfolio
    mentor.portfolio_text = post_data.get('portfolio_description', '').strip()
    mentor.save(update_fields=['portfolio_url', 'portfolio_text'])


def save_skills_from_post(mentor, post_data):
    mentor.skills.all().delete()
    valid_levels = {
        MentorSkill.LEVEL_JUNIOR,
        MentorSkill.LEVEL_MIDDLE,
        MentorSkill.LEVEL_SENIOR,
        MentorSkill.LEVEL_LEAD,
    }
    seen = set()

    def _create(name, level):
        name = name.strip()
        if not name or name in seen:
            return
        if level not in valid_levels:
            level = MentorSkill.LEVEL_MIDDLE
        seen.add(name)
        MentorSkill.objects.create(mentor=mentor, name=name, level=level)

    for name in post_data.getlist('skills'):
        _create(name, skill_level_from_post(post_data, name))

    for row in custom_skills_from_post(post_data):
        _create(row['name'], row['level'])


def mentor_profile_completion(mentor):
    checks = [
        (bool(mentor.photo), 'Фото'),
        (bool((mentor.headline or '').strip()), 'Краткое описание'),
        (bool(mentor.bio_display), 'О себе'),
        (bool(mentor.language_list), 'Языки'),
        (mentor.skills.exists(), 'Скиллы'),
        (mentor.consultation_topics.exists(), 'Запросы'),
        (mentor.work_experiences.exists(), 'Опыт работы'),
    ]
    done = sum(1 for ok, _label in checks if ok)
    total = len(checks)
    return {
        'percent': int(done / total * 100) if total else 0,
        'missing': [label for ok, label in checks if not ok],
        'done': done,
        'total': total,
    }


def mentee_profile_completion(mentee):
    checks = [
        (bool(mentee.photo), 'Фото'),
        (bool((mentee.bio or '').strip()), 'О себе'),
        (bool((mentee.goals or '').strip()), 'Цели обучения'),
        (mentee.interests.exists(), 'Интересы'),
    ]
    done = sum(1 for ok, _label in checks if ok)
    total = len(checks)
    return {
        'percent': int(done / total * 100) if total else 0,
        'missing': [label for ok, label in checks if not ok],
        'done': done,
        'total': total,
    }


def save_interests_from_post(mentee, post_data):
    mentee.interests.all().delete()
    seen = set()

    def _create(name):
        name = name.strip()
        if not name or name in seen:
            return
        seen.add(name)
        MenteeInterest.objects.create(mentee=mentee, name=name)

    for name in post_data.getlist('interests'):
        _create(name)

    for row in custom_interests_from_post(post_data):
        _create(row['name'])


def mentor_profile_sections_context(mentor):
    profile_links = list(mentor.profile_links.all())
    social_links = [
        link for link in profile_links
        if link.link_type == MentorProfileLink.TYPE_SOCIAL
    ]
    social_by_platform = {link.platform: link for link in social_links}
    return {
        'mentor_skills': list(mentor.skills.all()),
        'mentor_topics': list(mentor.consultation_topics.all()),
        'mentor_work_experiences': list(mentor.work_experiences.all()),
        'mentor_education': list(mentor.education_entries.all()),
        'mentor_portfolio_links': [
            link for link in profile_links
            if link.link_type == MentorProfileLink.TYPE_PORTFOLIO
        ],
        'mentor_social_links': social_links,
        'mentor_social_main': [
            {
                'platform': platform,
                'label': label,
                'url': social_by_platform[platform].url if platform in social_by_platform else '',
            }
            for platform, label in SOCIAL_MAIN_PLATFORMS
        ],
        'mentor_social_other': [
            link for link in social_links if link.platform == 'other'
        ],
        'mentor_reviews': list(
            mentor.reviews.filter(booking__isnull=False)
            .select_related('mentee', 'booking__slot')
            .order_by('-created_at')
        ),
    }

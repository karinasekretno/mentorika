from accounts.models import MentorSkill
from accounts.skills_catalog import MAX_CUSTOM_SKILLS, SKILL_CHOICES, standard_skill_names

MAX_CUSTOM_INTERESTS = MAX_CUSTOM_SKILLS


def interest_choices_for():
    return list(SKILL_CHOICES)


def standard_interest_names():
    return standard_skill_names()


def catalog_interests_from_saved(saved_names):
    standard = standard_interest_names()
    return {name for name in saved_names if name in standard}


def custom_interests_from_saved(saved_names):
    standard = standard_interest_names()
    rows = []
    for index, name in enumerate(name for name in saved_names if name not in standard):
        if index >= MAX_CUSTOM_INTERESTS:
            break
        rows.append({'index': index, 'name': name})
    return rows


def custom_interests_from_post(post_data):
    rows = []
    for index in range(MAX_CUSTOM_INTERESTS):
        name = post_data.get(f'custom_interest_{index}_name', '').strip()
        if not name:
            continue
        rows.append({'index': index, 'name': name})
    return rows


def interests_from_mentee(mentee):
    return [interest.name for interest in mentee.interests.all()]

from accounts.models import MentorSkill

SKILL_CHOICES = [
    ('HTML', 'HTML'),
    ('CSS', 'CSS'),
    ('JavaScript', 'JavaScript'),
    ('TypeScript', 'TypeScript'),
    ('React', 'React'),
    ('Vue.js', 'Vue.js'),
    ('Angular', 'Angular'),
    ('Node.js', 'Node.js'),
    ('Webpack', 'Webpack'),
    ('Python', 'Python'),
    ('Django', 'Django'),
    ('FastAPI', 'FastAPI'),
    ('Flask', 'Flask'),
    ('Java', 'Java'),
    ('Kotlin', 'Kotlin'),
    ('Swift', 'Swift'),
    ('Go', 'Go'),
    ('Rust', 'Rust'),
    ('C++', 'C++'),
    ('C#', 'C#'),
    ('PHP', 'PHP'),
    ('Ruby', 'Ruby'),
    ('SQL', 'SQL'),
    ('PostgreSQL', 'PostgreSQL'),
    ('MongoDB', 'MongoDB'),
    ('Redis', 'Redis'),
    ('Docker', 'Docker'),
    ('Kubernetes', 'Kubernetes'),
    ('Git', 'Git'),
    ('DevOps', 'DevOps'),
    ('AWS', 'AWS'),
    ('GraphQL', 'GraphQL'),
    ('REST API', 'REST API'),
    ('Linux', 'Linux'),
    ('Nginx', 'Nginx'),
    ('UI/UX', 'UI/UX'),
    ('Figma', 'Figma'),
    ('Product Management', 'Product Management'),
    ('Agile', 'Agile'),
    ('Data Science', 'Data Science'),
    ('Machine Learning', 'Machine Learning'),
    ('Mobile Development', 'Mobile Development'),
    ('Project Management', 'Project Management'),
    ('Leadership', 'Leadership'),
    ('Career Coaching', 'Career Coaching'),
]

SKILL_LEVEL_CHOICES = [
    (MentorSkill.LEVEL_JUNIOR, 'Junior'),
    (MentorSkill.LEVEL_MIDDLE, 'Middle'),
    (MentorSkill.LEVEL_SENIOR, 'Senior'),
    (MentorSkill.LEVEL_LEAD, 'Lead'),
]

MAX_CUSTOM_SKILLS = 10


def standard_skill_names():
    return {code for code, _ in SKILL_CHOICES}


def skill_choices_for():
    return list(SKILL_CHOICES)


def catalog_skill_levels(saved_skill_levels):
    standard = standard_skill_names()
    return {name: level for name, level in saved_skill_levels.items() if name in standard}


def custom_skills_from_saved(saved_skill_levels):
    standard = standard_skill_names()
    rows = []
    for index, (name, level) in enumerate(
        (name, level) for name, level in saved_skill_levels.items() if name not in standard
    ):
        if index >= MAX_CUSTOM_SKILLS:
            break
        rows.append({'index': index, 'name': name, 'level': level})
    return rows


def custom_skills_from_post(post_data):
    rows = []
    for index in range(MAX_CUSTOM_SKILLS):
        name = post_data.get(f'custom_skill_{index}_name', '').strip()
        if not name:
            continue
        rows.append({
            'index': index,
            'name': name,
            'level': post_data.get(f'custom_skill_{index}_level', MentorSkill.LEVEL_MIDDLE),
        })
    return rows


def skill_levels_from_mentor(mentor):
    return {skill.name: skill.level for skill in mentor.skills.all()}


def skill_level_field_name(skill_name):
    return 'skill_level_' + skill_name.replace(' ', '_').replace('+', 'plus')


def skill_level_from_post(post_data, skill_name):
    return post_data.get(skill_level_field_name(skill_name), MentorSkill.LEVEL_MIDDLE)

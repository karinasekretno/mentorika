from django.shortcuts import render

from accounts.models import MentorProfile
from accounts.recommendation_utils import (
    hero_mentors_for_landing,
    landing_mentor_count,
    landing_mentors_for_request,
)


def index(request):
    mentor_count = landing_mentor_count()
    mentors_context = landing_mentors_for_request(request.user)

    highlights = [
        {
            'icon': '◎',
            'title': 'Открытые профили',
            'text': 'Навыки, опыт и отзывы в профиле — выбирайте ментора осознанно.',
        },
        {
            'icon': '₽',
            'title': 'Бесплатно для учеников',
            'text': 'Запись на сессии без подписок и скрытых платежей.',
        },
        {
            'icon': '◎',
            'title': '1-on-1 формат',
            'text': 'Живые встречи, чат и расписание в одной платформе.',
        },
    ]

    audiences = [
        {
            'badge': 'Новичкам',
            'title': 'Старт в профессии',
            'text': 'Прокачайтесь после курсов и увереннее выходите на собеседования.',
        },
        {
            'badge': 'Опытным',
            'title': 'Рост вглубь',
            'text': 'Освойте новый стек, прокачайте soft skills или смените трек.',
        },
        {
            'badge': 'Всем',
            'title': 'Точечная помощь',
            'text': 'Разберите сложную задачу или получите обратную связь от наставника.',
        },
        {
            'badge': 'Менторам',
            'title': 'Делитесь опытом',
            'text': 'Ведите учеников, заполняйте анкету и управляйте расписанием.',
        },
    ]

    skill_tags = [
        'Python', 'Product', 'UX', 'React', 'Java', 'Go', 'DevOps', 'Data Science',
        'HR', 'Маркетинг', 'Дизайн', 'Agile', 'SQL', 'iOS', 'Android', 'Leadership',
        'Карьера', 'Собеседования', 'Figma', 'TypeScript', 'Django', '1С',
    ]

    features = [
        {
            'icon': '🎯',
            'title': 'Персональный план',
            'description': 'Ментор составит индивидуальную программу развития под ваши цели и текущий уровень.',
        },
        {
            'icon': '💬',
            'title': '1-on-1 сессии',
            'description': 'Живые встречи в удобном формате: видео, чат или очно. Гибкое расписание.',
        },
        {
            'icon': '📊',
            'title': 'Трекинг прогресса',
            'description': 'Отслеживайте достижения, получайте обратную связь и корректируйте траекторию.',
        },
        {
            'icon': '🔍',
            'title': 'Подбор по интересам',
            'description': 'Фильтруйте каталог по навыкам и направлениям — найдите ментора под свою задачу.',
        },
    ]

    plans = [
        {
            'name': 'Бесплатно',
            'price': 0,
            'period': 'навсегда',
            'features': ['Неограниченный поиск менторов', 'Бронирование сессий', 'Профиль менти и ментора'],
            'popular': True,
        },
    ]

    context = {
        'mentor_count': mentor_count,
        'hero_mentors': hero_mentors_for_landing(),
        'features': features,
        'plans': plans,
        'highlights': highlights,
        'audiences': audiences,
        'skill_tags': skill_tags,
        **mentors_context,
    }
    return render(request, 'landing/index.html', context)

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import (
    AvailabilitySlot,
    MentorProfile,
    MentorProject,
    MentorSkill,
    UserProfile,
)


DEMO_SKILLS = [
    'Python', 'JavaScript', 'React', 'Django', 'UI/UX',
    'Product Management', 'Project Management', 'Data Science',
    'Machine Learning', 'Leadership', 'Career Coaching', 'Agile',
    'DevOps', 'Mobile Development', 'SQL',
]


class Command(BaseCommand):
    help = 'Заполнить демо-скиллы и менторов'

    def handle(self, *args, **options):
        demo_mentors = [
            {
                'username': 'anna_pm',
                'first_name': 'Анна',
                'last_name': 'Козлова',
                'job_title': 'Senior Product Manager',
                'company': 'Сбер',
                'bio': '10+ лет в продуктовой разработке. Помогаю расти в PM и Agile.',
                'skills': ['Product Management', 'Agile', 'Career Coaching'],
            },
            {
                'username': 'dmitry_tech',
                'first_name': 'Дмитрий',
                'last_name': 'Морозов',
                'job_title': 'Tech Lead',
                'company': 'Яндекс',
                'bio': 'Python, архитектура, лидерство команд. Менторю middle → senior.',
                'skills': ['Python', 'Django', 'Leadership'],
            },
            {
                'username': 'elena_ux',
                'first_name': 'Елена',
                'last_name': 'Соколова',
                'job_title': 'UX Lead',
                'company': 'VK',
                'bio': 'UX-исследования, дизайн-системы, карьера в дизайне.',
                'skills': ['UI/UX', 'Product Management'],
            },
        ]

        today = timezone.localdate()
        for data in demo_mentors:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': f"{data['username']}@mentorika.local",
                },
            )
            if created:
                user.set_password('demo1234')
                user.save()

            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': UserProfile.ROLE_MENTOR,
                    'onboarding_completed': True,
                },
            )

            mentor, _ = MentorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'bio': data['bio'],
                    'job_title': data['job_title'],
                    'company': data['company'],
                    'rating': 0,
                    'sessions_count': 0,
                },
            )

            existing_skills = set(
                MentorSkill.objects.filter(mentor=mentor).values_list('name', flat=True)
            )
            for skill_name in data['skills']:
                if skill_name not in existing_skills:
                    MentorSkill.objects.create(
                        mentor=mentor,
                        name=skill_name,
                        level='middle',
                    )
                    existing_skills.add(skill_name)

            MentorProject.objects.get_or_create(
                mentor=mentor,
                title='Корпоративная платформа',
                defaults={'description': 'Разработка и запуск B2C-продукта с нуля.'},
            )

            for day_offset in range(1, 8):
                date = today + timedelta(days=day_offset)
                if day_offset % 2 == 0:
                    continue
                AvailabilitySlot.objects.get_or_create(
                    mentor=mentor,
                    date=date,
                    start_time='14:00',
                    defaults={'end_time': '15:00', 'is_available': True},
                )
                AvailabilitySlot.objects.get_or_create(
                    mentor=mentor,
                    date=date,
                    start_time='16:00',
                    defaults={'end_time': '17:00', 'is_available': True},
                )

        self.stdout.write(self.style.SUCCESS(
            f'Готово: {MentorSkill.objects.count()} скиллов, '
            f'{MentorProfile.objects.count()} менторов.'
        ))

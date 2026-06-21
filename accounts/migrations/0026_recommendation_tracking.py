import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0025_notification_and_booking_reminders'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecommendationExposure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tracking_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Токен показа')),
                ('rank', models.PositiveSmallIntegerField(verbose_name='Позиция в выдаче')),
                ('content_score', models.FloatField(verbose_name='Текстовая близость')),
                ('rating_score', models.FloatField(verbose_name='Вклад рейтинга')),
                ('experience_score', models.FloatField(verbose_name='Вклад опыта')),
                ('final_score', models.FloatField(verbose_name='Итоговый балл')),
                ('algorithm_version', models.CharField(default='tfidf-v1', max_length=32, verbose_name='Версия алгоритма')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('mentee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_exposures', to=settings.AUTH_USER_MODEL, verbose_name='Обучающийся')),
                ('mentor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_exposures', to='accounts.mentorprofile', verbose_name='Наставник')),
            ],
            options={
                'verbose_name': 'Показ рекомендации',
                'verbose_name_plural': 'Показы рекомендаций',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RecommendationEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('profile_opened', 'Открыт профиль'), ('booking_created', 'Создана запись'), ('attendance_confirmed', 'Подтверждено участие'), ('booking_cancelled', 'Запись отменена'), ('session_completed', 'Сессия завершена'), ('review_created', 'Оставлен отзыв'), ('repeat_booking', 'Повторная запись')], max_length=32, verbose_name='Тип события')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recommendation_events', to='accounts.sessionbooking', verbose_name='Бронирование')),
                ('exposure', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='accounts.recommendationexposure', verbose_name='Показ рекомендации')),
                ('review', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recommendation_events', to='accounts.review', verbose_name='Отзыв')),
            ],
            options={
                'verbose_name': 'Событие рекомендации',
                'verbose_name_plural': 'События рекомендаций',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='recommendationexposure',
            index=models.Index(fields=['mentee', '-created_at'], name='accounts_re_mentee__8f2d0a_idx'),
        ),
        migrations.AddIndex(
            model_name='recommendationexposure',
            index=models.Index(fields=['mentor', '-created_at'], name='accounts_re_mentor__d0f8f1_idx'),
        ),
        migrations.AddIndex(
            model_name='recommendationexposure',
            index=models.Index(fields=['-created_at'], name='accounts_re_created_0a1b2c_idx'),
        ),
        migrations.AddIndex(
            model_name='recommendationevent',
            index=models.Index(fields=['event_type', '-created_at'], name='accounts_re_event_t_1c2d3e_idx'),
        ),
        migrations.AddIndex(
            model_name='recommendationevent',
            index=models.Index(fields=['exposure', 'event_type'], name='accounts_re_exposur_4f5a6b_idx'),
        ),
    ]

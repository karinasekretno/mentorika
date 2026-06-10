from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0024_userprofile_email_verified'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='sessionbooking',
            name='reminder_1h_sent',
            field=models.BooleanField(default=False, verbose_name='Напоминание за час отправлено'),
        ),
        migrations.AddField(
            model_name='sessionbooking',
            name='reminder_24h_sent',
            field=models.BooleanField(default=False, verbose_name='Напоминание за сутки отправлено'),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('booking_created', 'Запись создана'), ('booking_cancelled', 'Запись отменена'), ('booking_rescheduled', 'Запись перенесена'), ('booking_reminder_24h', 'Напоминание за сутки'), ('booking_reminder_1h', 'Напоминание за час'), ('attendance_confirm', 'Подтверждение участия'), ('session_started', 'Сессия началась'), ('session_completed', 'Сессия завершена'), ('profile_incomplete', 'Профиль не заполнен'), ('onboarding_incomplete', 'Онбординг не завершён')], max_length=40, verbose_name='Тип')),
                ('title', models.CharField(max_length=200, verbose_name='Заголовок')),
                ('body', models.TextField(verbose_name='Текст')),
                ('link', models.CharField(blank=True, max_length=500, verbose_name='Ссылка')),
                ('is_read', models.BooleanField(default=False, verbose_name='Прочитано')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='accounts.sessionbooking')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Уведомление',
                'verbose_name_plural': 'Уведомления',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', 'is_read', '-created_at'], name='accounts_no_user_id_6f0a8a_idx')],
            },
        ),
    ]

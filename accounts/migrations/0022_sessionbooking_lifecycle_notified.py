from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_message_reply_to'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessionbooking',
            name='session_started_notified',
            field=models.BooleanField(default=False, verbose_name='Уведомление о начале отправлено'),
        ),
        migrations.AddField(
            model_name='sessionbooking',
            name='session_completed_notified',
            field=models.BooleanField(default=False, verbose_name='Уведомление о завершении отправлено'),
        ),
    ]

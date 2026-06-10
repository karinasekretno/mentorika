from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_remove_mentorprofile_experience_years'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessionbooking',
            name='attendance_status',
            field=models.CharField(
                choices=[
                    ('scheduled', 'Записан'),
                    ('confirmed', 'Подтвердил участие'),
                    ('declined', 'Отказался'),
                ],
                default='scheduled',
                max_length=12,
                verbose_name='Подтверждение участия',
            ),
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_remove_moderation_and_certificates'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mentorprofile',
            name='experience_years',
        ),
    ]

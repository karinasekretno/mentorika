from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_remove_specialization'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MentorCertificate',
        ),
        migrations.RemoveField(
            model_name='mentorprofile',
            name='is_verified',
        ),
        migrations.RemoveField(
            model_name='mentorprofile',
            name='status',
        ),
    ]

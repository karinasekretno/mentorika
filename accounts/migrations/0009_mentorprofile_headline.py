from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_mentorprofilelink'),
    ]

    operations = [
        migrations.AddField(
            model_name='mentorprofile',
            name='headline',
            field=models.CharField(blank=True, max_length=200, verbose_name='Краткое описание'),
        ),
    ]

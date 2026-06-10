from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mentorprofile',
            name='languages',
            field=models.CharField(blank=True, help_text='Через запятую', max_length=255, verbose_name='Языки'),
        ),
        migrations.AddField(
            model_name='mentorprofile',
            name='photo',
            field=models.ImageField(blank=True, upload_to='mentors/photos/', verbose_name='Фото'),
        ),
    ]

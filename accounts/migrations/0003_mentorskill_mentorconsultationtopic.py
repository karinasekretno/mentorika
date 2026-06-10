from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_mentorprofile_languages_mentorprofile_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='MentorSkill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, verbose_name='Навык')),
                ('level', models.CharField(
                    choices=[('junior', 'Junior'), ('middle', 'Middle'), ('senior', 'Senior'), ('lead', 'Lead')],
                    default='middle',
                    max_length=10,
                    verbose_name='Уровень',
                )),
                ('mentor', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='skills',
                    to='accounts.mentorprofile',
                )),
            ],
            options={
                'verbose_name': 'Скилл ментора',
                'verbose_name_plural': 'Скиллы ментора',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='MentorConsultationTopic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Заголовок')),
                ('description', models.TextField(verbose_name='Описание')),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')),
                ('mentor', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='consultation_topics',
                    to='accounts.mentorprofile',
                )),
            ],
            options={
                'verbose_name': 'Запрос ментора',
                'verbose_name_plural': 'Запросы ментора',
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]

from django.db import migrations, models


def copy_specializations_to_interests(apps, schema_editor):
    MenteeProfile = apps.get_model('accounts', 'MenteeProfile')
    MenteeInterest = apps.get_model('accounts', 'MenteeInterest')
    for mentee in MenteeProfile.objects.prefetch_related('skills').all():
        if mentee.interests.exists():
            continue
        for spec in mentee.skills.all():
            MenteeInterest.objects.get_or_create(mentee=mentee, name=spec.name)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_mentorprofile_headline'),
    ]

    operations = [
        migrations.AddField(
            model_name='menteeprofile',
            name='photo',
            field=models.ImageField(blank=True, upload_to='mentees/photos/', verbose_name='Фото'),
        ),
        migrations.CreateModel(
            name='MenteeInterest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, verbose_name='Интерес')),
                ('mentee', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='interests', to='accounts.menteeprofile')),
            ],
            options={
                'verbose_name': 'Интерес менти',
                'verbose_name_plural': 'Интересы менти',
                'ordering': ['name'],
            },
        ),
        migrations.AddConstraint(
            model_name='menteeinterest',
            constraint=models.UniqueConstraint(fields=('mentee', 'name'), name='unique_mentee_interest'),
        ),
        migrations.RunPython(copy_specializations_to_interests, migrations.RunPython.noop),
    ]

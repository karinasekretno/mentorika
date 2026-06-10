from django.db import migrations, models


def migrate_specializations_to_skills(apps, schema_editor):
    MentorProfile = apps.get_model('accounts', 'MentorProfile')
    MentorSkill = apps.get_model('accounts', 'MentorSkill')

    for mentor in MentorProfile.objects.prefetch_related('specializations').all():
        existing = set(
            MentorSkill.objects.filter(mentor=mentor).values_list('name', flat=True)
        )
        for spec in mentor.specializations.all():
            if spec.name not in existing:
                MentorSkill.objects.create(
                    mentor=mentor,
                    name=spec.name,
                    level='middle',
                )
                existing.add(spec.name)


def migrate_mentee_skills_to_interests(apps, schema_editor):
    MenteeProfile = apps.get_model('accounts', 'MenteeProfile')
    MenteeInterest = apps.get_model('accounts', 'MenteeInterest')

    for mentee in MenteeProfile.objects.prefetch_related('skills').all():
        existing = set(
            MenteeInterest.objects.filter(mentee=mentee).values_list('name', flat=True)
        )
        for spec in mentee.skills.all():
            if spec.name not in existing:
                MenteeInterest.objects.create(mentee=mentee, name=spec.name)
                existing.add(spec.name)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_lock_user_role'),
    ]

    operations = [
        migrations.RunPython(migrate_specializations_to_skills, migrations.RunPython.noop),
        migrations.RunPython(migrate_mentee_skills_to_interests, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='mentorprofile',
            name='specializations',
        ),
        migrations.RemoveField(
            model_name='menteeprofile',
            name='skills',
        ),
        migrations.DeleteModel(
            name='Specialization',
        ),
    ]

from django.db import migrations, models


def normalize_roles(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    for profile in UserProfile.objects.filter(role='both'):
        new_role = profile.active_role if profile.active_role in ('mentee', 'mentor') else 'mentee'
        profile.role = new_role
        profile.active_role = new_role
        profile.save(update_fields=['role', 'active_role'])
    for profile in UserProfile.objects.filter(role=''):
        profile.role = 'mentee'
        profile.active_role = 'mentee'
        profile.save(update_fields=['role', 'active_role'])
    UserProfile.objects.exclude(role__in=('mentee', 'mentor', 'both', '')).update(
        role='mentee',
        active_role='mentee',
    )
    for profile in UserProfile.objects.all():
        if profile.active_role != profile.role:
            profile.active_role = profile.role
            profile.save(update_fields=['active_role'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_conversation_message'),
    ]

    operations = [
        migrations.RunPython(normalize_roles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='userprofile',
            name='active_role',
            field=models.CharField(
                choices=[('mentee', 'Менти (ученик)'), ('mentor', 'Ментор')],
                editable=False,
                max_length=10,
                verbose_name='Активная роль (служебное)',
            ),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[('mentee', 'Менти (ученик)'), ('mentor', 'Ментор')],
                max_length=10,
                verbose_name='Роль',
            ),
        ),
    ]

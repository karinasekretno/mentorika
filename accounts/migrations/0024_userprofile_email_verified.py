from django.db import migrations, models


def mark_existing_users_verified(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    UserProfile.objects.all().update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_review_booking'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False, verbose_name='Email подтверждён'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='email_verification_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Письмо подтверждения отправлено'),
        ),
        migrations.RunPython(mark_existing_users_verified, migrations.RunPython.noop),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_messageattachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Удалено в'),
        ),
        migrations.AddField(
            model_name='message',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Удалено'),
        ),
    ]

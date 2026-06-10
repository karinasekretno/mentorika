import accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_message_attachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='attachment_mime_type',
            field=models.CharField(blank=True, max_length=127, verbose_name='MIME-тип'),
        ),
        migrations.AlterField(
            model_name='message',
            name='attachment',
            field=models.FileField(
                blank=True,
                upload_to=accounts.models.chat_attachment_upload_to,
                verbose_name='Вложение',
            ),
        ),
    ]

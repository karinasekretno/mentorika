import accounts.models
from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_attachments(apps, schema_editor):
    Message = apps.get_model('accounts', 'Message')
    MessageAttachment = apps.get_model('accounts', 'MessageAttachment')
    for message in Message.objects.exclude(attachment='').exclude(attachment__isnull=True):
        MessageAttachment.objects.create(
            message_id=message.pk,
            file=message.attachment,
            name=message.attachment_name or message.attachment.name.split('/')[-1],
            mime_type=message.attachment_mime_type,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_message_attachment_security'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=accounts.models.chat_attachment_upload_to, verbose_name='Файл')),
                ('name', models.CharField(max_length=255, verbose_name='Имя файла')),
                ('mime_type', models.CharField(blank=True, max_length=127, verbose_name='MIME-тип')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='accounts.message', verbose_name='Сообщение')),
            ],
            options={
                'verbose_name': 'Вложение в чате',
                'verbose_name_plural': 'Вложения в чате',
                'ordering': ['pk'],
            },
        ),
        migrations.RunPython(migrate_legacy_attachments, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='message',
            name='attachment',
        ),
        migrations.RemoveField(
            model_name='message',
            name='attachment_mime_type',
        ),
        migrations.RemoveField(
            model_name='message',
            name='attachment_name',
        ),
    ]

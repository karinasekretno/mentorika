from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_sessionbooking_attendance_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='attachment',
            field=models.FileField(blank=True, upload_to='chat/attachments/%Y/%m/', verbose_name='Вложение'),
        ),
        migrations.AddField(
            model_name='message',
            name='attachment_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Имя файла'),
        ),
        migrations.AlterField(
            model_name='message',
            name='text',
            field=models.TextField(blank=True, verbose_name='Текст'),
        ),
    ]

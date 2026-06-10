import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_message_soft_delete'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='reply_to',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='replies',
                to='accounts.message',
                verbose_name='Ответ на',
            ),
        ),
    ]

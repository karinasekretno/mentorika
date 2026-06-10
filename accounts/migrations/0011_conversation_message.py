from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0010_mentee_photo_interests'),
    ]

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('mentee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mentee_conversations', to=settings.AUTH_USER_MODEL)),
                ('mentor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='accounts.mentorprofile')),
            ],
            options={
                'verbose_name': 'Диалог',
                'verbose_name_plural': 'Диалоги',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(verbose_name='Текст')),
                ('is_system', models.BooleanField(default=False, verbose_name='Системное')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_messages', to='accounts.sessionbooking')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='accounts.conversation')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Сообщение',
                'verbose_name_plural': 'Сообщения',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='conversation',
            constraint=models.UniqueConstraint(fields=('mentor', 'mentee'), name='unique_mentor_mentee_conversation'),
        ),
    ]

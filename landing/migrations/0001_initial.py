# Generated manually for ContactRequest model

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ContactRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Имя')),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('message', models.TextField(blank=True, verbose_name='Сообщение')),
                ('direction', models.CharField(blank=True, max_length=100, verbose_name='Направление')),
                ('source', models.CharField(
                    choices=[('contact', 'Форма на странице'), ('sheet', 'Bottom Sheet')],
                    default='contact',
                    max_length=20,
                    verbose_name='Источник',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
            ],
            options={
                'verbose_name': 'Заявка',
                'verbose_name_plural': 'Заявки',
                'ordering': ['-created_at'],
            },
        ),
    ]

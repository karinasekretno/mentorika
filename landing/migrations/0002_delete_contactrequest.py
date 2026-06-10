from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ContactRequest',
        ),
    ]

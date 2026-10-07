from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taskmanager', '0006_profile'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='note',
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterModelOptions(
            name='subtask',
            options={'ordering': ['created_at']},
        ),
        migrations.AlterModelOptions(
            name='task',
            options={'ordering': ['deadline']},
        ),
        migrations.AlterField(
            model_name='task',
            name='description',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0045_transfer_gamification_models_to_gamification_app'),
        ('audiobooks', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='UserAudiobookProgress',
                ),
                migrations.DeleteModel(
                    name='AudiobookTrack',
                ),
            ],
            database_operations=[],
        ),
    ]

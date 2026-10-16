from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0044_transfer_clubs_models_to_clubs_app'),
        ('gamification', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='UserChallenge',
                ),
                migrations.DeleteModel(
                    name='UserBadge',
                ),
                migrations.DeleteModel(
                    name='ReadingGoal',
                ),
                migrations.DeleteModel(
                    name='DailyReadingLog',
                ),
                migrations.DeleteModel(
                    name='ReadingStreak',
                ),
                migrations.DeleteModel(
                    name='ReadingChallenge',
                ),
                migrations.DeleteModel(
                    name='Badge',
                ),
            ],
            database_operations=[],
        ),
    ]

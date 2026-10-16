from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0043_alter_author_photo_alter_book_cover_and_more'),
        ('clubs', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='ReadingClubDiscussionComment',
                ),
                migrations.DeleteModel(
                    name='ReadingClubDiscussion',
                ),
                migrations.DeleteModel(
                    name='ReadingClubBook',
                ),
                migrations.DeleteModel(
                    name='ReadingClubMember',
                ),
                migrations.DeleteModel(
                    name='ReadingClub',
                ),
            ],
            database_operations=[],
        ),
    ]

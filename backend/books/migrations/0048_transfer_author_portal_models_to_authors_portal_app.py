from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0047_transfer_marketplace_models_to_marketplace_app'),
        ('authors_portal', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='AuthorAnnouncement',
                ),
                migrations.DeleteModel(
                    name='AuthorClaim',
                ),
                migrations.DeleteModel(
                    name='AuthorEventAttendee',
                ),
                migrations.DeleteModel(
                    name='AuthorEvent',
                ),
                migrations.DeleteModel(
                    name='AuthorNewsletterSubscriber',
                ),
                migrations.DeleteModel(
                    name='AuthorNewsletterIssue',
                ),
                migrations.DeleteModel(
                    name='AuthorNewsletter',
                ),
                migrations.DeleteModel(
                    name='AuthorProfile',
                ),
            ],
            database_operations=[],
        ),
    ]

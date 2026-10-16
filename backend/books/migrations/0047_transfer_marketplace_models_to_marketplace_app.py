import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0046_transfer_audiobook_models_to_audiobooks_app'),
        ('marketplace', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='book',
                    name='publisher',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='books',
                        to='marketplace.publisher',
                        verbose_name='Editorial',
                    ),
                ),
                migrations.DeleteModel(
                    name='MarketplaceClick',
                ),
                migrations.DeleteModel(
                    name='BookBuyLink',
                ),
                migrations.DeleteModel(
                    name='Publisher',
                ),
            ],
            database_operations=[],
        ),
    ]

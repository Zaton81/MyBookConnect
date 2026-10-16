import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('books', '0044_transfer_clubs_models_to_clubs_app'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Badge',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('slug', models.SlugField(max_length=100, unique=True)),
                        ('name', models.CharField(max_length=150)),
                        ('description', models.TextField()),
                        ('icon', models.CharField(default='📚', max_length=50)),
                        ('category', models.CharField(choices=[('reading', 'Lectura'), ('streak', 'Rachas'), ('reviews', 'Reseñas'), ('community', 'Comunidad'), ('challenges', 'Retos')], db_index=True, default='reading', max_length=50)),
                        ('points', models.PositiveIntegerField(default=10)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                    ],
                    options={
                        'verbose_name': 'Insignia',
                        'verbose_name_plural': 'Insignias',
                        'db_table': 'books_badge',
                        'ordering': ['category', 'points', 'name'],
                    },
                ),
                migrations.CreateModel(
                    name='ReadingChallenge',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('slug', models.SlugField(max_length=100, unique=True)),
                        ('title', models.CharField(max_length=200)),
                        ('description', models.TextField()),
                        ('challenge_type', models.CharField(choices=[('books_count', 'Libros leídos'), ('pages_count', 'Páginas leídas'), ('reviews_count', 'Reseñas publicadas'), ('genre_books', 'Libros de género específico')], default='books_count', max_length=30)),
                        ('target_count', models.PositiveIntegerField(default=5)),
                        ('start_date', models.DateField()),
                        ('end_date', models.DateField()),
                        ('is_active', models.BooleanField(default=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('badge_reward', models.ForeignKey(blank=True, help_text='Insignia opcional que se otorga al superar el reto', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='challenges', to='gamification.badge')),
                        ('category', models.ForeignKey(blank=True, help_text='Categoría requerida si el reto es de tipo género específico', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='challenges', to='books.category')),
                    ],
                    options={
                        'verbose_name': 'Reto de lectura',
                        'verbose_name_plural': 'Retos de lectura',
                        'db_table': 'books_readingchallenge',
                        'ordering': ['-end_date'],
                    },
                ),
                migrations.CreateModel(
                    name='ReadingStreak',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('current_streak', models.PositiveIntegerField(default=0)),
                        ('longest_streak', models.PositiveIntegerField(default=0)),
                        ('last_reading_date', models.DateField(blank=True, null=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='reading_streak', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Racha de lectura',
                        'verbose_name_plural': 'Rachas de lectura',
                        'db_table': 'books_readingstreak',
                    },
                ),
                migrations.CreateModel(
                    name='DailyReadingLog',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('date', models.DateField(db_index=True, default=django.utils.timezone.now)),
                        ('pages_read', models.PositiveIntegerField(default=0)),
                        ('minutes_read', models.PositiveIntegerField(default=0)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('books', models.ManyToManyField(blank=True, db_table='books_dailyreadinglog_books', related_name='daily_logs', to='books.book')),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_reading_logs', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Log diario de lectura',
                        'verbose_name_plural': 'Logs diarios de lectura',
                        'db_table': 'books_dailyreadinglog',
                        'ordering': ['-date'],
                        'unique_together': {('user', 'date')},
                    },
                ),
                migrations.CreateModel(
                    name='ReadingGoal',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('year', models.PositiveIntegerField(db_index=True)),
                        ('target_books', models.PositiveIntegerField(default=12)),
                        ('target_pages', models.PositiveIntegerField(blank=True, default=0)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reading_goals', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Objetivo de lectura',
                        'verbose_name_plural': 'Objetivos de lectura',
                        'db_table': 'books_readinggoal',
                        'ordering': ['-year'],
                        'unique_together': {('user', 'year')},
                    },
                ),
                migrations.CreateModel(
                    name='UserBadge',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('awarded_at', models.DateTimeField(auto_now_add=True)),
                        ('metadata', models.JSONField(blank=True, default=dict)),
                        ('badge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_awards', to='gamification.badge')),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='badges', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Insignia de usuario',
                        'verbose_name_plural': 'Insignias de usuarios',
                        'db_table': 'books_userbadge',
                        'ordering': ['-awarded_at'],
                        'unique_together': {('user', 'badge')},
                    },
                ),
                migrations.CreateModel(
                    name='UserChallenge',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('current_progress', models.PositiveIntegerField(default=0)),
                        ('is_completed', models.BooleanField(default=False)),
                        ('completed_at', models.DateTimeField(blank=True, null=True)),
                        ('joined_at', models.DateTimeField(auto_now_add=True)),
                        ('challenge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='gamification.readingchallenge')),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='challenges', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Participación en reto',
                        'verbose_name_plural': 'Participaciones en retos',
                        'db_table': 'books_userchallenge',
                        'ordering': ['-joined_at'],
                        'unique_together': {('user', 'challenge')},
                    },
                ),
            ],
            database_operations=[],
        ),
    ]

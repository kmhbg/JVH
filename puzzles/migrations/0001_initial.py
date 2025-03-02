# Generated by Django 5.1.6 on 2025-02-09 21:51

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Friendship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Väntande'), ('accepted', 'Accepterad'), ('rejected', 'Avvisad')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Puzzle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_en', models.CharField(max_length=200)),
                ('name_nl', models.CharField(max_length=200)),
                ('product_number', models.CharField(max_length=20)),
                ('series', models.CharField(max_length=100)),
                ('pieces', models.CharField(max_length=20)),
                ('illustrator', models.CharField(max_length=100)),
                ('publisher', models.CharField(max_length=100)),
                ('release_date', models.CharField(max_length=50)),
                ('manufacturer', models.CharField(max_length=100)),
                ('image_url', models.URLField(blank=True, max_length=500, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PuzzleBorrowRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requester_id', models.IntegerField()),
                ('owner_id', models.IntegerField()),
                ('status', models.CharField(choices=[('pending', 'Väntande'), ('accepted', 'Accepterad'), ('rejected', 'Avvisad')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.TextField(blank=True)),
                ('puzzle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='puzzles.puzzle')),
            ],
            options={
                'db_table': 'puzzles_puzzleborrowrequest',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PuzzleImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, null=True, upload_to='puzzle_images/')),
                ('uploaded_by_id', models.IntegerField(blank=True, null=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('puzzle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_images', to='puzzles.puzzle')),
            ],
            options={
                'db_table': 'puzzles_puzzleimage',
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='PuzzleOwnership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner_id', models.IntegerField(null=True)),
                ('missing_pieces', models.IntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('borrowed_by', models.CharField(blank=True, max_length=200)),
                ('borrowed_date', models.DateField(blank=True, null=True)),
                ('return_date', models.DateField(blank=True, null=True)),
                ('puzzle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='puzzles.puzzle')),
            ],
            options={
                'unique_together': {('puzzle', 'owner_id')},
            },
        ),
        migrations.CreateModel(
            name='PuzzleBorrowHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('borrowed_by', models.CharField(max_length=200)),
                ('borrowed_date', models.DateField()),
                ('returned_date', models.DateField(blank=True, null=True)),
                ('puzzle_ownership', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='borrow_history', to='puzzles.puzzleownership')),
            ],
            options={
                'db_table': 'puzzles_puzzleborrowhistory',
                'ordering': ['-borrowed_date'],
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('role', models.CharField(choices=[('user', 'Användare'), ('admin', 'Administratör')], default='user', max_length=10)),
                ('friends', models.ManyToManyField(blank=True, through='puzzles.Friendship', to='puzzles.userprofile')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='friendship',
            name='receiver',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friendship_requests_received', to='puzzles.userprofile'),
        ),
        migrations.AddField(
            model_name='friendship',
            name='sender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friendship_requests_sent', to='puzzles.userprofile'),
        ),
        migrations.CreateModel(
            name='PuzzleCompletion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('puzzle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='puzzles.puzzle')),
            ],
            options={
                'db_table': 'puzzles_puzzlecompletion',
                'unique_together': {('puzzle', 'user_id')},
            },
        ),
        migrations.AlterUniqueTogether(
            name='friendship',
            unique_together={('sender', 'receiver')},
        ),
    ]

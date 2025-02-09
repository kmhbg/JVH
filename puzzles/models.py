from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Puzzle(models.Model):
    name_en = models.CharField(max_length=200)
    name_nl = models.CharField(max_length=200)
    product_number = models.CharField(max_length=20)
    series = models.CharField(max_length=100)
    pieces = models.CharField(max_length=20)
    illustrator = models.CharField(max_length=100)
    publisher = models.CharField(max_length=100)
    release_date = models.CharField(max_length=50)
    manufacturer = models.CharField(max_length=100)
    image_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.name_en} ({self.product_number})"

    @property
    def primary_image(self):
        return self.images.first().image_url if self.images.exists() else None

class PuzzleOwnership(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    owner_id = models.IntegerField(null=True)
    missing_pieces = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    borrowed_by = models.CharField(max_length=200, blank=True)
    borrowed_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('puzzle', 'owner_id')

    def __str__(self):
        return f"{self.puzzle.name_en} - Ägd av {self.owner_id}"

    @property
    def owner(self):
        if not self.owner_id:
            return None
        from django.contrib.auth.models import User
        try:
            user = User.objects.using('default').get(userprofile__id=self.owner_id)
            return user.userprofile
        except User.DoesNotExist:
            return None

class Friendship(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Väntande'),
        ('accepted', 'Accepterad'),
        ('rejected', 'Avvisad'),
    ]
    
    sender = models.ForeignKey('UserProfile', related_name='friendship_requests_sent', on_delete=models.CASCADE)
    receiver = models.ForeignKey('UserProfile', related_name='friendship_requests_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sender', 'receiver')

    def __str__(self):
        return f"{self.sender.user.username} -> {self.receiver.user.username} ({self.status})"

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('user', 'Användare'),
        ('admin', 'Administratör'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    friends = models.ManyToManyField('self', through='Friendship', symmetrical=False, blank=True)
    
    def __str__(self):
        return self.user.username
    
    def is_admin(self):
        return self.role == 'admin'

    @property
    def owned_puzzles(self):
        return Puzzle.objects.using('puzzles_db').filter(
            puzzleownership__owner_id=self.id
        )

    @property
    def completed_puzzles(self):
        return Puzzle.objects.using('puzzles_db').filter(
            puzzlecompletion__user_id=self.id
        )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and isinstance(self.user, User):
            self.role = 'admin' if self.user.is_superuser else 'user'
            super().save()

class PuzzleBorrowHistory(models.Model):
    puzzle_ownership = models.ForeignKey(PuzzleOwnership, on_delete=models.CASCADE, related_name='borrow_history')
    borrowed_by = models.CharField(max_length=200)
    borrowed_date = models.DateField()
    returned_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-borrowed_date']

    def __str__(self):
        return f"{self.puzzle_ownership.puzzle.name_en} - Lånad av {self.borrowed_by}"

class PuzzleImage(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, related_name='user_images')
    image = models.ImageField(upload_to='puzzle_images/', null=True, blank=True)
    uploaded_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

class PuzzleCompletion(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('puzzle', 'user_id')
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
    STATUS_CHOICES = [
        ('owned', 'Äger'),
        ('previously_owned', 'Har ägt'),
    ]
    
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    owner_id = models.IntegerField(null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='owned')
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
            puzzleownership__owner_id=self.id,
            puzzleownership__status='owned'
        )

    @property
    def previously_owned_puzzles(self):
        return Puzzle.objects.using('puzzles_db').filter(
            puzzleownership__owner_id=self.id,
            puzzleownership__status='previously_owned'
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

    def get_full_name(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username

class PuzzleBorrowHistory(models.Model):
    puzzle_ownership = models.ForeignKey(PuzzleOwnership, on_delete=models.CASCADE, related_name='borrow_history')
    borrowed_by = models.CharField(max_length=200)
    borrowed_date = models.DateField()
    returned_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-borrowed_date']
        db_table = 'puzzles_puzzleborrowhistory'
        app_label = 'puzzles'

    def save(self, *args, **kwargs):
        if 'using' not in kwargs:
            kwargs['using'] = 'puzzles_db'
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.puzzle_ownership.puzzle.name_en} - Lånad av {self.borrowed_by}"

class PuzzleImage(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, related_name='user_images')
    image = models.ImageField(upload_to='puzzle_images/', null=True, blank=True)
    uploaded_by_id = models.IntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        db_table = 'puzzles_puzzleimage'
        app_label = 'puzzles'

    def save(self, *args, **kwargs):
        if 'using' not in kwargs:
            kwargs['using'] = 'puzzles_db'
        return super().save(*args, **kwargs)

    @property
    def uploaded_by(self):
        if self.uploaded_by_id:
            return UserProfile.objects.using('default').get(id=self.uploaded_by_id)
        return None

class PuzzleCompletion(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('puzzle', 'user_id')
        db_table = 'puzzles_puzzlecompletion'
        app_label = 'puzzles'

    def save(self, *args, **kwargs):
        if 'using' not in kwargs:
            kwargs['using'] = 'puzzles_db'
        return super().save(*args, **kwargs)

class PuzzleBorrowRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Väntande'),
        ('accepted', 'Accepterad'),
        ('rejected', 'Avvisad'),
    ]
    
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    requester_id = models.IntegerField()
    owner_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'puzzles_puzzleborrowrequest'
        app_label = 'puzzles'

    def save(self, *args, **kwargs):
        if 'using' not in kwargs:
            kwargs['using'] = 'puzzles_db'
        return super().save(*args, **kwargs)

    @property
    def requester(self):
        return UserProfile.objects.using('default').get(id=self.requester_id)

    @property
    def owner(self):
        return UserProfile.objects.using('default').get(id=self.owner_id)

    def __str__(self):
        try:
            requester = self.requester.user.username
            owner = self.owner.user.username
            return f"{requester} vill låna {self.puzzle.name_en} från {owner}"
        except:
            return f"Låneförfrågan för {self.puzzle.name_en}"
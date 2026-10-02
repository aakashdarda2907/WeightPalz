from datetime import time, timedelta

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone

MEAL_FIELDS = ['breakfast', 'lunch', 'snacks', 'dinner']


class Profile(models.Model):
    """Extra info for each user: goal and weights from onboarding."""

    GOAL_CHOICES = [
        ('gain', 'Gain weight'),
        ('lose', 'Lose weight'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    goal = models.CharField(max_length=4, choices=GOAL_CHOICES, default='gain')
    start_weight = models.FloatField()
    target_weight = models.FloatField()
    reminder_time = models.TimeField(default=time(21, 0))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} ({self.goal})'

    @property
    def display_name(self):
        return self.user.first_name or self.user.username

    @property
    def meal_question(self):
        if self.goal == 'gain':
            return 'Did you eat a little more than yesterday?'
        return 'Did you eat a little less than yesterday?'

    def latest_weight(self):
        entry = self.user.weight_entries.first()  # ordered newest first
        return entry.weight if entry else self.start_weight

    def weekly_target(self):
        """
        A small target for this week, moving 0.3 kg from the weight at the
        start of the week toward the desired weight.
        Returns a dict: start, target, current, progress (0-100).
        """
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        before = self.user.weight_entries.filter(date__lt=monday).first()
        week_start = before.weight if before else self.start_weight
        current = self.latest_weight()
        step = 0.3

        if self.goal == 'gain':
            target = min(week_start + step, self.target_weight)
        else:
            target = max(week_start - step, self.target_weight)

        if target == week_start:
            progress = 100
        else:
            progress = (current - week_start) / (target - week_start) * 100
            progress = max(0, min(100, progress))

        return {
            'start': round(week_start, 1),
            'target': round(target, 1),
            'current': round(current, 1),
            'progress': round(progress),
        }

    def streak(self):
        """
        Consecutive days that count as checked in: weight logged OR all four
        meal buttons answered. Today is not required, so a streak does not
        break until the day ends.
        """
        weight_days = set(self.user.weight_entries.values_list('date', flat=True))
        meal_days = {m.date for m in self.user.meal_logs.all() if m.is_complete}
        active = weight_days | meal_days

        day = timezone.localdate()
        if day not in active:
            day -= timedelta(days=1)

        count = 0
        while day in active:
            count += 1
            day -= timedelta(days=1)
        return count


class WeightEntry(models.Model):
    """One weight reading per user per day."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_entries')
    date = models.DateField(default=timezone.localdate)
    weight = models.FloatField()

    class Meta:
        ordering = ['-date']
        unique_together = ('user', 'date')
        verbose_name_plural = 'weight entries'

    def __str__(self):
        return f'{self.user.username} {self.date}: {self.weight} kg'


class MealLog(models.Model):
    """
    The four daily buttons. Each field is:
    True = Yes, False = No, None = not answered yet.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_logs')
    date = models.DateField(default=timezone.localdate)
    breakfast = models.BooleanField(null=True, blank=True)
    lunch = models.BooleanField(null=True, blank=True)
    snacks = models.BooleanField(null=True, blank=True)
    dinner = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('user', 'date')

    def __str__(self):
        return f'{self.user.username} {self.date}: {self.yes_count}/4'

    @property
    def yes_count(self):
        return sum(1 for f in MEAL_FIELDS if getattr(self, f) is True)

    @property
    def answered_count(self):
        return sum(1 for f in MEAL_FIELDS if getattr(self, f) is not None)

    @property
    def is_complete(self):
        return self.answered_count == 4


class CalorieEntry(models.Model):
    """Optional calorie log. Never used in any goal or target calculation."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calorie_entries')
    date = models.DateField(default=timezone.localdate)
    name = models.CharField(max_length=100)
    kcal = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = 'calorie entries'

    def __str__(self):
        return f'{self.user.username} {self.date}: {self.name} ({self.kcal} kcal)'


class Friendship(models.Model):
    """A friend request. Becomes a friendship once the other person accepts."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
    ]

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f'{self.from_user.username} -> {self.to_user.username} ({self.status})'

    @staticmethod
    def friends_of(user):
        """All users who have an accepted friendship with `user`."""
        pairs = Friendship.objects.filter(status='accepted').filter(
            Q(from_user=user) | Q(to_user=user)
        )
        ids = set()
        for p in pairs:
            ids.add(p.to_user_id if p.from_user_id == user.id else p.from_user_id)
        return User.objects.filter(id__in=ids)

    @staticmethod
    def between(user_a, user_b):
        """The friendship row between two users, in either direction, or None."""
        return Friendship.objects.filter(
            Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a)
        ).first()


class Cheer(models.Model):
    """A 👏 sent to a friend. One per friend per day."""

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cheers_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cheers_received')
    date = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = ('from_user', 'to_user', 'date')

    def __str__(self):
        return f'{self.from_user.username} cheered {self.to_user.username} on {self.date}'
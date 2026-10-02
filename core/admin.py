from django.contrib import admin

from .models import CalorieEntry, Cheer, Friendship, MealLog, Profile, WeightEntry


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'goal', 'start_weight', 'target_weight', 'created_at')
    list_filter = ('goal',)
    search_fields = ('user__username', 'user__first_name', 'user__email')


@admin.register(WeightEntry)
class WeightEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight')
    list_filter = ('date',)
    search_fields = ('user__username',)
    date_hierarchy = 'date'


@admin.register(MealLog)
class MealLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'breakfast', 'lunch', 'snacks', 'dinner', 'yes_count')
    list_filter = ('date',)
    search_fields = ('user__username',)
    date_hierarchy = 'date'


@admin.register(CalorieEntry)
class CalorieEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'name', 'kcal')
    list_filter = ('date',)
    search_fields = ('user__username', 'name')


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('from_user__username', 'to_user__username')


@admin.register(Cheer)
class CheerAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'date')
    list_filter = ('date',)
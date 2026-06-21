from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from accounts.models import (
    AvailabilitySlot,
    MenteeProfile,
    MentorProfile,
    MentorProject,
    MentorSkill,
    RecommendationEvent,
    RecommendationExposure,
    Review,
    SessionBooking,
    UserProfile,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('role', 'onboarding_completed', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly.append('role')
        return readonly


class MenteeProfileInline(admin.StackedInline):
    model = MenteeProfile
    can_delete = False
    extra = 0
    fields = ('photo', 'bio', 'goals')
    verbose_name = 'Анкета менти'
    verbose_name_plural = 'Анкета менти'


class MentorProfileInline(admin.StackedInline):
    model = MentorProfile
    can_delete = False
    extra = 0
    fields = (
        'photo', 'headline', 'bio', 'gender', 'languages',
        'company', 'job_title',
        'rating', 'sessions_count',
    )
    readonly_fields = ('rating', 'sessions_count')
    verbose_name = 'Анкета ментора'
    verbose_name_plural = 'Анкета ментора'


class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'platform_role', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    @admin.display(description='Роль на платформе')
    def platform_role(self, obj):
        if hasattr(obj, 'profile') and obj.profile.role:
            return obj.profile.get_role_display()
        return '—'

    def get_inlines(self, request, obj=None):
        inlines = [UserProfileInline]
        if obj and hasattr(obj, 'profile'):
            if obj.profile.role == UserProfile.ROLE_MENTEE:
                inlines.append(MenteeProfileInline)
            elif obj.profile.role == UserProfile.ROLE_MENTOR:
                inlines.append(MentorProfileInline)
        return inlines


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


class MentorSkillInline(admin.TabularInline):
    model = MentorSkill
    extra = 0


class MentorProjectInline(admin.TabularInline):
    model = MentorProject
    extra = 0


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name_col', 'job_title', 'rating', 'sessions_count')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'company')
    readonly_fields = ('user', 'slug', 'rating', 'sessions_count', 'created_at')
    inlines = [MentorSkillInline, MentorProjectInline]

    @admin.display(description='Имя')
    def display_name_col(self, obj):
        return obj.display_name


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ('mentor', 'date', 'start_time', 'end_time', 'is_available')
    list_filter = ('date', 'is_available')


@admin.register(SessionBooking)
class SessionBookingAdmin(admin.ModelAdmin):
    list_display = ('mentee', 'mentor', 'slot', 'status', 'attendance_status', 'created_at')
    list_filter = ('status', 'attendance_status')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('mentor', 'mentee', 'rating', 'created_at')


class RecommendationEventInline(admin.TabularInline):
    model = RecommendationEvent
    extra = 0
    readonly_fields = ('event_type', 'booking', 'review', 'created_at')
    can_delete = False


@admin.register(RecommendationExposure)
class RecommendationExposureAdmin(admin.ModelAdmin):
    list_display = (
        'tracking_token',
        'mentee',
        'mentor',
        'rank',
        'final_score',
        'algorithm_version',
        'created_at',
    )
    list_filter = ('algorithm_version', 'created_at', 'mentor')
    search_fields = (
        'tracking_token',
        'mentee__username',
        'mentee__email',
        'mentor__user__username',
        'mentor__slug',
    )
    readonly_fields = (
        'tracking_token',
        'mentee',
        'mentor',
        'rank',
        'content_score',
        'rating_score',
        'experience_score',
        'final_score',
        'algorithm_version',
        'created_at',
    )
    inlines = [RecommendationEventInline]
    date_hierarchy = 'created_at'


@admin.register(RecommendationEvent)
class RecommendationEventAdmin(admin.ModelAdmin):
    list_display = ('exposure', 'event_type', 'booking', 'review', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('exposure__tracking_token',)
    readonly_fields = ('exposure', 'event_type', 'booking', 'review', 'created_at')
    raw_id_fields = ('exposure', 'booking', 'review')

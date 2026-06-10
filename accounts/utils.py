from accounts.models import UserProfile


def get_user_profile(user):
    profile, created = UserProfile.objects.get_or_create(user=user)
    if created and (user.is_superuser or user.is_staff):
        profile.onboarding_completed = True
        profile.save(update_fields=['onboarding_completed'])
    return profile

from accounts.notification_utils import get_unread_count


def notifications(request):
    if request.user.is_authenticated:
        return {'notification_unread_count': get_unread_count(request.user)}
    return {'notification_unread_count': 0}

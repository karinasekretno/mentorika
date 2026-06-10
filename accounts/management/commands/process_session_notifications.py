from django.core.management.base import BaseCommand

from accounts.notification_utils import process_booking_notifications


class Command(BaseCommand):
    help = 'Напоминания о сессиях, уведомления о начале/завершении и сообщения в чат.'

    def handle(self, *args, **options):
        process_booking_notifications()
        self.stdout.write(self.style.SUCCESS('Готово.'))

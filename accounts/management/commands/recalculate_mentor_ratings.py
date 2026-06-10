from django.core.management.base import BaseCommand

from accounts.review_utils import RATING_SESSION_WINDOW, recalculate_all_mentor_ratings


class Command(BaseCommand):
    help = (
        f'Пересчитывает рейтинг менторов как среднее за последние '
        f'{RATING_SESSION_WINDOW} оценённых сессий.'
    )

    def handle(self, *args, **options):
        count = recalculate_all_mentor_ratings()
        self.stdout.write(self.style.SUCCESS(f'Обновлено менторов: {count}.'))

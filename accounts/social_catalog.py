SOCIAL_PLATFORM_CHOICES = [
    ('telegram', 'Telegram'),
    ('linkedin', 'LinkedIn'),
    ('github', 'GitHub'),
    ('habr', 'Habr'),
    ('vk', 'VK'),
    ('youtube', 'YouTube'),
    ('website', 'Сайт'),
    ('other', 'Другое'),
]

SOCIAL_MAIN_PLATFORMS = SOCIAL_PLATFORM_CHOICES[:-1]

SOCIAL_PLATFORM_LABELS = dict(SOCIAL_PLATFORM_CHOICES)

SOCIAL_PLATFORM_INDEX = {value: index for index, (value, _label) in enumerate(SOCIAL_MAIN_PLATFORMS)}

SOCIAL_OTHER_START_INDEX = len(SOCIAL_MAIN_PLATFORMS)

MAX_PORTFOLIO_LINKS = 10
MAX_SOCIAL_LINKS = 10

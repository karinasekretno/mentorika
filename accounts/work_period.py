from datetime import date

RU_MONTHS = {
    1: 'янв.',
    2: 'фев.',
    3: 'мар.',
    4: 'апр.',
    5: 'мая',
    6: 'июн.',
    7: 'июл.',
    8: 'авг.',
    9: 'сент.',
    10: 'окт.',
    11: 'нояб.',
    12: 'дек.',
}


def month_value(value):
    if not value:
        return ''
    return value.strftime('%Y-%m')


def parse_month(value):
    if not value:
        return None
    year, month = value.split('-', 1)
    return date(int(year), int(month), 1)


def format_month_year(value):
    if not value:
        return ''
    return f'{RU_MONTHS[value.month]} {value.year} г.'


def format_work_period(start_date, end_date, is_current):
    if not start_date:
        return ''
    text = f'с {format_month_year(start_date)}'
    if is_current:
        return f'{text} по настоящее время'
    if end_date:
        return f'{text} по {format_month_year(end_date)}'
    return text

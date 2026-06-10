from django import template

from accounts.chat_utils import get_session_rating_prompt

register = template.Library()


@register.simple_tag
def session_rating_prompt(message, user):
    return get_session_rating_prompt(message, user)

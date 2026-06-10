import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from accounts.anketa_utils import (
    education_from_post,
    education_from_saved,
    empty_education_row,
    empty_portfolio_row,
    empty_work_row,
    portfolio_from_post,
    portfolio_from_saved,
    social_form_slots,
    social_from_post,
    social_from_saved,
    topics_from_post,
    topics_from_saved,
    work_from_post,
    work_from_saved,
)
from accounts.languages import language_choices_for
from accounts.interests_catalog import (
    custom_interests_from_post,
    custom_interests_from_saved,
    interest_choices_for,
    standard_interest_names,
)
from accounts.skills_catalog import (
    SKILL_LEVEL_CHOICES,
    catalog_skill_levels,
    custom_skills_from_post,
    custom_skills_from_saved,
    skill_choices_for,
    skill_level_field_name,
)
from accounts.models import AvailabilitySlot, MenteeProfile, MentorProfile, MentorSkill, UserProfile
from accounts.social_catalog import SOCIAL_OTHER_START_INDEX

class SignUpForm(forms.Form):
    name = forms.CharField(max_length=150, label='Имя')
    email = forms.EmailField(label='Email')
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput)
    role = forms.ChoiceField(
        label='Роль на платформе',
        choices=[
            (UserProfile.ROLE_MENTEE, 'Менти (ученик)'),
            (UserProfile.ROLE_MENTOR, 'Ментор'),
        ],
        initial=UserProfile.ROLE_MENTEE,
        widget=forms.RadioSelect,
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Пароли не совпадают.')
        if password1:
            validate_password(password1)
        return cleaned

    def _make_username(self, email):
        base = re.sub(r'[^\w.@+-]', '', email.split('@')[0])[:30] or 'user'
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{counter}'
            counter += 1
        return username

    def save(self):
        email = self.cleaned_data['email']
        role = self.cleaned_data['role']
        user = User.objects.create_user(
            username=self._make_username(email),
            email=email,
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['name'].strip(),
        )
        UserProfile.objects.create(
            user=user,
            role=role,
            active_role=role,
            onboarding_completed=(role == UserProfile.ROLE_MENTOR),
        )
        if role == UserProfile.ROLE_MENTEE:
            MenteeProfile.objects.create(user=user)
        else:
            MentorProfile.objects.create(user=user)
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Email')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)

    def clean(self):
        login = self.cleaned_data.get('username', '').strip()
        if '@' in login:
            user = User.objects.filter(email__iexact=login).first()
            if user:
                self.cleaned_data['username'] = user.username
        return super().clean()


class PasswordResetRequestForm(PasswordResetForm):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )


class MenteeOnboardingForm(forms.ModelForm):
    class Meta:
        model = MenteeProfile
        fields = ('bio', 'goals')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Расскажите, чем занимаетесь и что вас интересует...'}),
            'goals': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Например: освоить React, подготовиться к собеседованию...'}),
        }
        labels = {
            'bio': 'О себе',
            'goals': 'Цели обучения',
        }


class MenteePhotoForm(forms.ModelForm):
    class Meta:
        model = MenteeProfile
        fields = ('photo',)


class MenteeProfileForm(forms.Form):
    first_name = forms.CharField(label='Имя', max_length=150)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)
    bio = forms.CharField(
        label='О себе',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 8,
            'class': 'mentor-anketa__textarea',
            'placeholder': 'Расскажите, чем занимаетесь и что вас интересует...',
        }),
    )
    goals = forms.CharField(
        label='Цели обучения',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 6,
            'class': 'mentor-anketa__textarea',
            'placeholder': 'Например: освоить React, подготовиться к собеседованию...',
        }),
    )
    interests = forms.MultipleChoiceField(
        label='Интересы',
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, saved_interests=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interests'].choices = interest_choices_for()
        saved_interests = saved_interests or []
        standard = standard_interest_names()

        if self.is_bound:
            selected_interests = set(self.data.getlist('interests'))
            self.custom_interest_rows = custom_interests_from_post(self.data)
        else:
            selected_interests = {name for name in saved_interests if name in standard}
            self.custom_interest_rows = custom_interests_from_saved(saved_interests)

        for row in self.custom_interest_rows:
            row['name_field'] = f"custom_interest_{row['index']}_name"

        self.interest_rows = []
        for value, label in self.fields['interests'].choices:
            self.interest_rows.append({
                'value': value,
                'label': label,
                'checked': value in selected_interests,
            })


class MentorOnboardingForm(forms.ModelForm):
    class Meta:
        model = MentorProfile
        fields = (
            'bio', 'company', 'job_title',
            'portfolio_url', 'portfolio_text',
        )
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Опишите ваш опыт и чем можете помочь ученикам...'}),
            'portfolio_text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Ключевые проекты, достижения, ссылки на кейсы...'}),
            'company': forms.TextInput(attrs={'placeholder': 'Сбер, Яндекс, VK...'}),
            'job_title': forms.TextInput(attrs={'placeholder': 'Senior Developer, Product Manager...'}),
            'portfolio_url': forms.URLInput(attrs={'placeholder': 'https://...'}),
        }
        labels = {
            'bio': 'О себе и экспертизе',
            'company': 'Текущая компания',
            'job_title': 'Должность',
            'portfolio_url': 'Ссылка на портфолио',
            'portfolio_text': 'Описание портфолио и проектов',
        }


class AvailabilitySlotForm(forms.ModelForm):
    class Meta:
        model = AvailabilitySlot
        fields = ('date', 'start_time', 'end_time')
        labels = {
            'date': 'Дата',
            'start_time': 'Начало',
            'end_time': 'Конец',
        }
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'slot-form__control',
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'slot-form__control',
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'slot-form__control',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get('start_time')
        end_time = cleaned.get('end_time')
        if start_time and end_time and end_time <= start_time:
            raise ValidationError('Время окончания должно быть позже начала.')
        return cleaned


class BookingRescheduleForm(forms.Form):
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    start_time = forms.TimeField(
        label='Начало',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    end_time = forms.TimeField(
        label='Окончание',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get('start_time')
        end_time = cleaned.get('end_time')
        if start_time and end_time and end_time <= start_time:
            raise ValidationError('Время окончания должно быть позже начала.')
        return cleaned


class MentorSearchForm(forms.Form):
    first_name = forms.CharField(required=False, label='Имя')
    last_name = forms.CharField(required=False, label='Фамилия')
    min_rating = forms.IntegerField(required=False, min_value=0, max_value=5, label='Мин. рейтинг')
    max_rating = forms.IntegerField(required=False, min_value=0, max_value=5, label='Макс. рейтинг')
    sort = forms.ChoiceField(
        required=False,
        label='Сортировка',
        choices=[
            ('popular', 'Сначала: популярные'),
            ('rating', 'По рейтингу'),
            ('nearest', 'По ближайшим записям'),
        ],
        initial='popular',
    )

    def clean(self):
        cleaned = super().clean()
        min_rating = cleaned.get('min_rating')
        max_rating = cleaned.get('max_rating')
        if min_rating is None:
            cleaned['min_rating'] = 0
        if max_rating is None:
            cleaned['max_rating'] = 5
        if cleaned['min_rating'] > cleaned['max_rating']:
            cleaned['max_rating'] = cleaned['min_rating']
        return cleaned


class MentorPhotoForm(forms.ModelForm):
    class Meta:
        model = MentorProfile
        fields = ('photo',)


class MentorAnketaForm(forms.Form):
    headline = forms.CharField(
        label='Краткое описание',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Краткое описание'}),
    )
    first_name = forms.CharField(label='Имя', max_length=150)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)
    gender = forms.ChoiceField(
        label='Пол',
        required=False,
        choices=MentorProfile.GENDER_CHOICES,
    )
    bio = forms.CharField(
        label='О себе',
        required=False,
        widget=forms.Textarea(attrs={'rows': 10, 'placeholder': 'Расскажите о своём опыте, экспертизе и чем можете помочь...'}),
    )
    languages = forms.MultipleChoiceField(
        label='Языки',
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple,
    )
    skills = forms.MultipleChoiceField(
        label='Скиллы',
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple,
    )
    portfolio_description = forms.CharField(
        label='О портфолио',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Ключевые проекты, достижения, кейсы...'}),
    )

    def __init__(self, *args, saved_languages=None, saved_skill_levels=None, saved_topics=None, saved_work_experiences=None, saved_education=None, saved_mentor=None, **kwargs):
        super().__init__(*args, **kwargs)
        saved_skill_levels = saved_skill_levels or {}
        catalog_levels = catalog_skill_levels(saved_skill_levels)
        self.fields['languages'].choices = language_choices_for(saved_languages)
        self.fields['skills'].choices = skill_choices_for()
        self.saved_skill_levels = saved_skill_levels
        self.skill_level_choices = SKILL_LEVEL_CHOICES

        if self.is_bound:
            selected_skills = set(self.data.getlist('skills'))
            self.custom_skill_rows = custom_skills_from_post(self.data)
        else:
            selected_skills = set(catalog_levels.keys())
            if 'skills' in self.initial:
                selected_skills = set(self.initial.get('skills') or [])
            self.custom_skill_rows = custom_skills_from_saved(saved_skill_levels)

        for row in self.custom_skill_rows:
            row['name_field'] = f"custom_skill_{row['index']}_name"
            row['level_field'] = f"custom_skill_{row['index']}_level"

        if self.is_bound:
            self.topic_rows = topics_from_post(self.data, include_empty=True)
            if not self.topic_rows:
                self.topic_rows = [{'index': 0, 'text': ''}]
        else:
            self.topic_rows = topics_from_saved(saved_topics or [])

        for row in self.topic_rows:
            row['field'] = f"consultation_topic_{row['index']}"

        if self.is_bound:
            self.work_rows = work_from_post(self.data, include_empty=True)
            if not self.work_rows:
                self.work_rows = [empty_work_row()]
        else:
            self.work_rows = work_from_saved(saved_work_experiences or [])

        for row in self.work_rows:
            idx = row['index']
            row['company_field'] = f'work_experience_{idx}_company'
            row['start_field'] = f'work_experience_{idx}_start'
            row['end_field'] = f'work_experience_{idx}_end'
            row['is_current_field'] = f'work_experience_{idx}_is_current'
            row['job_title_field'] = f'work_experience_{idx}_job_title'
            row['description_field'] = f'work_experience_{idx}_description'

        if self.is_bound:
            self.education_rows = education_from_post(self.data, include_empty=True)
            if not self.education_rows:
                self.education_rows = [empty_education_row()]
        else:
            self.education_rows = education_from_saved(saved_education or [])

        for row in self.education_rows:
            idx = row['index']
            row['institution_field'] = f'education_{idx}_institution'
            row['graduation_year_field'] = f'education_{idx}_graduation_year'
            row['specialization_field'] = f'education_{idx}_specialization'

        if self.is_bound:
            self.portfolio_rows = portfolio_from_post(self.data, include_empty=True)
            if not self.portfolio_rows:
                self.portfolio_rows = [empty_portfolio_row()]
            social_rows = social_from_post(self.data, include_empty=True)
        else:
            self.portfolio_rows = portfolio_from_saved(saved_mentor) if saved_mentor else [empty_portfolio_row()]
            social_rows = social_from_saved(saved_mentor) if saved_mentor else []

        self.social_main_platforms, self.social_other_rows = social_form_slots(social_rows)

        for row in self.portfolio_rows:
            row['field'] = f"portfolio_link_{row['index']}"

        for platform in self.social_main_platforms:
            idx = platform['index']
            platform['platform_field'] = f'social_link_{idx}_platform'
            platform['url_field'] = f'social_link_{idx}_url'

        for row in self.social_other_rows:
            idx = row['index']
            row['platform_field'] = f'social_link_{idx}_platform'
            row['url_field'] = f'social_link_{idx}_url'

        self.social_other_start_index = SOCIAL_OTHER_START_INDEX

        self.skill_rows = []
        for value, label in self.fields['skills'].choices:
            self.skill_rows.append({
                'value': value,
                'label': label,
                'level_field': skill_level_field_name(value),
                'checked': value in selected_skills,
                'level_disabled': value not in selected_skills,
                'level': catalog_levels.get(value, MentorSkill.LEVEL_MIDDLE),
            })


class ChatMessageForm(forms.Form):
    text = forms.CharField(
        label='Сообщение',
        max_length=2000,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'chat-composer__input',
            'placeholder': 'Напишите сообщение...',
            'data-chat-input': '',
        }),
    )

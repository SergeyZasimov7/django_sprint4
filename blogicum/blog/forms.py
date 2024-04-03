from django import forms
from django.contrib.auth.models import User

from .models import Post, Congratulation, Profile


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ('author',)
        widgets = {
            'pub_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['pub_date'].widget = forms.DateInput(
            attrs={'type': 'date'}
        )

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        return first_name.split()[0]


class CongratulationForm(forms.ModelForm):

    class Meta:
        model = Congratulation
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3, 'placeholder': 'Введите ваш комментарий здесь'
            })
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 3, 'placeholder': 'Введите информацию о себе здесь'
            }),
        }


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name',)

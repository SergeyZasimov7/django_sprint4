from django import forms
from django.contrib.auth.models import User

from .models import Сomment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ('author',)


class CommentForm(forms.ModelForm):

    class Meta:
        model = Сomment
        fields = ('text',)


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name',)

from django.contrib import admin

from .models import Category, Сomment, Location, Post

admin.site.register(Post)
admin.site.register(Location)
admin.site.register(Category)
admin.site.register(Сomment)

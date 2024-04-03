from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('posts/<int:post_id>/', views.PostDetailView.as_view(),
         name='post_detail'
         ),
    path('posts/create/', views.CreatePostView.as_view(), name='create_post'),
    path('posts/<int:post_id>/edit/', views.EditPostView.as_view(),
         name='edit_post'
         ),
    path('posts/<int:post_id>/delete/', views.DeletePostView.as_view(),
         name='delete_post'
         ),
    path('category/<slug:category_slug>/', views.CategoryPostsView.as_view(),
         name='category_posts'
         ),
    path('<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('posts/<int:post_id>/edit_comment/<int:comment_id>/',
         views.edit_comment, name='edit_comment'
         ),
    path('posts/<int:post_id>/delete_comment/<int:comment_id>/',
         views.delete_comment, name='delete_comment'
         ),
    path('profile/edit/', views.EditProfileView.as_view(),
         name='edit_profile'
         ),
    path('profile/<str:username>/', views.ProfileView.as_view(),
         name='profile'
         ),
    path('', views.PostListView.as_view(), name='index'),
]

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView, View
from django.core.paginator import Paginator 

from .forms import CommentForm, PostForm, UserEditForm
from .models import Category, Сomment, Post

User = get_user_model()

ENTRIES_PER_PAGE = 10


def get_published_posts(posts, include_unpublished_posts=False):
    query_set = posts.annotate(
        comment_count=Count('comments')).order_by('-pub_date')
    if not include_unpublished_posts:
        query_set = query_set.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True
        )
    return query_set


class PostListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'posts'
    paginate_by = ENTRIES_PER_PAGE
    queryset = get_published_posts(Post.objects.all())


class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        post = super().get_object(queryset)

        if self.request.user != post.author:
            post = get_object_or_404(
                get_published_posts(Post.objects.filter(pk=post.pk))
            )

        return post

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            form=CommentForm(),
            comments=self.object.comments.all(),
        )


class CreatePostView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'blog/create.html', {'form': PostForm()})

    def post(self, request):
        form = PostForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, 'blog/create.html', {'form': form})
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect('blog:profile', username=request.user.username)


class EditPostView(LoginRequiredMixin, View):

    def get_post(self, post_id):
        return get_object_or_404(Post, pk=post_id)

    def get(self, request, post_id):
        post = self.get_post(post_id)
        if post.author == request.user:
            return render(request, 'blog/create.html', {
                'form': PostForm(instance=post)
            })
        else:
            return redirect('blog:index')

    def post(self, request, post_id):
        post = self.get_post(post_id)
        if post.author != request.user:
            return redirect('blog:post_detail', post_id=post_id)

        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            updated_post = form.save()
            return redirect(updated_post)
        return render(request, 'blog/create.html', {'form': form})


class DeletePostView(LoginRequiredMixin, View):

    def get_post(self, post_id):
        return get_object_or_404(Post, pk=post_id)

    def get(self, request, post_id):
        post = self.get_post(post_id)
        if post.author == request.user:
            form = PostForm(instance=post)
            return render(request, 'blog/create.html', {
                'form': form, 'delete_mode': True
            })
        else:
            return redirect('blog:index')

    def post(self, request, post_id):
        post = self.get_post(post_id)
        if post.author == request.user:
            post.delete()
        return redirect('blog:index')


class CategoryPostsView(DetailView):
    model = Category
    template_name = 'blog/category.html'
    slug_field = 'category_slug'
    slug_url_kwarg = 'category_slug'
    context_object_name = 'category'
    paginate_by = ENTRIES_PER_PAGE

    def get_object(self):
        return get_object_or_404(
            Category, slug=self.kwargs[self.slug_url_kwarg], is_published=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        posts = get_published_posts(category.posts.all())
        context['category'] = category
        context['page_obj'] = Paginator(
            posts, self.paginate_by).get_page(
            self.request.GET.get('page')
        )
        return context


class ProfileView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    context_object_name = 'user'
    paginate_by = ENTRIES_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        author = get_object_or_404(User, username=self.kwargs['username'])
        if self.request.user == author:
            posts = author.posts.all()
        else:
            posts = get_published_posts(author.posts)
        context['profile'] = author
        context['page_obj'] = Paginator(
            posts, self.paginate_by).get_page(
            self.request.GET.get('page')
        )

        return context


class EditProfileView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'blog/user.html'
    form_class = UserEditForm
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self) -> str:
        return reverse('blog:profile', args=[self.request.user.username])


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Сomment, pk=comment_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)

    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)

    return render(request, 'blog/comment.html', {
        'comment': comment, 'form': form
    })


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Сomment, pk=comment_id)

    if comment.author == request.user:
        if request.method == 'POST':
            comment.delete()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        return redirect('blog:index')

    return render(request, 'blog/comment.html', {'comment': comment})

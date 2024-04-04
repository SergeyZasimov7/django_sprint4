from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView, View

from .forms import CommentForm, PostForm, UserEditForm
from .models import Category, Сomment, Post

User = get_user_model()

ENTRIES_PER_PAGE = 10


def get_published_posts():
    return Post.objects.filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')


class PostListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'posts'
    paginate_by = ENTRIES_PER_PAGE

    def get_queryset(self):
        posts_with_comment_count = get_published_posts()
        return posts_with_comment_count

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = dict(**context, comment_count=Сomment.objects.count())
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def check_post_visibility(self, request):
        post = self.get_object()
        if not post.is_published:
            if post.author != request.user:
                raise get_object_or_404(
                    Post, pk=self.kwargs['post_id'], author=self.request.user
                )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_post_visibility(request)
        context = self.get_context_data(object=self.object)
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.all()
        return context


class CreatePostView(LoginRequiredMixin, View):

    def get(self, request):
        form = PostForm()
        return render(request, 'blog/create.html', {'form': form})

    def post(self, request):
        form = PostForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, 'blog/create.html', {'form': form})
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect(
            reverse('blog:profile', kwargs={'username': request.user.username})
        )


class EditPostView(LoginRequiredMixin, View):

    def get(self, request, post_id):
        return render(request, 'blog/create.html', {
            'form': PostForm(instance=get_object_or_404(Post, pk=post_id))
        })

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)

        if post.author != request.user:
            return redirect(
                reverse('blog:post_detail', kwargs={'post_id': post_id})
            )

        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            updated_post = form.save()
            return redirect(updated_post)
        return render(request, 'blog/create.html', {'form': form})


class DeletePostView(LoginRequiredMixin, View):

    def get(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        form = PostForm(instance=post)
        return render(
            request, 'blog/create.html', {'form': form, 'delete_mode': True}
        )

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
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
            Category, slug=self.kwargs['category_slug'], is_published=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        posts = category.posts.filter(
            is_published=True, pub_date__lte=timezone.now()
        )
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
        user_object = get_object_or_404(User, username=self.kwargs['username'])
        posts = user_object.posts.all()
        posts_with_comments = posts.annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')
        context['profile'] = user_object
        context['page_obj'] = Paginator(
            posts_with_comments, self.paginate_by).get_page(
                self.request.GET.get('page')
        )

        return context


class EditProfileView(UpdateView):
    model = User
    template_name = 'blog/user.html'
    form_class = UserEditForm
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.request.user)

    def get_success_url(self) -> str:
        username = str(self.request.user.username)
        return reverse('blog:profile', kwargs={'username': username})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        comments = post.comments.all()
        return render(request, 'blog/detail.html', {
            'post': post,
            'comments': comments,
            'form': CommentForm()
        })

    return render(request, 'blog/detail.html', {'form': form, 'post': post})


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Сomment, pk=comment_id)
    if comment.author != request.user:
        messages.error(request, "Вы не можете редактировать этот комментарий.")
        return redirect(
            reverse('blog:post_detail', kwargs={'post_id': post_id})
        )

    form = CommentForm(instance=comment)
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect(
                reverse('blog:post_detail', args=[post_id])
            )

    return render(request, 'blog/comment.html', {
        'comment': comment, 'form': form
    })


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Сomment, pk=comment_id)

    if comment.author == request.user or request.user.is_staff:
        if request.method == 'POST':
            comment.delete()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        return redirect('blog/index.html')

    return render(request, 'blog/comment.html', {'comment': comment})

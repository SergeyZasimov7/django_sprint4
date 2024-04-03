from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView, UpdateView, View

from .forms import PostForm, CongratulationForm, UserEditForm
from .models import Congratulation, Category, Post


def get_published_posts(posts):
    return posts.filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True
    )


class PostListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        posts = get_published_posts(Post.objects)
        posts_with_comment_count = posts.annotate(
            comment_count=Count('congratulations')
        )
        return posts_with_comment_count.order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_count'] = Congratulation.objects.count()
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.is_published and self.object.author != request.user:
            raise Http404("Сообщение не существует")
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CongratulationForm()
        context['comments'] = self.object.congratulations.all()
        return context


class CreatePostView(LoginRequiredMixin, View):
    def get(self, request):
        form = PostForm()
        return render(request, 'blog/create.html', {'form': form})

    def post(self, request):
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = request.user
            new_post.save()
            return redirect('/profile/' + request.user.username + '/')
        return render(request, 'blog/create.html', {'form': form})


class EditPostView(View):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        form = PostForm(instance=post)
        return render(request, 'blog/create.html', {'form': form})

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)

        if post.author != request.user:
            return redirect('/posts/{}/'.format(post_id))

        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.save()

            return redirect(updated_post)

        return render(request, 'blog/create.html', {'form': form})


class DeletePostView(View):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        form = PostForm(instance=post)
        return render(
            request, 'blog/create.html', {'form': form, 'delete_mode': True}
        )

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        if post.author == request.user or request.user.is_superuser:
            post.delete()
            return redirect('blog:index')
        else:
            raise Http404("Вам не разрешено удалять это сообщение")


class CategoryPostsView(DetailView):
    model = Category
    template_name = 'blog/category.html'
    slug_field = 'category_slug'
    slug_url_kwarg = 'category_slug'
    context_object_name = 'category'
    paginate_by = 10

    def get_object(self):
        return get_object_or_404(
            Category, slug=self.kwargs['category_slug'], is_published=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()

        posts = Post.objects.filter(
            category=category, is_published=True, pub_date__lte=timezone.now()
        )

        paginator = Paginator(posts, self.paginate_by)
        page = self.request.GET.get('page')
        posts_page = paginator.get_page(page)

        context['category'] = category
        context['page_obj'] = posts_page
        return context


class ProfileView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    context_object_name = 'user'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_object = get_object_or_404(User, username=self.kwargs['username'])
        profile = self.get_object()
        posts = user_object.posts.all()
        posts_with_comment_count = posts.annotate(
            comment_count=Count('congratulations')
        )

        sorted_posts = posts_with_comment_count.order_by('-pub_date')

        paginator = Paginator(sorted_posts, self.paginate_by)
        page = self.request.GET.get('page')
        posts_page = paginator.get_page(page)

        context['profile'] = profile
        context['page_obj'] = posts_page
        context['comment_count'] = Congratulation.objects.filter(
            post__in=posts).count()

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
        return reverse('blog:profile', kwargs={'username': self.request.user})


@login_required
def simple_view(request):
    return HttpResponse('Страница для залогиненных пользователей!')


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.method == 'POST':
        form = CongratulationForm(request.POST)
        if form.is_valid():
            congratulation = form.save(commit=False)
            congratulation.author = request.user
            congratulation.post = post
            congratulation.save()

            comments = post.congratulations.all()

            return render(request, 'blog/detail.html', {
                'post': post,
                'comments': comments,
                'form': CongratulationForm()
            })
    else:
        form = CongratulationForm()

    return render(request, 'blog/detail.html', {'form': form, 'post': post})


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Congratulation, pk=comment_id)
    if comment.author != request.user:
        messages.error(request, "Вы не можете редактировать этот комментарий.")
        return HttpResponseRedirect(
            reverse('blog:post_detail', kwargs={'post_id': post_id})
        )

    form = CongratulationForm(instance=comment)
    if request.method == 'POST':
        form = CongratulationForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(
                reverse('blog:post_detail', kwargs={'post_id': post_id})
            )

    return render(request, 'blog/comment.html', {
        'comment': comment, 'form': form
    })


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Congratulation, pk=comment_id)

    if comment.author == request.user or request.user.is_staff:
        if request.method == 'POST':
            comment.delete()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        return redirect('blog/index.html')

    return render(request, 'blog/comment.html', {'comment': comment})

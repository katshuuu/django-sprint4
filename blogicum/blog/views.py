from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import CommentForm, PostForm, UserEditForm
from .models import Category, Comment, Post
from .querysets import posts_for_list, published_posts

User = get_user_model()

POSTS_PER_PAGE = 10


class PostListView(ListView):
    model = Post
    paginate_by = POSTS_PER_PAGE


class IndexView(PostListView):
    template_name = 'blog/index.html'

    def get_queryset(self):
        return posts_for_list(published_posts())


class CategoryPostsView(PostListView):
    template_name = 'blog/category.html'

    def get_category(self):
        if not hasattr(self, '_category'):
            self._category = get_object_or_404(
                Category,
                slug=self.kwargs['category_slug'],
                is_published=True,
            )
        return self._category

    def get_queryset(self):
        category = self.get_category()
        return posts_for_list(published_posts(category.posts))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.get_category()
        return context


class ProfileView(PostListView):
    template_name = 'blog/profile.html'

    def get_author(self):
        if not hasattr(self, '_author'):
            self._author = get_object_or_404(
                User,
                username=self.kwargs['username'],
            )
        return self._author

    def get_queryset(self):
        return posts_for_list(
            Post.objects.filter(author=self.get_author()),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.get_author()
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username},
        )


class RegistrationView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')


def visible_post_or_404(post_id, user):
    """Автор видит свой пост, остальные — только опубликованный."""
    post = get_object_or_404(
        Post.objects.select_related('author', 'category', 'location'),
        pk=post_id,
    )
    if user.is_authenticated and user == post.author:
        return post
    return get_object_or_404(published_posts(), pk=post_id)


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        return visible_post_or_404(
            self.kwargs['post_id'],
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username},
        )


class AuthorRequiredMixin(LoginRequiredMixin):
    """Изменять объект может его автор."""

    def dispatch(self, request, *args, **kwargs):
        self.setup(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.object = self.get_object()
        if self.object.author != request.user:
            return redirect(self.get_denied_url())
        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs,
        )

    def get_denied_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']},
        )


class PostUpdateView(AuthorRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.object.pk},
        )


class PostDeleteView(AuthorRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.object)
        return context

    def get_success_url(self):
        return reverse('blog:index')


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm

    def get_post(self):
        return visible_post_or_404(
            self.kwargs['post_id'],
            self.request.user,
        )

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = self.get_post()
        return super().form_valid(form)

    def form_invalid(self, form):
        post = self.get_post()
        return render(
            self.request,
            'blog/detail.html',
            {
                'post': post,
                'form': form,
                'comments': post.comments.select_related('author'),
            },
        )

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']},
        )


class CommentUpdateView(AuthorRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    context_object_name = 'comment'

    def get_object(self, queryset=None):
        return get_object_or_404(
            Comment,
            pk=self.kwargs['comment_id'],
            post_id=self.kwargs['post_id'],
        )

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']},
        )


class CommentDeleteView(AuthorRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    context_object_name = 'comment'

    def get_object(self, queryset=None):
        return get_object_or_404(
            Comment,
            pk=self.kwargs['comment_id'],
            post_id=self.kwargs['post_id'],
        )

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']},
        )

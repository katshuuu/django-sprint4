from django.db.models import Count
from django.utils import timezone

from .models import Post


def published_posts(manager=None):
    """Посты, которые видят все посетители."""
    if manager is None:
        manager = Post.objects
    return manager.filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now(),
    )


def posts_for_list(queryset):
    """Список публикаций с автором, категорией и числом комментариев."""
    return queryset.select_related(
        'author',
        'category',
        'location',
    ).annotate(
        comment_count=Count('comments'),
    ).order_by('-pub_date')

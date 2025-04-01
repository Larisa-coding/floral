from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Category, Product


def home(request):
    """Домашняя страница"""
    featured_products = Product.objects.filter(featured=True, available=True)[:6]
    latest_products = Product.objects.filter(available=True).order_by('-created_at')[:8]
    categories = Category.objects.all()

    context = {
        'featured_products': featured_products,
        'latest_products': latest_products,
        'categories': categories,
    }
    return render(request, 'products/home.html', context)


def product_list(request):
    """Список всех товаров с возможностью фильтрации"""
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()
    current_category = None

    # Параметры фильтрации
    category_slug = request.GET.get('category')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort_by', 'name')

    # Фильтрация по категории
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=current_category)

    # Поиск по запросу
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Сортировка
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:  # по умолчанию по имени
        products = products.order_by('name')

    context = {
        'products': products,
        'categories': categories,
        'category_slug': category_slug,
        'current_category': current_category,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, slug):
    """Детальная страница товара"""
    product = get_object_or_404(Product, slug=slug, available=True)
    related_products = Product.objects.filter(category=product.category, available=True).exclude(id=product.id)[:4]

    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'products/product_detail.html', context)


def about(request):
    """Страница о магазине"""
    return render(request, 'products/about.html')


def contact(request):
    """Страница контактов"""
    return render(request, 'products/contact.html')
from django.urls import path

from skincareApi.views import (
    ingredient_list,
    ingredient_search,
    product_collection,
    product_detail,
    product_search,
)

urlpatterns = [
    path("products/", product_collection, name="skincare-product-collection"),
    path("products/search/", product_search, name="skincare-product-search"),
    path("products/<int:product_id>/", product_detail, name="skincare-product-detail"),
    path("ingredients/", ingredient_list, name="skincare-ingredient-list"),
    path("ingredients/search/", ingredient_search, name="skincare-ingredient-search"),
]

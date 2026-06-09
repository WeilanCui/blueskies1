from dataclasses import asdict

from core.ingestion.http import HttpError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from skincareApi.client import (
    create_product,
    get_product,
    list_ingredients,
    list_products,
    search_ingredients,
    search_products,
)
from skincareApi.serializers import (
    SkincareIngredientSerializer,
    SkincareProductCreateSerializer,
    SkincareProductSerializer,
)


def _upstream_error(exc: HttpError) -> Response:
    message = str(exc)
    if "404" in message or "unavailable" in message.lower():
        return Response(
            {
                "detail": (
                    "The upstream Skincare API is unavailable. "
                    "The Heroku deployment may be offline."
                ),
                "upstream": message,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if "400" in message:
        return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"detail": message}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET", "POST"])
def product_collection(request):
    if request.method == "POST":
        serializer = SkincareProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            product = create_product(
                brand=data["brand"],
                name=data["name"],
                ingredients=data["ingredients"],
            )
        except HttpError as exc:
            return _upstream_error(exc)

        return Response(
            SkincareProductSerializer(asdict(product)).data,
            status=status.HTTP_201_CREATED,
        )

    try:
        products = list_products()
    except HttpError as exc:
        return _upstream_error(exc)
    serializer = SkincareProductSerializer([asdict(item) for item in products], many=True)
    return Response(serializer.data)


@api_view(["GET"])
def product_detail(request, product_id: int):
    try:
        product = get_product(product_id)
    except HttpError as exc:
        return _upstream_error(exc)
    if product is None:
        return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = SkincareProductSerializer(asdict(product))
    return Response(serializer.data)


@api_view(["GET"])
def product_search(request):
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response(
            {"detail": "Query parameter `q` is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    limit = int(request.query_params.get("limit", 10))
    page = int(request.query_params.get("page", 1))

    try:
        products = search_products(query, limit=limit, page=page)
    except HttpError as exc:
        return _upstream_error(exc)

    serializer = SkincareProductSerializer([asdict(item) for item in products], many=True)
    return Response(
        {
            "query": query,
            "limit": limit,
            "page": page,
            "count": len(products),
            "results": serializer.data,
        }
    )


@api_view(["GET"])
def ingredient_list(request):
    try:
        ingredients = list_ingredients()
    except HttpError as exc:
        return _upstream_error(exc)
    serializer = SkincareIngredientSerializer(
        [asdict(item) for item in ingredients],
        many=True,
    )
    return Response(serializer.data)


@api_view(["GET"])
def ingredient_search(request):
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response(
            {"detail": "Query parameter `q` is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    limit = int(request.query_params.get("limit", 10))
    page = int(request.query_params.get("page", 1))

    try:
        ingredients = search_ingredients(query, limit=limit, page=page)
    except HttpError as exc:
        return _upstream_error(exc)

    serializer = SkincareIngredientSerializer(
        [asdict(item) for item in ingredients],
        many=True,
    )
    return Response(
        {
            "query": query,
            "limit": limit,
            "page": page,
            "count": len(ingredients),
            "results": serializer.data,
        }
    )

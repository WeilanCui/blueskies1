from skincareApi.client import parse_ingredient, parse_product


def test_parse_product():
    product = parse_product(
        {
            "id": 1,
            "brand": "amorepacific",
            "name": "age spot brightening pen",
            "ingredient_list": ["water", "butylene glycol"],
        }
    )
    assert product.id == 1
    assert product.brand == "amorepacific"
    assert product.ingredient_list == ["water", "butylene glycol"]


def test_parse_ingredient():
    ingredient = parse_ingredient({"id": 2493, "ingredient": "rose water"})
    assert ingredient.id == 2493
    assert ingredient.ingredient == "rose water"

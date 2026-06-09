export type SkincareProduct = {
  id: number;
  brand: string;
  name: string;
  ingredient_list: string[];
};

export type SkincareIngredient = {
  id: number;
  ingredient: string;
};

export type ProductSearchResponse = {
  query: string;
  limit: number;
  page: number;
  count: number;
  results: SkincareProduct[];
};

export type IngredientSearchResponse = {
  query: string;
  limit: number;
  page: number;
  count: number;
  results: SkincareIngredient[];
};

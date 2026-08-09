export type CatalogIngredient = {
  /** Position in the INCI list; unique within a formulation. */
  position: number;
  name: string;
  role: string;
  note: string;
  is_key_active: boolean;
  parse_status: string;
};

export type SkincareProduct = {
  /** Catalog slug for seeded rows, stringified pk otherwise. */
  id: string;
  product_id: number;
  formulation_id: number | null;
  brand: string;
  name: string;
  display_name: string;
  category: string;
  description: string;
  enrichment_status: string;
  ingredient_count: number;
  ingredients: CatalogIngredient[];
};

export type SkincareIngredient = {
  id: number;
  ingredient: string;
};

type SearchResponse<T> = {
  query: string;
  limit: number;
  page: number;
  /** Size of the whole match set, not of `results`. */
  count: number;
  results: T[];
};

export type ProductSearchResponse = SearchResponse<SkincareProduct>;
export type IngredientSearchResponse = SearchResponse<SkincareIngredient>;

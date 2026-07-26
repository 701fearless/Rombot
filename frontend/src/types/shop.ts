export interface ShopProduct {
  productId: string
  sku?: string
  title: string
  productName?: string
  description?: string
  price: number
  currency?: string
  category?: string
  subcategory?: string
  sizeText?: string | null
  measurementsText?: string | null
  imageUrl?: string | null
  detailUrl?: string | null
  rank?: number
  score?: number
  features?: string[]
}

export interface ClipSearchResponse {
  source: string
  topK: number
  results: ShopProduct[]
}

export interface VideoProductMatchEntry {
  label?: string
  name?: string
  cropUrl?: string
  products: ShopProduct[]
}

export interface VideoProductMatchesResponse {
  videoId: string
  matches: Record<string, VideoProductMatchEntry>
}

export interface ResolveReferenceResponse {
  parentFolder: string
  imageName: string
  matchedFolder: string
  matchScore: number
  referenceUrl: string
}

import type { ShopProduct } from '@/types/shop'

/** Bundled demo images under frontend/public + backend/static (no full IKEA index required). */
function mockProduct(input: {
  productId: string
  title: string
  price: number
  category?: string
  score?: number
  rank?: number
}): ShopProduct {
  return {
    productId: input.productId,
    sku: input.productId,
    title: input.title,
    productName: input.title,
    price: input.price,
    currency: 'USD',
    category: input.category || 'Demo',
    imageUrl: `/mock-products/${input.productId}.jpg`,
    detailUrl: `/static/shop.html#/p/${input.productId}`,
    score: input.score,
    rank: input.rank,
  }
}

const pendantProducts = [
  mockProduct({ productId: '39580734', title: 'DYKARKLOCKA / HEMMA pendant lamp, white stained oak veneer/black, 16"', price: 79.99, category: 'Lamps & light fixtures', score: 0.92, rank: 1 }),
  mockProduct({ productId: '09530972', title: 'KAPPELAND / HEMMA pendant lamp, rattan/white', price: 59.99, category: 'Lamps & light fixtures', score: 0.9, rank: 2 }),
  mockProduct({ productId: '59597210', title: 'JÄLLBY / MOLNART pendant lamp with LED bulb', price: 32.99, category: 'Lamps & light fixtures', score: 0.88, rank: 3 }),
  mockProduct({ productId: '10516022', title: 'FYRTIOFYRA pendant lamp', price: 24.99, category: 'Lamps & light fixtures', score: 0.86, rank: 4 }),
]

const vaseProducts = [
  mockProduct({ productId: '00339794', title: 'VILJESTARK vase', price: 0.99, category: 'Vases & decorating bowls', score: 0.93, rank: 1 }),
  mockProduct({ productId: '20539711', title: 'VINDFLÄKT vase, black', price: 9.99, category: 'Vases & decorating bowls', score: 0.9, rank: 2 }),
  mockProduct({ productId: '20511953', title: 'KONSTFULL vase, clear glass/patterned', price: 19.99, category: 'Vases & decorating bowls', score: 0.88, rank: 3 }),
  mockProduct({ productId: '60334703', title: 'GRADVIS vase, pink', price: 14.99, category: 'Vases & decorating bowls', score: 0.86, rank: 4 }),
]

const diningTableProducts = [
  mockProduct({ productId: '00293772', title: 'MÖCKELBY Table', price: 999, category: 'Dining furniture', score: 0.93, rank: 1 }),
  mockProduct({ productId: '09568696', title: 'MARIEDAMM / LILLÖNÄS table and 4 chairs', price: 869.99, category: 'Dining furniture', score: 0.9, rank: 2 }),
  mockProduct({ productId: '29568186', title: 'LISABO / ÄLVSTA table and 4 chairs', price: 679.99, category: 'Dining furniture', score: 0.88, rank: 3 }),
  mockProduct({ productId: '09533433', title: 'MITTZON conference table', price: 299.99, category: 'Tables', score: 0.84, rank: 4 }),
]

const curtainProducts = [
  mockProduct({ productId: '80570237', title: 'HÄGGVECKMAL room darkening curtains, 1 pair, dark green', price: 49.99, category: 'Window treatments & coverings', score: 0.93, rank: 1 }),
  mockProduct({ productId: '30586014', title: 'VILBORG room darkening curtains, 1 pair, pink', price: 54.99, category: 'Window treatments & coverings', score: 0.91, rank: 2 }),
  mockProduct({ productId: '50396758', title: 'TIBAST Curtains', price: 49.99, category: 'Window treatments & coverings', score: 0.89, rank: 3 }),
  mockProduct({ productId: '00323514', title: 'RITVA curtains with tie-backs', price: 24.99, category: 'Window treatments & coverings', score: 0.87, rank: 4 }),
]

const sofaProducts = [
  mockProduct({ productId: '09316608', title: 'MORABO sofa', price: 1849, category: 'Sofas & sectionals', score: 0.93, rank: 1 }),
  mockProduct({ productId: '09575885', title: 'MORABO sofa with chaise', price: 999, category: 'Sofas & sectionals', score: 0.91, rank: 2 }),
  mockProduct({ productId: '09542828', title: 'FINNALA sleeper sofa', price: 1999, category: 'Sleeper sofas & sofa beds', score: 0.88, rank: 3 }),
  mockProduct({ productId: '00584498', title: 'KLIPPAN cover for loveseat', price: 139, category: 'Sofa & armchairs covers', score: 0.84, rank: 4 }),
]

const chairProducts = [
  mockProduct({ productId: '00217797', title: 'GUNDE folding chair', price: 12.99, category: 'Chairs', score: 0.92, rank: 1 }),
  mockProduct({ productId: '10594034', title: 'TONSTAD chair', price: 75, category: 'Chairs', score: 0.9, rank: 2 }),
  mockProduct({ productId: '19484267', title: 'POÄNG armchair and ottoman', price: 369, category: 'Chairs', score: 0.88, rank: 3 }),
  mockProduct({ productId: '19551582', title: 'POÄNG low-back armchair', price: 139, category: 'Chairs', score: 0.86, rank: 4 }),
]

const bedProducts = [
  mockProduct({ productId: '09496671', title: 'TONSTAD bed frame with storage', price: 662, category: 'Beds', score: 0.93, rank: 1 }),
  mockProduct({ productId: '19574395', title: 'MALM bed frame', price: 269, category: 'Beds', score: 0.9, rank: 2 }),
  mockProduct({ productId: '39241188', title: 'SONGESAND bed frame with 4 storage boxes', price: 529, category: 'Beds', score: 0.88, rank: 3 }),
  mockProduct({ productId: '19544172', title: 'MALM bed frame with mattress', price: 798, category: 'Beds', score: 0.86, rank: 4 }),
]

const deskProducts = [
  mockProduct({ productId: '09429568', title: 'TROTTEN desk', price: 134.99, category: 'Desks & computer desks', score: 0.93, rank: 1 }),
  mockProduct({ productId: '09525838', title: 'MITTZON desk', price: 219.99, category: 'Desks & computer desks', score: 0.91, rank: 2 }),
  mockProduct({ productId: '09563665', title: 'LAGKAPTEN / SPÄNN desk', price: 83.99, category: 'Desks & computer desks', score: 0.88, rank: 3 }),
  mockProduct({ productId: '19417466', title: 'LAGKAPTEN / ADILS desk', price: 56.99, category: 'Desks & computer desks', score: 0.86, rank: 4 }),
]

const lampProducts = [
  mockProduct({ productId: '60518410', title: 'TVÄRHAND table lamp, black/bamboo', price: 22, category: 'Lamps & light fixtures', score: 0.92, rank: 1 }),
  mockProduct({ productId: '00469120', title: 'VINDKAST pendant lamp', price: 49.99, category: 'Lamps & light fixtures', score: 0.88, rank: 2 }),
  mockProduct({ productId: '00441070', title: 'GOTTORP Pendant lamp shade', price: 44.99, category: 'Lamps & light fixtures', score: 0.86, rank: 3 }),
  mockProduct({ productId: '10516022', title: 'FYRTIOFYRA pendant lamp', price: 24.99, category: 'Lamps & light fixtures', score: 0.84, rank: 4 }),
]

const rugProducts = [
  mockProduct({ productId: '30589574', title: 'FLYGVÄG rug', price: 499.99, category: 'Rugs', score: 0.94, rank: 1 }),
  mockProduct({ productId: '50495409', title: 'LYDERSHOLM rug flatwoven', price: 149.99, category: 'Rugs', score: 0.91, rank: 2 }),
  mockProduct({ productId: '50555281', title: 'TELEGRAFLINJE rug', price: 99.99, category: 'Rugs', score: 0.89, rank: 3 }),
  mockProduct({ productId: '60578017', title: 'RINGKLOCKA rug', price: 299.99, category: 'Rugs', score: 0.87, rank: 4 }),
]

const coffeeTableProducts = [
  mockProduct({ productId: '30500355', title: 'BORGEBY coffee table', price: 169.99, category: 'Accent tables', score: 0.93, rank: 1 }),
  mockProduct({ productId: '30413495', title: 'HEMNES Coffee table', price: 249.99, category: 'Accent tables', score: 0.91, rank: 2 }),
  mockProduct({ productId: '50515167', title: 'JAKOBSFORS coffee table', price: 149.99, category: 'Accent tables', score: 0.89, rank: 3 }),
  mockProduct({ productId: '50590406', title: 'TORSJÖ coffee table', price: 149.99, category: 'Accent tables', score: 0.87, rank: 4 }),
]

const wardrobeProducts = [
  mockProduct({ productId: '09559159', title: 'PAX / FORSAND wardrobe combination', price: 560, category: 'Storage solution systems', score: 0.93, rank: 1 }),
  mockProduct({ productId: '19568399', title: 'PAX / BERGSBO wardrobe combination', price: 1005, category: 'Storage solution systems', score: 0.91, rank: 2 }),
  mockProduct({ productId: '29560779', title: 'PAX / FORSAND / ÅHEIM wardrobe combination', price: 590, category: 'Storage solution systems', score: 0.88, rank: 3 }),
  mockProduct({ productId: '29560897', title: 'PAX / TONSTAD wardrobe combination', price: 1805, category: 'Storage solution systems', score: 0.86, rank: 4 }),
]

const cabinetProducts = [
  mockProduct({ productId: '09521741', title: 'EKET storage combination with feet', price: 140, category: 'Storage solution systems', score: 0.92, rank: 1 }),
  mockProduct({ productId: '09439384', title: 'SEKTION wall cabinet with glass door', price: 360, category: 'Kitchen systems', score: 0.88, rank: 2 }),
  mockProduct({ productId: '09559159', title: 'PAX / FORSAND wardrobe combination', price: 560, category: 'Storage solution systems', score: 0.84, rank: 3 }),
  mockProduct({ productId: '90586558', title: 'STOCKHOLM 2025 side table', price: 99, category: 'Accent tables', score: 0.8, rank: 4 }),
]

/** Exact candidate → product mapping for known pause tags. */
const byCandidate: Record<string, ShopProduct[]> = {
  candidate_pendant_light_001: pendantProducts,
  candidate_vase_001: vaseProducts,
  candidate_dining_table_001: diningTableProducts,
  candidate_curtain_001: curtainProducts,
  candidate_rug_001: rugProducts,
  candidate_coffee_table_001: coffeeTableProducts,
  candidate_wardrobe_001: wardrobeProducts,
  candidate_cabinet_001: cabinetProducts,
  candidate_sofa_001: sofaProducts,
  candidate_chair_001: chairProducts,
  candidate_armchair_001: chairProducts,
}

/** Label-level fallbacks (strict category alignment). */
const byLabel: Record<string, ShopProduct[]> = {
  pendant_light: pendantProducts,
  chandelier: pendantProducts,
  hanging_lamp: pendantProducts,
  lamp: lampProducts,
  table_lamp: lampProducts,
  vase: vaseProducts,
  plant_pot: vaseProducts,
  dining_table: diningTableProducts,
  table: diningTableProducts,
  coffee_table: coffeeTableProducts,
  side_table: coffeeTableProducts,
  curtain: curtainProducts,
  rug: rugProducts,
  carpet: rugProducts,
  mat: rugProducts,
  sofa: sofaProducts,
  loveseat: sofaProducts,
  chair: chairProducts,
  armchair: chairProducts,
  bed: bedProducts,
  desk: deskProducts,
  bookshelf: deskProducts,
  bookcase: deskProducts,
  wardrobe: wardrobeProducts,
  closet: wardrobeProducts,
  cabinet: cabinetProducts,
  tv_stand: cabinetProducts,
  sideboard: cabinetProducts,
}

function normalizeKey(value?: string | null) {
  return (value || '').trim().toLowerCase().replace(/[\s-]+/g, '_')
}

function labelFromCandidate(candidateId?: string | null) {
  const text = normalizeKey(candidateId)
  const match = text.match(/^candidate_(.+)_(\d+)$/)
  return match?.[1] || ''
}

function labelFromObjectId(objectId?: string | null) {
  const text = normalizeKey(objectId)
  const match = text.match(/^obj_(.+)_(\d+)$/)
  return match?.[1] || ''
}

/** Instant offline lookup — never calls CLIP / product index. */
export function lookupFeedProducts(input: {
  videoId?: string | null
  deduplicatedObjectId?: string | null
  objectId?: string | null
  label?: string | null
  hint?: string | null
}): ShopProduct[] {
  const candidate = normalizeKey(input.deduplicatedObjectId)
  if (candidate && byCandidate[candidate]) {
    return byCandidate[candidate].slice(0, 4)
  }

  // Prefer structured ids/labels only — ignore free-text hint to avoid wrong fuzzy hits.
  const labels = [
    normalizeKey(input.label),
    labelFromCandidate(input.deduplicatedObjectId),
    labelFromObjectId(input.objectId),
  ].filter(Boolean)

  for (const label of labels) {
    if (byLabel[label]) return byLabel[label].slice(0, 4)
  }

  // Controlled aliases only (longest key first). Never fall back to sofa.
  const keys = Object.keys(byLabel).sort((a, b) => b.length - a.length)
  for (const label of labels) {
    const hit = keys.find((key) => label === key || label.endsWith(`_${key}`) || label.startsWith(`${key}_`))
    if (hit) return byLabel[hit].slice(0, 4)
  }

  return []
}

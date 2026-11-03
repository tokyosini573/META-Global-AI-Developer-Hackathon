// What a founder tells Rehearsal about one app. The format is defined in docs/brief-format.md.

export type Category = 'dating' | 'resale' | 'rides'
export type Channel = {
  kind: 'feed' | 'search' | 'event' | 'outdoor' | 'referral'
  where: 'nationwide' | 'cities'; budget_share: number; start_day: number; end_day: number; side?: string
}
export type City = { name: string; open_day: number }
export type BriefAd = { id: string; angle: 'feature' | 'price' | 'trust' | 'other'; line: string }
export type Experiment = {
  changes: string
  budget_usd?: number; channels?: Channel[]; cities?: City[]; ads?: string[]; price?: number; trial_days?: number
}

export type Brief = {
  version: 2
  app: string
  category: Category
  market: 'United States'
  profile: { does: string; why: string; features?: string[] }
  audience: {
    age: [number, number]; who: string
    income?: 'under_30k' | '30_60k' | '60_100k' | 'over_100k' | 'mixed'
    lifestyle?: string; interests?: string; new_apps?: 'early' | 'friends' | 'rarely'
  }
  product: {
    signup_methods: ('email' | 'phone' | 'apple' | 'google' | 'facebook')[]
    permissions?: ('location' | 'camera' | 'photos' | 'contacts' | 'notifications')[]
    free_limits?: string
  }
  money: {
    model: 'subscription' | 'service_fee' | 'per_ride_fee' | 'one_time'
    price: number; per: 'week' | 'month' | 'transaction' | 'percent'; trial_days?: number
    paywall: 'after_signup' | 'after_free_limit' | 'after_trial' | 'at_checkout'
    free?: string; paid?: string
  }
  ads: BriefAd[]
  competition?: { now: string; switch: string }
  retention?: { back: string; leave: string }
  extra?: {
    women_share?: number; free_likes_per_day?: number
    fee_share?: number; seller_share?: number
    fare_usd?: number; driver_share?: number
  }
  setup: {
    people: 1000 | 5000 | 10000
    days: 7 | 14 | 30 | 90
    campaign?: { budget_usd: number; channels: Channel[]; cities?: City[]; ads: string[] } // live runs only
    experiments: Record<'a' | 'b', Experiment>
  }
}

// The images a run needs for each category (docs/brief-format.md "Images")
export function imageSlots(category: Category, ads: number): string[] {
  const main = category === 'dating' ? ['main', 'paywall']
    : category === 'resale' ? ['main_seller', 'main_buyer'] : ['main_driver', 'main_rider']
  return ['store', 'signup', ...main, ...Array.from({ length: ads }, (_, i) => `ad_${i + 1}`)]
}

// Text length limits (docs/brief-format.md); the engine trims longer text to these
export const LIMITS = {
  app: 24, does: 300, why: 200, feature: 40, features: 5, who: 200, lifestyle: 120, interests: 120,
  free_limits: 80, free: 120, paid: 120, line: 80, competition: 200, retention: 200, changes: 120,
} as const

// Age limits of each market pack (engine/packs/<id>.py "age")
export const AGE: Record<Category, [number, number]> = { dating: [18, 34], resale: [18, 64], rides: [21, 64] }

// The two sides a channel can aim at (engine/packs); dating channels reach both
export const SIDES: Record<Category, string[]> = { dating: [], resale: ['seller', 'buyer'], rides: ['driver', 'rider'] }

// Cities a campaign can open in (engine/world/geo.py METROS)
export const CITIES = [
  'New York, New York', 'Los Angeles, California', 'Chicago, Illinois', 'Houston, Texas', 'Phoenix, Arizona',
  'Philadelphia, Pennsylvania', 'San Antonio, Texas', 'San Diego, California', 'Dallas, Texas', 'Columbus, Ohio',
  'Seattle, Washington', 'Atlanta, Georgia', 'Miami, Florida', 'Boston, Massachusetts', 'San Francisco, California',
  'Detroit, Michigan', 'Minneapolis, Minnesota', 'Portland, Oregon', 'Las Vegas, Nevada', 'Charlotte, North Carolina',
  'St. Louis, Missouri', 'Kansas City, Missouri', 'Salt Lake City, Utah', 'Nashville, Tennessee', 'Denver, Colorado',
  'Austin, Texas',
]

export const CHANNEL_KINDS: Channel['kind'][] = ['feed', 'search', 'event', 'outdoor', 'referral']
export const PEOPLE: Brief['setup']['people'][] = [1000, 5000, 10000]
export const DAYS: Brief['setup']['days'][] = [7, 14, 30, 90]

// What a live run checks before it is sent: field path -> a plain-words problem. Empty means ready.
export function validate(b: Brief, images: Record<string, unknown>): Record<string, string> {
  const e: Record<string, string> = {}
  const need = (path: string, v: string | undefined, words: string) => { if (!v?.trim()) e[path] = words }
  need('app', b.app, 'Give the app a name.')
  need('profile.does', b.profile.does, 'Say in a sentence what the app does.')
  need('profile.why', b.profile.why, 'Say why people would pick it.')
  need('audience.who', b.audience.who, 'Say who it is for.')
  const [lo, hi] = AGE[b.category], [a0, a1] = b.audience.age
  if (!(a0 >= lo && a1 <= hi && a0 <= a1)) e['audience.age'] = `Pick ages between ${lo} and ${hi}.`
  if (!b.product.signup_methods.length) e['product.signup_methods'] = 'Pick at least one way to sign up.'
  if (!(b.money.price > 0)) e['money.price'] = 'Give a price above zero.'
  if (!b.ads.length) e.ads = 'Add at least one ad.'
  b.ads.forEach((ad, i) => need(`ads.${i}`, ad.line, 'Write the ad’s line.'))
  const missing = imageSlots(b.category, b.ads.length).filter(n => !images[n])
  if (missing.length) e.images = `Add ${missing.length === 1 ? 'one more image' : `${missing.length} more images`}.`
  for (const n of missing) e[`image.${n}`] = 'Add this image.'
  const c = b.setup.campaign
  if (c) {
    if (!(c.budget_usd > 0)) e['campaign.budget'] = 'Give a budget above zero.'
    if (!c.channels.length) e['campaign.channels'] = 'Turn on at least one channel.'
    if (c.channels.some(ch => ch.where === 'cities') && !c.cities?.length) e['campaign.cities'] = 'Pick a city, or run every channel nationwide.'
    if (!c.ads.length) e['campaign.ads'] = 'Show at least one ad.'
  }
  for (const k of ['a', 'b'] as const) {
    const x = b.setup.experiments[k]
    if (x.channels && !x.channels.length) e[`${k}.channels`] = 'Turn on at least one channel.'
    if (x.channels?.some(ch => ch.where === 'cities') && !(x.cities ?? c?.cities)?.length) e[`${k}.channels`] = 'Pick a city, or run every channel nationwide.'
    if (x.ads && !x.ads.length) e[`${k}.ads`] = 'Show at least one ad.'
    if (x.budget_usd !== undefined && !(x.budget_usd > 0)) e[`${k}.budget`] = 'Give a budget above zero.'
  }
  const same = (['a', 'b'] as const).every(k => Object.keys(b.setup.experiments[k]).every(f => f === 'changes'))
  if (same) e.experiments = 'Change at least one thing in experiment A or B, or they are the same.'
  return e
}

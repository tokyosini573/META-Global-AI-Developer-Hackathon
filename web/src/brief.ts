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

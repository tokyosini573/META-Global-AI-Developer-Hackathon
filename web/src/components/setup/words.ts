import type { Brief, Category, Channel, Experiment } from '../../brief'

// The words the Setup page shows for each value of the brief (docs/brief-format.md)

export const CATEGORY_WORDS: Record<Category, string> = { dating: 'Dating', resale: 'Local resale', rides: 'Rides' }

// The precomputed example of each market (web/public/replays)
export const EXAMPLE_REPLAY: Record<Category, string> = { dating: 'engine', resale: 'reloop', rides: 'hopway' }

export const INCOME: [NonNullable<Brief['audience']['income']>, string][] = [
  ['under_30k', 'Under $30k'], ['30_60k', '$30–60k'], ['60_100k', '$60–100k'], ['over_100k', 'Over $100k'], ['mixed', 'Mixed'],
]
export const NEW_APPS: [NonNullable<Brief['audience']['new_apps']>, string][] = [
  ['early', 'Tries new apps early'], ['friends', 'Waits for friends'], ['rarely', 'Rarely switches'],
]
export const SIGNUP: [Brief['product']['signup_methods'][number], string][] = [
  ['email', 'Email'], ['phone', 'Phone'], ['apple', 'Apple'], ['google', 'Google'], ['facebook', 'Facebook'],
]
export const PERMISSIONS: [NonNullable<Brief['product']['permissions']>[number], string][] = [
  ['location', 'Location'], ['camera', 'Camera'], ['photos', 'Photos'], ['contacts', 'Contacts'], ['notifications', 'Notifications'],
]
export const MODEL_WORDS: Record<Brief['money']['model'], string> = {
  subscription: 'Subscription', service_fee: 'Service fee', per_ride_fee: 'Per-ride fee', one_time: 'One-time purchase',
}
// The ways of making money that fit each market, the fee first
export const MODELS: Record<Category, Brief['money']['model'][]> = {
  dating: ['subscription', 'one_time'], resale: ['service_fee', 'subscription'], rides: ['per_ride_fee', 'subscription'],
}
export const PAYWALL: [Brief['money']['paywall'], string][] = [
  ['after_signup', 'Right after sign-up'], ['after_free_limit', 'After the free limit'],
  ['after_trial', 'After the trial'], ['at_checkout', 'At checkout'],
]
export const ANGLES: [Brief['ads'][number]['angle'], string][] = [
  ['feature', 'Feature'], ['price', 'Price'], ['trust', 'Trust'], ['other', 'Other'],
]
export const angleWords = (a: string) => ANGLES.find(([k]) => k === a)?.[1] ?? a

export const CHANNEL_WORDS: Record<Channel['kind'], string> = {
  feed: 'Feed ads', search: 'Search ads', event: 'Events and campus', outdoor: 'Outdoor posters', referral: 'Referrals',
}

export const SLOT_WORDS: Record<string, string> = {
  store: 'Store page', signup: 'Sign-up screen', main: 'Main screen', paywall: 'Paywall screen',
  main_seller: 'What a seller sees', main_buyer: 'What a buyer sees',
  main_driver: 'What a driver sees', main_rider: 'What a rider sees',
}

export const sideWords = (s: string) => `${s}s`

// The price in plain words: "$9.99 a week", "10% of each sale"
export function priceWords(m: Brief['money'], category: Category) {
  if (m.per === 'percent') return `${Math.round(m.price * 1000) / 10}% of each ${category === 'rides' ? 'ride' : 'sale'}`
  const usd = `$${m.price.toFixed(m.price % 1 ? 2 : 0)}`
  return m.per === 'transaction' ? `${usd} ${m.model === 'one_time' ? 'once' : category === 'rides' ? 'a ride' : 'a sale'}` : `${usd} a ${m.per}`
}

export const usd = (n: number) => `$${Math.round(n).toLocaleString('en-US')}`
export const shortCity = (c: string) => c.split(',')[0]
export const cityWords = (cs: { name: string; open_day: number }[]) =>
  cs.map((c, i) => (i === 0 && c.open_day === 0 ? shortCity(c.name) : `${shortCity(c.name)} on day ${c.open_day}`)).join(', ')

// One channel in plain words: "Feed ads 80%, day 0 to 60, sellers"
export function channelWords(c: Channel) {
  return `${CHANNEL_WORDS[c.kind]} ${Math.round(c.budget_share * 100)}%, day ${c.start_day} to ${c.end_day}`
    + `${c.where === 'cities' ? ', in the cities' : ''}${c.side ? `, ${sideWords(c.side)}` : ''}`
}

// What an experiment changes, in plain words (the default for `changes`)
export function changeWords(b: Brief, x: Experiment) {
  const out: string[] = []
  if (x.budget_usd !== undefined) out.push(`Budget ${usd(x.budget_usd)}`)
  if (x.cities?.length) out.push(cityWords(x.cities))
  else if (x.channels?.every(c => c.where === 'nationwide')) out.push('nationwide')
  if (x.channels) out.push(x.channels.map(c => CHANNEL_WORDS[c.kind].toLowerCase()).join(' and '))
  if (x.ads) out.push(`only ${x.ads.map(a => `ad ${a.slice(3)}`).join(' and ')}`)
  if (x.price !== undefined) out.push(priceWords({ ...b.money, price: x.price }, b.category))
  if (x.trial_days !== undefined) out.push(`${x.trial_days} days free`)
  return out.length ? out.join('; ') : 'Nothing: the shared campaign'
}

import type { Brief, Category } from '../../brief'

// The admin form's starting brief for each market: the demo apps (all fictional) with a shared
// campaign and two experiments like plans/<app>.yaml. When the example replay carries its own
// meta.brief, its text replaces sections 01-07 here (Setup.tsx).

const KINDRED: Brief = {
  version: 2, app: 'Kindred', category: 'dating', market: 'United States',
  profile: {
    does: 'A swipe dating app that shows you people who are actually nearby, so a match can turn into a date this week.',
    why: 'Fewer, closer profiles instead of endless scrolling through people who live an hour away.',
    features: ['Nearby profiles first', '5 free swipes a day', 'Unlimited swipes with Kindred Plus'],
  },
  audience: {
    age: [18, 34], who: 'Students and young professionals in US cities who want to meet someone nearby soon.',
    income: 'mixed', new_apps: 'early',
  },
  product: { signup_methods: ['phone', 'apple'], permissions: ['location', 'photos', 'notifications'], free_limits: '5 swipes a day' },
  money: {
    model: 'subscription', price: 9.99, per: 'week', trial_days: 0, paywall: 'after_free_limit',
    free: '5 swipes a day, matching and chat', paid: 'Unlimited swipes and seeing who liked you',
  },
  ads: [
    { id: 'ad_1', angle: 'feature', line: 'Swipe less. Meet more.' },
    { id: 'ad_2', angle: 'price', line: 'Free to start. 5 swipes a day on us.' },
    { id: 'ad_3', angle: 'trust', line: 'Real people, verified with a selfie.' },
  ],
  competition: {
    now: 'The big swipe apps, where most profiles are far away or no longer active.',
    switch: 'Kindred only shows people close enough to meet this week.',
  },
  retention: {
    back: 'A daily note when someone nearby liked you.',
    leave: 'No matches nearby in the first week, or the paywall before a first match.',
  },
  extra: { women_share: 0.5, free_likes_per_day: 5 },
  setup: {
    people: 10000, days: 90,
    campaign: {
      budget_usd: 40000, ads: ['ad_1', 'ad_2', 'ad_3'],
      channels: [{ kind: 'feed', where: 'nationwide', budget_share: 1, start_day: 0, end_day: 60 }],
    },
    experiments: {
      a: { changes: 'Nothing: the shared campaign, nationwide' },
      b: {
        changes: 'Austin, then Denver and Nashville; campus ambassadors; 30 days free',
        channels: [
          { kind: 'event', where: 'cities', budget_share: 0.5, start_day: 0, end_day: 90 },
          { kind: 'feed', where: 'cities', budget_share: 0.5, start_day: 0, end_day: 90 },
        ],
        cities: [{ name: 'Austin, Texas', open_day: 0 }, { name: 'Denver, Colorado', open_day: 30 }, { name: 'Nashville, Tennessee', open_day: 60 }],
        trial_days: 30,
      },
    },
  },
}

const RELOOP: Brief = {
  version: 2, app: 'Reloop', category: 'resale', market: 'United States',
  profile: {
    does: 'A local resale app: snap a photo of something you no longer use, and someone across town buys it and picks it up.',
    why: 'Buyers are close enough to pick up the same day, so there is no shipping and no waiting.',
    features: ['Listing in under a minute', 'Pick-up nearby', 'Pay in the app'],
  },
  audience: {
    age: [18, 64], who: 'People in US cities with things to clear out, and people who like a bargain close to home.',
    income: 'mixed', new_apps: 'friends',
  },
  product: { signup_methods: ['email', 'apple', 'google'], permissions: ['location', 'camera', 'notifications'], free_limits: 'Listing is free' },
  money: {
    model: 'service_fee', price: 0.1, per: 'percent', trial_days: 0, paywall: 'at_checkout',
    free: 'Listing, browsing and chat', paid: 'Buyers pay a 10% service fee at checkout',
  },
  ads: [
    { id: 'ad_1', angle: 'feature', line: 'Sell it this afternoon.' },
    { id: 'ad_2', angle: 'price', line: 'Free to list. Keep what you earn.' },
    { id: 'ad_3', angle: 'trust', line: 'Every buyer checked, every payment held.' },
  ],
  competition: {
    now: 'Neighborhood groups and classifieds, where many replies never turn up.',
    switch: 'Payment is held in the app, so pick-ups actually happen.',
  },
  retention: {
    back: 'A note when something you saved drops in price nearby.',
    leave: 'Nothing nearby to buy, or no one buying what they listed.',
  },
  extra: { fee_share: 0.1, seller_share: 0.42 },
  setup: {
    people: 10000, days: 90,
    campaign: {
      budget_usd: 40000, ads: ['ad_1', 'ad_2', 'ad_3'],
      channels: [
        { kind: 'feed', where: 'nationwide', budget_share: 0.8, start_day: 0, end_day: 60 },
        { kind: 'search', where: 'nationwide', budget_share: 0.2, start_day: 0, end_day: 90 },
      ],
    },
    experiments: {
      a: { changes: 'Nothing: the shared campaign, everyone at once' },
      b: {
        changes: 'Seattle, then Portland on day 45; sellers first',
        channels: [
          { kind: 'event', where: 'cities', budget_share: 0.4, start_day: 0, end_day: 90, side: 'seller' },
          { kind: 'feed', where: 'cities', budget_share: 0.6, start_day: 14, end_day: 90 },
        ],
        cities: [{ name: 'Seattle, Washington', open_day: 0 }, { name: 'Portland, Oregon', open_day: 45 }],
      },
    },
  },
}

const HOPWAY: Brief = {
  version: 2, app: 'Hopway', category: 'rides', market: 'United States',
  profile: {
    does: 'A ride app for mid-size cities: request a ride, and a driver from your own neighborhood picks you up.',
    why: 'Drivers keep more of each fare, so more of them stay on the road near you.',
    features: ['Fixed fare before you ride', 'Drivers keep 80%', 'Rides from your neighborhood'],
  },
  audience: {
    age: [21, 64], who: 'People in growing US cities without a car for every trip, and people who want to earn by driving.',
    income: 'mixed', new_apps: 'friends',
  },
  product: { signup_methods: ['phone', 'apple', 'google'], permissions: ['location', 'notifications'], free_limits: 'First ride $5 off' },
  money: {
    model: 'per_ride_fee', price: 0.2, per: 'percent', trial_days: 0, paywall: 'at_checkout',
    free: 'Seeing the fare and the drivers nearby', paid: 'Riders pay the fare; Hopway keeps 20%',
  },
  ads: [
    { id: 'ad_1', angle: 'feature', line: 'A ride from your own neighborhood.' },
    { id: 'ad_2', angle: 'price', line: 'Know the fare before you go.' },
    { id: 'ad_3', angle: 'trust', line: 'Every driver checked, every ride tracked.' },
  ],
  competition: {
    now: 'The big ride apps, with long waits outside the city center.',
    switch: 'More drivers nearby because they keep more of the fare.',
  },
  retention: {
    back: 'A note when a driver is close by at the times you usually ride.',
    leave: 'Long waits or no driver at all, or too few riders for drivers.',
  },
  extra: { fare_usd: 14, driver_share: 0.2 },
  setup: {
    people: 10000, days: 90,
    campaign: {
      budget_usd: 40000, ads: ['ad_1', 'ad_2', 'ad_3'],
      cities: [{ name: 'Austin, Texas', open_day: 0 }, { name: 'Denver, Colorado', open_day: 0 }, { name: 'Nashville, Tennessee', open_day: 0 }],
      channels: [
        { kind: 'feed', where: 'cities', budget_share: 0.7, start_day: 0, end_day: 90, side: 'rider' },
        { kind: 'feed', where: 'cities', budget_share: 0.3, start_day: 0, end_day: 90, side: 'driver' },
      ],
    },
    experiments: {
      a: { changes: 'Nothing: three cities at once, riders and drivers together' },
      b: {
        changes: 'Austin, then Denver on day 45; drivers first',
        channels: [
          { kind: 'event', where: 'cities', budget_share: 0.4, start_day: 0, end_day: 90, side: 'driver' },
          { kind: 'search', where: 'cities', budget_share: 0.2, start_day: 14, end_day: 90, side: 'rider' },
          { kind: 'feed', where: 'cities', budget_share: 0.4, start_day: 14, end_day: 90, side: 'rider' },
        ],
        cities: [{ name: 'Austin, Texas', open_day: 0 }, { name: 'Denver, Colorado', open_day: 45 }],
      },
    },
  },
}

export const EXAMPLES: Record<Category, Brief> = { dating: KINDRED, resale: RELOOP, rides: HOPWAY }

// A fresh copy, so editing never changes the example itself
export const exampleBrief = (c: Category): Brief => structuredClone(EXAMPLES[c])

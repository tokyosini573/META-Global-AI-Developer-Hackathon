"""Dating: men and women browse each other nearby; free users hit a paywall (the Kindred demo).

The context and situation sentences are the ones the committed Spark and Glimmer tables were
asked with: change them and those tables no longer describe the same question.
"""

MILES = {"none": 41, "few": 9, "many": 2}   # distance on the paywall's profile card (engine/screens/kindred.html)


def price_words(cfg, plan):
    price = f"${cfg['price_per_week']:.2f} a week"
    if plan["trial_days"]:
        return f"Free for each person's first {plan['trial_days']} days, then {price}"
    return price + f". Free users get {plan['free_swipes_per_day']} swipes a day."

PACK = {
    "id": "dating",
    "html": "kindred.html",          # the demo app's screens (engine/screens/)
    "goal_key": "paying",            # what the verdict counts (engine/run.py)
    "header": "Swipe dating app",
    "category": "a new swipe dating app",
    "mechanics": "swipe",
    "convert_target": "paid_30d",    # calibration target the paywall's "pay" is tied to
    "sides": [("m", "You are a man looking for women."), ("w", "You are a woman looking for men.")],
    "share_key": "share_male",
    "age": (18, 34),
    # how a person reached by each kind of channel meets the app (context key -> situation)
    "channel_context": {"feed": "tiktok_ad", "event": "ambassador", "referral": "friend", "friend": "friend",
                        "search": "search", "outdoor": "outdoor"},
    "contexts": {
        "tiktok_ad": "You are scrolling TikTok at night and this ad for a new dating app appears. What do you do?",
        "ambassador": "A student ambassador for a new dating app stopped you near campus and showed you its store page "
                      "on their phone. What do you do?",
        "friend": "A friend who recently matched with someone on this new dating app sent you this link. What do you do?",
        "search": "You searched the app store for a dating app and this new one came up. What do you do?",
        "outdoor": "You saw this ad for a new dating app on a poster in the subway, and looked it up later. "
                   "What do you do?",
    },
    "context_screen": {"tiktok_ad": "ad", "outdoor": "ad", "ambassador": "store", "friend": "store",
                       "search": "store"},
    # the decision each side faces while using the app for free
    "gates": {"m": "paywall", "w": "paywall"},
    "gate": {
        "paywall": {"options": ("pay", "come_back_tomorrow", "delete_app"), "act": "pay",
                    "question": "This is what Kindred shows you right now. What do you do?",
                    "week": {"w1": "You installed Kindred 3 days ago.",
                             "w2-4": "You installed Kindred about two weeks ago.",
                             "w5+": "You installed Kindred over a month ago."},
                    "success": {"no": "You have no matches yet.", "yes": "You have matched with someone on it."},
                    "nearby": {"none": "Almost everyone it shows you is far away.",
                               "few": "It shows you a handful of people in your area.",
                               "many": "It keeps showing you people close by."}},
    },
    # how the plans' channels read in Wonder's prompts and on the plan cards
    "channel_words": {"feed": "tiktok", "event": "ambassador"},
    "ad_words": {"feed": ("TikTok, nationwide", "local TikTok"), "event": ("Campus ambassadors", "Campus ambassadors")},
    "price_words": price_words,
    # v2 funnel (docs/replay-format.md "Version 2"); {days} is the run's last day
    "funnel": [("saw", "Saw an ad"), ("installed", "Installed"), ("signed_up", "Signed up"),
               ("first", "Got a match"), ("active", "Using on day {days}"), ("paid", "Paid")],
    "labels": {
        "stages": ["Installed", "Got a match", "Still using", "Paying"],
        "numbers": ["Paying users", "Got a match", "Quit in week one"],
        "legend": ["Paying", "Using", "Quit"],
        "goal": "paying users",
        "ask": {"converted": "Why did you pay?", "quit": "Why did you delete it?",
                "using": "What do you think of it so far?"},
        "last_screen": "Where {they} left",
        "since": "Paying since day {day}.",
    },
    "story": {
        "reach": {"feed": "Saw the ad on TikTok.", "event": "A campus ambassador showed off Kindred.",
                  "friend": "A friend sent a Kindred link.", "referral": "A friend sent a Kindred invite.",
                  "search": "Found Kindred in an app store search.",
                  "outdoor": "Saw a Kindred poster and looked it up."},
        "skip": {"feed": "Scrolled past."},
        "skip_default": "Did not install it.",
        "signup": {"finish": "Signed up.", "delete_app": "Deleted the app at sign-up."},
        "success": {"m": "Got a first match.", "w": "Got a first match."},
        "gate_head": {"paywall": "Hit the paywall."},
        "trial_head": "Free month ended. ",
        "outcome": {"paywall": {"pay": "Paid for unlimited swipes.", "come_back_tomorrow": "Came back the next day.",
                                "delete_app": "Deleted the app."}},
        "nearest": lambda bucket, side: f"Nearest person: {MILES[bucket[1]]} miles.",
    },
}

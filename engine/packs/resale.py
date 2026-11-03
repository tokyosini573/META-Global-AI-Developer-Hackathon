"""Resale: neighbors sell used things to each other, picked up in person (the Reloop demo).

Sellers offer by listing an item, which stays up for two weeks or until it sells. Buyers ask by
trying to buy something they like nearby. A sale needs a listing within reach on the day a buyer
wants one, so a thin local market leaves buyers empty-handed and sellers without offers.
"""

ITEMS = {"none": 0, "few": 6, "many": 48}      # listings shown near a buyer on the feed screen
BUYERS = {"none": 0, "few": 4, "many": 35}     # people browsing near a seller


def price_words(cfg, plan):
    return f"Free to list. Buyers pay a {cfg['fee_share']:.0%} service fee."


PACK = {
    "id": "resale",
    "html": "reloop.html",
    "screen_prefix": "reloop_",
    "goal_key": "transactions",
    "header": "Local resale app",
    "category": "a new app for buying and selling used things with people nearby",
    "mechanics": "transaction",
    "convert_target": "convert_30d",   # share of buyers with a first purchase within 30 days
    "sides": [("seller", "You want to sell things you no longer use."),
              ("buyer", "You like buying used things to save money.")],
    "share_key": "share_seller",
    "supply": "seller",
    "demand": "buyer",
    "offer_days": 14,                  # a listing stays up two weeks
    "offer_used_up": True,             # an item sells once
    "age": (18, 64),
    "channel_context": {k: k for k in ("feed", "search", "event", "outdoor", "referral", "friend")},
    "contexts": {
        "feed": "You are scrolling your social feed and this ad for a new app appears. What do you do?",
        "search": "You searched the app store for a way to buy and sell used things nearby, and this new app came "
                  "up. What do you do?",
        "event": "At a weekend market, someone from this new app showed you its store page on their phone. "
                 "What do you do?",
        "outdoor": "You saw this ad on a poster at the bus stop, and looked the app up later. What do you do?",
        "referral": "A friend sent you an invite to this new app. You both get a credit if you sign up. "
                    "What do you do?",
        "friend": "A friend who just sold something on this new app sent you the link. What do you do?",
    },
    "context_screen": {"feed": "ad", "outdoor": "ad", "search": "store", "event": "store", "referral": "store",
                       "friend": "store"},
    "gates": {"seller": "list", "buyer": "buy"},
    "gate": {
        "list": {"options": ("list_item", "come_back_tomorrow", "delete_app"), "act": "list_item",
                 "question": "You open Reloop. This is what it shows you. What do you do?",
                 "week": {"w1": "You installed Reloop 3 days ago.", "w2-4": "You installed Reloop about two weeks ago.",
                          "w5+": "You installed Reloop over a month ago."},
                 "success": {"no": "You have not sold anything yet.", "yes": "You have sold something on it."},
                 "nearby": {"none": "Almost nobody near you is browsing.",
                            "few": "A handful of people near you are browsing.",
                            "many": "Lots of people near you are browsing."}},
        "buy": {"options": ("buy_item", "come_back_tomorrow", "delete_app"), "act": "buy_item",
                "question": "You open Reloop. This is what it shows you. What do you do?",
                "week": {"w1": "You installed Reloop 3 days ago.", "w2-4": "You installed Reloop about two weeks ago.",
                         "w5+": "You installed Reloop over a month ago."},
                "success": {"no": "You have not bought anything yet.", "yes": "You have bought something on it."},
                "nearby": {"none": "There is almost nothing for sale near you.",
                           "few": "There are a few things for sale near you.",
                           "many": "There are lots of things for sale near you."}},
    },
    "price_words": price_words,
    "labels": {
        "stages": ["Installed", "Sold or bought", "Still using", "Repeat"],
        "numbers": ["Completed sales", "Sold or bought", "Quit in week one"],
        "legend": ["Traded", "Using", "Quit"],
        "goal": "completed sales",
        "ask": {"converted": "How did your first sale or purchase go?", "quit": "Why did you delete it?",
                "using": "What do you think of it so far?"},
        "last_screen": "What {they} saw last",
        "since": "First sale or purchase on day {day}.",
    },
    "story": {
        "reach": {"feed": "Saw a Reloop ad in the feed.", "search": "Found Reloop in an app store search.",
                  "event": "Met the Reloop team at a market.", "outdoor": "Saw a Reloop poster and looked it up.",
                  "referral": "Got a Reloop invite from a friend.", "friend": "A friend sent a Reloop link."},
        "skip": {"feed": "Scrolled past."},
        "skip_default": "Did not install it.",
        "success": {"seller": "Sold a first item.", "buyer": "Bought a first item."},
        "gate_head": {"list": "Opened the app.", "buy": "Opened the app."},
        "outcome": {"list": {"list_item": "Listed an item.", "come_back_tomorrow": "Came back the next day.",
                             "delete_app": "Deleted the app."},
                    "buy": {"buy_item": "Tried to buy something.", "come_back_tomorrow": "Came back the next day.",
                            "delete_app": "Deleted the app."}},
        "nearest": lambda bucket, side: (f"{ITEMS[bucket[1]]} items for sale nearby." if side == "buyer"
                                         else f"{BUYERS[bucket[1]]} people browsing nearby."),
    },
}

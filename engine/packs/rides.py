"""Ride-hailing: drivers go online, riders request rides nearby (the Hopway demo).

Drivers offer by going online for the day. Riders ask by requesting a ride, which is filled only
if an online driver is within reach; a driver can take several rides. With few drivers the wait
shown to riders is long, and riders who wait in vain quit; with few riders drivers sit idle.
"""

ETA = {"none": 18, "few": 9, "many": 3}         # minutes to the nearest car, shown to a rider
REQUESTS = {"none": 0, "few": 3, "many": 14}    # ride requests nearby in the last hour, shown to a driver


def price_words(cfg, plan):
    return f"Riders pay about ${cfg['fare_usd']:.0f} a ride. Drivers keep {1 - cfg['fee_share']:.0%}."


PACK = {
    "id": "rides",
    "html": "hopway.html",
    "screen_prefix": "hopway_",
    "goal_key": "transactions",
    "header": "Ride-hailing app",
    "category": "a new ride-hailing app",
    "mechanics": "transaction",
    "convert_target": "convert_30d",   # share of riders with a first completed ride within 30 days
    "sides": [("driver", "You have a car and want to earn money driving people."),
              ("rider", "You sometimes need a ride around town.")],
    "share_key": "share_driver",
    "supply": "driver",
    "demand": "rider",
    "offer_days": 0,                   # online for the day
    "offer_used_up": False,            # a driver can take several rides
    "age": (21, 64),
    "channel_context": {k: k for k in ("feed", "search", "event", "outdoor", "referral", "friend")},
    "contexts": {
        "feed": "You are scrolling your social feed and this ad for a new ride app appears. What do you do?",
        "search": "You needed a ride, searched the app store, and this new ride app came up. What do you do?",
        "event": "At a sign-up booth near the airport rideshare lot, someone from this new app showed you its "
                 "store page. What do you do?",
        "outdoor": "You saw this ad on a billboard on your commute, and looked the app up later. What do you do?",
        "referral": "A friend sent you an invite to this new ride app. You both get a credit after your first ride. "
                    "What do you do?",
        "friend": "A friend who got a ride with this new app sent you the link. What do you do?",
    },
    "context_screen": {"feed": "ad", "outdoor": "ad", "search": "store", "event": "store", "referral": "store",
                       "friend": "store"},
    "gates": {"driver": "drive", "rider": "ride"},
    "gate": {
        "drive": {"options": ("go_online", "come_back_tomorrow", "delete_app"), "act": "go_online",
                  "question": "You open Hopway's driver screen. This is what it shows you. What do you do?",
                  "week": {"w1": "You signed up to drive 3 days ago.", "w2-4": "You signed up to drive about two weeks ago.",
                           "w5+": "You signed up to drive over a month ago."},
                  "success": {"no": "You have not given a ride yet.", "yes": "You have given rides on it."},
                  "nearby": {"none": "Almost nobody near you is asking for rides.",
                             "few": "A few people near you ask for rides.",
                             "many": "Lots of people near you ask for rides."}},
        "ride": {"options": ("request_ride", "come_back_tomorrow", "delete_app"), "act": "request_ride",
                 "question": "You need to get somewhere and open Hopway. This is what it shows you. What do you do?",
                 "week": {"w1": "You installed Hopway 3 days ago.", "w2-4": "You installed Hopway about two weeks ago.",
                          "w5+": "You installed Hopway over a month ago."},
                 "success": {"no": "You have not had a ride yet.", "yes": "You have had rides with it."},
                 "nearby": {"none": "The nearest car is far away.", "few": "There are a few cars near you.",
                            "many": "There are cars all around you."}},
    },
    "price_words": price_words,
    "labels": {
        "stages": ["Installed", "First ride", "Still using", "Repeat"],
        "numbers": ["Completed rides", "Got a first ride", "Quit in week one"],
        "legend": ["Rode or drove", "Using", "Quit"],
        "goal": "completed rides",
        "ask": {"converted": "Why did you keep using it?", "quit": "Why did you delete it?",
                "using": "What do you think of it so far?"},
        "last_screen": "What {they} saw last",
        "since": "First ride on day {day}.",
    },
    "story": {
        "reach": {"feed": "Saw a Hopway ad in the feed.", "search": "Found Hopway in an app store search.",
                  "event": "Met the Hopway team at a sign-up booth.", "outdoor": "Saw a Hopway billboard and looked it up.",
                  "referral": "Got a Hopway invite from a friend.", "friend": "A friend sent a Hopway link."},
        "skip": {"feed": "Scrolled past."},
        "skip_default": "Did not install it.",
        "success": {"driver": "Gave a first ride.", "rider": "Got a first ride."},
        "gate_head": {"drive": "Opened the driver screen.", "ride": "Opened the app."},
        "outcome": {"drive": {"go_online": "Went online to drive.", "come_back_tomorrow": "Came back the next day.",
                              "delete_app": "Deleted the app."},
                    "ride": {"request_ride": "Asked for a ride.", "come_back_tomorrow": "Came back the next day.",
                             "delete_app": "Deleted the app."}},
        "nearest": lambda bucket, side: (f"Nearest car: {ETA[bucket[1]]} minutes away." if side == "rider"
                                         else f"{REQUESTS[bucket[1]]} ride requests nearby in the last hour."),
    },
}

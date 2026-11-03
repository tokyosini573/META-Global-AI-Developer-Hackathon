"""Where people left and why: the v2 report (docs/replay-format.md "Version 2", plans[k].report).

For each step of the funnel, the people who reached the step before it but never this one, and the
reasons they gave. Muse Wonder names up to three themes per step and sorts each distinct reason into
one; the engine counts the people. Also the one line under the ads table (plans[k].ads.line).

    build(rep, cfg, use_wonder=True, log=print)   # fills rep in place; called by engine/run.py rehearse

To be written in the v2 redesign; until then it leaves the replay as it is.
"""


def build(rep, cfg, use_wonder=True, log=print):
    """Add plans[k].report and plans[k].ads["line"] to the replay, in place."""
    return rep

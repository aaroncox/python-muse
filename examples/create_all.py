import datetime
from pprint import pprint
from muse import Muse

MUSE = muse(
    # this account creates the proposal
    proposer="xeroc",
    # Proposal needs to be approve within 1 hour
    proposal_expiration=60 * 5,
    # For testing, set this to true
    nobroadcast=False,
    # We want to bundle many operations into a single transaction
    bundle=True,
)
MUSE.wallet.unlock("")

MUSE.sport_create([          # relative id 0.0.0
    ["de", "Fussball"],
    ["en", "Soccer"],
])

MUSE.competitor_create([     # relative id 0.0.1
    ["de", "Greuter Fürth"],
    ["en", "GF"],
], sport_id="0.0.0")

MUSE.competitor_create([     # relative id 0.0.2
    ["de", "FC Nürnberg"],
    ["en", "FCN"],
], sport_id="0.0.0")

MUSE.event_group_create([    # relative id 0.0.3
    ["de", "1. Bundesliga"],
    ["en", "First Country League"],
], sport_id="0.0.0")

MUSE.event_create(           # relative id 0.0.4
    [["de", "Januar 2016"], ["en", "January 2016"]],  # season
    datetime.datetime(2016, 1, 1, 0, 0, 0),  # start_time
    ["0.0.1", "0.0.2"],    # competitors
    event_group_id="0.0.3"   # event group
)

MUSE.betting_market_group_create(  # relative id 0.0.5
    "spread",
    margin=10,
    event_id="0.0.4",
)

MUSE.betting_market_create(
    [["de", "Fürth gewinnt"], ["en", "Fürth wins"]],
    "MUSE1",
    group_id="0.0.5",
)

MUSE.betting_market_create(
    [["de", "Nürnberg gewinnt"], ["en", "Nuremberg wins"]],
    "MUSE1",
    group_id="0.0.5",
)

# Broadcast the whole transaction
pprint(
    MUSE.txbuffer.broadcast()
)

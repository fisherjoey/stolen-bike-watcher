# stolen-bike-watcher

A prototype that takes a stolen-bike report (Bike Index style) and scores
marketplace listings (Kijiji and Facebook Marketplace style) by how likely each
one is that bike. Everything runs on mock data. Nothing here scrapes a real site
or looks at a real photo.

```
python3 build_mock_data.py     # 5 reports, 213 listings, 6 labelled true matches
python3 evaluate.py            # add --verbose for every reason, --radius 300 to widen
python3 -m unittest            # 9 tests
```

## How it scores

A listing has to be posted after the theft (within 120 days) and within the
search radius. Anything that passes gets points for evidence: brand, model,
colour, size, bike type, a price far below the usual resale value, and
urgent-sale wording like "must go" or "cash only". Every point comes with a
reason you can read.

Most of the weight goes to the owner's distinguishing features ("orange bar
tape", "purple pedals", "co-op sticker"), because those survive a repaint or a
part-out. A feature that shows up in more than 3% of all listings, like a
kickstand, earns less and doesn't count as distinguishing. A matching serial is
near-certain. A different serial in the listing clears it.

Results fall into three tiers: near-certain (serial), strong (score of 4 or more
with at least one distinguishing piece of evidence), and worth a look (score of
3 or more on make, model and colour alone).

`photo_tags` in the mock listings stands in for what a vision model would
report from the photos. In a real version that step would be a model call.

## Results on the mock data

| | caught | false flags |
|---|---|---|
| saved-search alert (brand + model keyword) | 1 of 6 | 15 |
| watcher, 100 km | 5 of 6 | 9 (1 strong, 8 worth a look) |
| watcher, 300 km | 6 of 6 | 13 (1 strong, 12 worth a look) |

Each true listing ranks first for its report. That includes a repainted bike, a
listing with no brand named, a Facebook cross-post with the brand misspelled,
and a parted-out wheel bundle. The keyword alert misses all four of those.

The one strong false flag is a deliberately planted Giant Escape that has a
kickstand and a basket, as the stolen one did. Common bikes with generic
features look like each other, and scoring can't separate them.

## Limits

The mock data was written by the same person who wrote the matcher, so these
numbers are optimistic. Real listings are messier and real photos have to be
read by a model. Getting listings at all is the hard part: Facebook Marketplace
blocks scripted browsers. The bike in the Edmonton listing is only caught at
300 km, and the wider radius adds four more false flags.

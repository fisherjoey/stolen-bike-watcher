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

## First run on real data (2026-09-25)

`real_run.py` scores real stolen reports against real listings. It needs files
in `data/real/`, which is gitignored because it holds scraped listings and
photos:

- `bi_bikes.json`: 100 stolen reports within 60 km of Calgary from the Bike
  Index API (`/api/v3/search`, then `/api/v3/bikes/{id}`), stolen Aug 20 to
  Sept 24.
- `extracted.json`: clean brand, model and distinguishing features for each
  report, from one `claude -p` call over the raw report text.
- `kijiji_raw.json`: every Calgary-region Kijiji bike listing back to Aug 14
  (1,960 listings), from `sweep_kijiji.py`.

Nothing was recovered. The matcher flagged 30 Kijiji listings. I compared
photos for the most likely ones (a Giant Sedona, a Specialized Rockhopper, a
Santa Cruz Nomad, a Specialized Allez) and read the details on the rest. Every
one I could check was a different bike. I also searched Facebook Marketplace
through the `secondhand` MCP for 9 of the stolen models. A $900 aluminum
Santa Cruz Nomad in Calgary came closest: same frame generation and coil
shock, but a different frame colour, fork and rear tire.

What the real data showed:

- Only 11 of 100 reports list anything distinctive. Most give brand, model and
  colour, and 35 have no usable serial. The matcher's strongest evidence
  usually doesn't exist.
- A photo on the report matters more than anything else. Every candidate was
  settled by comparing photos, and 26 reports have none.
- Reports are unreliable. One owner listed a "2016" Nomad, but their photo
  shows a much older 26-inch frame. Three reports for the same Norco Storm 4
  look like one theft entered three times.
- Kijiji serves its search results as JSON inside the page, so sweeping it is
  easy. Facebook returns 15 results per search with no post date, so the only
  option is one search per stolen model.

The mock data hid four bugs that real data exposed: a blank serial matched
every listing, parts and accessories counted as bikes, brand plus colour was
enough to flag, and generic words like "fat" counted as model names.

## Limits

The mock data was written by the same person who wrote the matcher, so these
numbers are optimistic. Real listings are messier and real photos have to be
read by a model. Getting listings at all is the hard part: Facebook Marketplace
blocks scripted browsers. The bike in the Edmonton listing is only caught at
300 km, and the wider radius adds four more false flags.

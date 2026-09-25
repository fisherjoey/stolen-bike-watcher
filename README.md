# stolen-bike-watcher

[![test](https://github.com/fisherjoey/stolen-bike-watcher/actions/workflows/test.yml/badge.svg)](https://github.com/fisherjoey/stolen-bike-watcher/actions/workflows/test.yml)

Stolen bikes often get resold on local marketplaces within days. This takes the
bikes reported stolen on [Bike Index](https://bikeindex.org) near a city and
scores every used-bike listing in the area by how likely it is to be one of them.
Each score comes with the reasons behind it, so a person can check the result.

It's a weekend prototype. It has been run once on real data (Calgary, September
2026) and found no stolen bikes. See [what the real run showed](#first-real-run).

## Quick start

Python 3.10 or newer, no dependencies.

```
pip install -e .
sbw demo
```

`sbw demo` generates 5 made-up stolen reports and 213 made-up listings with
known answers, then compares the matcher with a plain saved-search alert:

| | caught | false flags |
|---|---|---|
| saved-search alert (brand + model keyword) | 1 of 6 | 15 |
| watcher, 100 km | 5 of 6 | 9 (1 strong, 8 worth a look) |

The listings the keyword alert misses are the realistic ones: a repainted bike,
a listing that never names the brand, a cross-post with the brand misspelled,
and wheels from a bike that was taken apart and sold in pieces. The one match
the watcher misses turned up 250 km away.

## Running it on real data

```
sbw fetch-reports "Calgary, AB"          # stolen reports within 60 km, from the Bike Index API
sbw extract                              # clean brand/model, pull out distinguishing features
sbw sweep-kijiji --since 2026-09-01      # every bike listing in the Kijiji region since then
sbw run -v                               # score them; -v prints every reason
```

Files land in `data/real/`, which is gitignored.

`sbw extract` sends the reports to a language model, because owners type
anything into these fields: a model field that repeats the brand, "Stolen
09/15/26" as the description. By default it calls the Claude Code CLI
(`claude -p`). `--llm "<command>"` swaps in any command that reads a prompt on
stdin, and `--no-llm` does a rough cleanup with no features.

The sweep defaults to Calgary. For another city, pass the Kijiji URL slug and
location id from a Kijiji search URL, for example `--city edmonton
--location-id 1700203`.

Other sources can be added as `data/real/listings-<name>.json`, a list of
listings in the matcher's shape (see `sbw/kijiji.py:to_listing`). Facebook
Marketplace is the obvious one, but it only returns about 15 results per search
and no posting dates, so it has to be searched one stolen model at a time.

## How the scoring works

A listing is only considered if it went up after the theft (within 120 days)
and inside the search radius. It then earns points for brand, model, colour,
size, bike type, a price far below the usual resale value, and wording like
"must go" or "cash only".

Most of the weight goes to details the owner noted, such as "orange bar tape"
or "purple pedals", because those survive a repaint or a part-out. A detail
that shows up in more than 3% of all listings, like a kickstand, earns less. A
matching serial number puts a listing at near-certain, and a different serial
in the listing rules it out.

Results come in three tiers:

- near-certain: the serial number matches
- strong: a score of 4 or more, including at least one owner-noted detail or a
  suspiciously low price
- worth a look: a score of 3 or more, with the model or an owner-noted detail
  matching. Brand and colour alone don't count, since that describes hundreds
  of listings.

In the mock data, `photo_tags` stands in for what a vision model would see in
listing photos. The real pipeline doesn't read photos yet.

## First real run

On 2026-09-25 I pulled the 100 most recent stolen reports around Calgary (stolen
Aug 20 to Sept 24) and all 1,960 Calgary-region Kijiji bike listings posted
since Aug 14. I also searched Facebook Marketplace by hand for 9 of the stolen
models.

The watcher flagged 30 Kijiji listings. I checked the likeliest ones against
the owners' photos. Every one was a different bike: the right model, but the
wrong era, colour, frame size or wheel size. The closest was an aluminum Santa
Cruz Nomad on Facebook with the same frame generation and coil shock as a
stolen one. It had a different frame colour, fork and rear tire.

What real data showed that mock data didn't:

- Most reports are thin. Only 11 of 100 mention anything distinctive, and 35
  have no usable serial number, so the matcher's best evidence usually isn't
  there.
- The owner's photo settled every candidate, and 26 reports have none. If you
  register a bike, add clear photos and anything that sets it apart.
- Reports contain mistakes. One says "2016 Nomad", but its photo shows a much
  older frame. Three reports for the same Norco Storm 4 look like one theft
  entered three times.
- Four bugs only showed up on real data. A blank serial matched every listing
  (18,064 flags before the fix), accessories counted as bikes, brand plus colour
  was enough to flag, and words like "fat" counted as model names. Each has a
  regression test now.

## Using this responsibly

A flag means "a person should look at this", not "this is stolen". Plenty of
flagged listings are honest sellers with the same popular bike.

If you think you've found a stolen bike, don't contact or confront the seller.
Give the listing to the owner through Bike Index, or to the police. Bike Index
has [a guide for this](https://bikeindex.org/news/what-to-do-when-you-find-your-stolen-bike-for-sale-on-facebook-marketp).

The Kijiji sweep reads public search pages one at a time with a pause between
requests. Keep it that way, and check the site's terms before running it
regularly. Don't commit or publish scraped listings: they can contain sellers'
contact details.

## Layout

```
sbw/matcher.py     scoring, tiers and reasons
sbw/bikeindex.py   Bike Index API client and report conversion
sbw/extract.py     language-model cleanup of report text
sbw/kijiji.py      Kijiji search, sweep and listing conversion
sbw/run.py         real-data run
sbw/mock.py        mock data generator
sbw/evaluate.py    mock-data evaluation
sbw/catalog.py     small bike catalogue: brands, models, resale values
tests/             python -m unittest
```

## License

MIT

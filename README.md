# KCE home page: two visual directions

Step 4 of the KCE Website Redesign brief: two home-page concepts applying the
brief's headline, proof points, section list and colour direction.

Live: https://anirudhatalmale6-alt.github.io/kce-home-directions/

- **Direction A, The Record** — white and deep green, hairline rules, a
  spec-document structure. The hero's right side is an operating-record table
  rather than a photograph. Instrument Sans.
- **Direction B, The Corridor** — deep navy hero with the 20-state coverage map
  as the atmosphere behind the headline, warm off-white below, a proof ribbon
  overlapping the two. Manrope.

Both carry every section the brief asks for on the home page: headline and
supporting line, proof-point bar, healthcare services preview, industries
served, how KCE verifies quality, credentials strip, coverage map and a single
call to action.

## Checked before hand-off

`tools/verify.py` runs in headless Chromium and asserts:

- no horizontal overflow at 390px
- the sample report bars actually render (they were collapsing to zero height
  because `.tr` / `.fl` are `<span>` elements, which ignore `height` until they
  are given `display:block`)
- the industries grid leaves no orphaned card on its last row
- every opaque text run meets WCAG 2.1 AA contrast

## Coverage map

`src/usmap.svg` is generated from the public `us-atlas` state boundaries by
`tools/build_map.py`, projected to Albers and emitted as one `<path>` per state
keyed by USPS code. Adding or removing a served state is one entry in the
`SERVED` set in `tools/build_concepts.py`, so KCE can change coverage without a
redesign.

## Build

```sh
python3 tools/build_map.py        # regenerate src/usmap.svg
python3 tools/build_concepts.py   # inline fonts + map into the two pages
python3 tools/verify.py           # the checks above
```

## Placeholders

The 20 highlighted states, the shield mark, the phone number and the sample
report figures are all placeholders pending KCE input. There is no photography
yet: the brief asks for real KCE crews in PPE and warns against stock that looks
like stock, so proof carries the page until a shoot happens. The testimonial
section is designed but switched off until real approved quotes arrive.

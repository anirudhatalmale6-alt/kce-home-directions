#!/usr/bin/env python3
"""Check the concepts for the things that silently break: zero-height bars,
horizontal overflow on a phone, orphaned grid rows, and unreadable contrast."""
import pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent / "concepts"
TARGETS = [("A", "concept-a-the-record.html"), ("B", "concept-b-the-corridor.html")]
fails = []


def srgb(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    r, g, b = rgb
    return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)


def parse(s):
    nums = [float(x) for x in s.replace("rgba(", "").replace("rgb(", "").rstrip(")").split(",")]
    return nums[:3], (nums[3] if len(nums) > 3 else 1.0)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tag, fname in TARGETS:
        url = (ROOT / fname).as_uri()

        # ---- phone: horizontal overflow ----
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        pg = ctx.new_page()
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_timeout(900)
        ov = pg.evaluate("""() => {
          const docW = document.documentElement.clientWidth;
          const bad = [];
          for (const el of document.querySelectorAll('body *')) {
            const r = el.getBoundingClientRect();
            if (r.width === 0) continue;
            // right edge past the viewport, ignoring deliberately-masked decoration
            if (r.right > docW + 0.5 || r.left < -0.5) {
              const cs = getComputedStyle(el);
              if (cs.position === 'absolute' && cs.pointerEvents === 'none') continue;
              bad.push({t: el.tagName + '.' + (el.className.toString().split(' ')[0] || ''),
                        l: Math.round(r.left), r: Math.round(r.right)});
            }
          }
          return {docW, scrollW: document.documentElement.scrollWidth, bad: bad.slice(0, 6)};
        }""")
        if ov["scrollW"] > ov["docW"] + 1 or ov["bad"]:
            fails.append(f"{tag} phone overflow: scrollW={ov['scrollW']} vs {ov['docW']}; {ov['bad']}")
        else:
            print(f"{tag} phone 390px: no horizontal overflow")
        ctx.close()

        # ---- desktop: bars, grid rows, contrast ----
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_timeout(2000)  # let the bar fills finish animating

        bars = pg.evaluate("""() => [...document.querySelectorAll('.bar .fl')].map(e => {
          const r = e.getBoundingClientRect();
          return {w: Math.round(r.width), h: Math.round(r.height)};
        })""")
        dead = [b for b in bars if b["h"] < 4 or b["w"] < 10]
        if not bars:
            fails.append(f"{tag}: no report bars found at all")
        elif dead:
            fails.append(f"{tag}: {len(dead)}/{len(bars)} report bars render collapsed -> {dead}")
        else:
            print(f"{tag} report bars: {len(bars)} drawn, widths {[b['w'] for b in bars]}")

        rows = pg.evaluate("""() => {
          const g = document.querySelector('.igrid, .inds');
          if (!g) return null;
          const tops = {};
          for (const c of g.children) {
            const t = Math.round(c.getBoundingClientRect().top);
            tops[t] = (tops[t] || 0) + 1;
          }
          return tops;
        }""")
        if rows:
            counts = list(rows.values())
            # a trailing row holding a single card next to dead space is the orphan we fixed
            if len(counts) > 1 and counts[-1] == 1 and counts[-1] < max(counts) - 1:
                fails.append(f"{tag}: industries grid orphans a card on the last row {counts}")
            else:
                print(f"{tag} industries grid rows: {counts}")

        bad_contrast = pg.evaluate("""() => {
          const out = [];
          for (const el of document.querySelectorAll('p,h1,h2,h3,h4,a,span,dt,dd,b')) {
            if (!el.textContent.trim() || el.children.length) continue;
            const cs = getComputedStyle(el);
            const size = parseFloat(cs.fontSize);
            let bgEl = el, bg = 'rgba(0, 0, 0, 0)';
            while (bgEl) {
              const c = getComputedStyle(bgEl).backgroundColor;
              if (c && !c.startsWith('rgba(0, 0, 0, 0')) { bg = c; break; }
              bgEl = bgEl.parentElement;
            }
            out.push({fg: cs.color, bg, size, w: cs.fontWeight,
                      txt: el.textContent.trim().slice(0, 34)});
          }
          return out;
        }""")
        worst = []
        for item in bad_contrast:
            fg, _ = parse(item["fg"])
            bg, a = parse(item["bg"])
            if a < 0.9:
                continue
            l1, l2 = lum(fg), lum(bg)
            ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
            large = item["size"] >= 24 or (item["size"] >= 18.66 and int(item["w"]) >= 700)
            need = 3.0 if large else 4.5
            if ratio < need:
                worst.append((round(ratio, 2), need, item["txt"]))
        if worst:
            worst.sort()
            fails.append(f"{tag}: {len(worst)} text runs under WCAG AA -> {worst[:5]}")
        else:
            print(f"{tag} contrast: all {len(bad_contrast)} opaque text runs meet WCAG AA")
        ctx.close()
    browser.close()

print()
if fails:
    print("FAILURES:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("all checks passed")

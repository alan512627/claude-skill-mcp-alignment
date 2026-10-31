import json, sys, re
from collections import defaultdict

src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
series = defaultdict(list)
units = {}
for blk in text.split("---"):
    blk = blk.strip()
    if not blk:
        continue
    try:
        o = json.loads(blk)
    except Exception:
        continue
    v = o.get("metricValue")
    if not isinstance(v, (int, float)):
        continue
    n = o["metricName"]
    series[n].append((o["timestamp"][:19], v))
    units[n] = o.get("metricUnit", "")

stats = []
for n, pts in series.items():
    vals = [p[1] for p in pts]
    stats.append({"name": n, "unit": units[n], "n": len(vals), "min": min(vals), "max": max(vals),
                  "avg": round(sum(vals) / len(vals), 3), "first": pts[0][0], "last": pts[-1][0]})
stats.sort(key=lambda s: (s["unit"], s["name"]))

# downsample to ~240 points per series for charts
ds = {}
for n, pts in series.items():
    step = max(1, len(pts) // 240)
    ds[n] = [[t, v] for t, v in pts[::step]]

json.dump({"stats": stats, "series": ds}, open(out, "w"), separators=(",", ":"))
print(len(stats), "sensors")
for s in stats:
    print(f'{s["name"]:40s} {s["unit"]:10s} n={s["n"]:5d} min={s["min"]:<10} max={s["max"]:<10} avg={s["avg"]}')

"""Evidence helpers: read raw log lines with line numbers, track which files get cited."""
import os, re, glob, json, shutil
from datetime import datetime

ROOTS = {}
LABEL = {"s2": "Slot2", "s46": "Slot46"}
CITED = {}  # (slot, relpath) -> True


def init(roots):
    ROOTS.update(roots)


def resolve(slot, rel):
    full = os.path.join(ROOTS[slot], rel)
    if "*" in rel:
        m = sorted(glob.glob(full))
        assert len(m) == 1, (slot, rel, m)
        full = m[0]
    assert os.path.exists(full), full
    return full, os.path.relpath(full, ROOTS[slot])


def lines(slot, rel):
    full, actual = resolve(slot, rel)
    with open(full, encoding="utf-8-sig", errors="replace") as f:
        return actual, f.read().splitlines()


def ev(slot, rel, pat=None, n=14, ctx=0, rng=None, after_last=None, maxlen=420, flags=re.I):
    """Return an evidence source: matching lines with their real line numbers."""
    actual, L = lines(slot, rel)
    CITED[(slot, actual)] = True
    start = 0
    if after_last:
        for i, l in enumerate(L):
            if re.search(after_last, l):
                start = i + 1
    idx = range(start, len(L))
    if rng:
        idx = range(rng[0] - 1, min(rng[1], len(L)))
    if pat:
        hit = [i for i in idx if re.search(pat, L[i], flags)]
        keep = []
        for i in hit:
            for j in range(max(start, i - ctx), min(len(L), i + ctx + 1)):
                if j not in keep:
                    keep.append(j)
        idx = keep[:n]
    else:
        idx = list(idx)[:n]
    out = [[i + 1, L[i][:maxlen]] for i in idx]
    return {"file": f"[{LABEL[slot]}] {actual}", "lines": out}


def ev_text(title, texts):
    return {"file": title, "lines": [["", t] for t in texts]}


def grep(slot, rel, pat, flags=re.I, after_last=None):
    actual, L = lines(slot, rel)
    start = 0
    if after_last:
        for i, l in enumerate(L):
            if re.search(after_last, l):
                start = i + 1
    return [(i + 1, L[i]) for i in range(start, len(L)) if re.search(pat, L[i], flags)]


def hms(s):
    return datetime.strptime(s, "%H:%M:%S")


def secs(a, b):
    return int((hms(b) - hms(a)).total_seconds())


def copy_evidence(dest, maxbytes=3_000_000):
    os.makedirs(dest, exist_ok=True)
    idx = []
    for (slot, rel) in sorted(CITED):
        src = os.path.join(ROOTS[slot], rel)
        if os.path.getsize(src) > maxbytes:
            idx.append(f"[{LABEL[slot]}] {rel}  (超過 3 MB，未複製，請從原 zip 取用)")
            continue
        dst = os.path.join(dest, LABEL[slot], rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        idx.append(f"[{LABEL[slot]}] {rel}")
    return idx

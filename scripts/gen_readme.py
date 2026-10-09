#!/usr/bin/env python3
"""Sync data/ from the live site and regenerate the README tables.

Usage:  python3 scripts/gen_readme.py --fetch    # weekly sync: download https://freeai.alexai.top/offers.json,
                                                 # then rebuild data/*.csv and both READMEs
        python3 scripts/gen_readme.py            # rebuild CSVs + READMEs from the local data/offers.json
        python3 scripts/gen_readme.py --check    # exit 1 if CSVs/READMEs are out of date
        FREE_AI_TODAY=YYYY-MM-DD python3 scripts/gen_readme.py   # override "today"

Source of truth: data/offers.json, a copy of the site's public feed (https://freeai.alexai.top/offers.json).
The "unverified_not_listed" rumour list is dropped, because this repo lists officially verified facts only.
data/offers.csv and data/offers_zh.csv are derived from it in the site's CSV format (see README "Data").
No third-party dependencies, Python 3.8+.
"""
import csv, datetime, io, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = "https://freeai.alexai.top"
FEED = SITE + "/offers.json"
EN_COLS = ["slug", "page", "status", "category", "provider", "models", "title", "what_free", "limits", "how_to_claim",
           "start", "end", "end_date", "extended", "commercial_use", "card_required", "phone_required", "region",
           "china_vendor", "conditions", "source_url", "source_label", "extra_sources", "source_type", "last_verified",
           "keywords", "notes"]
ZH_COLS = ["slug", "provider", "models", "title", "what_free", "limits", "how_to_claim", "end", "extended",
           "commercial_use", "card_required", "phone_required", "region", "conditions", "notes", "source_label", "cn_note"]
START, END = "<!-- OFFERS:START -->", "<!-- OFFERS:END -->"
VSTART, VEND = "<!-- VERIFIED:START -->", "<!-- VERIFIED:END -->"

LABELS = {
    "en": {"ended": "⚫ Ended", "soon": "🔴 Ending soon", "ext": "🟠 Extended", "active": "🟢 Active", "ongoing": "🟢 Ongoing",
           "cols": ["Provider", "Offer / models", "Free quota", "Deadline", "Status", "Verified", "Links"],
           "active_h": "Active offers", "ended_h": "Recently ended", "official": "Official", "details": "Details",
           "ongoing_end": "Ongoing", "count": "{a} active · {e} ended · last verified {d}"},
    "zh": {"ended": "⚫ 已结束", "soon": "🔴 即将截止", "ext": "🟠 已延期", "active": "🟢 进行中", "ongoing": "🟢 长期",
           "cols": ["厂商", "活动 / 模型", "免费额度", "截止时间", "状态", "核实日期", "链接"],
           "active_h": "进行中的免费额度", "ended_h": "最近已结束", "official": "官方来源", "details": "详情",
           "ongoing_end": "长期有效", "count": "进行中 {a} 条 · 已结束 {e} 条 · 最近核实 {d}"},
}
ZH_KEYS = ["provider", "models", "title", "what_free", "end", "extended"]


def today():
    t = os.environ.get("FREE_AI_TODAY")
    return datetime.date.fromisoformat(t) if t else datetime.date.today()


def load_feed():
    with open(os.path.join(DATA, "offers.json"), encoding="utf-8") as f:
        return json.load(f)


def fetch():
    req = urllib.request.Request(FEED, headers={"User-Agent": "free-ai-quota-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        doc = json.load(r)
    if doc.get("schema_version") != 1 or not doc.get("offers"):
        sys.exit("unexpected feed format; not overwriting data/offers.json")
    write_json(doc)
    print(f"fetched {FEED}: generated {doc.get('generated')}, {len(doc['offers'])} offers")


def write_json(doc):
    doc.pop("unverified_not_listed", None)
    with open(os.path.join(DATA, "offers.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


def to_rows(o):
    """One feed entry -> (EN csv row, ZH csv row) in the site's offers.csv / offers_zh.csv format."""
    en, zh = o["en"], o["zh"]
    extras = " ; ".join(f"{x['label']} => {x['url']}" for x in o.get("extra_sources", []))
    r = {"slug": o["slug"], "page": "1" if o.get("has_page") else "0", "status": o["status"], "category": o["category"],
         "start": o.get("start") or "", "end_date": o.get("end_date") or "", "china_vendor": "1" if o.get("china_vendor") else "0",
         "source_url": o["source_url"], "extra_sources": extras, "source_type": o.get("source_type", ""),
         "last_verified": o["last_verified"], "keywords": ""}
    for k in EN_COLS:
        if k not in r:
            v = en.get(k, "")
            r[k] = " | ".join(v) if isinstance(v, list) else (v or "")
    z = {"slug": o["slug"]}
    for k in ZH_COLS[1:]:
        v = zh.get(k, "")
        z[k] = " | ".join(v) if isinstance(v, list) else (v or "")
    return r, z


def csv_text(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def status_key(r, t):
    """Same rules as the site: auto-expiry by end_date, <=3 days = ending soon."""
    status = r["status"]
    days = (datetime.date.fromisoformat(r["end_date"]) - t).days if r["end_date"] else None
    if status == "active" and days is not None and days < 0:
        status = "expired"
    if status == "expired":
        return "ended", days
    if days is not None and days <= 3:
        return "soon", days
    if r["extended"].startswith(("Yes", "是")):
        return "ext", days
    return ("ongoing" if r["category"] == "evergreen" else "active"), days


def first_sentence(s, limit=160):
    s = " ".join(s.split())
    m = re.match(r"(.+?(?:[.!?](?=\s|$)|[。！？]))", s)
    s = m.group(1) if m else s
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def cell(s):
    return " ".join(str(s).split()).replace("|", "\\|")


def load(doc):
    t = today()
    rows = []
    for o in doc["offers"]:
        if o["status"] not in ("active", "expired"):  # never show 'unconfirmed'
            continue
        en, zh = to_rows(o)
        z = dict(en)
        z.update({k: zh.get(k) or en[k] for k in ZH_KEYS})
        st, days = status_key(en, t)
        rows.append({"en": en, "zh": z, "zh_csv": zh, "st": st, "days": days})
    order = {"soon": 0, "ext": 1, "active": 2, "ongoing": 3, "ended": 9}
    rows.sort(key=lambda x: (order[x["st"]], x["days"] if x["days"] is not None else 9999, x["en"]["provider"].lower()))
    return rows


def table(rows, lang):
    L = LABELS[lang]
    out = ["| " + " | ".join(L["cols"]) + " |", "|" + "---|" * len(L["cols"])]
    for x in rows:
        r = x[lang]
        prefix = "" if lang == "en" else "/zh"
        page = f"{SITE}{prefix}/{r['slug']}/" if r["page"] == "1" else f"{SITE}{prefix}/#{r['slug']}"
        links = f"[{L['official']}]({r['source_url']}) · [{L['details']}]({page})"
        out.append("| " + " | ".join(cell(c) for c in [
            f"**{r['provider']}**", r["models"], first_sentence(r["what_free"]), r["end"] or L["ongoing_end"],
            L[x["st"]], r["last_verified"], links]) + " |")
    return "\n".join(out)


def block(rows, lang):
    L = LABELS[lang]
    act = [x for x in rows if x["st"] != "ended"]
    end = [x for x in rows if x["st"] == "ended"]
    parts = [f"### {L['active_h']} ({len(act)})", "", table(act, lang)]
    if end:
        parts += ["", f"### {L['ended_h']} ({len(end)})", "", table(end, lang)]
    return "\n".join(parts)


def verified_line(rows, lang):
    d = max(x["en"]["last_verified"] for x in rows)
    a = sum(x["st"] != "ended" for x in rows)
    return LABELS[lang]["count"].format(a=a, e=len(rows) - a, d=d)


def replace(text, start, end, body):
    i, j = text.find(start), text.find(end)
    if i < 0 or j < i:
        sys.exit(f"markers {start} / {end} not found")
    return text[: i + len(start)] + "\n" + body + "\n" + text[j:]


def write_if_changed(path, new, check):
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if old == new:
        return True
    if not check:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"updated {os.path.relpath(path, ROOT)}")
    return False


def main():
    check = "--check" in sys.argv
    if "--fetch" in sys.argv:
        fetch()
    doc = load_feed()
    ok = "unverified_not_listed" not in doc
    if not ok and not check:
        write_json(doc)
    rows = load(doc)
    feed_order = {o["slug"]: i for i, o in enumerate(doc["offers"])}
    by_feed = sorted(rows, key=lambda x: feed_order[x["en"]["slug"]])
    ok &= write_if_changed(os.path.join(DATA, "offers.csv"), csv_text(EN_COLS, [x["en"] for x in by_feed]), check)
    ok &= write_if_changed(os.path.join(DATA, "offers_zh.csv"), csv_text(ZH_COLS, [x["zh_csv"] for x in by_feed]), check)
    for lang, name in (("en", "README.md"), ("zh", "README.zh-CN.md")):
        p = os.path.join(ROOT, name)
        with open(p, encoding="utf-8") as f:
            old = f.read()
        new = replace(old, START, END, block(rows, lang))
        new = replace(new, VSTART, VEND, verified_line(rows, lang))
        ok &= write_if_changed(p, new, check)
    act = sum(x["st"] != "ended" for x in rows)
    print(f"{len(rows)} offers: {act} active, {len(rows) - act} ended")
    if check and not ok:
        sys.exit("data/README out of date: run python3 scripts/gen_readme.py")


if __name__ == "__main__":
    main()

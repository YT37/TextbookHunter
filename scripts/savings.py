#!/usr/bin/env python3
"""Rank the legal routes for each textbook and total the savings.

Usage (from the Skill folder):
    python3 scripts/savings.py --file <findings.json> [--save] [--compare]
    python3 scripts/savings.py --sample [--compare]

State: ~/.config/textbook-hunter/last.json
Exit codes: 0 ok, 2 invalid findings, 3 findings file missing or not JSON, 4 no books.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import NoReturn, Optional

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "assets" / "sample_books.json"
SAMPLE_PREVIOUS = ROOT / "assets" / "sample_previous.json"
STATE = Path.home() / ".config" / "textbook-hunter" / "last.json"
CENT = Decimal("0.01")
ZERO = Decimal("0.00")

# Order also breaks price ties.
ROUTES = {
    "instructor_free": "free from the instructor",
    "open_textbook": "free open textbook",
    "library_ebook": "library ebook",
    "library_reserve": "library course reserve",
    "digital": "digital copy",
    "rental": "rental",
    "used": "used copy",
    "older_edition": "older edition",
    "new": "new copy",
}
PREFERENCE = list(ROUTES)
KEEPS = {"instructor_free", "open_textbook", "used", "older_edition", "new"}
NO_CODE = {"library_ebook", "library_reserve", "rental", "used", "older_edition"}
STATUSES = {"required", "recommended", "optional"}


class Invalid(Exception):
    pass


def fail(message: str, code: int) -> NoReturn:
    print(message, file=sys.stderr)
    sys.exit(code)


def money(value, where: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise Invalid(f"{where}: price {value!r} is not a number")
    if not amount.is_finite() or amount < 0:
        raise Invalid(f"{where}: price must be 0 or more, got {value!r}")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(amount: Optional[Decimal]) -> str:
    return "unknown" if amount is None else f"${amount:,.2f}"


def book_key(book: dict) -> str:
    isbn = str(book.get("isbn") or "").replace("-", "").strip()
    if isbn:
        return isbn
    return f"{str(book.get('course') or '').strip().upper()}|{str(book.get('title') or '').strip().lower()}"


def load_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def read_findings(path: Path) -> dict:
    if not path.is_file():
        fail(f"Findings file not found: {path}", 3)
    data = load_json(path)
    if data is None:
        fail(f"Findings file is not valid JSON: {path}", 3)
    if not isinstance(data, dict):
        fail("Findings must be a JSON object with a 'books' list.", 2)
    return data


def analyze_book(book: dict, index: int) -> dict:
    where = f"books[{index}]"
    if not isinstance(book, dict):
        raise Invalid(f"{where} must be an object")
    title = str(book.get("title") or "").strip()
    if not title:
        raise Invalid(f"{where}.title is missing")
    status = str(book.get("status") or "required").strip().lower()
    if status not in STATUSES:
        raise Invalid(f"{where}.status must be one of {sorted(STATUSES)}, got {status!r}")
    needs_code = bool(book.get("access_code"))
    exact_edition = bool(book.get("exact_edition_required"))

    baseline, baseline_label = None, None
    raw = book.get("baseline")
    if isinstance(raw, dict) and raw.get("price") is not None:
        baseline = money(raw["price"], f"{where}.baseline")
        baseline_label = str(raw.get("label") or "bookstore new").strip()

    options = book.get("options") or []
    if not isinstance(options, list):
        raise Invalid(f"{where}.options must be a list")
    usable, skipped = [], []
    for j, opt in enumerate(options):
        owhere = f"{where}.options[{j}]"
        if not isinstance(opt, dict):
            raise Invalid(f"{owhere} must be an object")
        route = str(opt.get("route") or "").strip().lower()
        if route not in ROUTES:
            raise Invalid(f"{owhere}.route must be one of {PREFERENCE}, got {route!r}")
        if opt.get("price") is None:
            raise Invalid(f"{owhere}.price is missing (use 0 for free)")
        item = {
            "route": route,
            "route_label": ROUTES[route],
            "source": str(opt.get("source") or "").strip(),
            "price": money(opt["price"], owhere),
            "url": str(opt.get("url") or "").strip(),
            "note": str(opt.get("note") or "").strip(),
            "keep": bool(opt["keep"]) if "keep" in opt else route in KEEPS,
        }
        if route == "older_edition" and exact_edition:
            skipped.append({**item, "why": "the course needs this exact edition"})
        elif needs_code and route in NO_CODE and not opt.get("includes_code"):
            skipped.append({**item, "why": "it would not come with the access code the course needs"})
        else:
            usable.append(item)

    if baseline is None:
        new_prices = [o["price"] for o in usable if o["route"] == "new"]
        if new_prices:
            baseline, baseline_label = max(new_prices), "new copy"

    usable.sort(key=lambda o: (o["price"], PREFERENCE.index(o["route"])))
    best = usable[0] if usable else None
    keep_cheapest = next((o for o in usable if o["keep"]), None)
    # Only worth showing when it differs from the best route and still beats full price.
    keep_best = keep_cheapest
    if keep_best is best or (keep_best and baseline is not None and keep_best["price"] >= baseline):
        keep_best = None

    saves = max(baseline - best["price"], ZERO) if best and baseline is not None else None

    return {
        "key": book_key(book),
        "course": str(book.get("course") or "").strip(),
        "title": title,
        "edition": str(book.get("edition") or "").strip(),
        "status": status,
        "access_code": needs_code,
        "baseline": baseline,
        "baseline_label": baseline_label,
        "best": best,
        "keep_best": keep_best,
        "keep_cheapest": keep_cheapest,
        "saves": saves,
        "skipped": skipped,
    }


def analyze(data: dict) -> dict:
    books = data.get("books")
    if not isinstance(books, list):
        fail("Findings need a 'books' list.", 2)
    if not books:
        fail("No books in the findings. Ask the student for a course, a syllabus or a bookstore screenshot.", 4)
    try:
        results = [analyze_book(b, i) for i, b in enumerate(books)]
    except Invalid as exc:
        fail(f"Invalid findings: {exc}", 2)

    priced = [r for r in results if r["status"] == "required" and r["baseline"] is not None and r["best"]]
    bookstore_total = sum((r["baseline"] for r in priced), ZERO)
    best_total = sum((r["best"]["price"] for r in priced), ZERO)
    keep_total = sum(((r["keep_cheapest"] or {}).get("price", r["baseline"]) for r in priced), ZERO)
    skippable = sum((r["baseline"] for r in results if r["status"] != "required" and r["baseline"] is not None), ZERO)
    return {
        "term": str(data.get("term") or "").strip(),
        "books": results,
        "totals": {
            "priced_books": len(priced),
            "bookstore_total": bookstore_total,
            "best_total": best_total,
            "keep_total": keep_total,
            "skip_recommended_saves": skippable,
            "no_price_data": [r["title"] for r in results if r["best"] is None or r["baseline"] is None],
        },
    }


def compare(report: dict, previous: Optional[dict]) -> list:
    if not previous:
        return ["No earlier run saved, so nothing to compare yet."]
    before = {b["key"]: b for b in previous.get("books", [])}
    current = {b["key"] for b in report["books"]}
    lines = []
    for book in report["books"]:
        name = f"{book['course']} {book['title']}".strip()
        old = before.get(book["key"])
        if old is None:
            lines.append(f"New on the list: {name}")
            continue
        best = book["best"]
        if best is None or old.get("best_price") is None:
            continue
        old_price = Decimal(old["best_price"])
        if best["price"] < old_price:
            lines.append(
                f"Cheaper now: {name}, {fmt(best['price'])} ({best['route_label']}) was {fmt(old_price)}, "
                f"down {fmt(old_price - best['price'])}"
            )
        elif best["price"] > old_price:
            lines.append(f"Pricier now: {name}, best is {fmt(best['price'])}, was {fmt(old_price)}")
        if best["route"] != old.get("best_route") and best["price"] <= old_price:
            lines.append(f"New best route for {book['title']}: {best['route_label']} ({best['source']})")
    for key, old in before.items():
        if key not in current:
            lines.append(f"No longer on the list: {old.get('title', key)}")
    return lines or ["No changes since the last check."]


def snapshot(report: dict) -> dict:
    return {
        "term": report["term"],
        "books": [
            {
                "key": b["key"],
                "title": b["title"],
                "course": b["course"],
                "best_price": str(b["best"]["price"]) if b["best"] else None,
                "best_route": b["best"]["route"] if b["best"] else None,
            }
            for b in report["books"]
        ],
    }


def render(report: dict, changes: Optional[list]) -> str:
    t = report["totals"]
    out = ["Textbook Hunter" + (f", {report['term']}" if report["term"] else "")]
    if t["priced_books"]:
        out.append(
            f"Required books: {fmt(t['bookstore_total'])} at full price -> {fmt(t['best_total'])} "
            f"with the best routes. Saves {fmt(t['bookstore_total'] - t['best_total'])}."
        )
        if t["keep_total"] != t["best_total"]:
            out.append(
                f"With copies you keep (no loans or rentals): {fmt(t['keep_total'])}. "
                f"Saves {fmt(t['bookstore_total'] - t['keep_total'])}."
            )
    if t["skip_recommended_saves"] > 0:
        out.append(f"Skipping the recommended-only books would save another {fmt(t['skip_recommended_saves'])}.")
    if changes is not None:
        out += ["", "Since last check:"] + [f"- {line}" for line in changes]

    for b in report["books"]:
        name = f"{b['course']} {b['title']}".strip()
        if b["edition"]:
            name += f" ({b['edition']})"
        if b["status"] != "required":
            name += f" [{b['status']}]"
        out += ["", name]
        best = b["best"]
        if best is None:
            out.append("  no legal route found yet; check the bookstore and library by ISBN")
        else:
            src = f", {best['source']}" if best["source"] else ""
            out.append(f"  best: {fmt(best['price'])} {best['route_label']}{src} "
                       f"({'keep it' if best['keep'] else 'borrow/return'})")
            if best["url"]:
                out.append(f"  {best['url']}")
            if best["note"]:
                out.append(f"  note: {best['note']}")
            if b["saves"] is not None and b["status"] == "required":
                out.append(f"  saves {fmt(b['saves'])} vs {b['baseline_label']} {fmt(b['baseline'])}")
        kb = b["keep_best"]
        if kb is not None:
            src = f", {kb['source']}" if kb["source"] else ""
            out.append(f"  to keep a copy: {fmt(kb['price'])} {kb['route_label']}{src}")
            if kb["url"]:
                out.append(f"  {kb['url']}")
        if b["access_code"]:
            out.append("  needs an access code: used, rented and library copies usually don't include one")
        for s in b["skipped"]:
            out.append(f"  left out {s['route_label']} ({fmt(s['price'])}) because {s['why']}")
        if b["status"] != "required" and b["baseline"] is not None:
            out.append(f"  listed as {b['status']}: skipping it saves {fmt(b['baseline'])}")

    if t["no_price_data"]:
        out += ["", "Missing a price or a route for: " + "; ".join(t["no_price_data"])]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank textbook routes and total the savings.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", help="JSON findings")
    source.add_argument("--sample", action="store_true", help="bundled example; never reads or writes saved state")
    parser.add_argument("--save", action="store_true", help="remember this run for later check-ins")
    parser.add_argument("--compare", action="store_true", help="show what changed since the saved run")
    args = parser.parse_args()

    if args.sample and args.save:
        fail("--save does not work with --sample.", 2)

    report = analyze(read_findings(SAMPLE if args.sample else Path(args.file)))
    changes = compare(report, load_json(SAMPLE_PREVIOUS if args.sample else STATE)) if args.compare else None

    if args.save:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(snapshot(report), indent=2))

    print(render(report, changes))


if __name__ == "__main__":
    main()

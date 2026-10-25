---
name: textbook-hunter
description: Finds the free or cheapest legal way to get each required textbook (library reserve, open textbook, older edition, used or rental) and says how much the student saves. Use when the student asks whether they really need to buy a book, sends a syllabus, a book list or a bookstore screenshot, complains about textbook or access code prices, asks for a cheaper or free copy, or is getting ready for a new semester, even if they never say "textbook".
---

# Textbook Hunter

Students overpay for course materials because nobody checks the free and cheap routes before the bookstore
checkout. This Skill reads what the course actually requires, checks every legal route for each book, and texts
back one number: what the student saves.

## When to use

- "bookstore wants $289 for my ECN 212 book, is there anything cheaper?"
- "do I actually need to buy the textbook for CSE 230?"
- A photo of a syllabus, or a screenshot of the bookstore's book list
- "registered for spring, what books do I need and what's the cheapest way to get them"
- "is the library copy of my chem book any good or should I rent"

Do not use it to summarize a book, write study notes, or build a study plan (the built-in study plan Skill does
that). Never use it to find unauthorized copies; see "Legal routes only".

## Legal routes only

Only suggest routes the student can use legally: the instructor's own posted copy, open textbooks, the library
(ebooks, course reserves, regular loans), rentals, used and older-edition copies, legitimate digital editions and
new copies. Never link to or describe "free PDF" download sites, shadow libraries, file-sharing posts or anything
else that copies a book without permission. If the student asks for one, say in one line that you can only point
to legal copies, then carry on with the legal routes, which are often free anyway.

## Steps

1. **Get the book list.** Use, in this order, whatever is available:
   - What the student sent: read the syllabus, the photo or the bookstore screenshot, or the course codes in
     their message.
   - The student's Canvas: for each current course (or the courses they named), read the syllabus, course pages
     and announcements, and search the course files for "syllabus", "textbook", "required materials" or
     "course materials".
   If Canvas is not connected and the student sent nothing, ask for one of these, with a default they can accept:
   "Send me a screenshot of your bookstore book list, or your course codes (like CSE 230)." Then stop and wait.
   If they are asking about next term and those courses are not in Canvas yet, ask for the course codes and
   sections or a bookstore screenshot instead.

2. **Write down each book exactly.** For every book capture the course, title, author, edition, ISBN-13 when the
   source shows one, whether it is required, recommended or optional, whether it needs an access code (online
   homework such as MyLab, Connect, WebAssign, Mastering, ALEKS), and whether the syllabus insists on that exact
   edition. Never guess an ISBN or an edition; leave it out and say so. If the course mentions "inclusive access",
   "day one access" or "first day" materials, note it: those are billed to the student unless they opt out by a
   deadline, so tell the student to check that deadline before buying elsewhere.

3. **Hunt each route.** Use the web, and the browser only where a site needs it, following
   `references/sources.md` (it lists the ASU sites and the general ones). For each book look for, in this order:
   - free: a copy the instructor posted in Canvas, an open textbook (when it is the same book or the instructor
     allows it), a library ebook, a library course reserve
   - cheaper: a rental, a used copy, a legitimate digital edition, an older edition (only when the course does
     not require the exact edition; warn that page and problem numbers may differ)
   - the baseline: the campus bookstore's new price (from the student's screenshot or the bookstore site)
   Record each route's real price, where it is, and its link. Use only prices you actually saw; when you could not
   find a price, leave that route out rather than estimating.

4. **Do the math with the script.** Write what you found to a findings file in the conversation's working folder
   (format below), then run from this Skill's folder:

   ```bash
   python3 scripts/savings.py --file <findings.json>
   ```

   The script ranks the routes, adds up the savings exactly, separates "cheapest overall" from "cheapest copy you
   keep", flags access codes and leaves out older editions the course does not allow. Use its numbers in the
   reply; never do the totals yourself. It needs no setup: it uses only Python's standard library.

5. **Reply** (see "Replies").

6. **Offer one follow-up check-in.** Prices and reserves change near the start of term. Offer one check-in and
   suggest a default: "Want me to re-check prices a week before classes start?" Create it only after the student
   says yes and picks or accepts the time. Word the check-in so it makes sense on its own later: "Textbook Hunter:
   re-check prices and library reserves for <courses>, then run the savings script with --compare and text only
   what changed." When you run it then, rebuild the findings and run
   `python3 scripts/savings.py --file <findings.json> --compare --save`.
   The first time the student accepts a check-in, also run the script once with `--save` so the check-in has
   something to compare against.

7. **Buying stays with the student.** Never buy, rent, reserve or check out anything. Give the link. If the student
   wants help, open the site in the browser, put the item in the cart only after they say yes, and hand the browser
   to them for payment.

## Findings file

```json
{
  "term": "Spring 2027",
  "books": [
    {
      "course": "CSE 230",
      "title": "Computer Systems: A Programmer's Perspective",
      "edition": "3e",
      "isbn": "",
      "status": "required",
      "access_code": false,
      "exact_edition_required": false,
      "baseline": {"label": "bookstore new", "price": 199.50, "url": "https://..."},
      "options": [
        {"route": "library_reserve", "source": "ASU Library", "price": 0, "url": "https://...", "note": "2-hour loan"},
        {"route": "used", "source": "<seller>", "price": 72.25, "url": "https://..."}
      ]
    }
  ]
}
```

- `status`: `required`, `recommended` or `optional`.
- `route`: one of `instructor_free`, `open_textbook`, `library_ebook`, `library_reserve`, `digital`, `rental`,
  `used`, `older_edition`, `new`.
- `price`: what the student would pay, `0` for free. Leave a route out if you have no real price for it.
- Optional per option: `keep` (true if the student keeps the copy; the script assumes it from the route),
  `includes_code` (true when a used, rented or digital option really comes with the access code), `note`.
- `baseline` is the bookstore's full price. If you have none, the script falls back to the dearest new copy.

To see the output format without real data, run `python3 scripts/savings.py --sample` (and `--sample --compare`
for a check-in). The sample never reads or writes the student's saved state.

## Replies

Keep each reply to a few short lines of plain text, no Markdown. Lead with the total the script printed, then one
line per book with its best route, then the links, each on its own line. If more than five books are on the list,
make a one-page PDF with the full comparison, send it, and text only the total and the three biggest savings.

Example:

```text
Found $335 in savings on your 4 books.

- ECN 212: free, it's on OpenStax
- CSE 230: $0 on library reserve, or $18 for the 2nd ed to keep
- MAT 343: needs a WebAssign code, $99 direct beats the $145 bundle

https://openstax.org/subjects/economics

Want me to re-check prices a week before classes start?
```

When the best route is a library reserve or rental, say so plainly ("2-hour loan", "return by finals"), and give
the cheapest copy to keep as well, since some students need the book at home. When the course needs an access
code, say that a used copy will not include one.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | The findings file has a wrong field (the message names it) | Fix that field and run again; do not show the error to the student |
| 3 | The findings file is missing or not valid JSON | Write the file again and rerun once |
| 4 | No books in the findings | Ask for the course codes, the syllabus or a bookstore screenshot |

- Canvas not connected and nothing sent: ask for a screenshot of the book list or the course codes, and stop.
- The syllabus lists no books: say so, and say whether the course looks like it uses only Canvas materials.
- No legal cheaper route found: say the bookstore price is the best you found, and mention renting or the
  library's regular loan if either exists.
- A site will not load: skip it, say which one you could not check, and do not guess its price.

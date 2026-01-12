"""
Data pipeline to clean, format, import, and export sample data for Author, Book, and Review.
- Import: python myapp/data_pipeline.py import
- Export CSV: python myapp/data_pipeline.py export
- Reset tables: python myapp/data_pipeline.py reset
"""

import argparse
import csv
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from myapp.models import Author, Book, Review  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "database"
EXPORT_DIR = DATA_DIR

# Ten basic fields we normalize in this pipeline.
BASIC_FIELDS = [
    "id",
    "username",
    "email",
    "full_name",
    "title",
    "body",
    "status",
    "post_id",
    "user_id",
    "created_at",
]


def _load_json(filename):
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    import json

    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _norm_text(value, fallback=""):
    if not value:
        return fallback
    return str(value).strip()


def _safe_price(post):
    reactions = post.get("reactions", {}) or {}
    likes = reactions.get("likes", 0) or 0
    dislikes = reactions.get("dislikes", 0) or 0
    views = post.get("views", 0) or 0
    raw = (views / 120) + (likes / 15) - (dislikes / 25)
    price = max(raw, 5.0)
    return Decimal(price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clean_authors(users):
    authors = []
    seen = set()
    for user in users:
        user_id = user.get("id")
        if user_id in seen:
            continue
        seen.add(user_id)
        full_name = " ".join(
            part for part in [_norm_text(user.get("firstName")), _norm_text(user.get("lastName"))] if part
        )
        name = full_name or _norm_text(user.get("username")) or f"User {user_id}"
        company = user.get("company", {}) or {}
        bio_bits = [
            _norm_text(company.get("title")),
            _norm_text(company.get("name")),
            _norm_text(user.get("university")),
        ]
        bio = " | ".join([bit for bit in bio_bits if bit]) or "No bio provided."
        authors.append(Author(id=user_id, name=name[:100], bio=bio[:500]))
    return authors


def _clean_books(posts, author_ids):
    books = []
    default_author_id = next(iter(author_ids), None)
    for post in posts:
        book_id = post.get("id")
        author_id = post.get("userId")
        if author_id not in author_ids:
            author_id = default_author_id
        title = _norm_text(post.get("title"), f"Untitled {book_id}")[:200]
        books.append(
            Book(
                id=book_id,
                title=title,
                author_id=author_id,
                price=_safe_price(post),
            )
        )
    return books


def _clean_reviews(comments, book_ids):
    reviews = []
    for comment in comments:
        book_id = comment.get("postId")
        if book_id not in book_ids:
            continue
        likes = comment.get("likes", 0) or 0
        rating = max(1, min(5, int(likes // 2) + 1))
        content = _norm_text(comment.get("body"), "No content provided.")
        reviews.append(
            Review(
                id=comment.get("id"),
                book_id=book_id,
                content=content,
                rating=rating,
            )
        )
    return reviews


def reset_tables():
    Review.objects.all().delete()
    Book.objects.all().delete()
    Author.objects.all().delete()


def import_data():
    users = _load_json("user.json")
    posts = _load_json("posts.json")
    comments = _load_json("comments.json")

    reset_tables()

    authors = _clean_authors(users)
    Author.objects.bulk_create(authors, ignore_conflicts=True)

    author_ids = set(Author.objects.values_list("id", flat=True))
    books = _clean_books(posts, author_ids)
    Book.objects.bulk_create(books, ignore_conflicts=True)

    book_ids = set(Book.objects.values_list("id", flat=True))
    reviews = _clean_reviews(comments, book_ids)
    Review.objects.bulk_create(reviews, ignore_conflicts=True)

    total = {
        "authors": Author.objects.count(),
        "books": Book.objects.count(),
        "reviews": Review.objects.count(),
    }
    print(f"Import complete: {total}")


def export_csv():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def write_csv(filename, rows, headers):
        path = EXPORT_DIR / filename
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {path}")

    author_rows = [{"id": a.id, "name": a.name, "bio": a.bio} for a in Author.objects.all()]
    book_rows = [
        {"id": b.id, "title": b.title, "author_id": b.author_id, "price": f"{b.price:.2f}"}
        for b in Book.objects.select_related("author").all()
    ]
    review_rows = [
        {"id": r.id, "book_id": r.book_id, "rating": r.rating, "content": r.content}
        for r in Review.objects.select_related("book").all()
    ]

    write_csv("authors.csv", author_rows, ["id", "name", "bio"])
    write_csv("books.csv", book_rows, ["id", "title", "author_id", "price"])
    write_csv("reviews.csv", review_rows, ["id", "book_id", "rating", "content"])


def main():
    parser = argparse.ArgumentParser(description="Data pipeline for myapp models.")
    parser.add_argument("action", choices=["import", "export", "reset"], help="Pipeline action to run.")
    args = parser.parse_args()

    if args.action == "import":
        import_data()
    elif args.action == "export":
        export_csv()
    elif args.action == "reset":
        reset_tables()
        print("Tables cleared.")


if __name__ == "__main__":
    main()

import os
import django
import random

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Author, Book, Review


def run():
    print("正在產生資料...")

    # 1. 產生 25 位作者
    authors = []
    for i in range(1, 26):
        author = Author.objects.create(name=f"作者 {i}", bio=f"這是作者 {i} 的簡介。")
        authors.append(author)

    # 2. 產生 25 本書
    books = []
    for i in range(1, 26):
        book = Book.objects.create(
            title=f"書籍 {i}",
            author=random.choice(authors),
            price=random.uniform(10, 100),
        )
        books.append(book)

    # 3. 產生 25 則評論
    for i in range(1, 26):
        Review.objects.create(
            book=random.choice(books),
            content=f"這是第 {i} 則評論內容。",
            rating=random.randint(1, 5),
        )

    print("成功！每個模型已各產生 25 筆資料。")


if __name__ == "__main__":
    run()

from application import *
import csv


db.execute('CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR UNIQUE NOT NULL, fullname VARCHAR NOT NULL '
           ',password VARCHAR CHECK(length(password) > 6) NOT NULL)')

db.execute('CREATE TABLE books (id SERIAL PRIMARY KEY,isbn VARCHAR UNIQUE NOT NULL, title VARCHAR NOT NULL,author'
           ' VARCHAR NOT NULL,year VARCHAR NOT NULL)')

db.execute('CREATE TABLE reviews (id SERIAL PRIMARY KEY, username VARCHAR REFERENCES users(username), '
           'books VARCHAR REFERENCES "books"(isbn),reviews VARCHAR NOT NULL,ratings VARCHAR NOT NULL)')

f = open("books.csv")
reader = csv.reader(f)
for isbn, title, author,year in reader:
    db.execute("INSERT INTO books (isbn, title, author,year) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn, "title": title, "author": author, 'year': year})
    print(f"Added {isbn},{title},{author},{year}")
db.commit()
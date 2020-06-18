import os
import requests
from flask import Flask, session, render_template, request, flash, redirect, url_for, jsonify, Response
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
os.environ["DATABASE_URL"] = 'postgres://rwsthezmrrypzj:81b33bc19d9c9dbfb371b5cde514e717c13d0d87c89912f725b0c5cf18527276@ec2-34-202-7-83.compute-1.amazonaws.com:5432/d8e5avgp6srogn'
os.environ['KEY'] = "cPJ01FT2PGeWhJFMKKOgg"

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['JSON_SORT_KEYS'] = False
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def encrypt(word, n):
    upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    lower = upper.lower()
    decryption = ''
    for i in word:
        if i in upper:
            j = upper.index(i) + n
            if j > (len(upper) - 1):
                j = j - (len(upper))
            decryption = decryption + upper[j]

        elif i in lower:
            j = lower.index(i) + n
            if j > (len(lower) - 1):
                j = j - (len(lower))
            decryption = decryption + lower[j]
        elif i.isdigit():
            decryption = decryption + str(9 % (int(i)+1))
        else:
            decryption = decryption + i
    return decryption


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'username' in session:
            return redirect(url_for('search'))
        return render_template('login.html')
    else:
        username = request.form.get('username')
        password1 = request.form.get('password')
        password = encrypt(password1, -22)
        x = db.execute("SELECT * FROM users WHERE username=:username AND password=:password", {
            'username': username, 'password': password}).fetchall()
        if not x:
            flash(f'Wrong username or password', 'danger')
            return render_template('login.html')
        else:
            session['username'] = username
            return redirect(url_for('search'))



@app.route("/sign_up")
def sign_up():
    return render_template('signup.html')


@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route("/add_user", methods=['POST'])
def add_user():
    fullname = request.form.get('fullname')
    username = request.form.get('username')
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')
    if password1 != password2:
        flash(f'make sure password are the same', 'danger')
        return render_template('signup.html')
    if len(password1) <= 6:
        flash(f'Password too short', 'danger')
        return render_template('signup.html')
    if (username,) in db.execute('SELECT username FROM users').fetchall():
        flash(f'Username already exist', 'danger')
        return render_template('signup.html')
    password = encrypt(password1, -22)
    db.execute("INSERT INTO users( username, fullname, password) VALUES (:username, :fullname, :password)", {
        'username': username, 'fullname': fullname, 'password': password})
    db.commit()
    flash(f'Registration successful', 'success')
    return render_template('login.html')


@app.route("/search")
def search():
    if 'username' in session:
        username = session['username']
        return render_template('search.html',username=username)
    else:
        return redirect(url_for('login'))


@app.route('/your-reviews')
def your_reviews():
    if 'username' in session:
        username = session['username']
        reviews = db.execute(" SELECT username,books,reviews,ratings,title,author,year FROM reviews JOIN books ON "
                             "books.isbn=reviews.books WHERE username=:username", {'username': username}).fetchall()
        return render_template('your_reviews.html', username=username, reviews=reviews)
    else:
        return redirect(url_for('login'))


@app.route("/books", methods=['POST'])
def books():
    if 'username' in session:
        username = session['username']
        value = request.form.get('type')
        search = request.form.get('search').lower()
        search1 = '%' + search + '%'
        if value == 'all':
            books = db.execute("SELECT * FROM books WHERE LOWER(books.isbn) LIKE :search OR LOWER(books.title)"
                               " LIKE :search OR LOWER(books.author) LIKE :search OR LOWER(books.year) LIKE :search"
                               , {'search': search1}).fetchall()
        else:
            books = db.execute("SELECT * FROM books WHERE " + value + " LIKE :search",
                               {'search': search1}).fetchall()
        return render_template('books.html', books=books, search=search, username=username)
    else:
        return redirect(url_for('login'))


@app.route("/reviews/<string:isbn>")
def reviews(isbn):
    if 'username' in session:
        username = session['username']
        isbn = str(isbn)
        details = db.execute("SELECT * FROM books WHERE isbn=:isbn", {'isbn': isbn}).fetchall()
        if not details:
            return render_template('error.html', message='Invalid isbn')
        reviews = db.execute("SELECT username,reviews,ratings FROM reviews WHERE books =:isbn",
                             {'isbn': isbn}).fetchall()
        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                           params={"key": os.getenv('KEY'), "isbns": isbn})
        if res.status_code != 200:
            rating = ['not available', 'not available']
        else:
            goodreads = res.json()
            rating = [goodreads['books'][0]['average_rating'], goodreads['books'][0]['ratings_count']]
        return render_template('reviews.html', details=details, isbn=isbn, username=username,
                               reviews=reviews, rating=rating)
    else:
        return redirect(url_for('login'))


@app.route("/add_review/<string:isbn>", methods=['POST'])
def add_review(isbn):
    if 'username' in session:
        username = session['username']
        review = request.form.get('review')
        rating = request.form.get('rating')
        check = db.execute("SELECT * FROM reviews WHERE username=:username AND books=:isbn",
                           {'username': username, 'isbn': isbn}).fetchall()
        if check:
            flash(f"you've reviewed this book already", 'danger')
            return reviews(isbn)
        else:
            db.execute("INSERT INTO reviews(username,books,reviews,ratings) VALUES(:username,:books,:reviews,:ratings)",
                       {'username': username, 'books': isbn, 'reviews': review, 'ratings': rating})
            db.commit()
            return reviews(isbn)
    else:
        return redirect(url_for('ogin'))

@app.route("/api/<string:isbn>")
def api(isbn):
    exist = db.execute("SELECT * FROM books WHERE isbn=:isbn", {'isbn': isbn}).fetchall()
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": os.getenv('KEY'), "isbns":  isbn})
    if res.status_code != 200:
        rating = ['not available', 'not available']
    else:
        goodreads = res.json()
        rating = [goodreads['books'][0]['average_rating'], goodreads['books'][0]['reviews_count']]
    if not exist:
        return jsonify({"error": "Invalid isbn"}), 404
    return jsonify({
            "title": exist[0][2],
            "author": exist[0][3],
            "year": exist[0][4],
            "isbn": exist[0][1],
            "review_count": rating[1],
            "average_score": rating[0]
        })
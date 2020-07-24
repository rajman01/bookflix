from datetime import datetime
from bookflix import db, login_manager, app
from flask_login import UserMixin
from sqlalchemy import or_, func
from itsdangerous import TimedJSONWebSignatureSerializer as serializer


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    reviews = db.relationship('Review', backref='author', lazy=True)

    def get_reset_token(self, expires=1800):
        s = serializer(app.config['SECRET_KEY'], expires)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return  User.query.get(user_id)


    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(30), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(15), nullable=False)
    reviews = db.relationship('Review', backref='book', lazy=True)

    def __repr__(self):
        return f"Book('{self.isbn}', '{self.title}', '{self.author}')"

    @staticmethod
    def search(query, type,page,per_page):
        if type == 'isbn':
            books = Book.query.filter(func.lower(Book.isbn).like(query)).paginate(page=page,per_page=per_page)
        elif type == 'title':
            books = Book.query.filter(func.lower(Book.title).like(query)).paginate(page=page,per_page=per_page)
        elif type == 'author':
            books = Book.query.filter(func.lower(Book.author).like(query)).paginate(page=page,per_page=per_page)
        elif type == 'year':
            books = Book.query.filter(func.lower(Book.year).like(query)).paginate(page=page,per_page=per_page)
        else:
            books = Book.query.filter(or_(func.lower(Book.isbn).like(query), func.lower(Book.title).like(query),
                                          func.lower(Book.author).like(query), func.lower(Book.year).like(query))).paginate(page=page,per_page=per_page)
        return books


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    review = db.Column(db.Text, nullable=False)
    rating = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_isbn = db.Column(db.String, db.ForeignKey('book.isbn'), nullable=False)

    def __repr__(self):
        return f"Review('{self.author.username}', '{self.book.isbn}', '{self.date_posted}')"

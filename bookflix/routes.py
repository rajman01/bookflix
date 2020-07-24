import os
import secrets
from PIL import Image
import requests
from flask import render_template, url_for, flash, redirect, request, current_app, abort, jsonify
from bookflix.forms import (RegistrationForm, LoginForm, UpdateAccountForm, MakeReviewForm, ResetPasswordForm,
							RequestResetForm)
from bookflix.models import User, Book, Review
from bookflix import app, bcrypt, db, mail
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import and_
from flask_mail import Message


@app.route("/")
@app.route('/home')
def home():
	page = request.args.get('page', 1, type=int)
	reviews = Review.query.order_by(Review.date_posted.desc()).paginate(page=page, per_page=5)
	return render_template('home.html', title='Home', reviews=reviews)


@app.route("/about")
def about():
	return render_template('about.html', title='About')


@app.route('/register', methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = RegistrationForm()
	if form.validate_on_submit():
		hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		user = User(username=form.username.data, email=form.email.data, password=hashed_password)
		db.session.add(user)
		db.session.commit()
		flash(f'Your account has been created! You are now able to login', 'success')
		return redirect(url_for('login'))
	return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user and bcrypt.check_password_hash(user.password, form.password.data):
			login_user(user, remember=form.remember.data)
			next_page = request.args.get('next')
			return redirect(next_page) if next_page else redirect(url_for('home'))
		else:
			flash('Login Unsuccessful. Please check email and password', 'danger')
	return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('login'))


def save_picture(form_picture):
	random_hex = secrets.token_hex(8)
	f_name, f_ext = os.path.split(form_picture.filename)
	picture_fn = random_hex + f_ext
	picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)
	output_size = (200,200)
	i = Image.open(form_picture)
	i.thumbnail(output_size)
	i.save(picture_path)
	return picture_fn


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
	form = UpdateAccountForm()
	if form.validate_on_submit():
		if form.picture.data:
			picture_file = save_picture(form.picture.data)
			current_user.image_file = picture_file
		current_user.username = form.username.data
		current_user.email = form.email.data
		db.session.commit()
		flash('your account has been updated!', 'success')
		return redirect(url_for('account'))
	elif request.method == 'GET':
		form.email.data = current_user.email
		form.username.data = current_user.username
	image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
	return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route('/search', methods=['GET','POST'])
def search():
	if request.method == 'GET':
		search = request.args.get('search')
		type = request.args.get('type')
		if not search or not type:
			abort(404)
		type = type.lower()
	else:
		search = request.form.get('search')
		type = request.form.get('type')
		if not search or not type:
			abort(404)
		type = type.lower()
	page = request.args.get('page', 1, type=int)
	search_data = search.lower()
	query = '%' + search_data + '%'
	books = Book.search(query, type, page=page, per_page=15)
	return render_template('search.html', title=search_data, books=books, search=search,type=type)


@app.route('/review/new', methods=['GET', 'POST'])
@login_required
def new_review():
	form = MakeReviewForm()
	books = Book.query.all()
	if form.validate_on_submit():
		check = Review.query.filter(and_(current_user == Review.author,form.isbn.data == Review.book_isbn)).first()
		if check:
			flash("Can't review a book more than once", "warning")
			return redirect(url_for('new_review'))
		review = Review(review=form.content.data, rating=form.rating.data, author=current_user, book_isbn=form.isbn.data)
		db.session.add(review)
		db.session.commit()
		flash(f'you made a review about', 'success')
		return redirect(url_for('home'))
	return render_template('make_review.html', title='New Review', form=form, books=books, legend='Make Review')


@app.route('/review/<int:review_id>')
def review(review_id):
	previous = request.args.get('previous')
	review = Review.query.get_or_404(review_id)
	return render_template('review.html', title=review.author.username + '-' + review.book.title, review=review,
						   previous=previous)


@app.route('/review/<int:review_id>/update',methods=['GET','POST'])
@login_required
def update_review(review_id):
	review = Review.query.get_or_404(review_id)
	previous = request.args.get('previous', url_for('review', review_id=review_id))
	if review.author != current_user:
		abort(403)
	form = MakeReviewForm()
	form.submit.label.text = 'Update'
	if request.method == 'POST':
		review.review = form.content.data
		review.rating = form.rating.data
		db.session.commit()
		flash('Your review has been updated', 'success')
		return redirect(previous)
	elif request.method == 'GET':
		form.isbn.render_kw = {'disabled':'true'}
		form.isbn.data = review.book_isbn
		form.content.data = review.review
		form.rating.data = review.rating
	return  render_template('make_review.html', title='Update Review', form=form, legend='Update Review')


@app.route('/review/<int:review_id>/delete',methods=['POST'])
@login_required
def delete_review(review_id):
	previous = request.args.get('previous',url_for('home'))
	review = Review.query.get_or_404(review_id)
	if review.author != current_user:
		abort(403)
	db.session.delete(review)
	db.session.commit()
	return redirect(previous)


@app.route('/book_review/<int:book_id>',methods=['GET','POST'])
@login_required
def book_review(book_id):
	book = Book.query.get_or_404(book_id)
	page = request.args.get('page', 1, type=int)
	reviews = Review.query.filter_by(book=book) \
		.order_by(Review.date_posted.desc()) \
		.paginate(page=page, per_page=5)
	form = MakeReviewForm()
	form.isbn.data = book.isbn
	form.submit.label.text = 'Add'
	web = os.getenv('GOODREADS')
	goodreads = requests.get(web, params={"key": os.getenv('KEY'), "isbns": book.isbn})
	if goodreads.status_code != 200:
		rating = ['not available', 'not available']
	else:
		goodreads_json = goodreads.json()
		rating = [goodreads_json['books'][0]['average_rating'], goodreads_json['books'][0]['reviews_count']]
	if form.validate_on_submit():
		check = Review.query.filter(and_(current_user == Review.author, book.isbn == Review.book_isbn)).first()
		if check:
			flash("Can't review a book more than once", "warning")
			return redirect(url_for('book_review',book_id=book_id))
		review = Review(review=form.content.data, rating=form.rating.data, author=current_user,
						book_isbn=book.isbn)
		db.session.add(review)
		db.session.commit()
		flash('Your review as been added', 'success' )
		return redirect(url_for('book_review', book_id=book_id))
	return render_template('book_review.html', reviews=reviews,title=book.title, book=book, form=form,
						   legend='Add Review', previous=url_for('book_review', book_id=book_id), rating = rating)


@app.route('/user/<int:user_id>')
def user_reviews(user_id):
	page = request.args.get('page', 1, type=int)
	user = User.query.get_or_404(user_id)
	reviews = Review.query.filter_by(author=user)\
		.order_by(Review.date_posted.desc())\
		.paginate(page=page, per_page=5)
	return render_template('user_reviews.html', title=user.username, reviews=reviews, user=user,
						previous=url_for('user_reviews',user_id=user_id))


def send_reset_email(user):
	token = user.get_reset_token()
	msg = Message('Password Reset Request',sender='noreply@demo.com', recipients=[user.email])
	msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request, then simply ignore this email and no changes will be made
'''
	mail.send(msg)


@app.route('/reset_password', methods=['GET','POST'])
def reset_request():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = RequestResetForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		send_reset_email(user)
		flash('An email has been sent with instruction to reset your password', 'info')
		return redirect(url_for('login'))
	return 	render_template('reset_request.html', form=form, title='Reset Request')


@app.route('/reset_password/<token>', methods=['GET','POST'])
def reset_token(token):
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	user = User.verify_reset_token(token)
	if user is None:
		flash('That is an invalid or expired token', 'warning')
		return redirect(url_for('reset_request'))
	form = ResetPasswordForm()
	if form.validate_on_submit():
		hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		user.password = hashed_password
		db.session.commit()
		flash(f'Your password has been update! You are now able to login','success')
		return redirect(url_for('login'))
	return	render_template('reset_token.html', form=form, title='Reset Request')


@app.route("/api/<string:isbn>")
def api(isbn):
	book = Book.query.filter_by(isbn=isbn).first()
	web = os.getenv('GOODREADS')
	goodreads = requests.get(web, params={"key": os.getenv('KEY'), "isbns": isbn})
	if goodreads.status_code != 200:
		rating = ['not available', 'not available']
	else:
		goodreads_json = goodreads.json()
		rating = [goodreads_json['books'][0]['average_rating'], goodreads_json['books'][0]['reviews_count']]
	if not book:
		return jsonify({"error": "Invalid isbn"}), 404
	return jsonify({"title": book.title, "author": book.author, "year": book.year, "isbn": book.isbn,
					"review_count": rating[1], "average_score": rating[0]})


@app.errorhandler(404)
def error_404(error):
	return render_template('404.html'), 404


@app.errorhandler(403)
def error_403(error):
	return render_template('403.html'), 403


@app.errorhandler(500)
def error_500(error):
	return render_template('500.html'), 500
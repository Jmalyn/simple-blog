from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from sqlalchemy import ForeignKey
from functools import wraps
import hashlib #used for md5, hashing the email address for gravatar in comment
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("secret_key")
ckeditor = CKEditor(app)
Bootstrap(app)


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///comments.db'


class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(250), nullable = False)
    posts = relationship("BlogPost", back_populates = "author")
    comments = relationship("Comment", back_populates = "comment_author")
db.create_all()

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    #author = db.Column(db.String(250), nullable=False) -> remove this since we link author to parent table Users
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, ForeignKey('users.id'))
    author = relationship("Users", back_populates = "posts")
db.create_all()

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key = True)
    text = db.Column(db.Text, nullable = False)
    comment_author_id = db.Column(db.Integer, ForeignKey("users.id"))
    comment_author = relationship("Users", back_populates = "comments")
db.create_all()

#Gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()

    if current_user.is_authenticated: # if user is logged in and authenticated
        id = current_user.id

    else:
        id = None
        #print(id)
    return render_template("index.html", all_posts=posts, id = id)


@app.route('/register', methods = ["POST", "Get"])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        email = request.form["email"]
        user = db.session.query(Users).filter_by(email = email).first() #check if a user with that email already exists
        if user: #if that email exists:
            flash("You are already registered, login instead.")
            return redirect(url_for("login"))
        else:
            name = request.form["name"]
            password = request.form["password"]
            hashed_pw = generate_password_hash(password, method= "pbkdf2:sha256", salt_length=8)
            new_user = Users(email = email, name = name, password = hashed_pw)
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)

            registered_user = db.session.query(Users).filter_by(email=email).first()  # get the data of the new user with that email
            return redirect(url_for('get_all_posts', id = registered_user.id))
    return render_template("register.html", form = register_form)


@app.route('/login', methods = ["POST", "GET"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = request.form["email"]
        password = request.form["password"]
        user1 = db.session.query(Users).filter_by(email = email).first()
        #print(user1.id)
        if not user1:
            flash("That email does not exist in our system, please register.")
        else:
            if check_password_hash(user1.password, password):
                login_user(user1)
                return redirect(url_for("get_all_posts", id = user1.id))
            else:
                flash("Password incorrect. Please try again.")
    return render_template("login.html", form = login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods = ["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()
    #hashed_email = None
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text = comment_form.comment.data,
                comment_author = current_user
            )
            #email_to_hash = current_user.email.encode("UTF-8")
            #hashed_email = hashlib.md5((((email_to_hash)).strip()).lower())

            db.session.add(new_comment)
            db.session.commit()
        #return render_template("post.html", post = requested_post, form = comment_form)
        else:
            flash("Please login first.")
            return redirect(url_for("login"))
    if current_user.is_authenticated: #this is for the "edit" button to not appear if the user_is is not 1, if cndition is on post.html
        id = current_user.id
    else:
        id = None
    comments = Comment.query.all()
    email = requested_post.author.email
    return render_template("post.html", post=requested_post, id = id, form = comment_form, all_comments = comments, email = email)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

# @app.errorhandler(403)
# def forbidden(e):
#     return (str(e))

def admin_only(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        else:
            return function(*args, **kwargs)
    #wrapper.__name__ = function.__name__ #renaming the wrapper function otherwise it will give an error: function mapping is overwriting an existing endpoint function
    return wrapper

#Angela's solution:
#Create admin-only decorator

# from functools import wraps
# from flask import abort
#
# def admin_only(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         #If id is not 1 then return abort with 403 error
#         if current_user.id != 1:
#             return abort(403)
#         #Otherwise continue with the route function
#         return f(*args, **kwargs)
#     return decorated_function

@app.route("/new-post", methods = ["POST", "GET"])
@admin_only #add this so that the "Create Post button will not show even if the user (who is not the admin/ id is not 1) will manually type /new-post in the url
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author =current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)

@app.route("/edit-post/<int:post_id>", methods = ["POST", "GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm( #doing this to pre populate the fields in the form
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author_id,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        #post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    #app.run(host='0.0.0.0', port=5000)
    app.run(debug = True)
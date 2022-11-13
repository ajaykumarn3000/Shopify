from flask import Flask, render_template, url_for, redirect, flash, request
from forms import RegisterFormEmail, RegisterFormPassword, RegisterFormOTP, LoginForm
from flask_bootstrap import Bootstrap
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequestKeyError
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from sqlalchemy.types import TypeDecorator
import datetime as dt
import json
import random
import os
import stripe

# This is your test secret API key.
stripe.api_key = os.environ.get("API_KEY")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "random string"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = EMAIL_ID = "ajaykumar.shopify.mails@gmail.com"
app.config['MAIL_PASSWORD'] = os.environ.get('password')
app.config["testing"] = False
app.config["MAIL_SUPPRESS_SEND"] = False
mail = Mail(app)

db = SQLAlchemy(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

YOUR_DOMAIN = 'https://shopify-nwlv.onrender.com'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class TextPickleType(TypeDecorator):
    impl = sqlalchemy.TEXT()

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class Json(TypeDecorator):
    impl = sqlalchemy.String

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)


# noinspection PyUnresolvedReferences
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    cart = db.Column(db.JSON(), nullable=False)
    phone = db.Column(db.Integer(), nullable=True)
    address = db.Column(db.JSON(), nullable=True)


# noinspection PyUnresolvedReferences
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(), nullable=False)
    price = db.Column(db.Float(), nullable=False)
    discount_price = db.Column(db.Float(), nullable=False)
    delivery = db.Column(db.Float(), nullable=False)
    warranty = db.Column(db.String(), nullable=False)
    highlight = db.Column(Json(), nullable=True)
    description = db.Column(db.String(), nullable=True)
    specifications = db.Column(db.JSON(), nullable=True)
    payment_id = db.Column(db.String(), nullable=False)


db.create_all()


otp = ""
email = ""


def send_otp():
    global otp
    otp = ""
    for _ in range(6):
        otp += str(random.randint(0, 9))

    msg = Message(f"Shopify: Email Verification OTP [{otp}]", sender=EMAIL_ID, recipients=[email])
    msg.html = f'''<h2>OTP for you Email Verification is-</h2>\n<h1>{otp}</h1>\n\n<h4>Thanks and Regards,</h4><h4>Shopify.</h4>'''
    mail.send(msg)


def order_mail(name, phone, product, address):
    msg = Message(f"You Received an Order!!", sender=EMAIL_ID, recipients=[os.environ.get("ADMIN_MAIL")])
    order_product = ""
    for item in product:
        order_product += f"<li><h2>{item[1]} X {item[0].name}</h2></li>"
    deliver_to = ""
    for key in address:
        deliver_to += f"<h3><strong>{key}: </strong>{address[key]}</h3>"
    msg.html = f'''<h3>You Received an Order of:</h3>\n<ul>{order_product}</ul>\n<h3>From: {name} {phone}</h3>\n\n<h3>Deliver To: \n{deliver_to}'''
    mail.send(msg)


@app.route('/register', methods=['GET', 'POST'])
def register():
    global email
    email_form = RegisterFormEmail()
    otp_form = RegisterFormOTP()
    password_form = RegisterFormPassword()

    if email_form.validate_on_submit():
        email = email_form.email.data
        if User.query.filter_by(email=email).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        send_otp()
        return render_template("register.html", otp_form=otp_form)
    elif otp_form.validate_on_submit():
        user_otp = ""
        user_otp += otp_form.otp1.data
        user_otp += otp_form.otp2.data
        user_otp += otp_form.otp3.data
        user_otp += otp_form.otp4.data
        user_otp += otp_form.otp5.data
        user_otp += otp_form.otp6.data


        if user_otp == otp:
            return render_template("register.html", password_form=password_form)
        else:
            flash("OTP is incorrect.")
            return render_template("register.html", otp_form=otp_form)
    elif password_form.validate_on_submit():
        username = password_form.name.data
        hash_and_salted_password = generate_password_hash(
            password_form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(name=username, email=email, password=hash_and_salted_password, cart={},
                        address={"name": "", "phone": "", "pincode": "", "locality": "", "address": "", "city": "",
                                 "state": "", "landmark": "", "alt-phone": ""})
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))

    return render_template("register.html", email_form=email_form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html", login_form=login_form)


@app.route('/', methods=['GET'])
def home():
    all_products = Product.query.all()

    return render_template("index.html", current_user=current_user, products=all_products)


@app.route('/product/<product_id>', methods=['GET'])
def product(product_id):
    item = Product.query.get(product_id)
    return render_template("product.html", current_usera=current_user, product=item)


@app.route('/cart', methods=['GET'])
@login_required
def cart():
    cart_data = []
    total_price = 0
    total_discount_price = 0
    delivery_date = (dt.datetime.today().date() + dt.timedelta(days=7)).strftime("%a %b %d")
    for key in current_user.cart:
        number = current_user.cart[key]
        cart_product = Product.query.get(int(key))
        price = cart_product.price * number
        discount_price = cart_product.discount_price * number
        total_price += price
        total_discount_price += discount_price

        cart_data.append({
            "product": cart_product,
            "number": number,
            "price": price,
            "discount_price": discount_price,
            "delivery_date": delivery_date
        })
    total_data = {
        "total_price": total_price,
        "total_discount_price": total_discount_price,
        "delivery_charges": 0
    }
    return render_template("cart.html", cart_data=cart_data, total_data=total_data)


@app.route('/add-to-cart/<product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    user_cart = {}
    for key in current_user.cart:
        user_cart[key] = current_user.cart[key]
    if product_id in user_cart:
        user_cart[product_id] += 1
    else:
        user_cart[product_id] = 1

    current_user.cart = user_cart
    db.session.commit()
    return redirect(url_for("product", product_id=product_id))


@app.route("/add-one/<product_id>/<place>", methods=["POST", "GET"])
@login_required
def add_one(product_id, place):
    user_cart = {}
    for key in current_user.cart:
        user_cart[key] = current_user.cart[key]
    if not user_cart[product_id] >= 4:
        user_cart[product_id] += 1
    else:
        user_cart[product_id] = 4

    current_user.cart = user_cart
    db.session.commit()
    return redirect(url_for(place))


@app.route("/remove-one/<product_id>/<place>", methods=["POST", "GET"])
@login_required
def remove_one(product_id, place):
    user_cart = {}
    for key in current_user.cart:
        user_cart[key] = current_user.cart[key]

    if not user_cart[product_id] <= 0:
        user_cart[product_id] -= 1
    else:
        del user_cart[product_id]

    current_user.cart = user_cart
    db.session.commit()
    return redirect(url_for(place))


@app.route("/remove-from-cart/<product_id>/<place>", methods=["POST", "GET"])
@login_required
def remove_from_cart(product_id, place):
    user_cart = {}
    for key in current_user.cart:
        user_cart[key] = current_user.cart[key]
    del user_cart[product_id]

    current_user.cart = user_cart
    db.session.commit()
    return redirect(url_for(place))


@app.route('/checkout/<mode>', methods=['GET', 'POST'])
@login_required
def checkout(mode):
    try:
        form = request.args["form"]
    except BadRequestKeyError:
        form = "login"
    cart_data = []
    total_price = 0
    total_discount_price = 0
    total_packaging_price = 0
    delivery_date = (dt.datetime.today().date() + dt.timedelta(days=7)).strftime("%a %b %d")
    if mode == "cart":
        for key in current_user.cart:
            number = current_user.cart[key]
            cart_product = Product.query.get(int(key))
            price = cart_product.price * number
            discount_price = cart_product.discount_price * number
            total_price += price
            total_packaging_price += 29 * number
            total_discount_price += discount_price
            cart_data.append({
                "product": cart_product,
                "number": number,
                "price": price,
                "discount_price": discount_price,
                "delivery_date": delivery_date
            })
        total_data = {
            "total_price": total_price,
            "total_discount_price": total_discount_price,
            "delivery_charges": 0,
            "packaging_charges": total_packaging_price
        }
    else:
        mode = int(mode)
        product = Product.query.get(mode)
        cart_data.append({
            "product": product,
            "number": 1,
            "price": product.price,
            "discount_price": product.discount_price,
            "delivery_date": delivery_date
        })
        total_data = {
            "total_price": product.price,
            "total_discount_price": product.discount_price,
            "delivery_charges": 0,
            "packaging_charges": 49
        }
    return render_template("checkout.html", cart_data=cart_data, total_data=total_data, current_user=current_user,
                           form=form, mode=mode)


@app.route('/login-checkout/<mode>', methods=['POST'])
def login_checkout(mode):
    try:
        phone = request.form["phone"]
        current_user.phone = int(request.form["phone"])
        db.session.commit()
        return redirect(url_for('checkout', form="address", mode=mode))

    except BadRequestKeyError:
        return redirect(url_for('checkout', form="address", mode=mode))


@app.route("/address-checkout/<mode>", methods=['POST'])
def address_checkout(mode):
    try:
        address_dict = {}
        for key in request.form:
            address_dict[key] = request.form[key]
        current_user.address = address_dict
        db.session.commit()
        return redirect(url_for('checkout', form="product", mode=mode))
    except BadRequestKeyError:
        return redirect(url_for('checkout', form="address", mode=mode))


@app.route('/create-checkout-session/<mode>', methods=['POST'])
@login_required
def create_checkout_session(mode):
    if mode == "cart":
        user_cart = current_user.cart
        items = []
        packing_no = 0
        for key in user_cart:
            payment_link = Product.query.get(int(key)).payment_id
            quantity = user_cart[key]
            packing_no += int(quantity)
            items.append({
                # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                'price': payment_link,
                'quantity': quantity,
            })
        items.append({
            "price": "price_1M3FtgSIyWOujbWBjB0QFVGD",
            "quantity": packing_no
        })
    else:
        payment_link = Product.query.get(int(mode)).payment_id
        items = [
            {
                # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                'price': payment_link,
                "quantity": 1,
            },
            {
                'price': "price_1M3FtgSIyWOujbWBjB0QFVGD",
                "quantity": 1,
            }
        ]
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=items,
            mode='payment',
            success_url=YOUR_DOMAIN + f'/success/{mode}',
            cancel_url=YOUR_DOMAIN + f'/cancel/{mode}',
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)


@app.route('/success/<mode>', methods=['GET'])
@login_required
def success(mode):
    if mode == "cart":
        cart_list = []
        user = User.query.get(int(current_user.id))
        for key in user.cart:
            product = Product.query.get(int(key))
            cart_list.append([product, user.cart[key]])
        user.cart = {}
        db.session.commit()
    else:
        product = Product.query.get(int(mode))
        cart_list = [[product, 1]]

    order_mail(product=cart_list, name=current_user.name, phone=current_user.phone, address=current_user.address)
    return render_template("success.html")


@app.route('/cancel/<mode>', methods=['GET'])
@login_required
def cancel(mode):
    return render_template("cancel.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/logout-n-login")
def logout_n_login():
    logout_user()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run()

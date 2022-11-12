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
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

db = SQLAlchemy(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

YOUR_DOMAIN = 'http://127.0.0.1:5000'


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
        print(email, otp)
        return render_template("register.html", otp_form=otp_form)
    elif otp_form.validate_on_submit():
        user_otp = ""
        user_otp += otp_form.otp1.data
        user_otp += otp_form.otp2.data
        user_otp += otp_form.otp3.data
        user_otp += otp_form.otp4.data
        user_otp += otp_form.otp5.data
        user_otp += otp_form.otp6.data
        print(user_otp, otp)

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


@app.route('/setup', methods=['GET'])
def setup():
    category = "mobile"
    name = "APPLE iPhone 13 Pro Max"
    image = "https://rukminim1.flixcart.com/image/832/832/ktketu80/mobile/3/e/o/iphone-13-pro-max-mll63hn-a-apple-original-imag6vpgwfgxdsj6.jpeg?q=70"
    price = 169900.0
    discount_price = 159900.0
    delivery = 0.0
    warranty = "Brand Warranty for 1 Year"
    highlight = ['512 GB ROM', '17.02 cm (6.7 inch) Super Retina XDR Display', '12MP + 12MP + 12MP | 12MP Front Camera',
                 'A15 Bionic Chip Processor']
    description = "iPhone 13. boasts an advanced dual-camera system that allows you to click mesmerising pictures with immaculate clarity. Furthermore, the lightning-fast A15 Bionic chip allows for seamless multitasking, elevating your performance to a new dimension. A big leap in battery life, a durable design, and a bright Super Retina XDR display facilitate boosting your user experience."
    specifications = {
        'General': {'In The Box': 'iPhone, USB-C to Lightning Cable, Documentation', 'Model Number': 'MND03HN/A',
                    'Model Name': 'iPhone 13 Pro Max', 'Color': 'Alpine Green', 'Browse Type': 'Smartphones',
                    'SIM Type': 'Dual Sim', 'Hybrid Sim Slot': 'No', 'Touchscreen': 'Yes', 'OTG Compatible': 'No',
                    'Quick Charging': 'Yes',
                    'Sound Enhancements': 'Dolby Digital (AC-3), Dolby Digital Plus (E-AC-3), Dolby Atmos and Audible (Formats 2, 3, 4, Audible Enhanced Audio, AAX and AAX+), Spatial Audio Playback'},
        'Display Features': {'Display Size': '17.02 cm (6.7 inch)', 'Resolution': '2778 x 1284 Pixels',
                             'Resolution Type': 'Super Retina XDR Display', 'Display Type': 'Super Retina XDR Display',
                             'Other Display Features': 'Super Retina XDR Display, 6.7 inch (Diagonal) All screen OLED Display, ProMotion Technology with Adaptive Refresh Rates up to 120Hz, HDR Display, True Tone, Wide Colour (P3), Haptic Touch, 20,00,000:1 Contrast Ratio (Typical), 1000 nits max Brightness (Typical), 1,200 nits max Brightness (HDR), Fingerprint-resistant Oleophobic Coating, Support for Display of Multiple Languages and Characters Simultaneously'},
        'Other Details': {'Smartphone': 'Yes', 'SIM Size': 'Nano + eSIM', 'Mobile Tracker': 'Yes',
                          'Removable Battery': 'No', 'SMS': 'Yes', 'Graphics PPI': '458 PPI',
                          'Sensors': 'Face ID, LiDAR Scanner, Barometer, Three axis Gyro, Accelerometer, Proximity Sensor, Ambient Light Sensor',
                          'Browser': 'Safari',
                          'Other Features': 'Splash, Water and Dust Resistant IP68 Rated (Maximum Depth of 6 metres up to 30 minutes) under IEC Standard 60529, Face ID Enabled by TrueDepth Camera for Facial Recognition, Compatible with MagSafe Accessories and Wireless Chargers',
                          'GPS Type': 'Built-in GPS, GLONASS, Galileo, QZSS and BeiDou'}}
    payment_id = "price_1M2zHdSIyWOujbWBsu8Rps8C"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "mobile"
    name = "APPLE iPhone 13"
    image = "https://rukminim1.flixcart.com/image/832/832/ktketu80/mobile/a/m/7/iphone-13-mlpj3hn-a-apple-original-imag6vpyk3w4zarg.jpeg?q=70"
    price = 79900.0
    discount_price = 75990.0
    delivery = 0.0
    warranty = "Brand Warranty for 1 Year"
    highlight = ['256 GB ROM', '15.49 cm (6.1 inch) Super Retina XDR Display', '12MP + 12MP | 12MP Front Camera',
                 'A15 Bionic Chip Processor']
    description = "iPhone 13. boasts an advanced dual-camera system that allows you to click mesmerising pictures with immaculate clarity. Furthermore, the lightning-fast A15 Bionic chip allows for seamless multitasking, elevating your performance to a new dimension. A big leap in battery life, a durable design, and a bright Super Retina XDR display facilitate boosting your user experience."
    specifications = {
        'General': {'In The Box': 'iPhone, USB-C to Lightning Cable, Documentation', 'Model Number': 'MLQ93HN/A',
                    'Model Name': 'iPhone 13', 'Color': 'Red', 'Browse Type': 'Smartphones', 'SIM Type': 'Dual Sim',
                    'Hybrid Sim Slot': 'No', 'Touchscreen': 'Yes', 'OTG Compatible': 'No', 'Quick Charging': 'Yes',
                    'Sound Enhancements': 'Dolby Digital (AC‑3), Dolby Digital Plus (E‑AC‑3), Dolby Atmos and Audible (formats 2, 3, 4, Audible Enhanced Audio, AAX and AAX+), Spatial Audio Playback'},
        'Display Features': {'Display Size': '15.49 cm (6.1 inch)', 'Resolution': '2532 x 1170 Pixels',
                             'Resolution Type': 'Super Retina XDR Display', 'Display Type': 'Super Retina XDR Display',
                             'Other Display Features': 'Super Retina XDR Display, 6.1‑inch (Diagonal) All‑screen OLED Display, HDR Display, True Tone, Wide Colour (P3), Haptic Touch, 20,00,000:1 Contrast Ratio (Typical), 800 nits max Brightness (Typical), 1,200 nits max Brightness (HDR), Fingerprint-resistant Oleophobic Coating, Support for Display of Multiple Languages and Characters Simultaneously'},
        'Other Details': {'Smartphone': 'Yes', 'SIM Size': 'Nano + eSIM', 'Mobile Tracker': 'Yes',
                          'Removable Battery': 'No', 'SMS': 'Yes', 'Graphics PPI': '460 PPI',
                          'Sensors': 'Face ID, Barometer, Three‑axis Gyro, Accelerometer, Proximity Sensor, Ambient Light Sensor',
                          'Browser': 'Safari',
                          'Other Features': 'Splash, Water and Dust Resistant IP68 Rated (Maximum Depth of 6 metres up to 30 minutes) under IEC Standard 60529, Face ID Enabled by TrueDepth Camera for Facial Recognition, Compatible with MagSafe Accessories and Wireless Chargers',
                          'GPS Type': 'Built-in GPS, GLONASS, Galileo, QZSS and BeiDou'}}
    payment_id = "price_1M3G4qSIyWOujbWBF9Pf60tr"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "mobile"
    name = "SAMSUNG Galaxy S22 Ultra 5G"
    image = "https://rukminim1.flixcart.com/image/832/832/xif0q/mobile/g/h/2/-original-imaggj68pbbezxcr.jpeg?q=70"
    price = 114900.0
    discount_price = 107000.0
    delivery = 0.0
    warranty = "Brand Warranty for 1 Year"
    highlight = ['12 GB RAM | 256 GB ROM', '17.27 cm (6.8 inch) Quad HD+ Display',
                 '108MP + 12MP + 10MP + 10MP | 40MP Front Camera', '5000 mAh Lithium-ion Battery',
                 'Octa Core Processor']
    description = "The first Galaxy S with embedded S Pen. Write comfortably like pen on paper, turn quick notes into legible text and use Air Actions to control your phone remotely. Improved latency in Samsung Notes makes every pen stroke feel as natural as ink on paper - and you can convert those hastily written ideas into legible text.5G Ready powered by Galaxy's first 4nm processor. Our fastest, most powerful chip ever. That means, a faster CPU and GPU compared to Galaxy S21 Ultra."
    specifications = {'General': {'In The Box': 'Handset, Ejection Pin, Data Cable, Quick Start Guide',
                                  'Model Number': 'SM-S908EZGGINU', 'Model Name': 'Galaxy S22 Ultra 5G',
                                  'Color': 'Green', 'Browse Type': 'Smartphones', 'SIM Type': 'Dual Sim',
                                  'Hybrid Sim Slot': 'No', 'Touchscreen': 'Yes', 'OTG Compatible': 'Yes',
                                  'Quick Charging': 'Yes'},
                      'Display Features': {'Display Size': '17.27 cm (6.8 inch)', 'Resolution': '3088 x 1440 Pixels',
                                           'Resolution Type': 'Quad HD+', 'GPU': 'Qualcomm Adreno 730',
                                           'Display Type': 'Dynamic AMOLED 2X Display', 'HD Game Support': 'Yes'},
                      'Other Details': {'Smartphone': 'Yes', 'SIM Size': 'Nano SIM', 'Social Networking Phone': 'Yes',
                                        'Instant Message': 'Yes', 'Removable Battery': 'No', 'MMS': 'Yes', 'SMS': 'Yes',
                                        'Keypad': 'No', 'Voice Input': 'Yes', 'Predictive Text Input': 'Yes',
                                        'Sensors': 'Accelerometer, Barometer, Fingerprint Sensor, Gyro Sensor, Geomagnetic Sensor, Hall Sensor, Light Sensor, Proximity Sensor',
                                        'Games': 'Multi',
                                        'Other Features': 'Wireless Charging, Fast Charging, Water Resistant'}}
    payment_id = "price_1M2zIcSIyWOujbWBCeUiXMTN"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "mobile"
    name = "OnePlus 10 Pro 5G"
    image = "https://rukminim1.flixcart.com/image/832/832/xif0q/mobile/5/f/n/-original-imaggcee7yprwrhx.jpeg?q=70"
    price = 65999.0
    discount_price = 60999.0
    delivery = 0.0
    warranty = "Brand Warranty for 1 Year"
    highlight = ['8 GB RAM | 128 GB ROM', '17.02 cm (6.7 inch) Display', '48MP Rear Camera', '5000 mAh Battery']
    description = "Camera: 48MP Main Camera with Sony IMX 789 Lens (OIS enabled), 50MP Ultra-wide angle camera & 8MP Tele photo lens; Front (Selfie) Camera: 32MP; Flash: Dual LED Camera Features: Hasselblad Camera for Mobile, Nightscape, Ultra HDR, Smart Scene Recognition, Portrait Mode, Pro Mode, Panorama Mode, Tilt-Shift mode, Long Exposure Mode, 150� Wide angle Mode, Dual-View Video, Movie Mode, Xpan Mode, Filters, Super Stable, Video Nightscape, Video HDR, Video Portrait, Focus Tracking, Timelapse Display: 6.7 Inches; 120 Hz QHD+ Fluid AMOLED with LTPO; Resolution: 3216 x 1440; Aspect Ratio: 20:9 Display Features: Nature tone display, Video colour enhancer, Colour personalization, Colour vision enhancement, Auto brightness, Manual brightness, Screen colour temperature, Bright HDR video mode, Night Mode, Multi-brightness colour calibration, Vibrant Colour Effect Pro, Ultra high resolution video Operating System: Oxygen OS based on Android 12 Processor: Qualcomm Snapdragon 8 Gen 1 Battery & Charging: 5000 mAh with 80W SuperVOOC In-Display Fingerprint Sensor Alexa Hands-Free capable: Download the Alexa app to use Alexa hands-free. Play music, make calls, hear news, open apps, navigate, and more, all using just your voice, while on-the-go."
    specifications = {'General': {
        'In The Box': 'Handset, 80W SUPERVOOC Power Adapter::Type-C Cable::Quick Start Guide::Welcome Letter::Safety Information and Warranty Card::Screen Protector (pre-applied)::Protective Case::SIM Tray Ejector',
        'Model Number': 'NE2211', 'Model Name': '10 Pro 5G', 'Color': 'Volcanic Black', 'Browse Type': 'Smartphones',
        'SIM Type': 'Dual Sim', 'Hybrid Sim Slot': 'yes', 'Touchscreen': 'Yes', 'OTG Compatible': 'Yes'},
                      'Display Features': {'Display Size': '17.02 cm (6.7 inch)', 'Resolution': '3216 x 1440 Pixels'},
                      'Os & Processor Features': {'Operating System': 'Android 12', 'Processor Core': 'Nano SIM',
                                                  'Social Networking Phone': 'Dual Core',
                                                  'Primary Clock Speed': '2.4 GHz'}}
    payment_id = "price_1M2zJBSIyWOujbWBCovcNaYT"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "mobile"
    name = "Nothing Phone (1) 5G"
    image = "https://rukminim1.flixcart.com/image/832/832/l5h2xe80/mobile/5/x/r/-original-imagg4xza5rehdqv.jpeg?q=70"
    price = 42999.0
    discount_price = 35999.0
    delivery = 0.0
    warranty = "Brand Warranty for 1 Year"
    highlight = ['12 GB RAM | 256 GB ROM', '16.64 cm (6.55 inch) Full HD+ Display', '50MP + 50MP | 16MP Front Camera',
                 '4500 mAh Lithium-ion Battery', 'Qualcomm Snapdragon 778G+ Processor',
                 'Meet the Glyph Interface. A New Way to Communicate',
                 '1 Billion Colours, True-to-Life Full HD Flexible OLED Display with HDR10+ for Richer Colour and Deeper Contrasts.']
    description = "The Nothing Phone (1) boasts an elegant style that comes to life with beautiful symbols to enable an enriched connection between you and your device. Moreover, its simplistic design ensures that you are never out of the limelight wherever you go. The innovative Glyph Interface of the Nothing smartphone lays the path for a one-of-a-kind sort of communication. Furthermore, distinct light patterns alert you to incoming calls, app alerts, charging status, and other information."
    specifications = {
        'General': {'In The Box': 'Handset, USB-C Cable, Sim Tray Ejector, Safety Information and Warranty Card',
                    'Model Number': 'A063', 'Model Name': 'Phone (1) 5G', 'Color': 'Black',
                    'Browse Type': 'Smartphones', 'SIM Type': 'Dual Sim', 'Hybrid Sim Slot': 'No', 'Touchscreen': 'Yes',
                    'OTG Compatible': 'Yes', 'Quick Charging': 'Yes'},
        'Display Features': {'Display Size': '16.64 cm (6.55 inch)', 'Resolution': '2400 x 1080 Pixels',
                             'Resolution Type': 'Full HD+', 'GPU': 'Qualcomm Adreno 642L',
                             'Display Type': 'Full HD Flexible OLED Display', 'HD Game Support': 'Yes',
                             'Other Display Features': 'HDR10+, Contrast Ratio: 1,000,000:1, Brightness: 500 nits, Peak Brightness: 1,200 nits, Adaptive Refresh Rate: 60 Hz - 120 Hz, Touch Sampling Rate: 240 Hz, Haptic Touch Motors'},
        'Other Details': {'Smartphone': 'Yes', 'SIM Size': 'Nano Sim', 'User Interface': 'Nothing OS',
                          'Removable Battery': 'No', 'MMS': 'Yes', 'SMS': 'Yes', 'Keypad': 'No', 'Voice Input': 'Yes',
                          'Graphics PPI': '402 PPI', 'Predictive Text Input': 'Yes', 'SIM Access': 'Dual Standby',
                          'Sensors': 'In-Display Fingerprint Sensor, Accelerometer, Electronic Compass, Gyroscope, Ambient Light Sensor, Proximity Sensor, SAR Sensor',
                          'Upgradable Operating System': '3 Years of Android Updates + 4 Years of Security Patches Every 2 Months',
                          'GPS Type': 'GPS Dual Band: L1 + L5, GLONASS, GALILEO (E1 + E5a Dual Band), BEIDOU, NAVIC, QZSS, SBAS, A-GPS'}}
    payment_id = "price_1M2zJmSIyWOujbWBrCPxfx1t"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "mobile"
    name = "SAMSUNG Galaxy Z Fold4 5G"
    image = "https://rukminim1.flixcart.com/image/832/832/xif0q/mobile/p/v/o/-original-imagh7nzmxwmbpvf.jpeg?q=70"
    price = 187999.0
    discount_price = 164999.0
    delivery = 0.0
    warranty = "1 Year Manufacturer Warranty"
    highlight = ['12 GB RAM | 512 GB ROM', '19.3 cm (7.6 inch) Full HD+ Display',
                 '50MP + 12MP + 10MP | 10MP Front Camera', '4400 mAh Lithium Ion Battery',
                 'Qualcomm Snapdragon 8+ Gen 1 Processor']
    description = "With the Samsung Galaxy Z Fold4 5G's impressive selection of unique apps, you can fold your way through a challenging workday and maintain productivity. The magnificent 19.21 cm (7.6) main screen and 15.73 cm (6.2) cover screen on this phone make multitasking effortless and improve efficiency. Furthermore, you can capture mesmerising photos with excellent images owing to the professional-grade camera system included in this phone. Additionally, the outstanding 120 Hz refresh rate on this phone offers stutter-free gaming and an immaculate user experience. "
    specifications = {'General': {'In The Box': 'Handset, Data Cable, Ejection Pin, Quick Start Guide',
                                  'Model Number': 'SM-F936BZAGINU', 'Model Name': 'Galaxy Z Fold4 5G',
                                  'Color': 'Graygreen', 'Browse Type': 'Smartphones', 'SIM Type': 'Dual Sim',
                                  'Hybrid Sim Slot': 'No', 'Touchscreen': 'Yes', 'OTG Compatible': 'Yes',
                                  'Quick Charging': 'Yes'},
                      'Display Features': {'Display Size': '19.3 cm (7.6 inch)', 'Resolution': '2176 x 1812 Pixels',
                                           'Resolution Type': 'Full HD+', 'GPU': 'Qualcomm Adreno 730',
                                           'Display Type': 'Full HD+ Dynamic AMOLED 2X Display',
                                           'HD Game Support': 'Yes', 'Display Colors': '16M'},
                      'Other Details': {'Smartphone': 'Yes', 'SIM Size': 'Nano Sim', 'Social Networking Phone': 'Yes',
                                        'Instant Message': 'Yes', 'Business Phone': 'Yes', 'Removable Battery': 'No',
                                        'MMS': 'Yes', 'SMS': 'Yes', 'Keypad': 'No', 'Voice Input': 'Yes',
                                        'Graphics PPI': '374 PPI', 'Predictive Text Input': 'Yes',
                                        'Sensors': 'Accelerometer, Barometer, Fingerprint Sensor, Gyro Sensor, Geomagnetic Sensor, Hall Sensor, Light Sensor, Proximity Sensor',
                                        'Browser': 'Google Chrome'}}
    payment_id = "price_1M2zKBSIyWOujbWBnrKr77H5"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "electronic accessories"
    name = "Canon EOS 1500D DSLR Camera"
    image = "https://rukminim1.flixcart.com/image/832/832/kk01pjk0/dslr-camera/f/v/o/eos-1500d-canon-original-imafzfugydh2mjgf.jpeg?q=70"
    price = 41995.0
    discount_price = 38995.0
    delivery = 0.0
    warranty = "2 Year Warranty"
    highlight = ['Effective Pixels: 24.1 MP', 'Sensor Type: CMOS', 'WiFi Available', '1080p recording at 30p']
    description = "This Canon Camera gives you the freedom to explore different ways to shoot subjects. It packs a multitude of shooting options which you can incorporate in still images to create art that embodies the exact mood and vision you are going for. Don’t worry about the lighting conditions of a place because this camera’s large-sized sensor is designed to capture picture-perfect shots even in a dimly lit environment. Thanks to its Wi-Fi connectivity and NFC paring options, sharing photos is as simple as it gets. "
    specifications = {
        'General': {'In The Box': '1 Camera Body, 18 - 55 mm Lens, Battery, Battery Charger', 'Brand': 'Canon',
                    'Model Number': '1500D', 'Series': 'EOS', 'Model Name': 'EOS',
                    'SLR Variant': 'Body+ 18-55 mm IS II Lens', 'Brand Color': 'Black', 'Type': 'DSLR',
                    'Color': 'Black', 'Effective Pixels': '24.1 MP', 'Tripod Socket': 'Yes', 'Wifi': 'Yes'},
        'Sensor Features': {'Sensor Type': 'CMOS', 'Image Sensor Size': '22.3 x 14.9 mm',
                            'ISO Rating': '100 - 6400 (Max up to 12800)'},
        'Shutter Features': {'Shutter Speed': '1/4000 sec', 'Self-timer': 'Yes', 'Continuous Shots': '3fps shooting'},
        'Video Features': {'Video Resolution': '1920 x 1080', 'Video Quality': '1080p recording at 30p'}}
    payment_id = "price_1M2zKnSIyWOujbWBjiy0ePbP"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "electronic accessories"
    name = "Redgear F-15 Wired Mouse"
    image = "https://rukminim1.flixcart.com/image/832/832/kqidx8w0/mouse/a/3/c/f-15-redgear-original-imag4gf8pzgwzxyt.jpeg?q=70"
    price = 999.0
    discount_price = 599.0
    delivery = 49.0
    warranty = "1 Year Warranty from the Date of Purchase"
    highlight = ['Wired', 'For Gaming', 'Interface: USB 2.0, USB 3.0', 'Optical Mouse', 'Plug & Play Gaming Mouse',
                 'Running RGB LEDs', 'Upto 6400dpi', '5Million Durable Switches', 'Suitable for Claw & Palm Grip']
    description = "None"
    specifications = {'General': {'Model Name': 'F-15', 'System Requirements': 'All Windows',
                                  'Sales Package': '1 Mouse, Warranty Card', 'Color': 'Black'},
                      'Connectivity And Power Features': {'Bluetooth': 'No'},
                      'Warranty': {'Domestic Warranty': '1 Year',
                                   'Warranty Summary': '1 Year Warranty from the Date of Purchase',
                                   'Covered in Warranty': 'Manufacturing Defects',
                                   'Not Covered in Warranty': 'Physical Damages'}}
    payment_id = "price_1M2zLASIyWOujbWBroQgSb0R"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "electronic accessories"
    name = "Epson L325 Color Printer"
    image = "https://rukminim1.flixcart.com/image/832/832/kwl0akw0/printer/x/q/3/-original-imag989ygsdy6v6x.jpeg?q=70"
    price = 17999.0
    discount_price = 15899.0
    delivery = 0.0
    warranty = "1 Year Warranty"
    highlight = ['Ink Tank', 'Output: Color', 'WiFi, WiFi Direct, USB | USB']
    description = "None"
    specifications = {'General': {'Printing Method': 'Inkjet', 'Type': 'Multi-function', 'Model Name': 'L3251',
                                  'Printing Output': 'Color', 'Brand': 'Epson', 'Refill Type': 'Ink Bottle',
                                  'Ideal Usage': 'Home & Small Office'},
                      'Dimensions And Weight': {'Height': '38.7 cm', 'Width': '17.95 cm', 'Weight': '4.4 kg',
                                                'Depth': '39.1 cm'}, 'Connectivity': {'Wireless Support': 'Yes'}}
    payment_id = "price_1M2zLZSIyWOujbWBeDrH8wqv"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "electronic accessories"
    name = "Google Nest Mini"
    image = "https://rukminim1.flixcart.com/image/832/832/k33c4nk0/smart-assistant/a/j/k/nest-mini-ga00781-in-google-original-imafmauqguud8wsz.jpeg?q=70"
    price = 4499.0
    discount_price = 3499.0
    delivery = 49.0
    warranty = "1 Year Manufacturing Warranty"
    highlight = ['Voice activated smart speaker with the Google Assistant', 'Available in Hindi',
                 '2X stronger bass than Google Home Mini', 'Wall-mount ready',
                 'Play music, control other smart devices in home', 'Wireless music streaming via Bluetooth',
                 'Configuration: Mono']
    description = "Right from when you wake up till when you go to bed, the Google Nest Mini acts as your personal assistant keeping you informed and entertained throughout the day. Apart from providing you with your personalised schedule and reminders and giving weather updates to letting you play your favourite songs on various streaming services, the Nest Mini is here to make your day better! "
    specifications = {'General': {'Sales Package': 'Google Nest Mini, Power Adapter and Cable, Documentation Bundle',
                                  'Model Number': 'GA00781-IN',
                                  'Model Name': 'Nest Mini (2nd Gen) with Google Assistant', 'Type': 'Smart Speaker',
                                  'Bluetooth': 'Yes', 'Configuration': 'Mono', 'Color': 'Black',
                                  'Power Input': '100-240 V AC'}}
    payment_id = "price_1M2zLtSIyWOujbWB65oiJ0bG"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "electronic accessories"
    name = "MSI NVIDIA GeForce RTX 3060"
    image = "https://rukminim1.flixcart.com/image/832/832/l3bx5e80/graphics-card/h/i/w/geforce-rtx-3060-ventus-2x-12g-oc-12gb-gddr6-192-bit-msi-original-imageh5fuag43pr6.jpeg?q=70"
    price = 76600.0
    discount_price = 35999.0
    delivery = 0.0
    warranty = "3 year manufacturer warranty"
    highlight = ['1807 MHzClock Speed', 'Chipset: NVIDIA', 'BUS Standard: PCI Express® Gen 4',
                 'Graphics Engine: GeForce 3060', 'Memory Interface 192 bit']
    description = "None"
    specifications = {'General': {'Brand': 'MSI', 'Graphics Engine': 'NVIDIA GeForce 3060', 'GPU Clock': '1807 MHz',
                                  'Processors and Cores': '3584 CUDA Cores', 'Bus Standard': 'PCI Express® Gen 4',
                                  'Model ID': 'GeForce RTX 3060 VENTUS 2X 12G OC 12GB GDDR6 192-bit',
                                  'Part Number': 'GeForce RTX 3060 VENTUS 2X 12G OC 12GB GDDR6 192-bit'},
                      'Memory': {'Memory': '192-bit, 12 GB GDDR6 Memory', 'Memory Bandwidth': '15 Gbps'},
                      'Display': {'Maximum Resolution': '7680 x 4320 (Digital)'}}
    payment_id = "price_1M2zMESIyWOujbWBsfrBzyoD"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()

    category = "electronic accessories"
    name = "boAt Rockerz 450 Pro"
    image = "https://rukminim1.flixcart.com/image/832/832/kmccosw0/headphone/9/h/j/rockerz-450-pro-boat-original-imagf9gyd4u6w85z.jpeg?q=70"
    price = 3990.0
    discount_price = 1999.0
    delivery = 49.0
    warranty = "1 Year Warranty from the Date of Purchase"
    highlight = ['With Mic:Yes', 'Connector type: 3.5 mm', 'Bluetooth version: 5', 'Wireless range: 10 m',
                 'Battery life: 70 hrs', 'ASAP Fast Charge: 10 mins charge= 10 hours playtime',
                 'Type-c Charging | 40mm Drivers | 70 hours playtime (at 60% volume)']
    description = "boAt Rockerz 450 Pro is a power-packed on-ear wireless headphone that has been ergonomically designed to meet the needs of music lovers. The headphones come equipped with Bluetooth V5.0 for instant wireless connectivity. Apart from the wireless connectivity, one can utilize the AUX cable as well for a wired playback experience. "
    specifications = {'General': {'Model Name': 'Rockerz 450 Pro with Upto 70 Hours Playback', 'Color': 'Aqua Blue',
                                  'Headphone Type': 'On the Ear', 'Inline Remote': 'No',
                                  'Sales Package': '1 Headphone, Type-C Charging Cable, Aux Cable, User Manual, Warranty Card',
                                  'Connectivity': 'Bluetooth', 'Headphone Design': 'Over the Head'},
                      'Product Details': {'Foldable/Collapsible': 'Yes', 'Deep Bass': 'Yes', 'With Microphone': 'Yes'},
                      'Connectivity Features': {'Bluetooth Version': '5', 'Bluetooth Range': '10 m',
                                                'Battery Life': '70 hrs', 'Play Time': '70 hrs'}}
    payment_id = "price_1M2zMUSIyWOujbWBqy2vpppx"
    product = Product(category=category, name=name, image=image, price=price,
                      discount_price=discount_price,
                      delivery=delivery,
                      warranty=warranty, highlight=highlight, description=description, specifications=specifications,
                      payment_id=payment_id)
    db.session.add(product)
    db.session.commit()
    return "success"


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
    print(all_products)
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
    print(cart_data)
    print(total_data)
    return render_template("cart.html", cart_data=cart_data, total_data=total_data)


@app.route('/add-to-cart/<product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    print(type(product_id))
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
        print(phone)
        current_user.phone = int(request.form["phone"])
        db.session.commit()
        return redirect(url_for('checkout', form="address", mode=mode))

    except BadRequestKeyError:
        return redirect(url_for('checkout', form="address", mode=mode))


@app.route("/address-checkout/<mode>", methods=['POST'])
def address_checkout(mode):
    try:
        print(request.form)
        address_dict = {}
        for key in request.form:
            print(key, request.form[key])
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
    app.run(debug=True)

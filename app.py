import os
import random
import uuid
import re
import secrets
import string
import logging
from data import names, countries, online_stores, products ,catchphrases, prices
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from langdetect import detect, LangDetectException, DetectorFactory
from string import ascii_uppercase
from random import choice
from flask_socketio import SocketIO, join_room, leave_room, send
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from sqlalchemy import Column, Integer, String, Float, Boolean  

# This will output the hashed version of your password



app = Flask(__name__)

app.config['SECRET_KEY'] = 'hjhjsdahhds'  # Using the second SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Example database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Initializing extensions
socketio = SocketIO(app)

# Other variables
online_users = {}
rooms = {}

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
file_path = os.path.join(UPLOAD_FOLDER, 'os_details.png')
admin_password = 'admin@1234'
hashed_password = generate_password_hash(admin_password)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
try:
    # Attempt to open the file or proceed with the logic if it exists
    if os.path.exists(file_path):
        # Proceed with the logic if file exists
        print('File found!')
        # Add your logic here
    else:
        # Handle the missing file scenario
        print('File not found!')

except FileNotFoundError:
    print(f'Error: The file {file_path} was not found.')


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'smtp.chathubb.co.ke'  # Use your email provider's SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'service@chathubb.co.ke'
app.config['MAIL_PASSWORD'] = 'Kenya@2024'
app.config['MAIL_DEFAULT_SENDER'] = 'service@chathubb.co.ke'


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.String(50), nullable=True)
    reason_for_joining = db.Column(db.String(255), nullable=True)  # New column
    earnings = db.Column(db.Float, default=0.0)
    gender = db.Column(db.String(10), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    zipcode = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    referral_code = Column(String, nullable=True)  # Set to nullable
    referred_by_id = Column(Integer, nullable=True)  # Optional field
    referral_count = Column(Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone = db.Column(db.String(20), nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Integer, default=1)
    is_suspended = db.Column(db.Boolean, default=False)
    star_level = db.Column(db.Integer)
    messages_limit = db.Column(db.Integer, default=50)
    messages_sent = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    comments = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.String(15), unique=True)
    uploaded_id = db.Column(db.String(150), nullable=True)
    violation_count = db.Column(db.Integer, default=0)
    driver_license = db.Column(db.String(255))  # Stores the filename of the uploaded driver's license
    selfie = db.Column(db.String(255))  # Stores the filename of the uploaded selfie
    chat_experience = db.Column(db.String(50), nullable=False, default='0')  # Default experience set to 0
    handling_personal_info = db.Column(db.String(255), nullable=False)   # Fixed column
    source = db.Column(db.String(50), nullable=True) 
    hours_available = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<User {self.first_name} {self.last_name}>'

    def can_send_message(self):
        return self.messages_sent < self.messages_limit

    @staticmethod
    def generate_user_id():
        return ''.join(random.choices(string.ascii_letters + string.digits, k=15))



class UpgradeRequest(db.Model):
    __tablename__ = 'upgrade_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Corrected foreign key reference
    package = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_code = db.Column(db.String(100), nullable=False)
    screenshot_filename = db.Column(db.String(100), nullable=True)

    user = db.relationship('User', backref='upgrade_requests')  # Relationship for easier access

    def __init__(self, user_id, package, payment_method, transaction_code, screenshot_filename=None):
        self.user_id = user_id
        self.package = package
        self.payment_method = payment_method
        self.transaction_code = transaction_code
        self.screenshot_filename = screenshot_filename


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)



class Message(db.Model):
    __tablename__ = 'messages'  # Assuming you have a table name defined

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Foreign key to the User model
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_email = db.Column(db.String(100), nullable=False)  # Existing field

    user = db.relationship('User', backref=db.backref('messages', lazy=True))




class WithdrawalRequest(db.Model):
    __tablename__ = 'withdrawal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_details = db.Column(db.String(255), nullable=False)  # New field for payment details
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')

    user = db.relationship('User', backref='withdrawal_requests')

    def __repr__(self):
        return f"<WithdrawalRequest(id={self.id}, user_id={self.user_id}, amount={self.amount}, payment_details='{self.payment_details}', status='{self.status}')>"





# Initialize BackgroundScheduler

# Initialize BackgroundScheduler
# Define allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def update_messages_limit(user):
    # Define a dictionary mapping star levels to message limits
    star_level_limits = {
        1: 50,
        2: 100,
        3: 200,
        4: 400,
        5: 800,
        6: float('inf')  # Infinite messages for level 6
    }

    # Update the messages_limit based on the user's star level
    user.messages_limit = star_level_limits.get(user.star_level, 50)  # Default to 50 if star_level is invalid

    # Commit changes to the database
    db.session.commit()  # Save changes to the database


def update_star_level(user, new_star_level):
    user.star_level = new_star_level
    update_messages_limit(user)  # Call the function to update message limit
    db.session.commit()  # Save changes to the database


def allowed_file(filename):
    # Check if the file has a valid extension
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_registration_id():
    return str(uuid.uuid4())

def can_send_message(self):
        # Define message limits based on star level
        message_limits = {
            1: 50,
            2: 100,
            3: 200,
            4: 400,
            5: 800,
            6: float('inf')  # Infinite messages for star level 6
        }
        return self.messages_sent < message_limits.get(self.star_level, 0)


def get_user_rating(email):
    user = User.query.filter_by(email=email).first()  # Query user by email
    return user.star_level if user else None  # Return star level or None if not found


def generate_user_id():
    """Generates a random 15-character user ID consisting of letters and digits."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(15))

def generate_unique_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def get_online_users():
    return [{'email': user['email'], 'id': user_id} for user_id, user in online_users.items()]


def contains_personal_info(message):
    # Define regex patterns for personal information
    patterns = [
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email
        r"\b(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b",  # Phone Number
        r"@([a-zA-Z0-9_]{1,15})",  # Social Media Handles
        r"https?://[^\s]+"  # URL
    ]
    
    for pattern in patterns:
        if re.search(pattern, message):
            print(f"Pattern matched: {pattern} in message: {message}")  # Debug log
            return True
    return False




DetectorFactory.seed = 0

def detect_non_english(text):
    try:
        # Detect the language of the text
        lang = detect(text)
        
        # Return True if the detected language is not English ('en')
        return lang != 'en'
    except LangDetectException:
        # If detection fails, assume non-English content
        return True

def get_online_users():
    # Simulate getting a list of online users from a database or session
    online_users = [
        {'email': 'user1@example.com', 'is_online': True},
        {'email': 'user2@example.com', 'is_online': True},
        {'email': 'user3@example.com', 'is_online': False},  # Not online, filter out
    ]

    # Only return the emails of users who are marked as online
    return [user['email'] for user in online_users if user.get('is_online', False)]


@app.route('/')
def index():
    app_info = {
        "name": "Chathubb",
        "description": "Welcome to Chathubb, a chatting application that connects you with online users for engaging conversations. Join us to meet new people and share your thoughts!",
        "features": [
            "Connect with users who are currently online",
            "Engage in real-time chats",
            "User-friendly interface",
            "Secure and private conversations"
        ]
    }
    return render_template('index.html', app_info=app_info)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        print(request.form)  # Log form data for debugging

        # Collect form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        reason = request.form.get('reason')  # Ensure reason is collected
        reason_for_joining = request.form['reason_for_joining']
        
        # Collect passwords
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validate password confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        # Collect chat_experience as a string
        chat_experience = request.form['chat_experience']  # No need for conversion to int

        handling_personal_info = request.form.get('handling_personal_info', default=None)  # Collect this
        gender = request.form['gender']
        country = request.form['country']
        city = request.form['city']
        zipcode = request.form['zipcode']
        address = request.form['address']
        hours_available = request.form['hours_available']

        # Handle file uploads
        id_file = request.files['file']
        selfie_file = request.files['selfie']
        
        terms_agreement = request.form.get('terms_agreement')
        
        # Validate input
        if not terms_agreement:
            flash('You must agree to the terms and conditions.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('register'))

        # Ensure files were uploaded
        if not id_file or not selfie_file:
            flash('Please upload both your ID and selfie.', 'danger')
            return redirect(url_for('register'))

        # Create a new user with is_active set to False for approval
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=generate_password_hash(password),  # Hash the password
            reason=reason,
            reason_for_joining=reason_for_joining,
            chat_experience=chat_experience,  # No need for conversion, it's already a string
            handling_personal_info=handling_personal_info,  # Ensure this is included
            gender=gender,
            country=country,
            city=city,
            zipcode=zipcode,
            address=address,
            hours_available=hours_available,
            driver_license=id_file.filename,
            selfie=selfie_file.filename,
            is_active=False  # Set to False for admin approval
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Your account is pending approval by an admin.', 'success')
        return redirect(url_for('success'))

    return render_template('register.html')


# Define online_users as a dictionary
online_users = {}  
active_rooms = []  # List to keep track of active chatrooms




@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        # Get the email and reason for the password change
        email = request.form['email']
        reason = request.form['reason']  # Get the reason from the separate field

        user = User.query.filter_by(email=email.strip()).first()

        if user:
            # Remove the email sending functionality
            # Commented out the email sending line
            # send_reset_email(user)
            flash('A password reset request has been recorded. Please contact support for further assistance.', 'success')

            # Create a notification for admin
            notification = Notification(
                message=f'Password reset requested for {user.email}. Reason: {reason.strip()}',
                timestamp=datetime.utcnow(),  # Automatically set to current time
                # Indicate this is a password reset notification
            )
            db.session.add(notification)
            db.session.commit()
        else:
            flash('Email not found.', 'danger')
        
        return redirect('/forgot_password')  # Redirect back to the forgot password page

    return render_template('forgot_password.html')





        
@app.route('/test')
def start_test():
    # List of 15 test questions
    questions = [
        {
            "question": "What is the purpose of chat moderation?",
            "options": [
                "To keep the conversation civil",
                "To allow any discussion",
                "To promote offensive content"
            ]
        },
        {
            "question": "How would you respond to abusive language in a chat?",
            "options": [
                "Ignore it",
                "Report it",
                "Encourage it"
            ]
        },
        {
            "question": "What actions can you take if a user is being disruptive?",
            "options": [
                "Mute the user",
                "Ban the user",
                "Ignore the user",
                "All of the above"
            ]
        },
        {
            "question": "What would you do if someone shares inappropriate content in the chat?",
            "options": [
                "Engage with them",
                "Report and remove the content",
                "Ignore it"
            ]
        },
        {
            "question": "How would you handle a situation where a user asks for personal information?",
            "options": [
                "Provide the information",
                "Politely decline and explain why",
                "Ignore the request"
            ]
        },
        {
            "question": "Correct the following sentence: 'He go to the store yesterday.'",
            "options": []
        },
        {
            "question": "I would like to sleep with you.How do you reply to that?",

            "options": []
        },
        {
            "question": "Fill in the blank: 'She ____ (to be) a great leader.'",
            "options": []
        },
        {
            "question": "What is the past tense of the verb 'to run'?",
            "options": []
        },
        {
            "question": "Write a brief summary of your favorite book.",
            "options": []
        },
        {
            "question": "Describe a time when you had to handle a difficult user in a chat environment.",
            "options": []
        },
        {
            "question": "What steps would you take to ensure a positive chat experience for all users?",
            "options": []
        },
        {
            "question": "What do you consider to be a red flag in chat moderation?",
            "options": [
                "Users asking about chat rules",
                "Frequent complaints about a user",
                "A user who is very quiet"
            ]
        },
        {
            "question": "How do you approach resolving conflicts between users in chat?",
            "options": []
        },
        {
            "question": "What strategies would you implement to improve chat engagement?",
            "options": []
        }
    ]
    
    return render_template('test.html', questions=questions)





@app.route('/success')
def success():
    return render_template('success.html', message="Your application was successful.You will now proceed to take a test.Kindly note the test is timed and you have 20 minutes to complete it.")

@app.route('/test_notification')
def test_notification():
    return render_template('test_notification.html')



@app.route('/buy_connects', methods=['GET', 'POST'])
def buy_connects():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not authenticated

    if request.method == 'POST':
        # Get form data
        package = request.form['package']
        payment_method = request.form['payment_method']
        transaction_code = request.form['transaction_code']

        # Get the current user's ID from the session
        user_id = session.get('user_id')

        # Handle the uploaded file (screenshot)
        screenshot_filename = None
        if 'screenshot' in request.files:
            screenshot = request.files['screenshot']
            if screenshot:
                screenshot_filename = secure_filename(screenshot.filename)
                screenshot.save(os.path.join('uploads', screenshot_filename))  # Ensure the 'uploads' directory exists

        # Create a new upgrade request
        upgrade_request = UpgradeRequest(
            user_id=user_id,
            package=package,
            payment_method=payment_method,
            transaction_code=transaction_code,
            screenshot_filename=screenshot_filename
        )
        db.session.add(upgrade_request)
        db.session.commit()

        flash(f'Upgrade request for {package} received. Payment method: {payment_method}, Transaction code: {transaction_code}', 'success')
        return redirect(url_for('home'))  # Redirect to the homepage or a confirmation page

    # For GET requests, render the buy connects form
    return render_template('buy_connects.html')  # Ensure you have a template for this



def generate_unique_code(length=4):
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            return code

def is_language_allowed(message, allowed_language="en"):
    try:
        return detect(message) == allowed_language
    except LangDetectException:
        return False



@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Query the database for the user
        user = User.query.filter_by(email=email).first()
        
        # Debugging output
       

        # Check if user exists and password matches
        if user:
            print(f"Stored password hash: {user.password}")
            if check_password_hash(user.password, password) and user.is_admin:
                session['admin_user_id'] = user.id  # Store the user ID in the session
                session['admin_email'] = user.email  # Store the email in the session
                session['is_admin'] = True  # Set a flag to indicate admin is logged in
                flash('Login successful!', 'success')
                return redirect(url_for('admin_panel'))  # Redirect to the admin panel
            else:
                flash('Invalid email or password. Please try again.', 'error')
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('admin_login.html')





rooms = {}  # Global variable to hold room information





@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if the user exists
        user = User.query.filter_by(email=email).first()

        if user:
            if user.is_suspended:
                flash('Your account has been suspended. Please contact support.', 'danger')
                return redirect(url_for('login'))
            
            star_level = user.star_level

            # Check if star_level is None
            if star_level is None:
                flash('This account is not yet active.', 'warning')
                return redirect(url_for('login'))

            # Password verification
            if check_password_hash(user.password, password):
                # Login successful, set the user in the session
                session['user_id'] = user.id
                session['user_name'] = choice(names)  # Generate random name
                session['user_country'] = choice(countries)  # Generate random country
                session['star_level'] = star_level  # Store the star level
                flash('Login successful!', 'success')
                return redirect(url_for('home'))  # Redirect to the home page
            else:
                flash('Invalid password. Please try again.', 'danger')
        else:
            flash('This account does not exist.', 'danger')  # Message for non-existent account
        
        return redirect(url_for('login'))

    return render_template('login.html')



# Initialize an in-memory dictionary to store active rooms
rooms = {}






def generate_unique_code(length):
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route("/home", methods=["POST", "GET"])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_name = session.get('user_name', 'Guest')
    user_country = session.get('user_country', 'Unknown')

    # Get the current active rooms, only show rooms with 3 or fewer members
    active_rooms = {code: room for code, room in rooms.items() if room["members"] <= 3}

    user_id = session.get('user_id')
    user = User.query.get(user_id)  # Fetch user from the database

    # Fetch the star level
    star_level = user.star_level if user else None

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        create = request.form.get("create") == "True"
        join = request.form.get("join") == "True"

        if not name:
            error = "Please enter a name."
            return render_template("home.html", name=name, error=error, active_rooms=active_rooms, user_name=user_name, user_country=user_country, star_level=star_level)

        if join and not code:
            error = "Please enter a room code."
            return render_template("home.html", name=name, error=error, active_rooms=active_rooms, user_name=user_name, user_country=user_country, star_level=star_level)

        room = None
        if create:
            # Check if the user can create a room based on their star level
            if star_level in [4, 5, 6]:
                room_code = generate_unique_code(4)
                rooms[room_code] = {"members": 1, "messages": [], "creator_id": user_id}  # Start with 1 member (the creator)
                room = room_code
            else:
                error = "You need to be at least star level 4 to create a room."
                return render_template("home.html", name=name, error=error, active_rooms=active_rooms, user_name=user_name, user_country=user_country, star_level=star_level)

        elif join and code:
            room = code
            if code not in rooms:
                error = "Room does not exist."
                return render_template("home.html", name=name, error=error, active_rooms=active_rooms, user_name=user_name, user_country=user_country, star_level=star_level)

            # Check if the room already has 2 members (max allowed 3)
            if rooms[room]['members'] >= 3:
                error = "This room is already full."
                return render_template("home.html", name=name, error=error, active_rooms=active_rooms, user_name=user_name, user_country=user_country, star_level=star_level)

            # Add the user to the room's member count
            rooms[room]['members'] += 1  # Increment member count
        else:
            error = "Could not determine room."
            return render_template("home.html", name=name, error=error, active_rooms=active_rooms, user_name=user_name, user_country=user_country, star_level=star_level)

        session["room"] = room
        session["name"] = name

        return redirect(url_for("room", room_name=room))

    return render_template("home.html", 
                           name=session.get("name", ""), 
                           error=None, 
                           active_rooms=active_rooms, 
                           user_name=user_name, 
                           user_country=user_country,
                           star_level=star_level)  # Pass the star level to the template


@app.route("/room")
def room():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    room = request.args.get("room_name")  # Use query parameter to get room_name

    # Guard clause to prevent direct access to room
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

ad_interval = 10 

@socketio.on("message")
def message(data):
    room = session.get("room")
    user_id = session.get("user_id")

    # Ensure the room exists and user is logged in
    if room not in rooms or not user_id:
        return

    user = User.query.get(user_id)
    
    # Check if user exists and if they can send messages
    if not user or not user.can_send_message():
        send({"name": "System", "message": "Message limit reached. You cannot send more messages."}, to=room)
        return

    # Prepare message content
    content = {
        "name": session.get("name"),
        "message": data["data"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Save message to the database
    new_message = Message(
        sender_id=user.id,  # Pass the user's ID
        sender_email=user.email,  # Pass the user's email
        content=data["data"]
    )
    db.session.add(new_message)
    db.session.commit()

    # Increment user's earnings and messages sent count
    user.total_earnings +=0.02  # Increment user's earnings
    user.messages_sent += 1  # Increment messages sent
    db.session.commit()

    print(f"{session.get('name')} said: {data['data']}")

    # Check if an ad should be sent
    if user.messages_sent % ad_interval == 0:
        if products and online_stores:  # Ensure both lists are not empty
            ad_product = random.choice(products)
            ad_store = random.choice(online_stores)
            ad_phrase = random.choice(catchphrases)
            ad_price = random.choice(prices)
            ad_message = f"Check out '{ad_product['name']}' at '{ad_store}' for only {ad_price}. {ad_phrase}"
            send({"name": "Ad", "message": ad_message}, to=room)
        else:
            print("No products or online stores available for ads.")

    # Store the message in the room
    rooms[room]["messages"].append(content)
    
    # Send the message to the room
    send(content, to=room)



@app.route('/view_messages', methods=['GET'])
def view_messages():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))
    
    search_query = request.args.get('search', '').strip()

    # Simple email validation (you can use more robust libraries for validation)
    if search_query and '@' not in search_query and not search_query.isalnum():
        flash('Invalid email format.', 'danger')
        return render_template('view_messages.html', messages=[])

    # Proceed with query if valid
    messages_query = Message.query

    if search_query:
        # Searching in both the sender's email and message content
        messages_query = messages_query.filter(
            (Message.sender_email.ilike(f'%{search_query}%')) | 
            (Message.content.ilike(f'%{search_query}%'))  # Assuming your message content is in a 'content' field
        )

    messages = messages_query.all()
    return render_template('view_messages.html', messages=messages)





@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return 

    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room."}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    user_id = session.get("user_id")

    if room:
        leave_room(room)  # Leave the room
        print(f"{name} left room {room}")

        # Check if the room exists in the dictionary
        if room in rooms:
            # Notify remaining members
            send({"name": name, "message": "has left the room."}, to=room)

            # Delete the room immediately after a member leaves
            del rooms[room]  # Remove the room from the dictionary
            print(f"Room {room} has been deleted as {name} left.")


        



@app.route('/admin_panel', methods=['GET', 'POST'])
def admin_panel():
    # Check if the admin user is logged in
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))  # Redirect to login if not logged in

    # Optionally, you can add additional logic for handling POST requests
    if request.method == 'POST':
        # Handle any form submissions if necessary
        pass

    # Render the admin panel template
    return render_template('admin_panel.html')  # Ensure this HTML file exists in your templates








@app.route('/admin/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'admin_user_id' not in session:
        return redirect(url_for('admin_login'))

    # Base query for active users
    users_query = User.query.filter_by(is_active=True)

    if request.method == 'POST':
        # Handle search functionality
        search_query = request.form.get('search_query')
        print(f"Search query received: {search_query}")  # Debug statement

        if search_query:
            users_query = users_query.filter(
                (User.first_name.ilike(f'%{search_query}%')) |
                (User.last_name.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
            print('Filtered users based on search query:', search_query)

        # Handling user actions (suspend, upgrade, etc.)
        user_id = request.form.get('user_id')
        print(f"User ID from form: {user_id}")  # Debug statement

        action = request.form.get('action')
        reason = request.form.get('reason', "")  # Reason for the action

        # Ensure user_id is valid
        if user_id:
            user = db.session.get(User, user_id)
            if not user:
                flash(f'User with ID {user_id} not found.', 'danger')
                return redirect(url_for('manage_users'))

            # Handle different actions
            if action == 'suspend':
                user.is_suspended = True
                flash(f'User {user.first_name} {user.last_name} suspended.', 'success')
            elif action == 'unsuspend':
                user.is_suspended = False
                flash(f'User {user.first_name} {user.last_name} unsuspended.', 'success')
            elif action == 'downgrade':
                new_star_level = request.form.get('new_star_level')
                if new_star_level:
                    user.star_level = new_star_level
                    flash(f'User {user.first_name} {user.last_name} downgraded to {new_star_level}-star.', 'success')
                else:
                    flash('No star level provided for downgrade.', 'danger')
            elif action == 'fine':
                fine_amount = request.form.get('fine_amount', type=float)
                if fine_amount and fine_amount > 0:
                    if user.total_earnings >= fine_amount:
                        user.total_earnings -= fine_amount
                        flash(f'User {user.first_name} {user.last_name} fined ${fine_amount:.2f}.', 'success')
                    else:
                        flash('Fine amount exceeds user earnings.', 'danger')
                else:
                    flash('Invalid fine amount.', 'danger')
            elif action == 'upgrade':
                new_star_level = request.form.get('new_star_level')
                if new_star_level in ['1', '2', '3', '4', '5', '6']:  # Validate the new star level
                    user.star_level = new_star_level
                    user.messages_limit = {
                        '1': 50,
                        '2': 100,
                        '3': 200,
                        '4': 400,
                        '5': 800,
                        '6': float('inf')  # Infinite messages for level 6
                    }.get(new_star_level)
                    flash(f'User {user.first_name} {user.last_name} upgraded to {new_star_level}-star.', 'success')
                else:
                    flash('Invalid star level provided for upgrade.', 'danger')
            elif action == 'update_password':
                new_password = request.form.get('new_password')
                if new_password:
                    # Hash the new password before saving
                    hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
                    user.password = hashed_password
                    flash(f'User {user.first_name} {user.last_name} password updated.', 'success')
                else:
                    flash('New password is required.', 'danger')

            # Store the reason for the action
            user.reason = reason

            # Commit changes to the database
            db.session.commit()
            return redirect(url_for('manage_users'))

    # Fetch the results after search/filtering or if no POST request
    users = users_query.all()
    print(f"Number of users found: {len(users)}")  # Debug statement

    if not users:
        flash('No users found matching the search criteria.', 'info')

    return render_template('manage_users.html', users=users)




@app.route('/reset_limits', methods=['POST'])  # Use POST to avoid CSRF issues
def reset_limits():
    # Ensure the user is logged in as admin
    if 'admin_user_id' not in session:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))  # Redirect to admin login if not logged in

    users = User.query.all()
    for user in users:
        # Reset each user's messages limit to the initial value based on star level
        user.messages_limit = 0  # Reset message limit for all users
        user.last_reset = datetime.utcnow()  # Update last reset timestamp

    db.session.commit()  # Commit all changes to the database
    flash('Message limits have been reset to zero for all users.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/view_earnings')
def view_earnings():
    user_id = session.get('user_id')  # Get the user ID from the session
    user = User.query.get(user_id)     # Retrieve the user from the database
    if user:
        return render_template('earnings.html', earnings=user.total_earnings)
    else:
        return redirect(url_for('login'))



@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not authenticated

    user_id = session.get('user_id')  # Get the current user's ID

    if request.method == 'POST':
        amount = float(request.form.get('amount'))  # Get the withdrawal amount from the form
        payment_details = request.form.get('payment_details')  # Get the payment details from the form

        # Ensure we're in the app context for database access
        with app.app_context():
            user = User.query.get(user_id)  # Get the user from the database

            if user:
                # Check if the user's total earnings are at least $180 to make a withdrawal
                if user.total_earnings < 180:
                    flash('Your total earnings must be at least $180 to make a withdrawal.', 'error')
                    return redirect(url_for('withdraw'))

                # Check if the requested amount is less than or equal to the user's earnings
                if amount > user.total_earnings:
                    flash('Insufficient balance for this withdrawal.', 'error')
                    return redirect(url_for('withdraw'))

                # Create a new withdrawal request with payment details
                withdrawal_request = WithdrawalRequest(
                    user_id=user_id,
                    amount=amount,
                    payment_details=payment_details,  # Store the payment details
                    timestamp=datetime.utcnow(),
                    status='Pending'  # Initial status
                )
                db.session.add(withdrawal_request)
                db.session.commit()

                # Create a notification for the admin
                admin_notification = Notification(
                    message=f'User with ID {user_id} requested a withdrawal of ${amount}. Payment details: {payment_details}.',
                )
                db.session.add(admin_notification)
                db.session.commit()

                flash('Withdrawal request submitted successfully. It is pending admin approval.', 'success')
                return redirect(url_for('withdraw'))  # Redirect to the withdrawal page

    return render_template('withdraw.html')  # Render the withdrawal template


@app.route('/admin/withdrawals', methods=['GET', 'POST'])
def manage_withdrawals():
    # Ensure the user is logged in as admin
    if 'admin_user_id' not in session:  # Check if admin user ID is in session
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))  # Redirect to admin login if not logged in

    # Fetch all withdrawal requests
    withdrawal_requests = WithdrawalRequest.query.all()

    if request.method == 'POST':
        request_id = request.form.get('request_id')
        action = request.form.get('action')  # 'approve' or 'reject'

        # Ensure we're in the app context for database access
        with app.app_context():
            withdrawal_request = WithdrawalRequest.query.get(request_id)
            if withdrawal_request:
                user = User.query.get(withdrawal_request.user_id)

                if action == 'approve':
                    # Check if the user has enough earnings
                    if user.total_earnings >= withdrawal_request.amount:
                        # Deduct the amount from user's earnings
                        user.total_earnings -= withdrawal_request.amount
                        withdrawal_request.status = 'Approved'  # Update withdrawal request status
                        flash(f'Withdrawal request for ${withdrawal_request.amount} approved.', 'success')
                    else:
                        flash('Insufficient funds for this withdrawal.', 'danger')

                elif action == 'reject':
                    withdrawal_request.status = 'Rejected'  # Update withdrawal request status
                    flash('Withdrawal request rejected.', 'warning')

                db.session.commit()  # Commit changes to the database

        return redirect(url_for('manage_withdrawals'))

    # Prepare the data to send to the template, including payment details
    withdrawal_requests_with_details = [
        {
            'request': wr,
            'email': User.query.get(wr.user_id).email,  # Fetch the user's email
            'payment_details': wr.payment_details  # Include payment details
        }
        for wr in withdrawal_requests
    ]

    return render_template('admin/manage_withdrawals.html', withdrawal_requests=withdrawal_requests_with_details)



@app.route('/admin/view_upgrade_requests', methods=['GET', 'POST'])
def view_upgrade_requests():
    if 'admin_user_id' not in session or session.get('is_admin') != True:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))

    requests = UpgradeRequest.query.all()  # Retrieve all upgrade requests

    if request.method == 'POST':
        request_id = request.form['request_id']
        upgrade_request = UpgradeRequest.query.get(request_id)

        if upgrade_request:
            user = User.query.get(upgrade_request.user_id)
            action = request.form['action']

            # Approve or deny logic
            if action == 'approve':
                # Logic to approve the request
                star_levels = {
                    '1star': (50, 1),
                    '2star': (100, 2),
                    '3star': (200, 3),
                    '4star': (400, 4),
                    '5star': (800, 5),
                    '6star': (float('inf'), 6)
                }

                if upgrade_request.package in star_levels:
                    user.messages_limit, user.star_level = star_levels[upgrade_request.package]
                    flash(f'User {user.first_name} {user.last_name} has been upgraded to {upgrade_request.package}.', 'success')

                    # Check who referred the user
                    referrer = User.query.get(user.referred_by_id) if user.referred_by_id else None
                    if referrer:
                        referrer.referral_count += 1  # Increment the referral count
                        db.session.commit()  # Commit the change

                        # Notify admin if the referral count reaches 10
                        if referrer.referral_count == 10:
                            notification_message = f'User {referrer.first_name} {referrer.last_name} has reached 10 referrals!'
                            notification = Notification(message=notification_message)
                            db.session.add(notification)
                            db.session.commit()

                    db.session.delete(upgrade_request)  # Delete the processed request
                    db.session.commit()
                else:
                    flash('Invalid package selected for upgrade.', 'danger')

            elif action == 'deny':
                # Logic to deny the request (you can add additional handling here)
                db.session.delete(upgrade_request)  # Optionally delete or keep the request
                db.session.commit()
                flash('Upgrade request denied.', 'danger')

        return redirect(url_for('view_upgrade_requests'))

    return render_template('admin/view_upgrade_requests.html', upgrade_requests=requests)





@app.route('/admin/view_user/<int:user_id>', methods=['GET'])
def view_user(user_id):
    # user_id from the URL parameter is already available, so we don't need to get it again from request.args
    user = User.query.get(user_id)
    
    if user:
        return render_template('admin/view_user.html', user=user)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('manage_users'))



@app.route('/admin/notifications')
def admin_notifications():
    # Check if the user is logged in as an admin
    if 'admin_user_id' not in session or session.get('is_admin') != True:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))  # Redirect to login if not admin

    notifications = Notification.query.order_by(Notification.timestamp.desc()).all()  # Get all notifications
    return render_template('admin/notifications.html', notifications=notifications)
   

@app.route('/admin/notifications/delete/<int:notification_id>', methods=['POST'])
def delete_notification(notification_id):
    # Check if the user is logged in as an admin
    if 'admin_user_id' not in session or session.get('is_admin') != True:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))  # Redirect to login if not admin

    notification = Notification.query.get(notification_id)

    if notification:
        db.session.delete(notification)
        db.session.commit()
        flash('Notification deleted successfully.', 'success')
    else:
        flash('Notification not found.', 'danger')

    return redirect(url_for('admin_notifications'))  # Redirect back to the notifications page



   





@app.route('/delete_room/<room_code>', methods=['POST'])
def delete_room(room_code):
    # Logic to delete the room
    if room_code in rooms:
        del rooms[room_code]
        return redirect(url_for('home'))  # Redirect to home or another page after deletion
    return "Room not found", 404

def room_exists(room_name):
    # Check if the room exists in your storage (like a database or a predefined list)
    return room_name in rooms



@app.route('/chat/<room_name>')
def chat_room(room_name):
    # Render the chat room template with the room name
    return f'Welcome to {room_name}!'


@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/user_details/<int:user_id>')
def user_details(user_id):
    # Assume you have a function to get a user by their ID
    user = get_user_by_id(user_id)  # Retrieve user data from the database
    if not user:
        return redirect(url_for('manage_registrations'))  # Redirect if user not found

    return render_template('user_detail.html', user=user)



@app.route('/admin/manage_registrations', methods=['GET', 'POST'])
def manage_registrations():
    if 'admin_user_id' not in session or session.get('is_admin') != True:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_login'))

    registrations = User.query.filter_by(is_active=False).all()

    if request.method == 'POST':
        action = request.form['action']
        user_id = request.form['user_id']
        user = User.query.get(user_id)

        if user:
            if action == 'approve':
                user.is_active = True
                user.star_level = 1
                user.messages_limit = 50
                flash(f'User {user.first_name} {user.last_name} has been approved!', 'success')

            elif action == 'reject':
                db.session.delete(user)
                flash(f'User {user.first_name} {user.last_name} has been rejected.', 'warning')

            db.session.commit()
        else:
            flash('User not found.', 'danger')

        return redirect(url_for('manage_registrations'))

    return render_template('admin/manage_registrations.html', registrations=registrations)


@app.route('/view_user_details', methods=['GET'])
def view_user_details():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if user:
        return render_template('user_details.html', user=user)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('manage_registrations'))


@app.route('/advertisers_login', methods=['GET', 'POST'])
def advertisers_login():
    if request.method == 'POST':
        # Simulate credential validation
        username = request.form['username']
        password = request.form['password']

        # Replace this with your actual validation logic
        if username != "valid_user" or password != "valid_password":
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('advertisers_login'))  # Redirect to the same route

    return render_template('advertisers_login.html')  # Render the login form




@app.route('/referral')
def referral():
    # Attempt to get user_id from session
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None  # Check if user is logged in

    if user is None:
        # Handle the case for non-logged-in users or adjust as needed
        flash('You must be logged in to access your referral link.', 'danger')
        return redirect(url_for('home'))

    referral_link = f"http://127.0.0.1:5000/register?referral={user.referral_code}"  # Adjust the domain as needed
    return render_template('referral.html', referral_link=referral_link)








@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_id', None)  # Remove admin from session
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

def create_db():
    create_tables()

# Start the scheduler


@app.route('/create_initial_admin', methods=['GET', 'POST'])
def create_initial_admin():
    # Check if an admin already exists
    existing_admin = User.query.filter_by(is_admin=True).first()
    
    if existing_admin:
        flash('Admin account already exists. Please log in.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Collect form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        gender = request.form['gender']
        country = request.form['country']
        city = request.form['city']
        zipcode = request.form['zipcode']
        address = request.form['address']
        password = request.form['password']

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('create_initial_admin'))

        # Hash the password using Werkzeug
        hashed_password = generate_password_hash(password)

        # Create the initial admin
        initial_admin = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=hashed_password,
            is_admin=True,
            reason='Not specified',
            reason_for_joining='Not specified',  # You might want to set this as well
            handling_personal_info='Not specified',  # Ensure this matches the User model
            gender=gender,
            country=country,
            city=city,
            zipcode=zipcode,
            is_active=True,
            address=address,
            referral_code=str(uuid.uuid4()),
            referred_by_id=None,
            rating=1,
            chat_experience=0  # Set default chat experience as needed
        )

        # Save the initial admin to the database
        db.session.add(initial_admin)
        db.session.commit()

        flash('Initial admin account created. You can now register other admins.', 'success')
        return redirect(url_for('login'))

    return render_template('create_initial_admin.html')



@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/cookie_policy')
def cookie_policy():
    return render_template('cookie_policy.html')


@app.route('/logout')
def logout():
    session.clear()  # Clear the session to log out the user
    return redirect(url_for('login'))  # Redirect back to the login page


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the tables
    app.run(debug=True)
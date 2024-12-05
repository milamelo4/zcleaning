from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
import os
from config import DevelopmentConfig, ProductionConfig
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from functools import wraps

# Create a Flask instance   
app = Flask(__name__)

# Load configuration based on the environment
if os.getenv('FLASK_ENV') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Initialize SQLAlchemy
db.init_app(app)

    
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        dbname=os.getenv('DB_NAME')
    )

# ####################################################
# -----------------------Middleware-------------------
# ####################################################

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("You need to log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ####################################################
# -----------------------Routes-----------------------
# ####################################################
# Home page
@app.route("/", methods=["GET", "POST"])
def index():
    return redirect(url_for("login"))


# Create a custom error page
@app.errorhandler(Exception)
def handle_error(e):
    error_code = e.code if hasattr(e, "code") else 500
    return render_template("error.html", error_code=error_code), error_code

@app.route('/test')
def get_users():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)  # Use dictionary=True for row dicts
    cursor.execute("SELECT * FROM client")
    users = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(users)

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if 'username' in session:
            return redirect(url_for('dashboard'))

        if request.method == "POST":
            email = request.form.get('username')
            password = request.form.get('password')

            # Debug: Print incoming form data
            #print(f"Email: {email}, Password: {password}")

            # Query the database for the user
            user = User.query.filter_by(account_email=email).first()
            #print(f"User fetched from database: {user}")

            # Debug: Check if user exists
            if not user:
                #print("User not found")
                flash("Invalid username or password", "danger")
                return redirect(url_for('login'))

            # Debug: Check if password exists
            if not user.account_password:
                #print("Password is missing for this user")
                flash("Invalid username or password", "danger")
                return redirect(url_for('login'))

            # Check the hashed password
            if check_password_hash(user.account_password, password):
                # Store user info in session
                session['username'] = user.account_email
                session['user_id'] = user.account_id
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid username or password", "danger")

        return render_template("login.html")

    except Exception as e:
        #print(f"Error in /login route: {e}")
        return f"Error in /login route: {e}", 500


# Register Page
@app.route("/register", methods=["GET", "POST"])
def register():
    try:
        if request.method == "POST":
            firstname = request.form.get('firstname')
            lastname = request.form.get('lastname')
            email = request.form.get('email')
            password = request.form.get('password')

            # Check if the email is already registered
            existing_user = User.query.filter_by(account_email=email).first()
            if existing_user:
                flash("Email already registered. Please log in.", "warning")
                return redirect(url_for('register'))

            # Hash the password for security
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)


            # Create a new user record
            new_user = User(
                account_firstname=firstname,
                account_lastname=lastname,
                account_email=email,
                account_password=hashed_password,
                account_type='Employee'  # Default account type
            )
            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))

        return render_template("register.html")

    except Exception as e:
        app.logger.error(f"Error in registration: {e}")
        flash("An error occurred. Please try again.", "danger")
        return redirect(url_for('register'))
    
# Logout Page
@app.route("/logout")
def logout():
    # Clear the session
    session.clear()
    # Redirect to the login page
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

# Dashboard Page
@app.route("/dashboard")
@login_required
def dashboard():
    if 'username' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('login'))

    # Retrieve user information from the database
    user = User.query.filter_by(account_email=session['username']).first()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('login'))

    # Logic for admin and employee
    if user.account_type == 'Admin':
        # Pull data to display admin privileges
        data = {
            "can_manage_employees": True,
            "can_view_reports": True,
            "can_access_finances": True
        }
    elif user.account_type == 'Employee':
        # Pull limited employee privileges
        data = {
            "can_manage_employees": False,
            "can_view_reports": True,
            "can_access_finances": False
        }
    else:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    return render_template("dashboard.html", user=user, data=data)



    
if __name__ == '__main__':
    app.run(debug=True)


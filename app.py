# from flask_wtf import FlaskForm
# from wtforms import StringField, SubmitField
# from wtforms.validators import DataRequired
# from flask_sqlalchemy import SQLAlchemy
# from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import os
from config import DevelopmentConfig, ProductionConfig
from models import db, User
from functools import wraps
import psycopg2 # type: ignore
import hashlib
from sqlalchemy import text


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

            # Query the database for the user
            user = User.query.filter_by(account_email=email).first()

            if not user or not user.account_password:
                flash("Invalid username or password", "danger")
                return redirect(url_for('login'))

            # Hash the entered password using SHA-256 and compare
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if hashed_password == user.account_password:
                # Store user info in session
                session['username'] = user.account_email
                session['user_id'] = user.account_id
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid username or password", "danger")

        return render_template("login.html")

    except Exception as e:
        app.logger.error(f"Error in /login route: {e}")
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
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

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

# manage_employees  
@app.route("/manage-employees")
@login_required
def manage_employees():
    try:
        if 'username' not in session:
            flash("You need to log in first.", "warning")
            return redirect(url_for('login'))

        user = User.query.filter_by(account_email=session['username']).first()

        if not user or user.account_type != 'Admin':
            flash("Unauthorized access.", "danger")
            return redirect(url_for('dashboard'))

        # Fetch employee data
        result = db.session.execute(text("""
    SELECT first_name, last_name, hourly_pay_rate, hire_date, employment_status 
    FROM zcleaning.employee
"""))
        # Debug: Print employees to the console
        print(f"Fetched employees: {result}")

        return render_template("manage_employees.html", employees=result)
    except Exception as e:
        app.logger.error(f"Error in /manage-employees route: {e}")
        return f"Error in /manage-employees route: {e}", 500

# view_reports
@app.route("/view-reports", methods=["GET", "POST"])
@login_required
def view_reports():
    try:
        user = User.query.filter_by(account_email=session['username']).first()
        if user.account_type != 'Admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('dashboard'))

        selected_date = None
        if request.method == "POST":
            selected_date = request.form.get("week_start_date")
        
        result = db.session.execute(text(f"""
        SELECT 
            CASE 
                WHEN GROUPING(e.first_name) = 1 THEN 'TOTAL ---->'
                ELSE e.first_name
            END AS name,
            CONCAT('$', TO_CHAR(SUM(a.total_hours_worked * e.hourly_pay_rate), 'FM999,999.00')) AS payment
        FROM zcleaning.employee e
        INNER JOIN zcleaning.attendance a USING (employee_id)
        WHERE a.week_start_date = :week_start_date
        GROUP BY GROUPING SETS ((e.first_name), ());
        """), {'week_start_date': selected_date}).fetchall()

        return render_template("view_reports.html", reports=result, selected_date=selected_date)

    except Exception as e:
        app.logger.error(f"Error in /view-reports route: {e}")
        return f"Error in /view-reports route: {e}", 500

# client_schedule
@app.route("/client-schedule", methods=["GET", "POST"])
@login_required
def client_schedule():
    try:
        # Ensure only Admins can access
        user = User.query.filter_by(account_email=session['username']).first()
        if user.account_type != 'Admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('dashboard'))

        selected_day = None
        if request.method == "POST":
            selected_day = request.form.get("preferred_day")

        result = db.session.execute(text("""
        SELECT 
            CASE
                WHEN GROUPING(c.first_name) = 1 THEN 'TOTAL HOURS'
                ELSE CONCAT(c.first_name, ' ', c.last_name)
            END AS name, 
            SUM(service_hours) AS total_hours
        FROM zcleaning.client c
        WHERE c.preferred_day = :preferred_day
            AND c.is_active = 'active'
            AND c.service_type_id BETWEEN 1 AND 3
        GROUP BY GROUPING SETS ((c.first_name, c.last_name, c.preferred_day), ()) order by total_hours asc;
        """), {'preferred_day': selected_day}).fetchall()

        return render_template("client_schedule.html", schedule=result, selected_day=selected_day)

    except Exception as e:
        app.logger.error(f"Error in /client-schedule route: {e}")
        return f"Error in /client-schedule route: {e}", 500



@app.route('/access-finances')
def access_finances():
    # Logic to fetch and display financial data (to be added later)
    return render_template('access_finances.html')



    
if __name__ == '__main__':
    app.run(debug=True)


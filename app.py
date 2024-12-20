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
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo


# Create a Flask instance   
app = Flask(__name__)

# Load configuration based on the environment
if os.getenv('FLASK_ENV') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Initialize CSRF protection
csrf = CSRFProtect(app)

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
            flash("Your session has expired or you need to log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ####################################################
# -----------------------Routes-----------------------
# ####################################################
# Home page
@app.route('/')
def index():
    # Check if the user is logged in
    is_logged_in = 'username' in session
    return render_template('index.html', is_logged_in=is_logged_in)

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
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if 'username' in session:
        return redirect(url_for('dashboard'))

    if form.validate_on_submit():  # This also validates CSRF token
        email = form.username.data
        password = form.password.data

        # Query the database for the user
        user = User.query.filter_by(account_email=email).first()

        if not user or hashlib.sha256(password.encode()).hexdigest() != user.account_password:
            flash("Invalid username or password", "danger")
            return redirect(url_for('login'))

        session['username'] = user.account_email
        session['user_id'] = user.account_id
        session.permanent = True  # Enable session timeout

        flash("Login successful!", "success")
        return redirect(url_for('dashboard'))

    return render_template("login.html", form=form)

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

# Register Page
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()  # Create an instance of RegistrationForm
    try:
        if not form.validate_on_submit():
            app.logger.debug("Form validation failed.")
            app.logger.debug(f"Errors: {form.errors}")

        if form.validate_on_submit():  # Check if the form is submitted and all validations pass
            app.logger.debug("Form validated successfully.")
            firstname = request.form.get('firstname')  # Assuming firstname is in your template
            lastname = request.form.get('lastname')    # Assuming lastname is in your template
            email = form.email.data
            password = form.password.data

            # Check if the email is already registered
            existing_user = User.query.filter_by(account_email=email).first()
            if existing_user:
                app.logger.debug("Email already registered.")
                flash("Email already registered. Please log in.", "warning")
                return redirect(url_for('register'))

            # Hash the password for security
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            app.logger.debug("Password hashed successfully.")
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

        return render_template("register.html", form=form)

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
    app.logger.debug("Accessing dashboard route")
    print("Accessing dashboard route")

    if 'username' not in session:
        app.logger.debug("No username in session")
        flash("You need to log in first.", "warning")
        return redirect(url_for('login'))

    user = User.query.filter_by(account_email=session['username']).first()
    if not user:
        app.logger.debug("User not found in database")
        flash("User not found.", "danger")
        return redirect(url_for('login'))

    app.logger.debug(f"User found: {user.account_email}, Role: {user.account_type}")

    if user.account_type == 'Admin':
        data = {
            "can_manage_employees": True,
            "can_view_reports": True,
            "can_access_finances": True
        }
    elif user.account_type == 'Employee':
        data = {
            "can_manage_employees": False,
            "can_view_reports": True,
            "can_access_finances": False
        }
    else:
        app.logger.debug("Unauthorized user role")
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    app.logger.debug(f"Data passed to template: user={user}, data={data}")
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
    SELECT first_name, last_name, hourly_pay_rate, hire_date, employment_status, CONCAT(SUBSTRING(phone_number, 1, 3), '-', SUBSTRING(phone_number, 4, 3), '-', SUBSTRING(phone_number, 7, 4)) AS formatted_phone_number,  Concat(street, ', ', city) AS street
    FROM zcleaning.employee
"""))
        # Debug: Print employees to the console
        #print(f"Fetched employees: {result}")

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
        # Check the logged-in user's role
        user = User.query.filter_by(account_email=session['username']).first()

        if user.account_type not in ['Admin', 'Employee']:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('dashboard'))

        selected_day = None
        if request.method == "POST":
            selected_day = request.form.get("preferred_day")

        # Query to fetch client schedule data
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
        GROUP BY GROUPING SETS ((c.first_name, c.last_name, c.preferred_day), ()) 
        ORDER BY total_hours ASC;
        """), {'preferred_day': selected_day}).fetchall()

        return render_template("client_schedule.html", schedule=result, selected_day=selected_day)

    except Exception as e:
        app.logger.error(f"Error in /client-schedule route: {e}")
        flash("An error occurred while accessing the schedule.", "danger")
        return redirect(url_for('dashboard'))


@app.route('/access-finances')
def access_finances():
    # Logic to fetch and display financial data (to be added later)
    return render_template('access_finances.html')

@app.route("/search_client", methods=["GET", "POST"])
@login_required
def search_client():
    try:
        user = User.query.filter_by(account_email=session['username']).first()
        if user.account_type != 'Admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('dashboard'))

        search_results = None
        if request.method == "POST":
            client_name = request.form.get("client_name")

            # Perform the database query
            search_results = db.session.execute(text("""
        SELECT 
        CONCAT(c.first_name, ' ', c.last_name) AS full_name, 
        CONCAT(SUBSTRING(c.phone_number, 1, 3), '-', SUBSTRING(c.phone_number, 4, 3), '-', SUBSTRING(c.phone_number, 7, 4)) AS formatted_phone_number, 
        c.hired_date, 
        c.service_hours, 
        c.preferred_day, 
        CONCAT(a.street, ', ', a.city) AS full_address,
        g.garage_code AS garage_code
    FROM zcleaning.client c
    INNER JOIN zcleaning.address a 
        ON c.client_id = a.client_id
    INNER JOIN zcleaning.garage_code g
        ON c.client_id = g.client_id
    WHERE c.last_name ILIKE :client_name
"""), {'client_name': f'%{client_name}%'}).fetchall()


        return render_template("search_client.html", search_results=search_results)

    except Exception as e:
        app.logger.error(f"Error in /search_client route: {e}")
        return f"Error in /search_client route: {e}", 500

@app.route("/add-client", methods=["GET", "POST"])
@login_required
def add_client():
    try:
        user = User.query.filter_by(account_email=session['username']).first()
        if user.account_type != 'Admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('dashboard'))

        if request.method == "POST":
            # Retrieve form data
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")
            phone_number = request.form.get("phone_number")
            hired_date = request.form.get("hired_date")
            service_hours = request.form.get("service_hours", 0)  # Default to 0
            preferred_day = request.form.get("preferred_day").upper()
            service_type_id = request.form.get("service_type_id", 1)  # Default to 1
            is_active = request.form.get("is_active", "active")  # Default to 'active'

            # Insert the new client into the database
            db.session.execute(text(f"""
                INSERT INTO zcleaning.client (first_name, last_name, phone_number, hired_date,
                service_hours, preferred_day, service_type_id, is_active)
                VALUES (:first_name, :last_name, :phone_number, :hired_date,
                :service_hours, :preferred_day, :service_type_id, :is_active)
            """), {
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "hired_date": hired_date,
                "service_hours": service_hours,
                "preferred_day": preferred_day,
                "service_type_id": service_type_id,
                "is_active": is_active
            })
            db.session.commit()

            flash("Client added successfully!", "success")
            return redirect(url_for('dashboard'))

        return render_template("add_client.html")

    except Exception as e:
        app.logger.error(f"Error in /add-client route: {e}")
        flash("An error occurred. Please try again.", "danger")
        return redirect(url_for('dashboard'))

@app.route("/my-personal-info")
@login_required
def my_personal_info():
    try:
        # Fetch user details based on session
        user = User.query.filter_by(account_id=session['user_id']).first()
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('dashboard'))

        app.logger.debug(f"Session user_id: {session['user_id']}")
        app.logger.debug(f"User details: {user}")

        # If the user is an admin, skip the employee query
        if user.account_type == 'Admin':
            user_data = {
                "firstname": user.account_firstname,
                "lastname": user.account_lastname,
                "email": user.account_email,
            }
            return render_template("my_personal_info.html", user=user_data)

        # Get employee_id from the account table
        employee_id = user.employee_id  # Ensure this is correctly populated in your account table
        if not employee_id:
            flash("Employee details not found.", "danger")
            return redirect(url_for('dashboard'))

        app.logger.debug(f"Employee ID for query: {employee_id}")

        # Query the employee table using the correct employee_id
        employee_data = db.session.execute(text("""
            SELECT 
                CONCAT(SUBSTRING(phone_number, 1, 3), '-', SUBSTRING(phone_number, 4, 3), '-', SUBSTRING(phone_number, 7, 4)) AS phone_number,
                dob,
                CONCAT(street, ', ', city) AS address,
                hire_date,
                employment_status,
                hourly_pay_rate
            FROM zcleaning.employee
            WHERE employee_id = :employee_id
        """), {'employee_id': employee_id}).fetchone()

        app.logger.debug(f"Employee data fetched: {employee_data}")

        if not employee_data:
            flash("Could not retrieve employee details.", "danger")
            return redirect(url_for('dashboard'))

        # Combine user and employee data
        user_data = {
            "firstname": user.account_firstname,
            "lastname": user.account_lastname,
            "email": user.account_email,
            "phone_number": employee_data.phone_number,
            "dob": employee_data.dob,
            "address": employee_data.address,
            "hire_date": employee_data.hire_date,
            "employment_status": employee_data.employment_status,
            "hourly_pay_rate": employee_data.hourly_pay_rate
        }

        return render_template("my_personal_info.html", user=user_data)

    except Exception as e:
        app.logger.error(f"Error in /my-personal-info route: {e}")
        flash("An error occurred while retrieving your information.", "danger")
        return redirect(url_for('dashboard'))







    
if __name__ == '__main__':
    app.run(debug=True)


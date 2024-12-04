from flask import Flask, render_template, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
import os
import mysql.connector
from config import DevelopmentConfig, ProductionConfig

# Create a Flask instance   
app = Flask(__name__)

# Load the appropriate configuration based on the environment
if os.getenv('FLASK_ENV') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define your models here
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

# Create a form
class NameForm(FlaskForm):
    name = StringField("What is your name?", validators=[DataRequired()])
    submit = SubmitField("Submit")

# ####################################################
# -----------------------Routes-----------------------
# ####################################################
# Create a route for the home page
@app.route("/")
def index():
    test = 'THis is <strong>bold</strong> text'
    favorite_pizza = ["pepperoni", "cheese", "bacon"]
    return render_template("index.html", 
    favorite_pizza=favorite_pizza, 
    test=test)

# Create a route for user
@app.route("/user/<name>")
def user(name):
    return render_template("user.html", user_name=name)

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


if __name__ == '__main__':
    app.run(debug=True)


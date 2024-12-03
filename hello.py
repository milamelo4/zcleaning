from flask import Flask, render_template

# Create a Flask instance   
app = Flask(__name__)

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

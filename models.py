from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'account'  # Ensure the table name matches exactly
    account_id = db.Column(db.Integer, primary_key=True)
    account_firstname = db.Column(db.String(50), nullable=False)
    account_lastname = db.Column(db.String(50), nullable=False)
    account_email = db.Column(db.String(100), unique=True, nullable=False)
    account_password = db.Column(db.String(255), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # Adjust to match ENUM
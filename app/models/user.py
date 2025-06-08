from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100))
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    gender = db.Column(db.Enum('male', 'female', name='gender_types'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, server_default='false')
    created_at = db.Column(db.DateTime, default=datetime.now)
    referral_code = db.Column(db.String(10), unique=True) 
    reward_points = db.Column(db.Integer, default=0)
    braintree_customer_id = db.Column(db.String(50))
    # Relationships
    orders = db.relationship('Order', foreign_keys='Order.client_id', backref='client', lazy=True)
    referrals = db.relationship('Referral', foreign_keys='Referral.referrer_id', backref='referrer', lazy=True)
    referred_by = db.relationship('Referral', foreign_keys='Referral.referred_id', backref='referred', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    blog_posts = db.relationship('BlogPost', backref='author', lazy=True)
    testimonials = db.relationship('Testimonial', backref='author', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Set the password hash from the provided password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def get_name(self):
        """Return full name if available, otherwise username."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def __repr__(self):
        return f'<User {self.username}>'
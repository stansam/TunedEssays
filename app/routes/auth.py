from flask import Blueprint, render_template, request, redirect, url_for, flash
from urllib.parse import urlparse
from sqlalchemy import or_
from datetime import datetime, timedelta
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db, limiter, get_token_serializer
from app.models.user import User
from app.utils.email import send_verification_email
import logging

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("8 per minute")
def login():
    # Redirect to home if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        # Validate input
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return redirect(url_for('auth.login'))

        # Find user
        user = User.query.filter(
            or_(
                User.username == username,
                User.email == username
            )
        ).first()

        # Check for too many failed attempts
        if user and user.failed_login_attempts >= 5 and user.last_failed_login:
            time_passed = datetime.now() - user.last_failed_login
            if time_passed < timedelta(minutes=15):
                logging.warning(f'Account locked due to too many failed attempts: {user.email}')
                flash('Account is temporarily locked. Please try again later.', 'danger')
                return redirect(url_for('auth.login'))
            else:
                # Reset counter after lockout period
                user.failed_login_attempts = 0
                db.session.commit()

        # Check if user exists and password is correct
        if user and user.check_password(password):
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.last_failed_login = None
            db.session.commit()

            if not user.email_verified:
                flash('Please verify your email first.', 'warning')
                send_verification_email(user)
                return redirect(url_for('auth.login'))
            # Login user with Flask-Login
            login_user(user, remember=remember)

            # Get the next page from request args, or default routes
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                if user.is_admin:
                    next_page = url_for('admin.index')
                else:
                    next_page = url_for('client.dashboard')

            flash(f'Welcome back, {user.get_name()}!', 'success')
            return redirect(next_page)
        else:
            if user:
                user.failed_login_attempts += 1
                user.last_failed_login = datetime.now()
                db.session.commit()
                logging.warning(f'Failed login attempt for user: {user.email}')
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html', title="Login")

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect to home if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        gender = request.form.get('gender')

        # Validate input
        if not username or not email or not password or not confirm_password or not gender:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

        # Check if username or email already exists
        username_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()

        if username_exists:
            flash('Username is already taken.', 'danger')
            return redirect(url_for('auth.register'))

        if email_exists:
            flash('Email is already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Create new user
        new_user = User(username=username, email=email, first_name=first_name, last_name=last_name, gender=gender)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Send verification email
        send_verification_email(new_user)

        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title="Register")

@auth_bp.route('/logout')
def logout():
    logout_user()

    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    try:
        # Get the token serializer from app config
        from flask import current_app
        token_serializer = get_token_serializer(current_app.config['SECRET_KEY'])
        
        email = token_serializer.loads(token, salt='email-verification-salt', max_age=86400)  # 24 hours
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Invalid verification link.', 'danger')
            return redirect(url_for('auth.login'))
            
        if user.email_verified:
            flash('Email already verified. Please login.', 'info')
        elif user.email_verification_token == token:
            user.email_verified = True
            user.email_verification_token = None
            db.session.commit()
            logging.info(f'Email verified for user: {email}')
            flash('Your email has been verified! You can now log in.', 'success')
        else:
            logging.warning(f'Invalid verification attempt for email: {email}')
            flash('Invalid verification link.', 'danger')
    except Exception as e:
        logging.error(f'Email verification error: {str(e)}')
        flash('Invalid or expired verification link.', 'danger')

    return redirect(url_for('auth.login'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    # Handle password reset request form
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        # Always show the same message to prevent user enumeration
        flash('If your email is registered, you will receive a password reset link.', 'info')
        
        if user:
            # Send password reset email
            from app.utils.email import send_password_reset_email
            send_password_reset_email(user)
            
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', title="Reset Password")

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    try:
        # Get the token serializer from app config
        from flask import current_app
        token_serializer = get_token_serializer(current_app.config['SECRET_KEY'])
        
        email = token_serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Invalid reset link.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Handle password reset form
        if request.method == 'POST':
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if not password or password != confirm_password:
                flash('Passwords do not match or are empty.', 'danger')
                return render_template('auth/reset_password.html', token=token, title="Reset Password")
            
            user.set_password(password)
            db.session.commit()
            flash('Your password has been reset successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        
        return render_template('auth/reset_password.html', token=token, title="Reset Password")
    except Exception as e:
        logging.error(f'Password reset error: {str(e)}')
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.login'))
from flask import url_for, current_app
from app.extensions import mail, get_token_serializer
from flask_mail import Message
import logging

def send_verification_email(user):
    """Send email verification link to user"""
    # Get token serializer
    token_serializer = get_token_serializer(current_app.config['SECRET_KEY'])
    token = token_serializer.dumps(user.email, salt='email-verification-salt')
    verification_url = url_for('auth.verify_email', token=token, _external=True)

    msg = Message('Verify your email',
                  recipients=[user.email])
    msg.body = f'Please verify your email by clicking on this link: {verification_url}'
    
    try:
        mail.send(msg)
        
        # Save token to user
        user.email_verification_token = token
        from app.extensions import db
        db.session.commit()
        
        logging.info(f'Verification email sent to {user.email}')
    except Exception as e:
        logging.error(f'Failed to send verification email: {str(e)}')
        raise

def send_password_reset_email(user):
    """Send password reset link to user"""
    # Get token serializer
    token_serializer = get_token_serializer(current_app.config['SECRET_KEY'])
    token = token_serializer.dumps(user.email, salt='password-reset-salt')
    reset_url = url_for('auth.reset_password', token=token, _external=True)

    msg = Message('Password Reset Request',
                  recipients=[user.email])
    msg.body = f'''To reset your password, click the following link:
{reset_url}

If you did not request a password reset, please ignore this email.
This link is valid for 1 hour.
'''
    
    try:
        mail.send(msg)
        logging.info(f'Password reset email sent to {user.email}')
    except Exception as e:
        logging.error(f'Failed to send password reset email: {str(e)}')
        raise

def send_order_confirmation(order, user):
    """Send order confirmation email to user"""
    msg = Message('Order Confirmation',
                  recipients=[user.email])
    msg.body = f'''
Hello {user.get_name()},

Thank you for your order! Your order number is {order.order_number}.

Order Details:
- Title: {order.title}
- Service: {order.service.name}
- Academic Level: {order.academic_level.name}
- Deadline: {order.deadline.name}
- Due Date: {order.due_date.strftime('%Y-%m-%d %H:%M')}
- Total Price: ${order.total_price:.2f}

You can view the details of your order here:
{url_for('orders.order_detail', order_number=order.order_number, _external=True)}

If you have any questions, please don't hesitate to contact us.

Best regards,
Academic Writing Team
'''
    
    try:
        mail.send(msg)
        logging.info(f'Order confirmation email sent to {user.email} for order {order.order_number}')
    except Exception as e:
        logging.error(f'Failed to send order confirmation email: {str(e)}')
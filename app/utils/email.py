from flask import url_for, current_app, render_template
from app.extensions import mail, get_token_serializer
from flask_mail import Message
import logging
import os

def send_verification_email(user):
    """Send email verification link to user"""
    # Get token serializer
    token_serializer = get_token_serializer(current_app.config['SECRET_KEY'])
    token = token_serializer.dumps(user.email, salt='email-verification-salt')
    verification_url = url_for('auth.verify_email', token=token, _external=True)

    msg = Message('Verify your email',
                  recipients=[user.email],
                  sender="no-reply@tunedessays.com")
    # msg.sender = "noreply@tunedessays.com"
    msg.html = render_template('emails/email_verification.html', 
                              verification_url=verification_url,
                              user=user,
                              base_url=os.environ.get('BASE_URL', 'https://tunedessays.com'))
    # msg.body = f'Please verify your email by clicking on this link: {verification_url}'
    msg.body = f'''
    Welcome to TunedEssays!
    
    Thanks for creating a TunedEssays account. Please verify your email to gain full access.
    
    Click this link to verify your email: {verification_url}
    
    Welcome to the future of polished writing.
    
    Best regards,
    TunedEssays Team
    '''
    
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
                  recipients=[user.email],
                  sender="no-reply@tunedessays.com")
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
    order_url = url_for('order_details.order_details', order_id=order.id, _external=True)
    msg = Message('Order Confirmation',
                  recipients=[user.email],
                  sender="no-reply@tunedessays.com")
    msg.html = render_template(
        'emails/confirm_order.html',
        user=user,
        order=order,
        order_url=order_url,
        base_url=os.environ.get('BASE_URL', 'https://tunedessays.com')
    )
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
{url_for('order_details.order_details', order_id=order.id, _external=True)}

If you have any questions, please don't hesitate to contact us.

Best regards,
Academic Writing Team
'''
    
    try:
        mail.send(msg)
        logging.info(f'Order confirmation email sent to {user.email} for order {order.order_number}')
    except Exception as e:
        logging.error(f'Failed to send order confirmation email: {str(e)}')

def send_order_created(user, order):
    """Send order confirmation email to admin"""
    order_url = url_for('admin.view_order', order_id=order.id, _external=True)
    msg = Message('Order Recieved',
                  recipients=[user.email],
                  sender="no-reply@tunedessays.com")
    msg.html = render_template(
        'emails/order_created.html',
        user=user,
        order=order,
        order_url=order_url,
        base_url=os.environ.get('BASE_URL', 'https://tunedessays.com')
    )

    
    try:
        mail.send(msg)
        logging.info(f'Order confirmation email sent to {user.email} for order {order.order_number}')
    except Exception as e:
        logging.error(f'Failed to send order confirmation email: {str(e)}')

def send_welcome_email(user):
    """
    Send welcome email using external template file
    
    Args:
        user: User object with email attribute
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Template variables
        template_vars = {
            'user_name': getattr(user, 'username', None),
            'account_url': f"{os.environ.get('BASE_URL', 'https://tunedessays.com')}/client",
            'base_url': os.environ.get('BASE_URL', 'https://tunedessays.com')
        }
        
        # Render template from file (save the HTML template as templates/welcome_email.html)
        html_content = render_template('emails/welcome_email.html', **template_vars)
        
        msg = Message(
            subject='Welcome to TunedEssays - Thanks for Signing Up!',
            recipients=[user.email],
            html=html_content,
            sender="no-reply@tunedessays.com"
        )
        
        mail.send(msg)
        print(f"Welcome email sent successfully to {user.email}")
        return True
        
    except Exception as e:
        print(f"Error sending welcome email to {user.email}: {str(e)}")
        return False

def send_payment_completion_email(user, payment_url, order) -> bool:
    """
    Send a payment completion email using an external HTML template file.
    
    Args:
        user (dict): User object containing user information
        payment_url (str, optional): URL for payment completion
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not payment_url:
            payment_url = f"https://tunedessays.com/payment/checkout/{order.id}"
        
        # Render template from file (create templates/email_payment_completion.html)
        html_content = render_template(
            'emails/complete_payment.html', 
            user=user, 
            payment_url=payment_url,
            order=order,
            base_url=os.environ.get('BASE_URL', 'https://tunedessays.com')
        )
        
        msg = Message(
            subject="Complete Your TunedEssays Order - Action Required",
            recipients=[user.email],
            html=html_content,
            sender="no-reply@tunedessays.com"
        )
        
        mail.send(msg)
        print(f"Payment completion email sent successfully to {user.get('email')}")
        return True
        
    except Exception as e:
        print(f"Error sending email to {user.get('email', 'unknown')}: {str(e)}")
        return False
    

def send_order_completed_email(order, user):
    """
    Send order completion email to user
    
    Args:
        order: Order object containing order details
        user: User object containing user information
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Generate order review URL
        order_review_url = url_for('order_details.order_details', order_id=order.id, _external=True)
        
        # Render the email template
        html_body = render_template(
            'emails/order_completed.html',
            order=order,
            user=user,
            order_review_url=order_review_url,
            base_url=os.environ.get('BASE_URL', 'https://tunedessays.com') 
        )
        
        # Create email message
        msg = Message(
            subject='Your Order Is Ready 🎉 - TunedEssays',
            recipients=[user.email],
            html=html_body,
            sender="no-reply@tunedessays.com"
        )
        
        # Send email
        mail.send(msg)
        
        # Log successful email sending (optional)
        logging.info(f"Order completion email sent to {user.email} for order {order.id}")
        
        return True
        
    except Exception as e:
        # Log error
        logging.error(f"Failed to send email to {user.email}: {str(e)}")
        return False

def send_payment_confirmation_email(invoice, user):
    """
    Send payment confirmation email to user
    
    Args:
        invoice: Invoice object containing payment details
        user: User object containing user information
    """
    try:
        # Create the email message
        order_url= url_for('order_details.order_details', order_id=invoice.order_id, _external=True)
        msg = Message(
            subject=f'Payment Confirmed - Invoice {invoice.invoice_number}',
            sender='no-reply@tunedessays.com',
            recipients=[user.email]
        )
        
        # Render the HTML template
        msg.html = render_template(
            'emails/payment_completed.html',
            invoice=invoice,
            user=user,
            order_url=order_url,
            base_url=os.environ.get('BASE_URL', 'https://tunedessays.com')
        )
        
        # Optional: Add plain text version
        msg.body = f"""
        Hi {user.first_name if user.first_name else 'Customer'},
        
        Your payment has been confirmed!
        
        Invoice Number: {invoice.invoice_number}
        Amount Paid: ${invoice.total:.2f}
        
        You can view your order details by logging into your account.
        
        Thank you for choosing TunedEssays!
        
        Best regards,
        TunedEssays Team
        """
        
        # Send the email
        mail.send(msg)
        
        return True, "Email sent successfully"
        
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"
    
def send_revision_request_email(order, user):
    """
    Send revision request confirmation email to user
    
    Args:
        order: Order object containing order details
        user: User object containing user information
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Generate status URL (adjust based on your routing)
        status_url = url_for('order_details.order_details', order_id=order.id, _external=True)
        
        # Render the email template
        html_body = render_template(
            'emails/revision_request.html',
            user=user,
            order=order,
            status_url=status_url,
            base_url=os.environ.get('BASE_URL', 'https://tunedessays.com')
        )
        
        # Create the email message
        msg = Message(
            subject='Your Revision Request Has Been Received - TunedEssays',
            recipients=[user.email],
            html=html_body,
            sender="no-reply@tunedessays.com"
        )
        
        # Add a plain text version as fallback
        msg.body = f"""
        Hi {user.username},

        Thanks for your feedback! We're now working on your revision and will deliver the updated file soon.
        You'll be notified as soon as it's ready!

        Check your order status: {status_url}

        Best regards,
        TunedEssays Team
        """
        
        # Send the email
        mail.send(msg)
        
        # Log successful email send (optional)
        logging.info(f'Revision request email sent to {user.email} for order {order.id}')
        
        return True
        
    except Exception as e:
        # Log the error (you might want to use proper logging)
        logging.error(f'Failed to send revision request email to {user.email}: {str(e)}')
        return False

def send_extension_request_email(order, user):
    """
    Send deadline extension request confirmation email to user.
    
    Args:
        order: Order object with attributes like id, title, deadline, etc.
        user: User object with attributes like email, name, etc.
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Create the email message
        msg = Message(
            subject='Deadline Extension Request Confirmed - TunedEssays',
            recipients=[user.email],
            sender="no-reply@tunedessays.com"
        )
        
        # Render the HTML template with context
        msg.html = render_template(
            'emails/extension_request.html',
            order=order,
            user=user,
            order_url=url_for('order_details.order_details', order_id=order.id, _external=True),
            base_url=os.environ.get('BASE_URL', 'https://tunedessays.com')
        )
        
        # Optional: Add plain text version
        msg.body = f"""
        Dear {user.username},
        
        Thank you for confirming and extending the time and letting us work on this.
        
        Your order #{order.id} deadline has been successfully extended.
        
        You can check your order status at any time by visiting our website.
        
        Best regards,
        TunedEssays Team
        
        TunedEssays.com
        """
        
        # Send the email
        mail.send(msg)
        
        # Log successful send (optional)
        logging.info(f'Extension request email sent successfully to {user.email} for order {order.id}')
        
        return True
        
    except Exception as e:
        # Log the error
        logging.error(f'Failed to send extension request email to {user.email}: {str(e)}')
        return False

def send_anything_else_email(user):
    """
    Send a "Need Help With Anything Else?" email to a user
    
    Args:
        user: User object with at least 'email' and 'username' attributes
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Render the HTML template
        html_body = render_template('emails/anything_else.html', user=user)
        
        # Create the email message
        msg = Message(
            subject="Need Help With Anything Else? - TunedEssays",
            recipients=[user.email],
            html=html_body,
            sender="no-reply@tunedessays.com"
        )
        
        # Send the email
        mail.send(msg)
        
        print(f"Email sent successfully to {user.email}")
        return True
        
    except Exception as e:
        print(f"Failed to send email to {user.email}: {str(e)}")
        return False
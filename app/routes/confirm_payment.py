from flask import Flask, request, jsonify, current_app, Blueprint
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
import json
import re
from functools import wraps
import traceback
from typing import Dict, Any, Optional, Tuple



confirm_payment_bp = Blueprint('confirm_payment', __name__)
def setup_logging():
    """Setup comprehensive logging for the payment API"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('payment_api.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class PaymentConfirmationError(Exception):
    """Custom exception for payment confirmation errors"""
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code

class PaymentConfirmationService:
    """Service class to handle payment confirmation logic"""
    
    @staticmethod
    def validate_payment_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming payment confirmation data"""
        logger.info(f"Validating payment data: {data}")
        
        # Required fields
        required_fields = ['email', 'paymentMethod', 'orderId']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            raise PaymentConfirmationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # Validate email format
        email = data.get('email', '').strip()
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            raise PaymentConfirmationError("Invalid email format")
        
        # Validate payment method
        valid_payment_methods = ['paypal', 'payoneer']
        payment_method = data.get('paymentMethod', '').lower()
        if payment_method not in valid_payment_methods:
            raise PaymentConfirmationError(
                f"Invalid payment method. Must be one of: {', '.join(valid_payment_methods)}"
            )
        
        # Validate order ID format 
        order_id = data.get('orderId')
        if isinstance(order_id, str) and order_id.startswith('ORD-'):
            try:
                # Extract numeric part from ORD-123456 format
                order_id = int(order_id.split('-')[1])
            except (IndexError, ValueError):
                raise PaymentConfirmationError("Invalid order ID format")
        elif not isinstance(order_id, int):
            try:
                order_id = int(order_id)
            except (ValueError, TypeError):
                raise PaymentConfirmationError("Invalid order ID format")
        
        # Validate amount if provided
        amount = data.get('amount')
        if amount:
            try:
                amount = float(str(amount).replace('$', ''))
                if amount <= 0:
                    raise PaymentConfirmationError("Amount must be greater than 0")
            except (ValueError, TypeError):
                raise PaymentConfirmationError("Invalid amount format")
        
        return {
            'email': email,
            'paymentMethod': payment_method,
            'orderId': order_id,
            'amount': amount,
            'currency': data.get('currency', 'USD'),
            'serviceType': data.get('serviceType', 'ID Service'),
            'timestamp': data.get('timestamp', datetime.now().isoformat())
        }
    
    @staticmethod
    def find_order_and_user(order_id: int) -> Tuple[Any, Any]:
        """Find order and associated user"""
        try:
            from app.models.user import User  
            from app.models.order import Order
            
            order = Order.query.get(order_id)
            if not order:
                raise PaymentConfirmationError(f"Order {order_id} not found", 404)
            
            user = User.query.get(order.client_id)
            if not user:
                raise PaymentConfirmationError(f"User for order {order_id} not found", 404)
            
            logger.info(f"Found order {order_id} for user {user.id}")
            return order, user
            
        except Exception as e:
            logger.error(f"Error finding order and user: {str(e)}")
            raise PaymentConfirmationError(f"Database error: {str(e)}", 500)
    
    @staticmethod
    def create_support_ticket(order: Any, user: Any, payment_data: Dict[str, Any]) -> Any:
        """Create a support ticket for payment confirmation"""
        try:
            from app.models.order import SupportTicket
            from app.extensions import db 
            
            # Create detailed subject
            subject = f"Payment Confirmation - Order #{order.id} - {payment_data['paymentMethod'].title()}"
            
            # Create comprehensive message
            message = f"""
PAYMENT CONFIRMATION SUBMITTED

Order Details:
- Order ID: {order.id}
- Service Type: {payment_data['serviceType']}
- Amount: ${payment_data['amount']} {payment_data['currency']}
- Customer: {user.email}

Payment Information:
- Payment Method: {payment_data['paymentMethod'].title()}
- Customer Email Used: {payment_data['email']}
- Submission Time: {payment_data['timestamp']}

Payment Instructions Used:
{PaymentConfirmationService._get_payment_instructions(payment_data['paymentMethod'])}

Action Required:
Please verify this payment in the {payment_data['paymentMethod'].title()} account and update the order status accordingly.
            """.strip()
            
            # Create support ticket
            support_ticket = SupportTicket(
                order_id=order.id,
                user_id=user.id,
                subject=subject,
                message=message,
                status='open'
            )
            
            db.session.add(support_ticket)
            db.session.commit()
            
            logger.info(f"Created support ticket {support_ticket.id} for order {order.id}")
            return support_ticket
            
        except Exception as e:
            logger.error(f"Error creating support ticket: {str(e)}")
            db.session.rollback()
            raise PaymentConfirmationError(f"Failed to create support ticket: {str(e)}", 500)
    
    @staticmethod
    def _get_payment_instructions(payment_method: str) -> str:
        """Get payment instructions based on method"""
        instructions = {
            'paypal': """
PayPal Payment Instructions:
- Email: turquoisesave@gmail.com
- Please include Order ID in payment notes
- This is the recommended payment method
            """,
            'payoneer': """
Payoneer Payment Instructions:
- Email: bbeatish@gmail.com
- Please add Order ID in review/notes
- Alternative payment method
            """
        }
        return instructions.get(payment_method, "Unknown payment method")
    
    @staticmethod
    def send_notifications(support_ticket: Any, order: Any, user: Any) -> None:
        """Send notifications about the payment confirmation"""
        try:
            from app.models.user import User
            from app.routes.main import notify
            # from app.utils.emails import send_email
            notify(user, "Payment Confirmation Request", f"Your payment confirmation for Order #{order.order_number} has been sent and is under review.", type='info')

            # Notify the admin about the payment request for a particular order
            admin_user = User.query.filter_by(is_admin=True).first()  
            if admin_user:
                notify(admin_user, "New Payment Confirmation", f"A payment confirmation has been submitted for Order #{order.order_number} by {user.full_name}.", type='alert', link=f"/admin/orders/{order.id}")

            
            logger.info(f"Notifications sent for support ticket {support_ticket.id}")
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
            # Don't raise error here as ticket is already created

def handle_api_errors(f):
    """Decorator to handle API errors consistently"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except PaymentConfirmationError as e:
            logger.error(f"Payment confirmation error: {e.message}")
            return jsonify({
                'success': False,
                'message': e.message,
                'error_code': 'PAYMENT_CONFIRMATION_ERROR'
            }), e.code
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again later.',
                'error_code': 'INTERNAL_ERROR'
            }), 500
    return decorated_function


    
@confirm_payment_bp.route('/confirm', methods=['POST'])
@handle_api_errors
def confirm_payment():
    """Handle payment confirmation requests"""
    logger.info("Payment confirmation request received")
    
    # Get and validate request data
    if not request.is_json:
        raise PaymentConfirmationError("Request must be JSON")
    
    data = request.get_json()
    if not data:
        raise PaymentConfirmationError("No data provided")
    
    # Log the request (excluding sensitive data)
    safe_data = {k: v for k, v in data.items() if k != 'email'}
    logger.info(f"Processing payment confirmation: {safe_data}")
    
    # Validate payment data
    validated_data = PaymentConfirmationService.validate_payment_data(data)
    
    # Find order and user
    order, user = PaymentConfirmationService.find_order_and_user(validated_data['orderId'])
    
    # Check if payment confirmation already exists
    from app.models.order import SupportTicket  # Replace with your actual import
    existing_ticket = SupportTicket.query.filter_by(
        order_id=order.id,
        subject=f"Payment Confirmation - Order #{order.id} - {validated_data['paymentMethod'].title()}"
    ).first()
    
    if existing_ticket:
        logger.warning(f"Duplicate payment confirmation attempt for order {order.id}")
        return jsonify({
            'success': False,
            'message': 'Payment confirmation already submitted for this order.',
            'error_code': 'DUPLICATE_CONFIRMATION'
        }), 409
    
    # Create support ticket
    support_ticket = PaymentConfirmationService.create_support_ticket(
        order, user, validated_data
    )
    
    # Send notifications
    PaymentConfirmationService.send_notifications(support_ticket, order, user)
    
    # Return success response
    response_data = {
        'success': True,
        'message': 'Payment confirmation submitted successfully! Our team will verify your payment shortly.',
        'data': {
            'ticketId': support_ticket.id,
            'orderId': order.id,
            'status': 'submitted',
            'estimatedProcessingTime': '2-4 hours'
        }
    }
    
    logger.info(f"Payment confirmation successful for order {order.id}, ticket {support_ticket.id}")
    return jsonify(response_data), 200

@confirm_payment_bp.route('/status/<int:order_id>', methods=['GET'])
@handle_api_errors
def check_payment_status(order_id: int):
    """Check payment confirmation status for an order"""
    logger.info(f"Checking payment status for order {order_id}")
    
    # Find order
    order, user = PaymentConfirmationService.find_order_and_user(order_id)
    
    # Find related support tickets
    from app.models.order import SupportTicket  # Replace with your actual import
    tickets = SupportTicket.query.filter_by(order_id=order_id).all()
    
    payment_tickets = [
        ticket for ticket in tickets 
        if 'Payment Confirmation' in ticket.subject
    ]
    
    if not payment_tickets:
        return jsonify({
            'success': True,
            'status': 'no_confirmation',
            'message': 'No payment confirmation submitted yet.'
        }), 200
    
    # Get latest payment ticket
    latest_ticket = max(payment_tickets, key=lambda t: t.created_at)
    
    return jsonify({
        'success': True,
        'status': 'confirmation_submitted',
        'data': {
            'ticketId': latest_ticket.id,
            'status': latest_ticket.status,
            'submittedAt': latest_ticket.created_at.isoformat(),
            'lastUpdated': latest_ticket.updated_at.isoformat()
        }
    }), 200

@confirm_payment_bp.route('/logs', methods=['POST'])
def handle_frontend_logs():
    """Handle logs from frontend"""
    try:
        data = request.get_json()
        if data:
            frontend_logger = logging.getLogger('frontend')
            log_level = data.get('level', 'info')
            message = data.get('message', '')
            log_data = data.get('data', {})
            
            getattr(frontend_logger, log_level)(f"Frontend: {message}", extra=log_data)
        
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error handling frontend logs: {str(e)}")
        return jsonify({'success': False}), 500

# # Example usage in your main app
# def setup_payment_api(app: Flask):
#     """Setup payment API routes in your Flask app"""
#     create_payment_routes(app)
    
#     # Configure additional logging
#     if not app.debug:
#         file_handler = logging.FileHandler('payment_api.log')
#         file_handler.setLevel(logging.INFO)
#         formatter = logging.Formatter(
#             '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
#         )
#         file_handler.setFormatter(formatter)
#         app.logger.addHandler(file_handler)

# Example integration in your main Flask app file:
"""
from flask import Flask
from your_payment_api import setup_payment_api

app = Flask(__name__)
# ... your existing app configuration ...

# Setup payment API
setup_payment_api(app)

if __name__ == '__main__':
    app.run(debug=True)
"""
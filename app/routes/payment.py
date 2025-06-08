from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
import braintree
from app.routes.pay_ser import BraintreePaymentService  
from app.models.payment import Payment, Invoice, Refund  
from app.models.order import Order
from app.extensions import db  

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')
payment_service = BraintreePaymentService()

@payment_bp.route('/client-token')
@login_required
def client_token():
    """Generate client token for Braintree Drop-in UI"""
    if current_user.braintree_customer_id:
        token = payment_service.generate_client_token(str(current_user.braintree_customer_id))
    else:
        token = payment_service.generate_client_token()
    if token:
        return jsonify({'clientToken': token})
    return jsonify({'error': 'Failed to generate client token'}), 500

@payment_bp.route('/checkout/<int:order_id>')
@login_required
def checkout(order_id):
    """Render checkout page for an order"""
    order = Order.query.get_or_404(order_id)
    
    # Verify order belongs to current user
    if order.client_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if order is already paid
    if order.paid:
        return jsonify({'error': 'Order already paid'}), 400
    if current_user.braintree_customer_id:
        client_token = payment_service.generate_client_token(str(current_user.braintree_customer_id))
    else:
        client_token = payment_service.generate_client_token()
    
    # client_token = payment_service.generate_client_token(str(current_user.id))
    
    return render_template('payment/checkout.html', 
                         order=order, 
                         client_token=client_token)

# @payment_bp.route('/process', methods=['POST'])
# @login_required
# def process_payment():
#     """Process payment for an order"""
#     try:
#         data = request.get_json()
#         order_id = data.get('order_id')
#         payment_method_nonce = data.get('payment_method_nonce')
#         payment_method = data.get('payment_method', 'credit_card')
        
#         if not all([order_id, payment_method_nonce]):
#             return jsonify({'error': 'Missing required fields'}), 400
        
#         # Get order and verify ownership
#         order = Order.query.get(order_id)
#         if not order or order.client_id != current_user.id:
#             return jsonify({'error': 'Order not found or unauthorized'}), 404
        
#         if order.paid:
#             return jsonify({'error': 'Order already paid'}), 400
        
#         # Process payment based on method
#         if payment_method == 'paypal':
#             result = payment_service.process_paypal_payment(
#                 order_id, payment_method_nonce, order.total_price, current_user.id
#             )
#         elif payment_method == 'apple_pay':
#             result = payment_service.process_apple_pay_payment(
#                 order_id, payment_method_nonce, order.total_price, current_user.id
#             )
#         elif payment_method == 'google_pay':
#             result = payment_service.process_google_pay_payment(
#                 order_id, payment_method_nonce, order.total_price, current_user.id
#             )
#         else:
#             # Default to credit card
#             result = payment_service.process_payment(
#                 order_id, payment_method_nonce, order.total_price, current_user.id
#             )
        
#         if result['success']:
#             return jsonify({
#                 'success': True,
#                 'message': 'Payment processed successfully',
#                 'payment_id': result['payment_id'],
#                 'transaction_id': result.get('transaction_id')
#             })
#         else:
#             return jsonify({
#                 'success': False,
#                 'error': result['error']
#             }), 400
            
#     except Exception as e:
#         current_app.logger.error(f"Payment processing error: {str(e)}")
#         return jsonify({'error': 'Payment processing failed'}), 500

@payment_bp.route('/process', methods=['POST'])
@login_required
def process_payment():
    """Process payment for an order with improved error handling"""
    try:
        # Validate content type
        if not request.is_json:
            current_app.logger.error(f"Invalid content type: {request.content_type}")
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
        
        # Log the incoming request for debugging
        current_app.logger.info(f"Payment request data: {data}")
        
        # Extract and validate required fields
        order_id = data.get('order_id')
        payment_method_nonce = data.get('payment_method_nonce')
        payment_method = data.get('payment_method', 'credit_card')
        device_data = data.get('device_data')
        # More detailed validation
        if not order_id:
            current_app.logger.error("Missing order_id")
            return jsonify({'error': 'Order ID is required'}), 400
            
        if not payment_method_nonce:
            current_app.logger.error("Missing payment_method_nonce")
            return jsonify({'error': 'Payment method nonce is required'}), 400
        
        # Validate order_id is numeric if expected
        try:
            order_id = int(order_id)
        except (ValueError, TypeError):
            current_app.logger.error(f"Invalid order_id format: {order_id}")
            return jsonify({'error': 'Invalid order ID format'}), 400
        
        # Get order and verify ownership with better error handling
        try:
            order = Order.query.get(order_id)
        except Exception as e:
            current_app.logger.error(f"Database error fetching order {order_id}: {str(e)}")
            return jsonify({'error': 'Database error'}), 500
        
        if not order:
            current_app.logger.error(f"Order {order_id} not found")
            return jsonify({'error': 'Order not found'}), 404
            
        if order.client_id != current_user.id:
            current_app.logger.error(f"User {current_user.id} unauthorized for order {order_id}")
            return jsonify({'error': 'Unauthorized access to order'}), 403
        
        if order.paid:
            current_app.logger.error(f"Order {order_id} already paid")
            return jsonify({'error': 'Order already paid'}), 400
        
        # Validate order amount
        if not hasattr(order, 'total_price') or order.total_price <= 0:
            current_app.logger.error(f"Invalid order amount: {getattr(order, 'total_price', 'missing')}")
            return jsonify({'error': 'Invalid order amount'}), 400
        
        # Process payment based on method with better error handling
        formatted = "{:.2f}".format(float(order.total_price))
        order_number = order.order_number
        try:
            if payment_method == 'paypal':
                result = payment_service.process_paypal_payment(
                    order_id, payment_method_nonce, order.total_price, current_user.id
                )
            elif payment_method == 'apple_pay':
                result = payment_service.process_apple_pay_payment(
                    order_id, payment_method_nonce, order.total_price, current_user.id
                )
            elif payment_method == 'google_pay':
                result = payment_service.process_google_pay_payment(
                    order_id, payment_method_nonce, order.total_price, current_user.id
                )
            elif payment_method == 'venmo':
                result = payment_service.process_venmo_payment(
                    order_id, payment_method_nonce, order.total_price, current_user.id, device_data, order_number
                )
            else:
                # Default to credit card
                result = payment_service.process_payment(
                    order_id, payment_method_nonce, order.total_price, current_user.id, device_data, order_number
                )
        except AttributeError as e:
            current_app.logger.error(f"Payment service method not found: {str(e)}")
            return jsonify({'error': 'Payment method not supported'}), 400
        except Exception as e:
            current_app.logger.error(f"Payment service error: {str(e)}")
            return jsonify({'error': f'Payment processing failed: {str(e)}'}), 500
        
        # Validate payment service response
        if not isinstance(result, dict):
            current_app.logger.error(f"Invalid payment service response: {type(result)}")
            return jsonify({'error': 'Invalid payment service response'}), 500
        
        if result.get('success'):
            current_app.logger.info(f"Payment successful for order {order_id}")
            return jsonify({
                'success': True,
                'message': 'Payment processed successfully',
                'payment_id': result.get('payment_id'),
                'transaction_id': result.get('transaction_id')
            })
        else:
            error_msg = result.get('error', 'Payment failed')
            current_app.logger.error(f"Payment failed for order {order_id}: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Unexpected payment processing error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Payment processing failed'}), 500


@payment_bp.route('/success/<payment_id>')
@login_required
def payment_success(payment_id):
    """Payment success page"""
    payment = Payment.query.filter_by(payment_id=payment_id).first_or_404()
    
    # Verify payment belongs to current user
    if payment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    order = payment.order
    invoice = payment.invoice
    
    return render_template('payment/success.html', 
                         payment=payment, 
                         order=order, 
                         invoice=invoice)

@payment_bp.route('/failed/<payment_id>')
@login_required
def payment_failed(payment_id):
    """Payment failed page"""
    payment = Payment.query.filter_by(payment_id=payment_id).first_or_404()
    
    if payment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return render_template('payment/failed.html', payment=payment)

@payment_bp.route('/history')
@login_required
def payment_history():
    """View user's payment history"""
    payments = Payment.query.filter_by(user_id=current_user.id)\
                           .order_by(Payment.created_at.desc())\
                           .all()
    
    return render_template('payment/history.html', payments=payments)

@payment_bp.route('/invoice/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View invoice details"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return render_template('payment/invoice.html', invoice=invoice)

@payment_bp.route('/refund/request', methods=['POST'])
@login_required
def request_refund():
    """Request a refund for a payment"""
    try:
        data = request.get_json()
        payment_id = data.get('payment_id')
        reason = data.get('reason', '')
        amount = data.get('amount')  # Optional for partial refunds
        
        if not payment_id:
            return jsonify({'error': 'Payment ID required'}), 400
        
        payment = Payment.query.get(payment_id)
        if not payment or payment.user_id != current_user.id:
            return jsonify({'error': 'Payment not found or unauthorized'}), 404
        
        if payment.status != 'completed':
            return jsonify({'error': 'Can only refund completed payments'}), 400
        
        # Check if refund already exists
        existing_refund = Refund.query.filter_by(payment_id=payment_id).first()
        if existing_refund:
            return jsonify({'error': 'Refund already requested for this payment'}), 400
        
        # Create refund request (pending admin approval)
        refund = Refund(
            payment_id=payment_id,
            amount=amount or payment.amount,
            reason=reason,
            status='pending'
        )
        
        db.session.add(refund)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Refund request submitted successfully',
            'refund_id': refund.id
        })
        
    except Exception as e:
        current_app.logger.error(f"Refund request error: {str(e)}")
        return jsonify({'error': 'Failed to submit refund request'}), 500

# Admin routes (add proper admin authentication)
@payment_bp.route('/admin/refund/process/<int:refund_id>', methods=['POST'])
@login_required  # Add admin_required decorator
def process_refund_admin(refund_id):
    """Process a refund (admin only)"""
    try:
        refund = Refund.query.get_or_404(refund_id)
        
        if refund.status != 'pending':
            return jsonify({'error': 'Refund already processed'}), 400
        
        result = payment_service.process_refund(
            refund.payment_id, 
            refund.amount, 
            refund.reason
        )
        
        if result['success']:
            refund.processed_by = current_user.id
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Refund processed successfully',
                'transaction_id': result.get('transaction_id')
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Admin refund processing error: {str(e)}")
        return jsonify({'error': 'Failed to process refund'}), 500

@payment_bp.route('/admin/transaction/<transaction_id>')
@login_required  # Add admin_required decorator
def get_transaction_details(transaction_id):
    """Get transaction details from Braintree (admin only)"""
    result = payment_service.get_transaction_details(transaction_id)
    
    if result['success']:
        transaction = result['transaction']
        return jsonify({
            'success': True,
            'transaction': {
                'id': transaction.id,
                'amount': str(transaction.amount),
                'status': transaction.status,
                'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
                'payment_method': transaction.payment_instrument_type
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 404

@payment_bp.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handle Braintree webhook notifications"""
    try:
        webhook_notification = braintree.WebhookNotification.parse(
            request.form["bt_signature"],
            request.form["bt_payload"]
        )
        
        # Import the webhook handler function
        from app.routes.pay_ser import handle_braintree_webhook
        
        if handle_braintree_webhook(webhook_notification):
            return '', 200
        else:
            return '', 400
            
    except Exception as e:
        current_app.logger.error(f"Webhook error: {str(e)}")
        return '', 400

# Utility routes
@payment_bp.route('/status/<payment_id>')
@login_required
def payment_status(payment_id):
    """Get payment status"""
    payment = Payment.query.filter_by(payment_id=payment_id).first_or_404()
    
    if payment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'payment_id': payment.payment_id,
        'status': payment.status,
        'amount': payment.amount,
        'method': payment.method,
        'created_at': payment.created_at.isoformat(),
        'order_id': payment.order_id
    })

@payment_bp.route('/methods')
@login_required
def available_payment_methods():
    """Get available payment methods"""
    return jsonify({
        'methods': [
            {'id': 'credit_card', 'name': 'Credit/Debit Card', 'enabled': True},
            {'id': 'paypal', 'name': 'PayPal', 'enabled': True},
            {'id': 'apple_pay', 'name': 'Apple Pay', 'enabled': True},
            {'id': 'google_pay', 'name': 'Google Pay', 'enabled': True}
        ]
    })
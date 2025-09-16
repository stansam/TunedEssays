import os
import logging
import requests
import base64
import json
import time
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
import paypalrestsdk
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin, urlencode
from app.extensions import db
from app.models.order import Order
from app.models.payment import Payment, Invoice, Transaction, Refund
from app.models.user import User
from dotenv import load_dotenv
load_dotenv("../.env")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create blueprint
payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

# PayPal Configuration
PAYPAL_API_BASE_URL = os.environ.get(
    "PAYPAL_API_BASE_URL", "https://api-m.paypal.com"
)  # https://api-m.paypal.com 
PAYPAL_SDK_BASE_URL = os.environ.get(
    "PAYPAL_SDK_BASE_URL", "https://www.paypal.com"
)  # https://www.paypal.com 
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET")
PAYPAL_MERCHANT_ID = os.environ.get("PAYPAL_MERCHANT_ID")
PAYPAL_BN_CODE = os.environ.get("PAYPAL_BN_CODE")
DOMAINS = os.environ.get("DOMAINS", "localhost:5000")  

def configure_paypal():
    """Configure PayPal SDK with environment variables (for legacy support)"""
    paypal_mode = os.environ.get('PAYPAL_MODE', 'sandbox')  # 'live'
    
    paypalrestsdk.configure({
        "mode": paypal_mode,
        "client_id": PAYPAL_CLIENT_ID,
        "client_secret": PAYPAL_CLIENT_SECRET
    })
    
    logger.info(f"PayPal configured in {paypal_mode} mode")


configure_paypal()

#######################################################################
## Fastlane Token generation helpers
#######################################################################

def get_auth_assertion_token(client_id, merchant_id):
    """Generate PayPal auth assertion token for Fastlane"""
    
    header = {"alg": "none"}
    body = {"iss": client_id, "payer_id": merchant_id}
    signature = ""

    def encode_part(part):
        return base64.urlsafe_b64encode(json.dumps(part).encode()).decode().rstrip("=")

    jwt_parts = [header, body, signature]
    encoded_parts = [encode_part(part) if part else "" for part in jwt_parts]
    auth_assertion = ".".join(encoded_parts)

    return auth_assertion

def get_fastlane_client_token():
    """Get client token for Fastlane SDK initialization"""
    try:
        url = f"{PAYPAL_API_BASE_URL}/v1/oauth2/token"
        auth = HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        logger.info(f"{PAYPAL_CLIENT_ID} \n {PAYPAL_CLIENT_SECRET} \n {url}\n {auth} \n {headers}")
        if PAYPAL_MERCHANT_ID:
            headers["PayPal-Auth-Assertion"] = get_auth_assertion_token(
                PAYPAL_CLIENT_ID, PAYPAL_MERCHANT_ID
            )

        data = {
            "grant_type": "client_credentials"
        }

        response = requests.post(url, headers=headers, data=data, auth=auth)
        response.raise_for_status()
        responseJson = response.json()

        return {
            "clientId": PAYPAL_CLIENT_ID,
            "clientToken": responseJson["access_token"],
            "paypalSdkBaseUrl": PAYPAL_SDK_BASE_URL,
        }
    except Exception as error:
        logger.error(f"Error getting Fastlane client token: {error}")
        return None

def get_fastlane_access_token():
    """Get access token for Fastlane API calls"""
    try:
        url = f"{PAYPAL_API_BASE_URL}/v1/oauth2/token"
        auth = HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        logger.info(f"Using client ID: {PAYPAL_CLIENT_ID[:10]}...")
        logger.info(f"Merchant ID present: {bool(PAYPAL_MERCHANT_ID)}")
        if PAYPAL_MERCHANT_ID:
            # headers["PayPal-Partner-Attribution-ID"] = PAYPAL_BN_CODE
            headers["PayPal-Auth-Assertion"] = get_auth_assertion_token(
                PAYPAL_CLIENT_ID, PAYPAL_MERCHANT_ID
            )

        data = {
            "grant_type": "client_credentials",
        }

        response = requests.post(url, headers=headers, data=data, auth=auth)
        response.raise_for_status()
        responseJson = response.json()

        return responseJson["access_token"]
    except Exception as error:
        logger.error(f"Error getting Fastlane access token: {error}")
        return None

def get_paypal_sdk_url():
    """Generate PayPal SDK URL with Fastlane components"""
    if not PAYPAL_CLIENT_ID:
        raise ValueError("Missing PAYPAL_CLIENT_ID")

    sdk_url = urljoin(PAYPAL_SDK_BASE_URL, "/sdk/js")
    sdk_params = {
        "client-id": PAYPAL_CLIENT_ID,
        "components": "buttons,fastlane",
    }
    sdk_url_with_params = f"{sdk_url}?{urlencode(sdk_params)}"
    return sdk_url_with_params

def create_fastlane_order(payment_token, shipping_address=None, amount=None):
    """Create order using Fastlane payment token"""
    try:
        access_token = get_fastlane_access_token()
        if not access_token:
            raise Exception("Failed to get access token")

        url = f"{PAYPAL_API_BASE_URL}/v2/checkout/orders"
        headers = {
            "PayPal-Request-Id": str(int(time.time())),
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "intent": "CAPTURE",
            "payment_source": {"card": {"single_use_token": payment_token["id"]}},
            "purchase_units": [{"amount": {"currency_code": "USD", "value": f"{amount:.2f}"}}],
        }

        if shipping_address:
            shipping_address_name = shipping_address.get("name", {})
            shipping_address_phone_number = shipping_address.get("phoneNumber", {})

            payload["purchase_units"][0]["shipping"] = {
                "type": "SHIPPING",
                "name": (
                    {"full_name": shipping_address["name"]["fullName"]}
                    if shipping_address_name.get("fullName")
                    else None
                ),
                "company_name": shipping_address.get("companyName"),
                "address": {
                    "address_line_1": shipping_address["address"]["addressLine1"],
                    "address_line_2": shipping_address["address"].get("addressLine2"),
                    "admin_area_2": shipping_address["address"]["adminArea2"],
                    "admin_area_1": shipping_address["address"]["adminArea1"],
                    "postal_code": shipping_address["address"]["postalCode"],
                    "country_code": shipping_address["address"]["countryCode"],
                },
                "phone_number": (
                    {
                        "country_code": shipping_address["phoneNumber"]["countryCode"],
                        "national_number": shipping_address["phoneNumber"]["nationalNumber"],
                    }
                    if shipping_address_phone_number.get("countryCode")
                    and shipping_address_phone_number.get("nationalNumber")
                    else None
                ),
            }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        return result
    except Exception as error:
        logger.error(f"Error creating Fastlane order: {error}")
        raise

#######################################################################
## Routes
#######################################################################

@payment_bp.route('/checkout/<int:order_id>')
@login_required
def checkout(order_id):
    """Display checkout page for an order with Fastlane integration"""
    order = Order.query.get_or_404(order_id)
    if order.client_id != current_user.id:
        flash('Access denied: This order does not belong to you.', 'error')
        return redirect(url_for('orders.list_orders'))
    if order.paid:
        flash('This order has already been paid for.', 'info')
        return redirect(url_for('orders.list_orders'))

    return render_template('client/checkout.html', order=order)
    #try:
     #   order = Order.query.get_or_404(order_id)
        
        # Verify order belongs to current user
      #  if order.client_id != current_user.id:
       #     flash('Access denied: This order does not belong to you.', 'error')
        #    return redirect(url_for('orders.list_orders'))
        
        # Check if order is already paid
        #if order.paid:
         #   flash('This order has already been paid for.', 'info')
          #  return redirect(url_for('orders.list_orders'))
        
        # Check for existing pending payment
#        existing_payment = Payment.query.filter_by(
 #           order_id=order_id,
  #          status='pending'
   #     ).first()
        
    #    if existing_payment:
     #       logger.info(f"Found existing pending payment: {existing_payment.payment_id}")
        
        # Get Fastlane client token and SDK URL
      #  logger.info('Getting client token')
       # client_token_data = get_fastlane_client_token()
        #print(client_token_data)
        #logger.info('Getting sdk url')
       # sdk_url = get_paypal_sdk_url()
        #print(sdk_url)
        #print(client_token_data["clientToken"])
        
       # return render_template('payment/checkout.html',
        #                     order=order, 
         #                    existing_payment=existing_payment,
          #                   client_token_data=client_token_data["clientToken"],
           #                  sdk_url=sdk_url,
            #                 paypal_client_id=PAYPAL_CLIENT_ID)
        
#    except Exception as e:
 #       logger.error(f"Error loading checkout page: {str(e)}")
  #      flash('Error loading checkout page. Please try again.', 'error')
   #     return redirect(url_for('orders.list_orders'))

@payment_bp.route('/create-fastlane', methods=['POST'])
@login_required
def create_fastlane_payment():
    """Create payment using Fastlane"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        payment_token = data.get('paymentToken')
        shipping_address = data.get('shippingAddress')
        
        if not order_id or not payment_token:
            return jsonify({'success': False, 'error': 'Order ID and payment token are required'}), 400
        
        order = Order.query.get_or_404(order_id)
        
        # Verify order belongs to current user
        if order.client_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Check if order is already paid
        if order.paid:
            return jsonify({'success': False, 'error': 'Order already paid'}), 400
        
        # Create Fastlane order
        fastlane_order = create_fastlane_order(
            payment_token=payment_token,
            shipping_address=shipping_address,
            amount=order.total_price
        )
        
        if fastlane_order.get('status') == 'COMPLETED':
            logger.info(f"Fastlane payment completed: {fastlane_order['id']}")
            
            # Save payment record to database
            db_payment = Payment(
                order_id=order_id,
                user_id=current_user.id,
                amount=order.total_price,
                method='fastlane',
                status='completed',
                processor_id=fastlane_order['id']
            )
            
            # Update order status
            order.paid = True
            order.status = 'active'
            
            # Create transaction record
            capture_id = fastlane_order['purchase_units'][0]['payments']['captures'][0]['id']
            transaction = Transaction(
                payment_id=db_payment.id,
                transaction_id=capture_id,
                type='payment',
                amount=order.total_price,
                status='completed',
                processor_id=fastlane_order['id'],
                processor_response=json.dumps(fastlane_order)
            )
            
            # Generate invoice
            invoice = Invoice(
                order_id=order.id,
                user_id=current_user.id,
                payment_id=db_payment.id,
                subtotal=order.total_price,
                total=order.total_price,
                created_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=30),
                paid=True
            )
            
            db.session.add(db_payment)
            db.session.add(transaction)
            db.session.add(invoice)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'payment_id': db_payment.payment_id,
                'order_id': fastlane_order['id']
            })
        else:
            logger.error(f"Fastlane payment not completed: {fastlane_order}")
            return jsonify({
                'success': False,
                'error': 'Payment not completed',
                'details': fastlane_order
            }), 400
            
    except Exception as e:
        logger.error(f"Error creating Fastlane payment: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@payment_bp.route('/create', methods=['POST'])
@login_required
def create_payment():
    """Create PayPal payment (legacy method)"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        payment_method = data.get('payment_method', 'paypal')  # Default to PayPal
        
        if not order_id:
            return jsonify({'success': False, 'error': 'Order ID is required'}), 400
        
        order = Order.query.get_or_404(order_id)
        
        # Verify order belongs to current user
        if order.client_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Check if order is already paid
        if order.paid:
            return jsonify({'success': False, 'error': 'Order already paid'}), 400
        
        # If Fastlane is requested, redirect to Fastlane endpoint
        if payment_method == 'fastlane':
            return create_fastlane_payment()
        
        # Continue with legacy PayPal payment creation
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": request.url_root.rstrip('/') + url_for('payment.execute_payment'),
                "cancel_url": request.url_root.rstrip('/') + url_for('payment.cancel_payment', order_id=order_id)
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"TunedEssays - {order.title[:50]}",
                        "sku": order.order_number,
                        "price": f"{order.total_price:.2f}",
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": f"{order.total_price:.2f}",
                    "currency": "USD"
                },
                "description": f"Payment for order {order.order_number}",
                "custom": str(order.order_number)
            }]
        })
        
        if payment.create():
            logger.info(f"PayPal payment created: {payment.id}")
            
            # Save payment record to database
            db_payment = Payment(
                order_id=order_id,
                user_id=current_user.id,
                amount=order.total_price,
                method='paypal',
                status='pending',
                processor_id=payment.id
            )
            
            db.session.add(db_payment)
            db.session.commit()
            
            # Find approval URL
            approval_url = None
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    break
            
            return jsonify({
                'success': True,
                'payment_id': payment.id,
                'approval_url': approval_url
            })
        else:
            logger.error(f"PayPal payment creation failed: {payment.error}")
            return jsonify({
                'success': False,
                'error': 'Failed to create PayPal payment',
                'details': str(payment.error)
            }), 500
            
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoints for Fastlane SDK
@payment_bp.route('/api/client-token')
@login_required
def get_client_token_api():
    """API endpoint to get client token for Fastlane"""
    try:
        client_token_data = get_fastlane_client_token()
        if client_token_data:
            print(client_token_data)
            return jsonify(client_token_data)
        else:
            return jsonify({'error': 'Failed to get client token'}), 500
    except Exception as e:
        logger.error(f"Error getting client token: {str(e)}")
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/api/sdk-url')
def get_sdk_url_api():
    """API endpoint to get PayPal SDK URL"""
    try:
        sdk_url = get_paypal_sdk_url()
        return jsonify({'url': sdk_url})
    except Exception as e:
        logger.error(f"Error getting SDK URL: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Keep all existing routes (execute_payment, cancel_payment, success, failed, etc.)
@payment_bp.route('/execute')
@login_required
def execute_payment():
    """Execute PayPal payment after user approval (legacy)"""
    try:
        payment_id = request.args.get('paymentId')
        payer_id = request.args.get('PayerID')
        
        if not payment_id or not payer_id:
            flash('Invalid payment parameters.', 'error')
            return redirect(url_for('orders.list_orders'))
        
        # Get payment from PayPal
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if not payment:
            flash('Payment not found.', 'error')
            return redirect(url_for('orders.list_orders'))
        
        # Execute payment
        if payment.execute({"payer_id": payer_id}):
            logger.info(f"PayPal payment executed successfully: {payment_id}")
            
            # Get order_id from custom field
            order_id = payment.transactions[0].custom
            # order = Order.query.get(order_id)
            order = Order.query.filter_by(order_number=order_id).first()

            
            if not order:
                logger.error(f"Order not found: {order_id}")
                flash('Order not found.', 'error')
                return redirect(url_for('orders.list_orders'))
            
            # Update database payment record
            db_payment = Payment.query.filter_by(
                processor_id=payment_id,
                user_id=current_user.id
            ).first()
            
            if db_payment:
                db_payment.status = 'completed'
                db_payment.payer_id = payer_id
                db_payment.processor_response = str(payment.to_dict())
                
                # Update order status
                order.paid = True
                order.status = 'active'
                
                # Create transaction record
                transaction = Transaction(
                    payment_id=db_payment.id,
                    transaction_id=payment.transactions[0].related_resources[0].sale.id,
                    type='payment',
                    amount=order.total_price,
                    status='completed',
                    processor_id=payment_id,
                    processor_response=str(payment.to_dict())
                )
                
                # Generate invoice
                invoice = Invoice(
                    order_id=order.id,
                    user_id=current_user.id,
                    payment_id=db_payment.id,
                    subtotal=order.total_price,
                    total=order.total_price,
                    due_date=datetime.now() + timedelta(days=30),
                    paid=True
                )
                
                db.session.add(transaction)
                db.session.add(invoice)
                db.session.commit()
                
                logger.info(f"Payment completed successfully for order {order.order_number}")
                flash('Payment completed successfully!', 'success')
                
                return redirect(url_for('payment.success', payment_id=db_payment.payment_id))
            else:
                logger.error(f"Database payment record not found for PayPal payment: {payment_id}")
                flash('Payment record not found.', 'error')
                return redirect(url_for('orders.list_orders'))
        else:
            logger.error(f"PayPal payment execution failed: {payment.error}")
            
            # Update payment status to failed
            db_payment = Payment.query.filter_by(
                processor_id=payment_id,
                user_id=current_user.id
            ).first()
            
            if db_payment:
                db_payment.status = 'failed'
                db_payment.processor_response = str(payment.error)
                db.session.commit()
            
            flash('Payment execution failed. Please try again.', 'error')
            return redirect(url_for('payment.failed', payment_id=payment_id))
            
    except Exception as e:
        logger.error(f"Error executing payment: {str(e)}")
        db.session.rollback()
        flash('An error occurred while processing your payment.', 'error')
        return redirect(url_for('orders.list_orders'))

@payment_bp.route('/cancel/<int:order_id>')
@login_required
def cancel_payment(order_id):
    """Handle payment cancellation"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Verify order belongs to current user
        if order.client_id != current_user.id:
            flash('Access denied.', 'error')
            return redirect(url_for('orders.list_orders'))
        
        flash('Payment was cancelled. You can try again anytime.', 'info')
        return redirect(url_for('payment.checkout', order_id=order_id))
        
    except Exception as e:
        logger.error(f"Error handling payment cancellation: {str(e)}")
        flash('An error occurred.', 'error')
        return redirect(url_for('orders.list_orders'))

@payment_bp.route('/success/<payment_id>')
@login_required
def success(payment_id):
    """Display payment success page"""
    try:
        payment = Payment.query.filter_by(
            payment_id=payment_id,
            user_id=current_user.id
        ).first_or_404()
        
        order = payment.order
        invoice = payment.invoice
        
        return render_template('payment/success.html',
                             payment=payment,
                             order=order,
                             invoice=invoice)
        
    except Exception as e:
        logger.error(f"Error loading success page: {str(e)}")
        flash('Error loading payment details.', 'error')
        return redirect(url_for('orders.list_orders'))

@payment_bp.route('/failed/<payment_id>')
@login_required
def failed(payment_id):
    """Display payment failure page"""
    try:
        # Try to find payment by processor_id first (PayPal payment ID)
        payment = Payment.query.filter_by(
            processor_id=payment_id,
            user_id=current_user.id
        ).first()
        
        # If not found, try by our internal payment_id
        if not payment:
            payment = Payment.query.filter_by(
                payment_id=payment_id,
                user_id=current_user.id
            ).first()
        
        if not payment:
            flash('Payment not found.', 'error')
            return redirect(url_for('orders.list_orders'))
        
        return render_template('payment/failed.html', payment=payment)
        
    except Exception as e:
        logger.error(f"Error loading failed payment page: {str(e)}")
        flash('Error loading payment details.', 'error')
        return redirect(url_for('orders.list_orders'))

@payment_bp.route('/invoice/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View invoice details"""
    try:
        invoice = Invoice.query.filter_by(
            id=invoice_id,
            user_id=current_user.id
        ).first_or_404()
        
        return render_template('payment/invoice.html', invoice=invoice)
        
    except Exception as e:
        logger.error(f"Error loading invoice: {str(e)}")
        flash('Error loading invoice.', 'error')
        return redirect(url_for('orders.list_orders'))

@payment_bp.route('/refund/<int:payment_id>', methods=['POST'])
@login_required
def request_refund(payment_id):
    """Request a refund for a payment (admin)"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        data = request.get_json()
        amount = data.get('amount')
        reason = data.get('reason', 'Requested by admin')
        
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.status != 'completed':
            return jsonify({'success': False, 'error': 'Can only refund completed payments'}), 400
        
        # Handle refunds for both Fastlane and legacy PayPal payments
        if payment.method == 'fastlane':
            # Fastlane refund logic would need to be implemented using the v2/payments/captures/{capture_id}/refund endpoint
            # This is a simplified version - you'd need to extract the capture ID from the original transaction
            return jsonify({'success': False, 'error': 'Fastlane refunds not implemented yet'}), 501
        else:
            # Legacy PayPal refund logic (existing code)
            paypal_payment = paypalrestsdk.Payment.find(payment.processor_id)
            
            if not paypal_payment:
                return jsonify({'success': False, 'error': 'PayPal payment not found'}), 404
            
            # Get the sale transaction
            sale_id = None
            for transaction in paypal_payment.transactions:
                for resource in transaction.related_resources:
                    if hasattr(resource, 'sale'):
                        sale_id = resource.sale.id
                        break
            
            if not sale_id:
                return jsonify({'success': False, 'error': 'Sale transaction not found'}), 404
            
            # Create refund
            sale = paypalrestsdk.Sale.find(sale_id)
            refund = sale.refund({
                "amount": {
                    "total": f"{amount:.2f}",
                    "currency": "USD"
                },
                "reason": reason
            })
            
            if refund:
                logger.info(f"PayPal refund created: {refund.id}")
                
                # Create refund record
                db_refund = Refund(
                    payment_id=payment.id,
                    amount=amount,
                    reason=reason,
                    status='processed',
                    processed_by=current_user.id,
                    refund_date=datetime.now(),
                    processor_refund_id=refund.id
                )
                
                # Create transaction record
                transaction = Transaction(
                    payment_id=payment.id,
                    transaction_id=refund.id,
                    type='refund',
                    amount=amount,
                    status='completed',
                    processor_id=refund.id,
                    processor_response=str(refund.to_dict())
                )
                
                db.session.add(db_refund)
                db.session.add(transaction)
                db.session.commit()
                
                return jsonify({'success': True, 'refund_id': refund.id})
            else:
                logger.error(f"PayPal refund failed: {refund.error}")
                return jsonify({
                    'success': False,
                    'error': 'Refund failed',
                    'details': str(refund.error)
                }), 500
            
    except Exception as e:
        logger.error(f"Error processing refund: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle PayPal webhooks"""
    try:
        # PayPal webhook verification would go here
        # This is a simplified version - in production, you should verify the webhook signature
        
        webhook_data = request.get_json()
        event_type = webhook_data.get('event_type')
        
        logger.info(f"Received PayPal webhook: {event_type}")
        
        if event_type == 'PAYMENT.SALE.COMPLETED':
            # Handle successful payment
            resource = webhook_data.get('resource', {})
            payment_id = resource.get('parent_payment')
            
            if payment_id:
                payment = Payment.query.filter_by(processor_id=payment_id).first()
                if payment and payment.status == 'pending':
                    payment.status = 'completed'
                    payment.order.paid = True
                    payment.order.status = 'active'
                    db.session.commit()
                    logger.info(f"Payment updated via webhook: {payment_id}")
        
        elif event_type == 'PAYMENT.SALE.DENIED':
            # Handle failed payment
            resource = webhook_data.get('resource', {})
            payment_id = resource.get('parent_payment')
            
            if payment_id:
                payment = Payment.query.filter_by(processor_id=payment_id).first()
                if payment:
                    payment.status = 'failed'
                    db.session.commit()
                    logger.info(f"Payment marked as failed via webhook: {payment_id}")
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500
    
@payment_bp.route('/history')
@login_required
def payment_history():
    """Display payment history for current user"""
    try:
        payments = Payment.query.filter_by(user_id=current_user.id)\
                                .order_by(Payment.created_at.desc())\
                                .all()
        
        return render_template('payment/history.html', payments=payments)
        
    except Exception as e:
        logger.error(f"Error loading payment history: {str(e)}")
        flash('Error loading payment history.', 'error')
        return redirect(url_for('orders.list_orders'))

@payment_bp.route('/admin/payments')
@login_required
def admin_payments():
    """Admin view of all payments"""
    try:
        if not current_user.is_admin:
            flash('Access denied.', 'error')
            return redirect(url_for('main.index'))
        
        payments = Payment.query.order_by(Payment.created_at.desc()).all()
        
        return render_template('payment/admin_payments.html', payments=payments)
        
    except Exception as e:
        logger.error(f"Error loading admin payments: {str(e)}")
        flash('Error loading payments.', 'error')
        return redirect(url_for('main.index'))

@payment_bp.route('/admin/transactions')
@login_required
def admin_transactions():
    """Admin view of all transactions"""
    try:
        if not current_user.is_admin:
            flash('Access denied.', 'error')
            return redirect(url_for('main.index'))
        
        transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
        
        return render_template('payment/admin_transactions.html', transactions=transactions)
        
    except Exception as e:
        logger.error(f"Error loading admin transactions: {str(e)}")
        flash('Error loading transactions.', 'error')
        return redirect(url_for('main.index'))

@payment_bp.route('/admin/refunds')
@login_required
def admin_refunds():
    """Admin view of all refunds"""
    try:
        if not current_user.is_admin:
            flash('Access denied.', 'error')
            return redirect(url_for('main.index'))
        
        refunds = Refund.query.order_by(Refund.created_at.desc()).all()
        
        return render_template('payment/admin_refunds.html', refunds=refunds)
        
    except Exception as e:
        logger.error(f"Error loading admin refunds: {str(e)}")
        flash('Error loading refunds.', 'error')
        return redirect(url_for('main.index'))

@payment_bp.route('/status/<payment_id>')
@login_required
def payment_status(payment_id):
    """Get payment status (API endpoint)"""
    try:
        payment = Payment.query.filter_by(
            payment_id=payment_id,
            user_id=current_user.id
        ).first_or_404()
        
        return jsonify({
            'success': True,
            'status': payment.status,
            'amount': float(payment.amount),
            'method': payment.method,
            'created_at': payment.created_at.isoformat(),
            'order_id': payment.order_id
        })
        
    except Exception as e:
        logger.error(f"Error getting payment status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Error handlers
@payment_bp.errorhandler(404)
def payment_not_found(error):
    """Handle 404 errors in payment blueprint"""
    flash('Payment not found.', 'error')
    return redirect(url_for('orders.list_orders'))

@payment_bp.errorhandler(500)
def payment_server_error(error):
    """Handle 500 errors in payment blueprint"""
    logger.error(f"Payment server error: {str(error)}")
    flash('An error occurred while processing your request.', 'error')
    return redirect(url_for('orders.list_orders'))

# Helper functions for payment validation
def validate_payment_amount(amount, order_total):
    """Validate payment amount matches order total"""
    return abs(float(amount) - float(order_total)) < 0.01

def generate_payment_reference():
    """Generate unique payment reference"""
    import uuid
    return f"PAY_{uuid.uuid4().hex[:12].upper()}"

def is_payment_expired(payment, hours=24):
    """Check if payment has expired (for pending payments)"""
    if payment.status != 'pending':
        return False
    
    expiry_time = payment.created_at + timedelta(hours=hours)
    return datetime.now() > expiry_time

# Context processor for payment-related template variables
@payment_bp.app_context_processor
def inject_payment_vars():
    """Inject payment-related variables into templates"""
    return {
        'paypal_client_id': PAYPAL_CLIENT_ID,
        'paypal_sdk_url': get_paypal_sdk_url() if PAYPAL_CLIENT_ID else None
    }

import braintree
import braintree.exceptions
from flask import current_app
from datetime import datetime, timedelta
from app.extensions import db
from app.config import Config
from app.models.payment import Payment, Invoice, Transaction, Refund
from app.models.order import Order  
import logging
from flask_login import current_user

# Configure the gateway at module level
gateway = braintree.BraintreeGateway(braintree.Configuration(
    braintree.Environment.Sandbox,  # or Config.BRAIN_TREE_ENVIRONMENT
    merchant_id=Config.BRAIN_TREE_MERCHANT_ID,
    public_key=Config.BRAIN_TREE_PUBLIC_KEY,
    private_key=Config.BRAIN_TREE_PRIVATE_KEY
))

class BraintreePaymentService:
    
    def __init__(self):
        self.gateway = gateway  # Use the module-level gateway
        self.logger = logging.getLogger(__name__)
    
    def generate_client_token(self, customer_id=None):
        """Generate client token for Braintree Drop-in UI"""
        try:
            self.logger.info(f"Generating client token for customer: {customer_id}")
            client_token = self.gateway.client_token.generate()
            self.logger.info("Generated client token without customer ID")
            return client_token
                    
        except braintree.exceptions.AuthenticationError as e:
            self.logger.error(f"Braintree authentication error: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error generating client token: {str(e)}")
            return None
    
    def create_customer(self, user_id, email, first_name, last_name, phone=None):
        """Create a customer in Braintree"""
        try:
            result = self.gateway.customer.create({
                "id": str(user_id),
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone
            })
            
            if result.is_success:
                return result.customer
            else:
                self.logger.error(f"Error creating customer: {result.message}")
                return None
        except Exception as e:
            self.logger.error(f"Error creating customer: {str(e)}")
            return None
    
    def process_payment(self, order_id, payment_method_nonce, amount, user_id, device_data, order_number):
        """Process a payment using Braintree"""
        try:
            # Create payment record
            payment = Payment(
                order_id=order_id,
                user_id=user_id,
                amount=amount,
                method='credit_card',  # Default, can be updated based on payment method
                status='pending'
            )
            db.session.add(payment)
            db.session.flush()  # Get the payment ID
            formatted_amount = "{:.2f}".format(amount)
            # Process payment with Braintree using gateway
            result = self.gateway.transaction.sale({
                "amount": str(formatted_amount),
                "payment_method_nonce": payment_method_nonce,
                "device_data": device_data,
                "options": {
                    "submit_for_settlement": True
                },
                "custom_fields": {
                    "order_number": str(order_number),
                    "payment_id": payment.payment_id
                }
            })
            
            if result.is_success:
                transaction = result.transaction
                
                # Update payment with Braintree transaction details
                payment.processor_id = transaction.id
                payment.status = 'completed'
                payment.processor_response = str(transaction.status)
                payment.method = self._get_payment_method_type(transaction)
                
                # Create transaction record
                transaction_record = Transaction(
                    payment_id=payment.id,
                    transaction_id=transaction.id,
                    type='payment',
                    amount=float(transaction.amount),
                    status=transaction.status,
                    processor_id=transaction.id,
                    processor_response=str(transaction)
                )
                db.session.add(transaction_record)
                
                # Update order payment status
                order = Order.query.get(order_id)
                if order:
                    order.paid = True
                    order.status = 'active'  # or whatever status indicates paid
                
                # Generate invoice
                self._generate_invoice(payment, order)
                
                db.session.commit()
                
                return {
                    'success': True,
                    'payment_id': payment.payment_id,
                    'transaction_id': transaction.id,
                    'status': transaction.status
                }
            else:
                # Payment failed
                payment.status = 'failed'
                payment.processor_response = result.message
                db.session.commit()
                
                return {
                    'success': False,
                    'error': result.message,
                    'payment_id': payment.payment_id
                }
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error processing payment: {str(e)}")
            return {
                'success': False,
                'error': 'Payment processing failed. Please try again.'
            }
    
    def process_paypal_payment(self, order_id, payment_method_nonce, amount, user_id):
        """Process PayPal payment"""
        try:
            payment = Payment(
                order_id=order_id,
                user_id=user_id,
                amount=amount,
                method='paypal',
                status='pending'
            )
            db.session.add(payment)
            db.session.flush()
            
            result = self.gateway.transaction.sale({
                "amount": str(amount),
                "payment_method_nonce": payment_method_nonce,
                "options": {
                    "submit_for_settlement": True,
                    "paypal": {
                        "description": f"Order #{order_id} - Paper Writing Service"
                    }
                }
            })
            
            if result.is_success:
                transaction = result.transaction
                payment.processor_id = transaction.id
                payment.status = 'completed'
                payment.processor_response = str(transaction.status)
                
                # Create transaction record
                transaction_record = Transaction(
                    payment_id=payment.id,
                    transaction_id=transaction.id,
                    type='payment',
                    amount=float(transaction.amount),
                    status=transaction.status,
                    processor_id=transaction.id
                )
                db.session.add(transaction_record)
                
                # Update order
                order = Order.query.get(order_id)
                if order:
                    order.paid = True
                    order.status = 'active'
                
                self._generate_invoice(payment, order)
                db.session.commit()
                
                return {
                    'success': True,
                    'payment_id': payment.payment_id,
                    'transaction_id': transaction.id
                }
            else:
                payment.status = 'failed'
                payment.processor_response = result.message
                db.session.commit()
                return {'success': False, 'error': result.message}
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error processing PayPal payment: {str(e)}")
            return {'success': False, 'error': 'PayPal payment failed'}
    
    def process_apple_pay_payment(self, order_id, payment_method_nonce, amount, user_id):
        """Process Apple Pay payment"""
        return self._process_digital_wallet_payment(
            order_id, payment_method_nonce, amount, user_id, 'apple_pay'
        )
    
    def process_google_pay_payment(self, order_id, payment_method_nonce, amount, user_id):
        """Process Google Pay payment"""
        return self._process_digital_wallet_payment(
            order_id, payment_method_nonce, amount, user_id, 'google_pay'
        )
    
    def _process_digital_wallet_payment(self, order_id, payment_method_nonce, amount, user_id, method):
        """Generic digital wallet payment processing"""
        try:
            payment = Payment(
                order_id=order_id,
                user_id=user_id,
                amount=amount,
                method=method,
                status='pending'
            )
            db.session.add(payment)
            db.session.flush()
            
            result = self.gateway.transaction.sale({
                "amount": str(amount),
                "payment_method_nonce": payment_method_nonce,
                "options": {
                    "submit_for_settlement": True
                }
            })
            
            if result.is_success:
                transaction = result.transaction
                payment.processor_id = transaction.id
                payment.status = 'completed'
                payment.processor_response = str(transaction.status)
                
                transaction_record = Transaction(
                    payment_id=payment.id,
                    transaction_id=transaction.id,
                    type='payment',
                    amount=float(transaction.amount),
                    status=transaction.status,
                    processor_id=transaction.id
                )
                db.session.add(transaction_record)
                
                order = Order.query.get(order_id)
                if order:
                    order.paid = True
                    order.status = 'active'
                
                self._generate_invoice(payment, order)
                db.session.commit()
                
                return {
                    'success': True,
                    'payment_id': payment.payment_id,
                    'transaction_id': transaction.id
                }
            else:
                payment.status = 'failed'
                payment.processor_response = result.message
                db.session.commit()
                return {'success': False, 'error': result.message}
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error processing {method} payment: {str(e)}")
            return {'success': False, 'error': f'{method} payment failed'}
        
    def process_venmo_payment(self, order_id, payment_method_nonce, amount, user_id, device_data=None, order_number=None):
        """Process Venmo payment"""
        try:
            payment = Payment(
                order_id=order_id,
                user_id=user_id,
                amount=amount,
                method='venmo',
                status='pending'
            )
            db.session.add(payment)
            db.session.flush()
            
            formatted_amount = "{:.2f}".format(amount)
            
            # Venmo-specific transaction options
            transaction_options = {
                "submit_for_settlement": True
            }
            
            # Add device data if available (important for fraud detection with Venmo)
            transaction_data = {
                "amount": str(formatted_amount),
                "payment_method_nonce": payment_method_nonce,
                "device_data": device_data,
                "options": transaction_options
            }
            
            if device_data:
                transaction_data["device_data"] = device_data
                
            if order_number:
                transaction_data["custom_fields"] = {
                    "order_number": str(order_number),
                    "payment_id": payment.payment_id
                }
            
            result = self.gateway.transaction.sale(transaction_data)
            
            if result.is_success:
                transaction = result.transaction
                payment.processor_id = transaction.id
                payment.status = 'completed'
                payment.processor_response = str(transaction.status)
                
                # Create transaction record
                transaction_record = Transaction(
                    payment_id=payment.id,
                    transaction_id=transaction.id,
                    type='payment',
                    amount=float(transaction.amount),
                    status=transaction.status,
                    processor_id=transaction.id,
                    processor_response=str(transaction)
                )
                db.session.add(transaction_record)
                
                # Update order
                order = Order.query.get(order_id)
                if order:
                    order.paid = True
                    order.status = 'active'
                
                self._generate_invoice(payment, order)
                db.session.commit()
                
                return {
                    'success': True,
                    'payment_id': payment.payment_id,
                    'transaction_id': transaction.id,
                    'status': transaction.status
                }
            else:
                payment.status = 'failed'
                payment.processor_response = result.message
                db.session.commit()
                return {'success': False, 'error': result.message, 'payment_id': payment.payment_id}
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error processing Venmo payment: {str(e)}")
            return {'success': False, 'error': 'Venmo payment failed'}
    
    def process_refund(self, payment_id, amount=None, reason=None):
        """Process a refund for a payment"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment or not payment.processor_id:
                return {'success': False, 'error': 'Payment not found or not processed'}
            
            # Create refund record
            refund = Refund(
                payment_id=payment_id,
                amount=amount or payment.amount,
                reason=reason,
                status='pending'
            )
            db.session.add(refund)
            db.session.flush()
            
            # Process refund with Braintree using gateway
            if amount and amount < payment.amount:
                # Partial refund
                result = self.gateway.transaction.refund(payment.processor_id, amount)
            else:
                # Full refund
                result = self.gateway.transaction.refund(payment.processor_id)
            
            if result.is_success:
                refund_transaction = result.transaction
                refund.status = 'processed'
                refund.refund_date = datetime.now()
                
                # Create transaction record for refund
                transaction_record = Transaction(
                    payment_id=payment_id,
                    transaction_id=refund_transaction.id,
                    type='refund',
                    amount=float(refund_transaction.amount),
                    status=refund_transaction.status,
                    processor_id=refund_transaction.id
                )
                db.session.add(transaction_record)
                
                # Update payment status if fully refunded
                if not amount or amount >= payment.amount:
                    payment.status = 'refunded'
                
                db.session.commit()
                
                return {
                    'success': True,
                    'refund_id': refund.id,
                    'transaction_id': refund_transaction.id
                }
            else:
                refund.status = 'denied'
                db.session.commit()
                return {'success': False, 'error': result.message}
                
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error processing refund: {str(e)}")
            return {'success': False, 'error': 'Refund processing failed'}
    
    def get_transaction_details(self, transaction_id):
        """Get transaction details from Braintree"""
        try:
            transaction = self.gateway.transaction.find(transaction_id)
            return {
                'success': True,
                'transaction': transaction
            }
        except Exception as e:
            self.logger.error(f"Error fetching transaction: {str(e)}")
            return {'success': False, 'error': 'Transaction not found'}
    
    def void_transaction(self, payment_id):
        """Void a transaction (only possible before settlement)"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment or not payment.processor_id:
                return {'success': False, 'error': 'Payment not found'}
            
            result = self.gateway.transaction.void(payment.processor_id)
            
            if result.is_success:
                payment.status = 'failed'
                
                # Create transaction record for void
                transaction_record = Transaction(
                    payment_id=payment_id,
                    transaction_id=result.transaction.id,
                    type='void',
                    amount=payment.amount,
                    status='voided',
                    processor_id=result.transaction.id
                )
                db.session.add(transaction_record)
                db.session.commit()
                
                return {'success': True, 'transaction_id': result.transaction.id}
            else:
                return {'success': False, 'error': result.message}
                
        except Exception as e:
            self.logger.error(f"Error voiding transaction: {str(e)}")
            return {'success': False, 'error': 'Void failed'}
    
    def _get_payment_method_type(self, transaction):
        """Determine payment method type from Braintree transaction"""
        if hasattr(transaction, 'paypal_details') and transaction.paypal_details:
            return 'paypal'
        elif hasattr(transaction, 'venmo_account_details') and transaction.venmo_account_details:
            return 'venmo'
        elif hasattr(transaction, 'apple_pay_details') and transaction.apple_pay_details:
            return 'apple_pay'
        elif hasattr(transaction, 'google_pay_details') and transaction.google_pay_details:
            return 'google_pay'
        else:
            return 'credit_card'
    
    def _generate_invoice(self, payment, order):
        """Generate invoice for completed payment"""
        try:
            # Check if invoice already exists
            existing_invoice = Invoice.query.filter_by(order_id=order.id).first()
            if existing_invoice:
                existing_invoice.payment_id = payment.id
                existing_invoice.paid = True
                return existing_invoice
            
            # Calculate due date (typically immediate for online payments)
            due_date = datetime.now()
            
            # Create new invoice
            invoice = Invoice(
                order_id=order.id,
                user_id=order.client_id,
                subtotal=order.total_price,
                total=order.total_price,
                due_date=due_date,
                payment_id=payment.id,
                paid=True
            )
            
            db.session.add(invoice)
            return invoice
            
        except Exception as e:
            self.logger.error(f"Error generating invoice: {str(e)}")
            return None

# Webhook handler for Braintree notifications
def handle_braintree_webhook(webhook_notification):
    """Handle Braintree webhook notifications"""
    try:
        if webhook_notification.kind == braintree.WebhookNotification.Kind.TransactionDisbursed:
            # Transaction has been disbursed
            transaction = webhook_notification.transaction
            payment = Payment.query.filter_by(processor_id=transaction.id).first()
            if payment:
                # Update payment status or handle disbursement
                pass
                
        elif webhook_notification.kind == braintree.WebhookNotification.Kind.TransactionSettled:
            # Transaction has been settled
            transaction = webhook_notification.transaction
            payment = Payment.query.filter_by(processor_id=transaction.id).first()
            if payment:
                # Update payment status
                payment.status = 'completed'
                db.session.commit()
                
        elif webhook_notification.kind == braintree.WebhookNotification.Kind.TransactionSettlementDeclined:
            # Transaction settlement was declined
            transaction = webhook_notification.transaction
            payment = Payment.query.filter_by(processor_id=transaction.id).first()
            if payment:
                payment.status = 'failed'
                db.session.commit()
                
        return True
        
    except Exception as e:
        logging.error(f"Error handling webhook: {str(e)}")
        return False
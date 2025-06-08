from app.extensions import db
from datetime import datetime
import uuid
from sqlalchemy.sql import func

class Payment(db.Model):
    """Model for tracking payments"""
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(100), unique=True, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    payment_method_token = db.Column(db.String(255))
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded
    method = db.Column(db.String(20), nullable=False)  # credit_card, paypal, apple_pay, google_pay
    
    # Payment processor info
    processor_id = db.Column(db.String(255))
    processor_response = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    order = db.relationship('Order', back_populates='payments')
    user = db.relationship('User', backref=db.backref('payments', lazy=True))
    transactions = db.relationship('Transaction', backref='payment', lazy=True)
    invoice = db.relationship('Invoice', back_populates='payment', uselist=False)
    
    def __init__(self, order_id, user_id, amount, method, status='pending', processor_id=None, processor_response=None):
        self.payment_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        self.order_id = order_id
        self.user_id = user_id
        self.amount = amount
        self.status = status
        self.method = method
        self.processor_id = processor_id
        self.processor_response = processor_response
    
    def __repr__(self):
        return f"Payment {self.payment_id} for Order {self.order_id}"

class Invoice(db.Model):
    """Model for invoices"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    
    subtotal = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    due_date = db.Column(db.DateTime, nullable=False)
    paid = db.Column(db.Boolean, default=False)
    
    # Relationships
    order = db.relationship('Order', back_populates='invoice')
    user = db.relationship('User', backref=db.backref('invoices', lazy=True))
    payment = db.relationship('Payment', back_populates='invoice')
    
    def __init__(self, order_id, user_id, subtotal, total, due_date, payment_id=None, discount=0, tax=0, paid=False):
        # Generate invoice number: INV-YYYYMM-NNNN
        year_month = datetime.now().strftime('%Y%m')
        # Get count of invoices in this month and year
        count = Invoice.query.filter(
            func.strftime('%Y%m', Invoice.created_at) == year_month
        ).count() + 1
        
        self.invoice_number = f"INV-{year_month}-{count:04d}"
        self.order_id = order_id
        self.user_id = user_id
        self.payment_id = payment_id
        self.subtotal = subtotal
        self.discount = discount
        self.tax = tax
        self.total = total
        self.due_date = due_date
        self.paid = paid
    
    def __repr__(self):
        return f"Invoice {self.invoice_number}"

class Transaction(db.Model):
    """Model for tracking payment transactions"""
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # payment, refund, chargeback
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    
    processor_id = db.Column(db.String(255))
    processor_response = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __init__(self, payment_id, transaction_id, type, amount, status, processor_id=None, processor_response=None):
        self.payment_id = payment_id
        self.transaction_id = transaction_id
        self.type = type
        self.amount = amount
        self.status = status
        self.processor_id = processor_id
        self.processor_response = processor_response
    
    def __repr__(self):
        return f"{self.type.title()} of {self.amount} for Payment #{self.payment_id}"
    
class Discount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(200))
    discount_type = db.Column(db.String(20), default='percentage')  # percentage, fixed
    amount = db.Column(db.Float, nullable=False)  # percentage or fixed amount
    min_order_value = db.Column(db.Float, default=0)
    max_discount_value = db.Column(db.Float)
    valid_from = db.Column(db.DateTime, default=datetime.now)
    valid_to = db.Column(db.DateTime)
    usage_limit = db.Column(db.Integer)
    times_used = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    orders = db.relationship('Order', secondary='order_discount', backref='discounts')
    
    def __repr__(self):
        return f'<Discount {self.code}>'

# Association table for many-to-many relationship between Order and Discount
order_discount = db.Table('order_discount',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id'), primary_key=True),
    db.Column('discount_id', db.Integer, db.ForeignKey('discount.id'), primary_key=True)
)

class Refund(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, processed, denied
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    refund_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    payment = db.relationship('Payment', backref='refunds')
    admin = db.relationship('User', backref='processed_refunds')
    
    def __repr__(self):
        return f'<Refund {self.id}>'
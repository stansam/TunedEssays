from app.extensions import db
from datetime import datetime, timedelta
from uuid import uuid4
from app.models.user import User
from app.models.price import PriceRate
from app.models.service import Service
from app.models.order_delivery import OrderDelivery, OrderDeliveryFile



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    academic_level_id = db.Column(db.Integer, db.ForeignKey('academic_level.id'), nullable=False)
    deadline_id = db.Column(db.Integer, db.ForeignKey('deadline.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    word_count = db.Column(db.Integer, nullable=False)
    page_count = db.Column(db.Float, nullable=False)
    format_style = db.Column(db.Text, default=False)
    report_type =db.Column(db.String,default=False, nullable=True)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="pending")
    paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    due_date = db.Column(db.DateTime, nullable=False)
    writer_is_assigned = db.Column(db.Boolean, default=False)
    writer_assigned_at = db.Column(db.DateTime)
    extension_requested = db.Column(db.Boolean, default=False)
    extension_requested_at = db.Column(db.DateTime)
    
    # Relationships
    files = db.relationship('OrderFile', backref='order', lazy=True)
    payments = db.relationship('Payment', back_populates='order', lazy=True)
    invoice = db.relationship('Invoice', back_populates='order', uselist=False)
    comments = db.relationship('OrderComment', backref='order', lazy=True, cascade="all, delete-orphan")
    deliveries = db.relationship('OrderDelivery', backref='order', lazy=True, cascade="all, delete-orphan")
    @property
    def status_color(self):
        colors = {
            'pending': 'secondary',
            'active': 'primary',
            'completed pending review': 'success',
            'completed': 'success',
            'overdue': 'danger',
            'canceled': 'dark',
            'revision': 'info',
        }
        return colors.get(self.status, 'warning')
    
    @staticmethod
    def generate_order_number():
        return f'ORD-{uuid4().hex[:8].upper()}'
    @property
    def latest_delivery(self):
        """Get the most recent delivery for this order"""
        return OrderDelivery.query.filter_by(order_id=self.id).order_by(OrderDelivery.delivered_at.desc()).first()

    @property
    def is_delivered(self):
        """Check if order has been delivered"""
        return self.latest_delivery is not None
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order_number = self.generate_order_number()
    
       
    def __repr__(self):
        return f'<Order {self.order_number}>'
    
class OrderFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    # file_category = db.Column(db.String(255), nullable=False)
    # file_type = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.now)
    is_from_client = db.Column(db.Boolean, default=True)
    
    @property
    def file_size(self):
        """
        Return size in bytes of the file on disk, or 0 if missing.
        """
        import os
        try:
            return os.path.getsize(self.file_path)
        except (OSError, TypeError):
            return 0
    
    # @property
    # def is_from_client(self):
    #     user = User.query.get(self.uploaded_by)
    #     return not user.is_admin
    
    def __repr__(self):
        return f'<OrderFile {self.filename}>'

class OrderComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    message = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationship
    user = db.relationship('User', backref='order_comments')
    
    def __repr__(self):
        return f'<OrderComment {self.id}>'


class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, closed, in_progress
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    order = db.relationship('Order', backref='support_tickets')
    user = db.relationship('User', backref='support_tickets')
    
    def __repr__(self):
        return f'<SupportTicket {self.id} for Order {self.order_id}>'
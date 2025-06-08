from datetime import datetime
from app.extensions import db

class OrderDelivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    delivery_status = db.Column(db.String(20), default='delivered')  # delivered, revised, redelivered
    delivered_at = db.Column(db.DateTime, default=datetime.now)
    client_notified = db.Column(db.Boolean, default=False)  # Whether client was notified
    client_notified_at = db.Column(db.DateTime)
        
    # Relationships
    delivery_files = db.relationship('OrderDeliveryFile', backref='delivery', lazy=True, cascade="all, delete-orphan")
    
    @property
    def has_plagiarism_report(self):
        """Check if delivery includes a plagiarism report file"""
        return any(file.file_type == 'plagiarism_report' for file in self.delivery_files)
    
    @property
    def delivery_files_count(self):
        """Count of main delivery files (excluding plagiarism reports)"""
        return len([file for file in self.delivery_files if file.file_type == 'delivery'])
    
    @property
    def status_color(self):
        colors = {
            'delivered': 'success',
            'revised': 'warning', 
            'redelivered': 'info'
        }
        return colors.get(self.delivery_status, 'secondary')
    
    def __repr__(self):
        return f'<OrderDelivery Order:{self.order_id} Status:{self.delivery_status}>'


class OrderDeliveryFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('order_delivery.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)  # Original name before any processing
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # 'delivery', 'plagiarism_report', 'supplementary'
    file_format = db.Column(db.String(10))  # pdf, docx, txt, etc.
    uploaded_at = db.Column(db.DateTime, default=datetime.now)
    description = db.Column(db.Text)  # Optional description of the file
    
    @property
    def file_size(self):
        """Return size in bytes of the file on disk, or 0 if missing."""
        import os
        try:
            return os.path.getsize(self.file_path)
        except (OSError, TypeError):
            return 0
    
    @property
    def file_size_mb(self):
        """Return file size in MB rounded to 2 decimal places"""
        size_bytes = self.file_size
        return round(size_bytes / (1024 * 1024), 2) if size_bytes > 0 else 0
    
    @property
    def is_plagiarism_report(self):
        """Check if this file is a plagiarism report"""
        return self.file_type == 'plagiarism_report'
    
    @property
    def file_icon(self):
        """Return appropriate icon class based on file format"""
        icons = {
            'pdf': 'fa-file-pdf',
            'docx': 'fa-file-word',
            'doc': 'fa-file-word',
            'txt': 'fa-file-text',
            'zip': 'fa-file-archive',
            'rar': 'fa-file-archive'
        }
        return icons.get(self.file_format, 'fa-file')
    
    def __repr__(self):
        return f'<OrderDeliveryFile {self.filename} Type:{self.file_type}>'
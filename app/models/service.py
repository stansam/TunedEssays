from app.extensions import db
from datetime import datetime

class ServiceCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    
    services = db.relationship('Service', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ServiceCategory {self.name}>'
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'order': self.order
        }

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('service_category.id'))
    featured = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(255), nullable=True) 
    pricing_category_id = db.Column(db.Integer, db.ForeignKey('pricing_category.id'))
    
    orders = db.relationship('Order', backref='service', lazy=True)
    samples = db.relationship('Sample', backref='service', lazy=True)
    testimonials = db.relationship('Testimonial', backref='service', lazy=True)
    pricing_category = db.relationship('PricingCategory', back_populates='service')
    
    
    def __repr__(self):
        return f'<Service {self.name}>'
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category_id': self.category_id,
            'featured': self.featured,
            'tags': self.tags,
            'pricing_category_id': self.pricing_category_id
        }
    def get_tags(self):
        """
        Return a list of tags for the service.
        """
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []

class AcademicLevel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)
    
    orders = db.relationship('Order', backref='academic_level', lazy=True)
    price_rates = db.relationship('PriceRate', backref='academic_level', lazy=True)
    
    def __repr__(self):
        return f'<AcademicLevel {self.name}>'
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'order': self.order
        }
    

class Deadline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hours = db.Column(db.Integer, nullable=False)
    order = db.Column(db.Integer, default=0)
    
    orders = db.relationship('Order', backref='deadline', lazy=True)
    price_rates = db.relationship('PriceRate', backref='deadline', lazy=True)
    
    def __repr__(self):
        return f'<Deadline {self.name}>'
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'hours': self.hours,
            'order': self.order
        }
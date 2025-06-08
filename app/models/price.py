from app.extensions import db
from datetime import datetime

class PricingCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    
    # Relationships
    service = db.relationship('Service', back_populates='pricing_category', lazy=True)
    price_rates = db.relationship('PriceRate', back_populates='pricing_category', lazy=True)
    
    def __repr__(self):
        return f'<PricingCategory {self.name}>'
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'display_order': self.display_order
        }

class PriceRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pricing_category_id = db.Column(db.Integer, db.ForeignKey('pricing_category.id'), nullable=False)
    academic_level_id = db.Column(db.Integer, db.ForeignKey('academic_level.id'), nullable=False)
    deadline_id = db.Column(db.Integer, db.ForeignKey('deadline.id'), nullable=False)
    price_per_page = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        db.UniqueConstraint('pricing_category_id', 'academic_level_id', 'deadline_id'),
    )
    pricing_category = db.relationship("PricingCategory", back_populates="price_rates")
    # pricing_category = db.relationship("PricingCategory", back_populates="price_rates")
    # academic_level = db.relationship("AcademicLevel", back_populates="price_rates")
    # deadline = db.relationship("Deadline", back_populates="price_rates")
    
    
    def __repr__(self):
        return f'<PriceRate for Category {self.pricing_category_id}, Level {self.academic_level_id}, Deadline {self.deadline_id}>'

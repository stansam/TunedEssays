from app.extensions import db
from datetime import datetime

class Sample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    word_count = db.Column(db.Integer, default=0)
    featured = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(255), nullable=True) 
    image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Sample {self.title}>'

class Testimonial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'))
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5) # 1-5 rating scale
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='valid_rating'),
    )

    def __repr__(self):
        return f'<Testimonial by {self.user.username}>'

class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), default='General')
    order = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<FAQ {self.question[:30]}...>'
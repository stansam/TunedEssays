from app.extensions import db
from datetime import datetime

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    code = db.Column(db.String(10), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')
    commission = db.Column(db.Float, default=0.0) #earnings
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Referral {self.code}>'
from app.extensions import db
from datetime import datetime

class PlagiarismCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    content = db.Column(db.Text)
    result = db.Column(db.JSON)
    similarity_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    order = db.relationship('Order', backref='plagiarism_checks')
    
    def __repr__(self):
        return f'<PlagiarismCheck for Order {self.order_id}>'

class CitationGenerator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_text = db.Column(db.Text)
    style = db.Column(db.String(20))  # APA, MLA, Chicago
    generated_citation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<CitationGenerator {self.id} - {self.style}>'

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'))
    content = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref='chat_messages')
    
    def __repr__(self):
        return f'<ChatMessage {self.id} by {"AI" if self.is_ai else "User"}>'
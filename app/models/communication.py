from app.extensions import db
from datetime import datetime

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<ContactMessage {self.subject}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='info')  # info, success, warning, error
    link = db.Column(db.String(255),    nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def mark_as_read(self):
        self.is_read = True
        from app.extensions import db
        db.session.commit()
    
    def to_dict(self):
        return {
            'id':         self.id,
            'title':      self.title,
            'message':    self.message,
            'type':       self.type,
            'link':       self.link,
            'is_read':    self.is_read,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Notification {self.title}>'

class NewsletterSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<NewsletterSubscriber {self.email}>'
    
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject = db.Column(db.String(255))
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    status = db.Column(db.String(20), default='active')  # active, closed
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    messages = db.relationship('ChatMessage', backref='chat', lazy="dynamic", cascade="all, delete-orphan")
    user = db.relationship('User', foreign_keys=[user_id], backref='user_chats')
    admin = db.relationship('User', foreign_keys=[admin_id], backref='admin_chats')
    order = db.relationship('Order', backref='chats')
    
    def __repr__(self):
        return f'<Chat {self.id}>'

# class ChatMessage(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
#     content = db.Column(db.Text, nullable=False)
#     is_admin = db.Column(db.Boolean, default=False)
#     is_read = db.Column(db.Boolean, default=False)
#     created_at = db.Column(db.DateTime, default=datetime.now)
    
#     # Relationships
#     user = db.relationship('User', backref='chat_messages')
    
#     def __repr__(self):
#         return f'<ChatMessage {self.id}>'
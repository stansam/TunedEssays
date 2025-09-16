from app.extensions import db
from datetime import datetime

class BlogCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    # Relationships
    posts = db.relationship('BlogPost', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<BlogCategory {self.name}>'

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    featured_image = db.Column(db.String(255))
    tags = db.Column(db.String(255))  # Comma-separated tags
    author = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('blog_category.id'))
    meta_description = db.Column(db.String(220))
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    published_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<BlogPost {self.title}>'

class BlogComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'))
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    content = db.Column(db.Text, nullable=False)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationship
    user = db.relationship('User', backref='blog_comments')
    
    def __repr__(self):
        return f'<BlogComment {self.id}>'
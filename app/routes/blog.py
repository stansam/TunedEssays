from flask import Blueprint, render_template, request
from app.models.blog import BlogPost, BlogCategory
from datetime import datetime

blog_bp = Blueprint('blog', __name__)

@blog_bp.route('/')
@blog_bp.route('/page/<int:page>')
def index(page=1):
    posts_query = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.published_at.desc())
    pagination = posts_query.paginate(page=page, per_page=6, error_out=False)
    posts = pagination.items

    # Get featured post (can be the most recent one)
    featured_post = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.published_at.desc()).first()

    # Get recent posts for sidebar
    recent_posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.published_at.desc()).limit(5).all()

    # Get all categories
    categories = BlogCategory.query.all()

    return render_template('blog/blog.html', 
                          posts=posts,
                          pagination=pagination,
                          featured_post=featured_post,
                          recent_posts=recent_posts,
                          categories=categories,
                          request=request,
                          title="Blog")

@blog_bp.route('/category/<string:slug>')
@blog_bp.route('/category/<string:slug>/page/<int:page>')
def category(slug, page=1):
    category = BlogCategory.query.filter_by(slug=slug).first_or_404()
    posts_query = BlogPost.query.filter_by(category=category, is_published=True).order_by(BlogPost.published_at.desc())
    pagination = posts_query.paginate(page=page, per_page=6, error_out=False)
    posts = pagination.items

    # Get all categories for sidebar
    categories = BlogCategory.query.all()

    # Get recent posts for sidebar
    recent_posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.published_at.desc()).limit(5).all()

    return render_template('blog/blog_category.html', 
                          category=category, 
                          posts=posts,
                          pagination=pagination,
                          categories=categories,
                          recent_posts=recent_posts,
                          request=request,
                          title=f"Blog - {category.name}")

@blog_bp.route('/<string:slug>')
def post(slug):
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()

    # Get recent posts for sidebar
    recent_posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.published_at.desc()).limit(5).all()

    # Get all categories for sidebar
    categories = BlogCategory.query.all()

    # Get related posts from same category but not the current post
    related_posts = BlogPost.query.filter(
        BlogPost.category_id == post.category_id, 
        BlogPost.id != post.id, 
        BlogPost.is_published == True
    ).order_by(BlogPost.published_at.desc()).limit(2).all()

    return render_template('blog/blog_post.html', 
                          post=post, 
                          recent_posts=recent_posts,
                          related_posts=related_posts,
                          categories=categories,
                          request=request,
                          title=post.title)
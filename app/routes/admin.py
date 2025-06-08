from slugify import slugify
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app.models.user import User
from app.models.order import Order, OrderComment, OrderFile, SupportTicket
from app.models.order_delivery import OrderDelivery, OrderDeliveryFile
from app.models.communication import Notification, Chat
from app.models.content import Testimonial, Sample
from app.models.blog import BlogPost, BlogCategory, BlogComment
from app.models.service import Service, AcademicLevel, Deadline, ServiceCategory
from app.models.payment import Payment, Refund, Discount
from app.models.tools import PlagiarismCheck, ChatMessage
from app.models.price import PriceRate, PricingCategory
from app.models.referral import Referral
from app.extensions import db
from app.utils.email import send_verification_email
from app.extensions import socketio
from app.routes.main import notify
from app.config import Config
from PIL import Image
from datetime import datetime, timedelta
import calendar
import uuid
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge 
from app.utils.file_upload import allowed_file
from werkzeug.security import generate_password_hash
import os
import re


admin_bp = Blueprint('admin', __name__)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Display the admin dashboard with statistics and charts."""
    # Get counts for dashboard
    users_count = User.query.filter_by(is_admin=False).count()
    orders_count = Order.query.count()
    unread_messages_count = ChatMessage.query.filter_by(is_read=False).count()
    pending_testimonials_count = Testimonial.query.filter_by(is_approved=False).count()
    
    # Calculate total revenue
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter(Payment.status == 'completed').scalar() or 0
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Calculate client satisfaction rate (percentage of orders that weren't cancelled or refunded)
    total_completed_orders = Order.query.filter(Order.status == 'completed').count()
    total_orders_with_feedback = total_completed_orders or 1  # Avoid division by zero
    happy_clients_count = Order.query.filter(Order.status == 'completed').count()
    satisfaction_rate = int((happy_clients_count / total_orders_with_feedback) * 100)
    
    # Calculate order stats by status
    pending_count = Order.query.filter_by(status='pending').count()
    in_progress_count = Order.query.filter_by(status='active').count()
    completed_count = Order.query.filter_by(status='completed').count()
    cancelled_count = Order.query.filter_by(status='cancelled').count()
    revision_count = Order.query.filter_by(status='revision').count()
    overdue_count = Order.query.filter(Order.due_date < datetime.now()).count()
    
    # Calculate new vs returning clients
    total_clients = User.query.filter_by(is_admin=False).count()
    clients_with_multiple_orders = db.session.query(Order.client_id).group_by(Order.client_id).having(db.func.count(Order.id) > 1).count()
    new_clients = total_clients - clients_with_multiple_orders
    returning_rate = int((clients_with_multiple_orders / total_clients) * 100) if total_clients > 0 else 0
    
    return render_template('admin/dashboard/index.html',
                           users_count=users_count,
                           orders_count=orders_count,
                           unread_messages_count=unread_messages_count,
                           pending_testimonials_count=pending_testimonials_count,
                           total_revenue=total_revenue,
                           recent_orders=recent_orders,
                           satisfaction_rate=satisfaction_rate,
                           pending_count=pending_count,
                           in_progress_count=in_progress_count,
                           completed_count=completed_count,
                           cancelled_count=cancelled_count,
                           revision_count=revision_count,
                           new_clients=new_clients,
                           returning_rate=returning_rate,
                           title="Admin Dashboard")

@admin_bp.route('/revenue-chart-data')
@login_required
@admin_required
def revenue_chart_data():
    """Get data for the revenue chart."""
    period = request.args.get('period', 'monthly')
    
    current_date = datetime.now()
    
    if period == 'weekly':
        # Get data for the last 7 days
        labels = []
        current_data = []
        previous_data = []
        
        for i in range(6, -1, -1):
            day = current_date - timedelta(days=i)
            previous_day = day - timedelta(days=7)
            
            labels.append(day.strftime('%a'))
            
            # Current week data
            day_revenue = db.session.query(db.func.sum(Payment.amount)) \
                .filter(Payment.status == 'completed') \
                .filter(db.func.date(Payment.created_at) == day.date()) \
                .scalar() or 0
            current_data.append(float(day_revenue))
            
            # Previous week data
            prev_day_revenue = db.session.query(db.func.sum(Payment.amount)) \
                .filter(Payment.status == 'completed') \
                .filter(db.func.date(Payment.created_at) == previous_day.date()) \
                .scalar() or 0
            previous_data.append(float(prev_day_revenue))
    
    elif period == 'monthly':
        # Get data for the last 6 months
        labels = []
        current_data = []
        previous_data = []
        
        for i in range(5, -1, -1):
            # Calculate current and previous month dates
            month_offset = i
            current_month = current_date.month - month_offset
            current_year = current_date.year
            
            # Adjust year if needed
            while current_month <= 0:
                current_month += 12
                current_year -= 1
            
            # Calculate previous year's equivalent month
            prev_year = current_year - 1
            
            # Get month name
            month_name = calendar.month_abbr[current_month]
            labels.append(month_name)
            
            # Get start and end dates for current month
            current_start = datetime(current_year, current_month, 1)
            if current_month == 12:
                current_end = datetime(current_year + 1, 1, 1) - timedelta(days=1)
            else:
                current_end = datetime(current_year, current_month + 1, 1) - timedelta(days=1)
            
            # Get start and end dates for previous year's month
            prev_start = datetime(prev_year, current_month, 1)
            if current_month == 12:
                prev_end = datetime(prev_year + 1, 1, 1) - timedelta(days=1)
            else:
                prev_end = datetime(prev_year, current_month + 1, 1) - timedelta(days=1)
            
            # Current month revenue
            month_revenue = db.session.query(db.func.sum(Payment.amount)) \
                .filter(Payment.status == 'completed') \
                .filter(Payment.created_at.between(current_start, current_end)) \
                .scalar() or 0
            current_data.append(float(month_revenue))
            
            # Previous year's month revenue
            prev_month_revenue = db.session.query(db.func.sum(Payment.amount)) \
                .filter(Payment.status == 'completed') \
                .filter(Payment.created_at.between(prev_start, prev_end)) \
                .scalar() or 0
            previous_data.append(float(prev_month_revenue))
    
    else:  # yearly
        # Get data for the last 5 years
        labels = []
        current_data = []
        
        current_year = current_date.year
        
        for i in range(4, -1, -1):
            year = current_year - i
            labels.append(str(year))
            
            # Year revenue
            year_revenue = db.session.query(db.func.sum(Payment.amount)) \
                .filter(Payment.status == 'completed') \
                .filter(db.extract('year', Payment.created_at) == year) \
                .scalar() or 0
            current_data.append(float(year_revenue))
    
    return jsonify({
        'labels': labels,
        'current': current_data,
        'previous': previous_data if period != 'yearly' else []
    })

@admin_bp.route('/orders-by-status')
@login_required
@admin_required
def orders_by_status():
    """Get data for the orders by status chart."""
    # Count orders by status
    pending_count = Order.query.filter_by(status='pending').count()
    in_progress_count = Order.query.filter_by(status='active').count()
    completed_count = Order.query.filter_by(status='completed').count()
    cancelled_count = Order.query.filter_by(status='cancelled').count()
    revision_count = Order.query.filter_by(status='revision').count()
    
    return jsonify({
        'labels': ['pending', 'active', 'completed', 'cancelled', 'revision'],
        'data': [pending_count, in_progress_count, completed_count, cancelled_count, revision_count],
        'colors': ['#FFC107', '#2196F3', '#4CAF50', '#F44336', '#9C27B0']
    })

@admin_bp.route('/orders-by-service')
@login_required
@admin_required
def orders_by_service():
    """Get data for the orders by service chart."""
    # Get top services by order count
    services_data = db.session.query(
        Order.service_id,
        db.func.count(Order.id).label('order_count')
    ) \
    .join(Order.service) \
    .group_by(Order.service_id) \
    .order_by(db.desc('order_count')) \
    .limit(5) \
    .all()
    
    labels = []
    data = []
    
    for service_id, count in services_data:
        service = db.session.query(Service).get(service_id)
        if service:
            labels.append(service.name)
            data.append(count)
    
    return jsonify({
        'labels': labels,
        'data': data
    })


# Helper function to generate a unique slug
def generate_unique_slug(title, model, current_id=None):
    base_slug = slugify(title)
    slug = base_slug
    count = 1
    
    while True:
        # Check if slug exists in the database
        existing = model.query.filter_by(slug=slug).first()
        
        # If no collision or it's the current object, return the slug
        if not existing or (current_id and existing.id == current_id):
            return slug
        
        # Otherwise, increment counter and try again
        slug = f"{base_slug}-{count}"
        count += 1

# Blog Posts
@admin_bp.route('/blog')
@login_required
@admin_required
def list_blog_posts():
    """Display all blog posts with filtering options."""
    published_filter = request.args.get('published', '')
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    
    # Base query
    query = BlogPost.query
    
    # Apply filters
    if published_filter == 'true':
        query = query.filter(BlogPost.is_published == True)
    elif published_filter == 'false':
        query = query.filter(BlogPost.is_published == False)
        
    if search_query:
        query = query.filter(
            (BlogPost.title.ilike(f'%{search_query}%')) |
            (BlogPost.content.ilike(f'%{search_query}%'))
        )
    
    if category_filter:
        query = query.filter(BlogPost.category_id == category_filter)
    
    # Get the sorted posts
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    if sort_order == 'desc':
        query = query.order_by(getattr(BlogPost, sort_by).desc())
    else:
        query = query.order_by(getattr(BlogPost, sort_by).asc())
    
    posts = query.all()
    
    # Get all categories for filter dropdown
    categories = BlogCategory.query.all()
    
    # Get stats for the sidebar
    total_posts = BlogPost.query.count()
    published_posts = BlogPost.query.filter_by(is_published=True).count()
    draft_posts = BlogPost.query.filter_by(is_published=False).count()
    
    return render_template('admin/content/blog/list.html', 
                           posts=posts,
                           categories=categories,
                           published_filter=published_filter,
                           search_query=search_query,
                           category_filter=category_filter,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           total_posts=total_posts,
                           published_posts=published_posts,
                           draft_posts=draft_posts,
                           title='Blog Management')

@admin_bp.route('/blog/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_blog_post():
    """Create a new blog post."""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        excerpt = request.form.get('excerpt', '')
        category_id = request.form.get('category_id')
        published = True if request.form.get('published') == 'true' else False
        meta_description = request.form.get('meta_description', '')
        tags = request.form.get('tags', '').split(',')
        # tags = [tag.strip() for tag in tags if tag.strip()]
        # if tags and len(tags) > 0:
        #     for tag in tags:
        #         content += f"\n{tag}\n"
        if tags:
            cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
        else:
            cleaned_tags = []
            
        # Generate slug from title
        slug = generate_unique_slug(title, BlogPost)
        
        # Handle featured image upload
        featured_image = None
        if 'featured_image' in request.files:
            file = request.files['featured_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                
                # Create directory if it doesn't exist
                upload_dir = os.path.join('app', 'static', 'uploads', 'blog')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save the file
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                
                # Save the path relative to static directory
                featured_image = f"uploads/blog/{unique_filename}"
        
        # Create new blog post
        post = BlogPost(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            featured_image=featured_image,
            tags = ','.join(cleaned_tags),
            author_id=current_user.id,
            category_id=category_id,
            is_published=published,
            published_at=datetime.now() if published else None
        )
        try:
            db.session.add(post)
            db.session.commit()
            other = current_user
            notify(other, 
                title=f"New blog has been created by {current_user.get_name()}", 
                message=post.excerpt[:50], 
                type='info', 
                link=url_for('admin.view_blog_post', post_id=post.id))
            all_users = User.query.all()
            for user in all_users:
                if user.id != current_user.id:      
                    notify(user, 
                        title=f"New blog has been created by {current_user.get_name()}", 
                        message=post.excerpt[:50], 
                        type='info', 
                        link=url_for('blog.post', slug=post.slug))
            flash('Blog post created successfully', 'success')
            return redirect(url_for('admin.view_blog_post', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating blog post: {str(e)}")
            flash('An error occurred while creating the blog post. Please try again.', 'danger')
            return redirect(url_for('admin.create_blog_post'))
    
    # GET request - render form
    categories = BlogCategory.query.all()
    
    return render_template('admin/content/blog/create.html',
                           categories=categories,
                           title='Create Blog Post')

@admin_bp.route('/blog/<int:post_id>')
@login_required
@admin_required
def view_blog_post(post_id):
    """View a specific blog post."""
    post = BlogPost.query.get_or_404(post_id)
    comments = BlogComment.query.filter_by(post_id=post_id).order_by(BlogComment.created_at.desc()).all()
    all_approved = all(comment.approved for comment in comments)
    
    return render_template('admin/content/blog/view.html',
                           post=post,
                           all_approved=all_approved,
                           comments=comments,
                           title=post.title)

@admin_bp.route('/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_blog_post(post_id):
    """Edit a blog post."""
    post = BlogPost.query.get_or_404(post_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        excerpt = request.form.get('excerpt', '')
        category_id = request.form.get('category_id')
        published = True if request.form.get('published') == 'true' else False
        meta_description = request.form.get('meta_description', '')
        tags = request.form.get('tags', '').split(',')
        tags = [tag.strip() for tag in tags if tag.strip()]
        
        # Update post details
        post.title = title
        post.content = content
        post.excerpt = excerpt
        post.category_id = category_id
        post.meta_description = meta_description
        post.tags = tags
        
        # Update slug if title changed
        if post.title != title:
            post.slug = generate_unique_slug(title, BlogPost, post.id)
        
        # Update published status
        if post.published != published:
            post.published = published
            if published and not post.publish_date:
                post.publish_date = datetime.now()
        
        # Handle featured image upload
        if 'featured_image' in request.files:
            file = request.files['featured_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                
                # Create directory if it doesn't exist
                upload_dir = os.path.join('app', 'static', 'uploads', 'blog')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save the file
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                
                # Delete old image if exists
                if post.featured_image:
                    old_path = os.path.join('app', 'static', post.featured_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # Save the path relative to static directory
                post.featured_image = os.path.join('uploads', 'blog', unique_filename)
        try:
            db.session.commit()
            other = current_user
            notify(other, 
                title=f"Post #{post.title} has been updated by {current_user.get_name()}", 
                message="Blog post updated successfully", 
                type='info', 
                link=url_for('admin.view_blog_post', post_id=post.id))
            all_users = User.query.all()
            for user in all_users:
                notify(user, 
                    title=f"Post #{post.title} has been updated by {current_user.get_name()}", 
                    message="Blog post updated successfully", 
                    type='info', 
                    link=url_for('admin.view_blog_post', post_id=post.id))
            
            flash('Blog post updated successfully', 'success')
            return redirect(url_for('admin.view_blog_post', post_id=post.id))

        except Exception as e:
            db.session.rollback()
            flash('Failed to update blog', 'error')
            return redirect(url_for('admin.view_blog_post', post_id=post.id))
        
    
    # GET request - render form with current values
    categories = BlogCategory.query.all()
    
    return render_template('admin/content/blog/edit.html',
                           post=post,
                           categories=categories,
                           title=f'Edit: {post.title}')

@admin_bp.route('/blog/<int:post_id>/toggle-published', methods=['POST'])
@login_required
@admin_required
def toggle_post_published(post_id):
    """Toggle the published status of a blog post."""
    post = BlogPost.query.get_or_404(post_id)
    
    # Toggle the published status
    post.is_published = not post.is_published
    
    # Update published_at timestamp if being published
    if post.is_published and not post.published_at:
        post.published_at = datetime.now()
    
    # Create notification message based on new status
    status_message = "published" if post.is_published else "unpublished"
    
    # Notify the current user
    try:
        db.session.commit()
        notify(current_user, 
            title=f"Post '{post.title}' has been {status_message} by {current_user.get_name()}", 
            message=f"Blog post {status_message}.", 
            type='info', 
            link=url_for('admin.view_blog_post', post_id=post.id))
        
        # Notify all users
        all_users = User.query.all()
        for user in all_users:
            if user.id != current_user.id:  # Avoid duplicate notification for current user
                notify(user, 
                    title=f"Post '{post.title}' has been {status_message} by {current_user.get_name()}", 
                    message=f"Blog post {status_message}.", 
                    type='info', 
                    link=url_for('admin.view_blog_post', post_id=post.id))
        
        
        flash(f'Blog post {status_message} successfully', 'success')
        return redirect(url_for('admin.view_blog_post', post_id=post.id))
    except Exception as e:
        db.session.rollback()
        flash("Error updating featured status", "error")
        return redirect(url_for("admin.view_blog_post", post_id=post.id))


@admin_bp.route('/blog/<int:post_id>/duplicate', methods=['POST'])
@login_required
@admin_required
def duplicate_blog_post(post_id):
    """Create a duplicate of a blog post."""
    original_post = BlogPost.query.get_or_404(post_id)
    
    # Create a copy of the post with a modified title
    duplicate_title = f"{original_post.title} (Copy)"
    
    # Generate a unique slug for the duplicate
    duplicate_slug = generate_unique_slug(duplicate_title, BlogPost)
    
    # Create the duplicate post (unpublished by default)
    duplicate_post = BlogPost(
        title=duplicate_title,
        slug=duplicate_slug,
        content=original_post.content,
        excerpt=original_post.excerpt,
        featured_image=original_post.featured_image,  # Same image reference
        author_id=current_user.id,  # Current user becomes the author
        category_id=original_post.category_id,
        is_published=False,  # Always start as draft
        published_at=None    # Reset published date
    )
    try:
        db.session.add(duplicate_post)
        db.session.commit()
        
        # Notify the current user
        notify(current_user, 
            title=f"Post '{original_post.title}' has been duplicated by {current_user.get_name()}", 
            message=f"A draft copy has been created.", 
            type='info', 
            link=url_for('admin.edit_blog_post', post_id=duplicate_post.id))
        
        flash('Blog post duplicated successfully. You can now edit the copy.', 'success')
        return redirect(url_for('admin.edit_blog_post', post_id=duplicate_post.id))
    except Exception as e:
        db.session.rollback()
        flash("Error duplicating pos", "error")
        return redirect(url_for("admin.view_blog_post",post_id=duplicate_post.id))
    
@admin_bp.route('/blog/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_blog_post(post_id):
    """Delete a blog post."""
    post = BlogPost.query.get_or_404(post_id)
    
    # Delete featured image if exists
    if post.featured_image:
        image_path = os.path.join('app', 'static', post.featured_image)
        if os.path.exists(image_path):
            os.remove(image_path)
    try:    
        db.session.delete(post)
        db.session.commit()
        all_users = User.query.all()
        for user in all_users:
            notify(user, 
                title=f"Post #{post.title} has been deleted by {current_user.get_name()}", 
                message="Blog post deleted successfully", 
                type='info', 
                link=None)
        
        flash('Blog post deleted successfully', 'success')
        return redirect(url_for('admin.list_blog_posts'))
    except Exception as e:
        db.session.rollback()
        flash("Fialed to delete post", "error")
        return redirect(url_for('admin.list_blog_posts'))

# Blog Categories
@admin_bp.route('/blog/categories')
@login_required
@admin_required
def list_blog_categories():
    """List all blog categories."""
    categories = BlogCategory.query.all()
    return render_template('admin/content/blog/categories.html',
                           categories=categories,
                           title='Blog Categories')

@admin_bp.route('/blog/categories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_blog_category():
    """Create a new blog category."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        parent_id = request.form.get('parent_id', None)
        
        if not parent_id or parent_id == '0':
            parent_id = None
        
        # Generate slug from name
        slug = generate_unique_slug(name, BlogCategory)
        
        # Create category
        category = BlogCategory(
            name=name,
            slug=slug,
            description=description,
            parent_id=parent_id
        )
        other = current_user
        notify(other, 
            title=f"Blog category #{category.name} has been created by {current_user.get_name()}", 
            message="Category created successfully", 
            type='info', 
            link=None)
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category created successfully', 'success')
        return redirect(url_for('admin.list_blog_categories'))
    
    # GET request - render form
    categories = BlogCategory.query.all()
    
    return render_template('admin/content/blog/create_category.html',
                           categories=categories,
                           title='Create Blog Category')

@admin_bp.route('/blog/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_blog_category(category_id):
    """Edit a blog category."""
    category = BlogCategory.query.get_or_404(category_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        parent_id = request.form.get('parent_id', None)
        
        if not parent_id or parent_id == '0':
            parent_id = None
        
        # Prevent setting parent to self or any of its descendants
        if parent_id and int(parent_id) == category_id:
            flash('Category cannot be its own parent', 'danger')
            return redirect(url_for('admin.edit_blog_category', category_id=category_id))
        
        # Update category
        category.name = name
        category.description = description
        category.parent_id = parent_id
        
        # Update slug if name changed
        if category.name != name:
            category.slug = generate_unique_slug(name, BlogCategory, category.id)
        other = current_user
        notify(other, 
            title=f"Blog category #{category.name} has been edited by {current_user.get_name()}", 
            message="Category edited successfully", 
            type='info', 
            link=None)
        
        try:
            db.session.commit()
            flash('Category updated successfully', 'success')
            return redirect(url_for('admin.list_blog_categories'))
        except Exception as e:
            db.session.rollback()
            flash('Database error occurred while updating the category', 'danger')
            return redirect(url_for('admin.edit_blog_category', category_id=category_id))
    
    # GET request - render form
    categories = BlogCategory.query.all()
    
    return render_template('admin/content/blog/edit_category.html',
                           category=category,
                           categories=categories,
                           title=f'Edit Category: {category.name}')

@admin_bp.route('/blog/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_blog_category(category_id):
    """Delete a blog category."""
    category = BlogCategory.query.get_or_404(category_id)
    
    # Check if category has posts
    if category.posts:
        flash('Cannot delete category with associated posts', 'danger')
        return redirect(url_for('admin.list_blog_categories'))
    
    # Check if category has subcategories
    if category.subcategories:
        flash('Cannot delete category with subcategories', 'danger')
        return redirect(url_for('admin.list_blog_categories'))
    
    try:
        db.session.delete(category)
        db.session.commit()
        other = current_user
        notify(other, 
            title=f"Blog category #{category.name} has been deleted by {current_user.get_name()}", 
            message="Category deleted successfully", 
            type='info', 
            link=None)
        flash('Category deleted successfully', 'success')
        return redirect(url_for('admin.list_blog_categories'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the category.', 'danger')
        return redirect(url_for('admin.list_blog_categories'))

# Testimonials
@admin_bp.route('/testimonials')
@login_required
@admin_required
def list_testimonials():
    """List all testimonials."""
    approved_filter = request.args.get('approved', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = Testimonial.query
    
    # Apply filters
    if approved_filter == 'true':
        query = query.filter(Testimonial.is_approved == True)
    elif approved_filter == 'false':
        query = query.filter(Testimonial.is_approved == False)
        
    if search_query:
        query = query.filter(
            (Testimonial.client_name.ilike(f'%{search_query}%')) |
            (Testimonial.content.ilike(f'%{search_query}%'))
        )
    
    testimonials = query.order_by(Testimonial.created_at.desc()).all()
    
    # Get stats
    total_testimonials = Testimonial.query.count()
    approved_testimonials = Testimonial.query.filter_by(is_approved=True).count()
    pending_testimonials = Testimonial.query.filter_by(is_approved=False).count()
    
    return render_template('admin/content/testimonials/list.html',
                           testimonials=testimonials,
                           approved_filter=approved_filter,
                           search_query=search_query,
                           total_testimonials=total_testimonials,
                           approved_testimonials=approved_testimonials,
                           pending_testimonials=pending_testimonials,
                           title='Testimonial Management')

@admin_bp.route('/testimonials/<int:testimonial_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_testimonial(testimonial_id):
    """Approve a testimonial."""
    testimonial = Testimonial.query.get_or_404(testimonial_id)
    testimonial.is_approved = True
    try:
        db.session.commit()
        other = current_user
        notify(other, 
            title=f"Testimonial #{testimonial.id} by {testimonial.user.username} has been approved by {current_user.get_name()}", 
            message="Testimonial approved successfully", 
            type='info', 
            link=None)
        notify(testimonial.user, 
            title=f"Testimonial #{testimonial.id} by {testimonial.user.username} has been approved by {current_user.get_name()}", 
            message="Testimonial approved successfully", 
            type='info', 
            link=None)
        flash('Testimonial approved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while approving the testimonial.', 'danger')
    return redirect(url_for('admin.list_testimonials'))

@admin_bp.route('/testimonials/<int:testimonial_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_testimonial(testimonial_id):
    """Reject a testimonial."""
    testimonial = Testimonial.query.get_or_404(testimonial_id)
    testimonial.is_approved = False
    try:
        db.session.commit()
        other = current_user
        notify(other, 
            title=f"Testimonial #{testimonial.id} by {testimonial.user.username} has not been approved by {current_user.get_name()}", 
            message="Testimonial rejected", 
            type='info', 
            link=None)
        notify(testimonial.user, 
            title=f"Testimonial #{testimonial.id} by {testimonial.user.username} has not been approved by {current_user.get_name()}", 
            message="Testimonial rejected", 
            type='info', 
            link=None)

        flash('Testimonial rejected', 'success')
        return redirect(url_for('admin.list_testimonials'))
    except Exception as e:
        db.session.rollback()
        flash('Daabase error while rejecting testimonial', 'error')
        return redirect(url_for('admin.list_testimonials'))

@admin_bp.route('/testimonials/<int:testimonial_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_testimonial(testimonial_id):
    """Delete a testimonial."""
    testimonial = Testimonial.query.get_or_404(testimonial_id)
    try:
        db.session.delete(testimonial)
        db.session.commit()
        other = current_user
        notify(other, 
            title=f"Testimonial #{testimonial.id} by {testimonial.user.username} has been deleted by {current_user.get_name()}", 
            message="Testimonial deleted", 
            type='info', 
            link=None)
        notify(testimonial.user, 
            title=f"Testimonial #{testimonial.id} by {testimonial.user.username} has been deleted by {current_user.get_name()}", 
            message="Testimonial deleted", 
            type='info', 
            link=None)
        
        flash('Testimonial deleted successfully', 'success')
        return redirect(url_for('admin.list_testimonials'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the testimonial.', 'danger')
        return redirect(url_for('admin.list_testimonials'))

# Samples
@admin_bp.route('/samples')
@login_required
@admin_required
def list_samples():
    """List all writing samples."""
    featured_filter = request.args.get('featured', '')
    search_query = request.args.get('search', '')
    service_filter = request.args.get('service', '')
    
    # Base query
    query = Sample.query
    
    # Apply filters
    if featured_filter == 'true':
        query = query.filter(Sample.featured == True)
    elif featured_filter == 'false':
        query = query.filter(Sample.featured == False)
        
    if search_query:
        query = query.filter(
            (Sample.title.ilike(f'%{search_query}%')) |
            (Sample.description.ilike(f'%{search_query}%')) |
            (Sample.content.ilike(f'%{search_query}%'))
        )
    
    if service_filter:
        query = query.filter(Sample.service_id == service_filter)
    
    samples = query.order_by(Sample.created_at.desc()).all()
    
    # Get all services for filter dropdown
    services = Service.query.all()
    
    return render_template('admin/content/samples/list.html',
                           samples=samples,
                           services=services,
                           featured_filter=featured_filter,
                           search_query=search_query,
                           service_filter=service_filter,
                           title='Sample Management')

#*********************************************************************************************************
#****************************************** ADMIN SAMPLES ******************************************
def process_image(file, upload_folder):
    """Process and save uploaded image with optimization"""
    if not file or not allowed_file(file.filename, "picture"):
        return None
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_{name}{ext}"
    
    # Ensure upload directory exists
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_filename)
    
    try:
        # Open and process image
        image = Image.open(file.stream)
        
        # Convert RGBA to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Resize image if too large (maintain aspect ratio)
        max_size = (1200, 800)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.LANCZOS)
        
        # Save optimized image
        image.save(file_path, optimize=True, quality=85)
        
        return unique_filename
    
    except Exception as e:
        current_app.logger.error(f"Error processing image: {str(e)}")
        return None

def extract_word_count(content):
    """Extract word count from HTML content"""
    if not content:
        return 0
    
    # Remove HTML tags and count words
    clean_text = re.sub(r'<[^>]+>', ' ', content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    if not clean_text:
        return 0
    
    return len(clean_text.split())
pic_ext = Config.ALLOWED_PIC_EXT
# pic_ext = current_app.config.get('ALLOWED_PIC_EXT')
def validate_sample_data(data, file=None):
    """Validate sample form data"""
    errors = []
    
    # Validate title
    title = data.get('title', '').strip()
    if not title:
        errors.append('Title is required.')
    elif len(title) < 10:
        errors.append('Title must be at least 10 characters long.')
    elif len(title) > 200:
        errors.append('Title must not exceed 200 characters.')
    
    # Validate service selection
    service_id = data.get('service_id')
    if not service_id:
        errors.append('Please select a service category.')
    else:
        try:
            service_id = int(service_id)
            service = Service.query.get(service_id)
            if not service:
                errors.append('Selected service category is invalid.')
        except (ValueError, TypeError):
            errors.append('Invalid service category selected.')
    
    # Validate content
    content = data.get('content', '').strip()
    if not content:
        errors.append('Content is required.')
    elif len(content) < 100:
        errors.append('Content must be at least 100 characters long.')
    
    # Validate excerpt (optional but with length limit)
    excerpt = data.get('excerpt', '').strip()
    if excerpt and len(excerpt) > 500:
        errors.append('Excerpt must not exceed 500 characters.')
    
    # Validate word count if provided
    word_count = data.get('word_count')
    if word_count:
        try:
            word_count = int(word_count)
            if word_count < 0:
                errors.append('Word count must be a positive number.')
        except (ValueError, TypeError):
            errors.append('Word count must be a valid number.')
    
    # Validate featured flag
    featured = data.get('featured', '0')
    if featured not in ['0', '1']:
        errors.append('Invalid featured flag value.')
    
    # Validate image if provided
    if file and file.filename:
        if not allowed_file(file.filename, "picture"):
            errors.append(f'Invalid image format. Allowed formats: {", ".join(pic_ext).upper()}')
    
    return errors


@admin_bp.route('/samples/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_sample():
    """Create a new writing sample."""
    if request.method == 'POST':
        try:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            form_data = request.form.to_dict()
            uploaded_file = request.files.get('image')
            validation_errors = validate_sample_data(form_data, uploaded_file)
            if validation_errors:
                error_message = ' '.join(validation_errors)
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'message': error_message,
                        'errors': validation_errors
                    }), 400
                else:
                    flash(error_message, 'error')
                    return redirect(url_for('admin.create_sample'))
                
            image_filename = None
            if uploaded_file and uploaded_file.filename:
                upload_folder = os.path.join('app', 'static', 'uploads', 'samples')
                os.makedirs(upload_folder, exist_ok=True)
                image_filename = process_image(uploaded_file, upload_folder)
                
                if not image_filename:
                    error_msg = 'Failed to process uploaded image. Please try again.'
                    if is_ajax:
                        return jsonify({'success': False, 'message': error_msg}), 400
                    else:
                        flash(error_msg, 'error')
                        return redirect(url_for('admin.create_sample'))
            content = form_data.get('content', '')
            word_count = form_data.get('word_count')
            if word_count:
                try:
                    word_count = int(word_count)
                except (ValueError, TypeError):
                    word_count = extract_word_count(content)
            else:
                word_count = extract_word_count(content)
            # Create new sample
            sample = Sample(
                title=form_data.get('title', '').strip(),
                content=content,
                excerpt=form_data.get('excerpt', '').strip() or None,
                service_id=int(form_data.get('service_id')),
                word_count=word_count,
                featured=form_data.get('featured', '0') == '1',
                tags=form_data.get('tags').strip() or None,
                image=image_filename,
                created_at=datetime.now()
            )
            
            try:
                db.session.add(sample)
                db.session.commit()
                notify(current_user,
                    title=f"Sample #{sample.title} has been created by {current_user.get_name()}", 
                    message="Sample created successfully", 
                    type='info', 
                    link=url_for('main.sample_detail', sample_id=sample.id))
                all_users = User.query.all()
                for user in all_users:
                    notify(user,
                        title=f"Sample #{sample.title} has been created by {current_user.get_name()}", 
                        message="Sample created successfully", 
                        type='info', 
                        link=url_for('main.sample_detail', sample_id=sample.id))
                current_app.logger.info(f"Sample created successfully: {sample.title} (ID: {sample.id})")
                
                # Return success response
                success_message = f'Sample \"{sample.title}\" has been created successfully!'
                
                if is_ajax:
                    return jsonify({
                        'success': True,
                        'message': success_message,
                        'sample_id': sample.id,
                        'redirect_url': url_for('main.sample_detail', sample_id=sample.id)
                    })
                else:
                    flash(success_message, 'success')
                    return redirect(url_for('main.sample_detail', sample_id=sample.id))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error saving sample: {str(e)}")
                error_message = 'An error occurred while saving the sample. Please try again.'
                if is_ajax:
                    return jsonify({'success': False, 'message': error_message}), 500
                else:
                    flash(error_message, 'error')
                    return redirect(url_for('admin.create_sample'))
            # flash('Sample created successfully', 'success')
            # return redirect(url_for('admin.list_samples'))
        except RequestEntityTooLarge:
            error_msg = 'Uploaded file is too large. Maximum size allowed is 5MB.'
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 413
            else:
                flash(error_msg, 'error')
                return redirect(url_for('admin.create_sample'))
        except Exception as e:
            db.session.rollback()  
            current_app.logger.error(f"Error creating sample: {str(e)}")
            if 'image_filename' in locals() and image_filename:
                try:
                    upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'samples')
                    file_path = os.path.join(upload_folder, image_filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as cleanup_error:
                    current_app.logger.error(f"Error cleaning up uploaded file: {str(cleanup_error)}")
            error_message = 'An error occurred while creating the sample. Please try again.'

            if is_ajax:
                return jsonify({'success': False, 'message': error_message}), 500
            else:
                flash(error_message, 'error')
                return redirect(url_for('admin.create_sample'))
            # flash('An error occurred while creating the sample. Please try again.', 'danger')
            # return redirect(url_for('admin.list_samples'))
    elif request.method == 'GET':
        try:
            # GET request - render form
            services = Service.query.all()
            
            return render_template('admin/content/samples/create.html',
                                services=services,
                                title='Create Sample')
        except Exception as e:
            current_app.logger.error(f"Error rendering sample creation form: {str(e)}")
            flash('An error occurred while loading the form. Please try again.', 'danger')
            return redirect(url_for('admin.list_samples'))

            # title = request.form.get('title')
            # description = request.form.get('description', '')
            # content = request.form.get('content')
            # service_id = request.form.get('service_id')
            # academic_level = request.form.get('academic_level', '')
            # format_style = request.form.get('format_style', '')
            # word_count = request.form.get('word_count', 0, type=int)
            # featured = True if request.form.get('featured') == 'true' else False
# @admin_bp.route('/samples/<int:sample_id>/edit', methods=['GET', 'POST'])
# @login_required
# @admin_required
# def edit_sample(sample_id):
#     """Edit a writing sample."""
#     sample = Sample.query.get_or_404(sample_id)
    
#     if request.method == 'POST':
#         title = request.form.get('title')
#         description = request.form.get('description', '')
#         content = request.form.get('content')
#         service_id = request.form.get('service_id')
#         academic_level = request.form.get('academic_level', '')
#         format_style = request.form.get('format_style', '')
#         word_count = request.form.get('word_count', 0, type=int)
#         featured = True if request.form.get('featured') == 'true' else False
        
#         # Update sample
#         sample.title = title
#         sample.description = description
#         sample.content = content
#         sample.service_id = service_id
#         sample.academic_level = academic_level
#         sample.format_style = format_style
#         sample.word_count = word_count
#         sample.featured = featured
        
#         try:
#             db.session.commit()
#             notify(current_user,
#                     title=f"Sample #{sample.title} has been updated by {current_user.get_name()}",
#                     message="Sample updated successfully",
#                     type='info',
#                     link=url_for('main.sample_detail', sample_id=sample.id))
#             all_users = User.query.all()
#             for user in all_users:
#                 notify(user,
#                         title=f"Sample #{sample.title} has been updated by {current_user.get_name()}",
#                         message="Sample updated successfully",
#                         type='info',
#                         link=url_for('main.sample_detail', sample_id=sample.id))

#             flash('Sample updated successfully', 'success')
#             return redirect(url_for('admin.list_samples'))
#         except Exception as e:
#             db.session.rollback()
#             flash('An error occurred while updating the sample. Please try again.', 'danger')
#             return redirect(url_for('admin.edit_sample', sample_id=sample.id))
    
#     # GET request - render form
#     services = Service.query.all()
    
#     return render_template('admin/content/samples/edit.html',
#                            sample=sample,
#                            services=services,
#                            title=f'Edit Sample: {sample.title}')

@admin_bp.route('/samples/edit/<int:sample_id>', methods=['GET'])
def get_sample_for_edit(sample_id):
    """Get sample details for editing"""
    try:
        sample = Sample.query.get_or_404(sample_id)
        
        sample_data = {
            'id': sample.id,
            'title': sample.title,
            'content': sample.content,
            'excerpt': sample.excerpt,
            'service_id': sample.service_id,
            'word_count': sample.word_count,
            'featured': sample.featured,
            'image': sample.image,
            'created_at': sample.created_at.isoformat() if sample.created_at else None
        }
        
        return jsonify({
            'success': True,
            'sample': sample_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching sample {sample_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error fetching sample'
        }), 500

@admin_bp.route('/samples/edit/<int:sample_id>', methods=['PUT', 'POST'])
def update_sample(sample_id):
    """Update existing sample"""
    try:
        sample = Sample.query.get_or_404(sample_id)
        
        # Get form data
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        excerpt = request.form.get('excerpt', '').strip()
        service_id = request.form.get('service_id')
        featured = request.form.get('featured', 'false').lower() == 'true'
        
        # Validation
        if not title:
            return jsonify({
                'success': False,
                'message': 'Title is required'
            }), 400
            
        if not content:
            return jsonify({
                'success': False,
                'message': 'Content is required'
            }), 400
        
        # Handle image upload if provided
        image_filename = sample.image  # Keep existing image by default
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                try:
                    # Delete old image if it exists
                    if sample.image:
                        old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], sample.image)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    # Process new image using existing helper function
                    image_filename = process_image(file, current_app.config['UPLOAD_FOLDER'])
                    
                except Exception as e:
                    current_app.logger.error(f"Error processing image: {str(e)}")
                    return jsonify({
                        'success': False,
                        'message': 'Error processing image'
                    }), 500
        
        # Extract word count using existing helper function
        word_count = extract_word_count(content)
        
        # Update sample fields
        sample.title = title
        sample.content = content
        sample.excerpt = excerpt
        sample.service_id = int(service_id) if service_id else None
        sample.word_count = word_count
        sample.featured = featured
        sample.image = image_filename
        
        # Commit changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sample updated successfully',
            'sample': {
                'id': sample.id,
                'title': sample.title,
                'content': sample.content,
                'excerpt': sample.excerpt,
                'service_id': sample.service_id,
                'word_count': sample.word_count,
                'featured': sample.featured,
                'image': sample.image,
                'created_at': sample.created_at.isoformat() if sample.created_at else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating sample {sample_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error updating sample'
        }), 500


@admin_bp.route('/samples/<int:sample_id>/toggle-featured', methods=['POST'])
@login_required
@admin_required
def toggle_sample_featured(sample_id):
    """Toggle featured status of a sample."""
    sample = Sample.query.get_or_404(sample_id)
    sample.featured = not sample.featured
    try:
        db.session.commit()
        status = 'featured' if sample.featured else 'unfeatured'
        flash(f'Sample {status} successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating the sample status.', 'danger')
    return redirect(url_for('admin.list_samples'))

@admin_bp.route('/samples/<int:sample_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_sample(sample_id):
    """Delete a writing sample."""
    sample = Sample.query.get_or_404(sample_id)
    notify(current_user,
            title=f"Sample #{sample.title} has been deleted by {current_user.get_name()}",
            message="Sample deleted successfully",
            type='info',
            link=None)
    all_users = User.query.all()
    for user in all_users:
        notify(user,
               title=f"Sample #{sample.title} has been deleted by {current_user.get_name()}",
                message="Sample deleted successfully",
                type='info',
                link=None)
    try:
        db.session.delete(sample)
        db.session.commit()
        flash('Sample deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the sample.', 'danger')
    return redirect(url_for('admin.list_samples'))
# @admin_bp.route('/orders')
# @login_required
# @admin_required
# def orders():
#     orders = Order.query.all()
#     return render_template('admin/orders.html', orders=orders, title='Order Management')

# @admin_bp.route('/users')
# @login_required
# @admin_required
# def users():
#     users = User.query.all()
#     return render_template('admin/users.html', users=users, title='User Management')

# @admin_bp.route('/messages')
# @login_required
# @admin_required
# def messages():
#     messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
#     return render_template('admin/messages.html', messages=messages, title='Contact Messages')

@admin_bp.route('/testimonials')
@login_required
@admin_required
def testimonials():
    testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return render_template('admin/testimonials.html', testimonials=testimonials, title='Testimonial Management')

# @admin_bp.route('/testimonials/<int:testimonial_id>/approve', methods=['POST'])
# @login_required
# @admin_required
# def approve_testimonial(testimonial_id):
#     testimonial = Testimonial.query.get_or_404(testimonial_id)
#     testimonial.is_approved = True
#     db.session.commit()
#     flash('Testimonial approved successfully!', 'success')
#     return redirect(url_for('admin.testimonials'))

# @admin_bp.route('/testimonials/<int:testimonial_id>/delete', methods=['POST'])
# @login_required
# @admin_required
# def delete_testimonial(testimonial_id):
#     testimonial = Testimonial.query.get_or_404(testimonial_id)
#     db.session.delete(testimonial)
#     db.session.commit()
#     flash('Testimonial deleted successfully!', 'success')
#     return redirect(url_for('admin.testimonials'))

# @admin_bp.route('/quality-control')
# @login_required
# @admin_required
# def quality_control():
#     return render_template('admin/quality_control.html', title='Quality Control')

# @admin_bp.route('/payment-processing')
# @login_required
# @admin_required
# def payment_processing():
#     return render_template('admin/payment_processing.html', title='Payment Processing')



# Contact Messages
@admin_bp.route('/messages')
@login_required
@admin_required
def list_messages():
    """List all contact messages."""
    read_filter = request.args.get('read', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = ChatMessage.query \
        .join(User, ChatMessage.user_id == User.id) \
        .join(Chat, ChatMessage.chat_id == Chat.id)
    
    # Apply filters
    if read_filter == 'true':
        query = query.filter(ChatMessage.is_read == True)
    elif read_filter == 'false':
        query = query.filter(ChatMessage.is_read == False)
        
    if search_query:
        query = query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%')) |
            (Chat.subject.ilike(f'%{search_query}%')) |
            (ChatMessage.content.ilike(f'%{search_query}%'))
        )
    
    messages = query.order_by(ChatMessage.created_at.desc()).all()
    
    # Get stats
    total_messages = ChatMessage.query.count()
    unread_messages = ChatMessage.query.filter_by(is_read=False).count()
    read_messages = ChatMessage.query.filter_by(is_read=True).count()
    
    return render_template('admin/communication/messages.html',
                           messages=messages,
                           read_filter=read_filter,
                           search_query=search_query,
                           total_messages=total_messages,
                           unread_messages=unread_messages,
                           read_messages=read_messages,
                           title='Contact Messages')

@admin_bp.route('/messages/<int:message_id>')
@login_required
@admin_required
def view_message(message_id):
    """View a specific contact message and mark it as read."""
    message = ChatMessage.query.get_or_404(message_id)
    chat = Chat.query \
    .join(ChatMessage) \
    .filter(ChatMessage.id == message_id) \
    .options(joinedload(Chat.messages)) \
    .first_or_404()
    
    # Mark as read if not already
    if not message.is_read:
        message.is_read = True
        db.session.commit()
    
    return render_template('admin/communication/message_detail.html',
                           message=message,
                            chat=chat,
                           title=f'Message: {message.content}')

@admin_bp.route('/messages/<int:message_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_message(message_id):
    """Delete a contact message."""
    message = ChatMessage.query.get_or_404(message_id)
    try:
        db.session.delete(message)
        db.session.commit()
        notify(current_user,
                title=f"Message #{message.id} has been deleted by {current_user.get_name()}",
                message="Message deleted successfully",
                type='info',
                link=None)
        
        user = User.query.filter_by(id=message.chat.user_id).first()
        if user:
            notify(user,
                title=f"Message #{message.id} has been deleted by {current_user.get_name()}",
                message="Message deleted successfully",
                type='info',
                link=None)
        flash('Message deleted successfully', 'success')
        return redirect(url_for('admin_communication.list_messages'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the message.', 'danger')
        return redirect(url_for('admin.list_messages'))
    
    

# Notifications
@admin_bp.route('/notifications')
@login_required
@admin_required
def list_notifications():
    """List and manage system notifications."""
    notifications = Notification.query.order_by(Notification.created_at.desc()).all()
    return render_template('admin/communication/notifications.html',
                           notifications=notifications,
                           title='System Notifications')

@admin_bp.route('/notifications/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_notification():
    """Create a new notification for a user or all users."""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        notification_type = request.form.get('type', 'system')
        link = request.form.get('link', '')
        user_id = request.form.get('user_id')
        send_to_all = True if request.form.get('send_to_all') == 'true' else False
        
        if not title or not content:
            flash('Title and content are required', 'danger')
            return redirect(url_for('admin.create_notification'))
        
        if send_to_all:
            # Create notification for all users
            users = User.query.filter_by(is_admin=False).all()
            for user in users:
                notification = Notification(
                    user_id=user.id,
                    title=title,
                    content=content,
                    type=notification_type,
                    link=link
                )
                db.session.add(notification)
            
            flash(f'Notification sent to {len(users)} users', 'success')
        else:
            # Create notification for specific user
            if not user_id:
                flash('User is required for individual notifications', 'danger')
                return redirect(url_for('admin.create_notification'))
            
            notification = Notification(
                user_id=user_id,
                title=title,
                content=content,
                type=notification_type,
                link=link
            )
            db.session.add(notification)
            db.session.commit()
            flash('Notification sent successfully', 'success')
        
        return redirect(url_for('admin.list_notifications'))
    
    # GET request - render form
    users = User.query.filter_by(is_admin=False).all()
    
    return render_template('admin/communication/create_notification.html',
                           users=users,
                           title='Create Notification')

@admin_bp.route('/notifications/<int:notification_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_notification(notification_id):
    """Delete a notification."""
    notification = Notification.query.get_or_404(notification_id)
    try:
        db.session.delete(notification)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Error:{e}", "error")
        return redirect(url_for("admin.list_notifications"))
        
    
    flash('Notification deleted successfully', 'success')
    return redirect(url_for('admin.list_notifications'))

# Chat System
@admin_bp.route('/chats')
@login_required
@admin_required
def list_chats():
    """List all client chats."""
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    
    # Base query - join with User to search by name
    query = Chat.query.join(User, Chat.user_id == User.id)
    
    # Apply filters
    if status_filter:
        query = query.filter(Chat.status == status_filter)
        
    if search_query:
        query = query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%')) |
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%'))
        )
    
    chats = query.order_by(Chat.created_at.desc()).all()
    
    return render_template('admin/communication/chats.html',
                           chats=chats,
                           status_filter=status_filter,
                           search_query=search_query,
                           title='Client Chat System')

@admin_bp.route('/chats/<int:chat_id>')
@login_required
@admin_required
def view_chat(chat_id):
    """View a specific chat conversation."""
    chat = Chat.query.get_or_404(chat_id)
    messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.asc()).all()
    unread_messages = ChatMessage.query.filter_by(
        chat_id=chat_id,
        is_read=False
    ).filter(ChatMessage.user_id != current_user.id).all()
    # If chat is associated with an order, get order details
    order = None
    if chat.order_id:
        order = Order.query.get(chat.order_id)
    for message in unread_messages:
        message.is_read = True
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking chat messages as read: {str(e)}")
        flash('An error occurred while updating chat messages.', 'danger')
    socketio.emit('messages_marked_read', {
        'chat_id': chat_id,
        'user_id': current_user.id
    }, room=f"chat_{chat_id}")
    socketio.emit('update_unread_count', {'user_id': current_user.id}, room=None)
    return render_template('admin/communication/chat_detail.html',
                           chat=chat,
                           messages=messages,
                           order=order,
                           title=f'Chat with {chat.user.username}')

@admin_bp.route('/chats/<int:chat_id>/send', methods=['POST'])
@login_required
@admin_required
def send_chat_message(chat_id):
    """Send a message in a chat."""
    # chat = Chat.query.filter_by(id=chat_id, admin_id=current_user.id).first_or_404()
    # content = request.form.get('content')
    
    # if not content:
    #     flash('Message cannot be empty', 'danger')
    #     return redirect(url_for('admin.view_chat', chat_id=chat_id))
    chat = Chat.query.get_or_404(chat_id)  # Remove the admin_id filter
    content = request.form.get('content')
    
    if not content:
        # if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'error', 'message': 'Message cannot be empty'}), 500
        # flash('Message cannot be empty', 'danger')
        # return redirect(url_for('admin.view_chat', chat_id=chat_id))
    # Create new message
    print(content)
    message = ChatMessage(
        chat_id=chat_id,
        user_id=current_user.id,
        content=content,
        is_read=False
    )
    chat.admin_id = current_user.id
    try:
        db.session.add(message)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error sending chat message: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Failed to send message.'}), 500
        # flash('Failed to send message.', 'danger')
        # return redirect(url_for('admin.view_chat', chat_id=chat_id))
        return jsonify({"error": "Failed to fetch blog posts"}), 500

    message_data = {
        'id': message.id,
        'chat_id': message.chat_id,
        'user_id': message.user_id,
        'content': message.content,
        'is_read': message.is_read,
        'created_at': message.created_at.strftime('%H:%M'),
        'sender_name': current_user.username
    }
    
    # Emit to chat room
    socketio.emit('new_message', message_data, room=f'chat_{chat_id}')
    
    # Emit to the other user's personal room (for notifications)
    other_user_id = chat.user_id
    socketio.emit('new_message', message_data, room=f'user_{other_user_id}')
    socketio.emit('update_unread_count', {'user_id': other_user_id}, room=f'user_{other_user_id}')
    
    # If this is an AJAX request, return JSON
    # if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    print("Message sent successfully")
    return jsonify({
        'status': 'success',
        'message': message_data
    })
    # notify(chat.user,
    #         title=f"New message from {current_user.get_name()}",
    #         message=content,
    #         type='info',
    #         link=url_for('client.view_chat', chat_id=chat_id))
    # notify(current_user,
    #         title=f"Message sent to {chat.user.username}",
    #         message=content,
    #         type='info',
    #         link=url_for('admin.view_chat', chat_id=chat_id))
    # flash('Message sent successfully', 'success')
    # return redirect(url_for('admin.view_chat', chat_id=chat_id))

@admin_bp.route('/chats/<int:chat_id>/close', methods=['POST'])
@login_required
@admin_required
def close_chat(chat_id):
    """Close a chat conversation."""
    chat = Chat.query.get_or_404(chat_id)
    chat.status = 'closed'
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while closing the chat.', 'danger')
        return redirect(url_for('admin.list_chats'))
    notify(chat.user,
            title=f"Chat with {current_user.get_name()} has been closed",
            message="The chat has been closed successfully.",
            type='info',
            link=None)
    notify(current_user,
            title=f"Chat with {chat.user.username} has been closed",
            message="The chat has been closed successfully.",
            type='info',
            link=None)
    
    flash('Chat closed successfully', 'success')
    return redirect(url_for('admin.list_chats'))

@admin_bp.route('/chats/<int:chat_id>/reopen', methods=['POST'])
@login_required
@admin_required
def reopen_chat(chat_id):
    """Reopen a closed chat conversation."""
    chat = Chat.query.get_or_404(chat_id)
    chat.status = 'active'
    db.session.commit()
    notify(chat.user,
            title=f"Chat with {current_user.get_name()} has been reopened",
            message="The chat has been reopened successfully.",
            type='info',
            link=url_for('client.view_chat', chat_id=chat_id))
    notify(current_user,
            title=f"Chat with {chat.user.username} has been reopened",
            message="The chat has been reopened successfully.",
            type='info',
            link=url_for('admin.view_chat', chat_id=chat_id))
    
    flash('Chat reopened successfully', 'success')
    return redirect(url_for('admin.view_chat', chat_id=chat_id))

@admin_bp.route('/chats/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_chat():
    """Create a new chat with a client."""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        order_id = request.form.get('order_id', None)
        initial_message = request.form.get('initial_message', '')
        
        if not user_id:
            flash('User is required', 'danger')
            return redirect(url_for('admin.create_chat'))
        
        # Create chat
        chat = Chat(
            user_id=user_id,
            admin_id=current_user.id,
            order_id=order_id if order_id else None,
            status='active'
        )
        
        db.session.add(chat)
        db.session.flush()  # Get the chat ID
        notify(chat.user,
                title=f"New chat started by {current_user.get_name()}",
                message="You have a new chat with the admin.",
                type='info',
                link=url_for('client.view_chat', chat_id=chat.id))
        notify(current_user,
                title=f"Chat started with {chat.user.username}",
                message="You have a new chat with the client.",
                type='info',
                link=url_for('admin.view_chat', chat_id=chat.id))
        # Add initial message if provided
        if initial_message:
            message = ChatMessage(
                chat_id=chat.id,
                user_id=current_user.id,
                content=initial_message,
                is_read=True
            )
            db.session.add(message)
        
        db.session.commit()
        # notify(current_user,    
        #         title=f"Chat #{chat.id} has been created by {current_user.get_name()}",
        #         message="Chat created successfully",
        #         type='info',
        #         link=url_for('admin.view_chat', chat_id=chat.id))
        # notify(chat.user,
        #         title=f"Chat #{chat.id} has been created by {current_user.get_name()}",
        #         message="Chat created successfully",
        #         type='info',
        #         link=url_for('client.view_chat', chat_id=chat.id))
        flash('Chat created successfully', 'success')
        return redirect(url_for('admin.view_chat', chat_id=chat.id))
    
    # GET request - render form
    users = User.query.filter_by(is_admin=False).all()
    orders = Order.query.all()
    
    return render_template('admin/communication/create_chat.html',
                           users=users,
                           orders=orders,
                           title='Start New Chat')



@admin_bp.route('/orders')
@login_required
@admin_required
def list_orders():
    """Display all orders with filtering options."""
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = Order.query
    
    # Apply filters
    if status_filter:
        query = query.filter(Order.status == status_filter)
        
    if search_query:
        query = query.filter(
            (Order.order_number.ilike(f'%{search_query}%')) |
            (Order.subject.ilike(f'%{search_query}%')) |
            (Order.topic.ilike(f'%{search_query}%'))
        )
    
    # Get the sorted orders
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    if sort_order == 'desc':
        query = query.order_by(getattr(Order, sort_by).desc())
    else:
        query = query.order_by(getattr(Order, sort_by).asc())
    
    orders = query.all()
    
    # Get stats for the sidebar
    pending_count = Order.query.filter_by(status='pending').count()
    in_progress_count = Order.query.filter_by(status='active').count()
    under_review_count = Order.query.filter_by(status='completed pending review').count()
    completed_count = Order.query.filter_by(status='completed').count()
    revision_count = Order.query.filter_by(status='revision').count()
    now = datetime.now()
    return render_template('admin/orders/list.html', 
                           orders=orders,
                           status_filter=status_filter,
                           search_query=search_query,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           pending_count=pending_count,
                           in_progress_count=in_progress_count,
                           under_review_count=under_review_count,
                           completed_count=completed_count,
                           revision_count=revision_count,
                           now=now,
                           title='Order Management')

@admin_bp.route('/orders/<int:order_id>')
@login_required
@admin_required
def view_order(order_id):
    """View detailed information about a specific order."""
    order = Order.query.get_or_404(order_id)
    comments = OrderComment.query.filter_by(order_id=order_id).order_by(OrderComment.created_at.desc()).all()
    files = OrderFile.query.filter_by(order_id=order_id).all()
    delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
    chat = Chat.query.filter_by(order_id=order_id).first()
    if not chat:
        chat = []
    support_ticket = SupportTicket.query.filter_by(order_id=order_id).first()
    print(support_ticket)
    if not support_ticket:
        support_ticket = []
    print(delivery)
    if delivery:           
        admin_files = OrderDeliveryFile.query.filter_by(delivery_id=delivery.id).all()
    else:
        admin_files = []
    payments = Payment.query.filter_by(order_id=order_id).all()
    plagiarism_checks = PlagiarismCheck.query.filter_by(order_id=order_id).all()
    client_stats = {
        'total_orders': Order.query.filter_by(client_id=order.client_id).count(),
        'total_spent': db.session.query(
            func.coalesce(func.sum(Order.total_price), 0.0)
        ).filter(
            and_(
                Order.client_id == order.client_id,
                Order.paid == True
            )
        ).scalar(),
        'joined_days': (datetime.now() - order.client.created_at).days
    }

    return render_template('admin/orders/view.html',
                           order=order,
                           chat=chat,
                           comments=comments,
                           files=files,
                           admin_files=admin_files,
                           payments=payments,
                           plagiarism_checks=plagiarism_checks,
                           client_stats=client_stats,
                           datetime=datetime.now(),
                           support_ticket=support_ticket,
                           title=f'Order #{order.order_number}')



@admin_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_status(order_id):
    """Update the status of an order."""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status not in ['pending', 'active', 'completed', 'cancelled', 'revision', 'overdue']:
        flash('Invalid status value', 'danger')
        return redirect(url_for('admin.view_order', order_id=order_id))
    
    # If marking as completed, set completion date
    if new_status == 'completed' and order.status != 'completed':
        order.completion_date = datetime.now()
    
    order.status = new_status
    db.session.commit()
    notify(current_user,
            title=f"Order #{order.order_number} status updated to {new_status}",
            message="Order status updated successfully",
            type='info',
            link=url_for('admin.view_order', order_id=order.id))
    notify(order.client,
            title=f"Your order #{order.order_number} status updated to {new_status}",
            message="Order status updated successfully",
            type='info',
            link=url_for('orders.order_detail', order_number=order.id))
    flash(f'Order status updated to {new_status}', 'success')
    return redirect(url_for('admin.view_order', order_id=order_id))

@admin_bp.route('/orders/<int:order_id>/add-comment', methods=['POST'])
@login_required
@admin_required
def add_comment(order_id):
    """Add a comment to an order."""
    order = Order.query.get_or_404(order_id)
    message = request.form.get('message')
    
    if not message:
        flash('Comment cannot be empty', 'danger')
        return redirect(url_for('admin.view_order', order_id=order_id))
    
    comment = OrderComment(
        order_id=order_id,
        user_id=current_user.id,
        message=message,
        is_admin=True
    )
    notify(current_user,
            title=f"Comment added to Order #{order.order_number}",
            message=message,
            type='info',
            link=url_for('admin.view_order', order_id=order.id))
    notify(order.client,
            title=f"New comment on your Order #{order.order_number}",
            message=message,
            type='info',
            link=url_for('client.view_order', order_id=order.id))
    db.session.add(comment)
    db.session.commit()
    
    flash('Comment added successfully', 'success')
    return redirect(url_for('admin.view_order', order_id=order_id))

@admin_bp.route('/orders/<int:order_id>/upload-file', methods=['POST'])
@login_required
@admin_required
def upload_file(order_id):
    """Upload a file to an order."""
    order = Order.query.get_or_404(order_id)
    
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('admin.view_order', order_id=order_id))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('admin.view_order', order_id=order_id))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_category = "submission"
        file_type = request.form.get('file_type')
        
        # Create directory if it doesn't exist
        upload_dir = os.path.join('app', 'static', 'uploads', 'orders', str(order_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Save file info to database
        order_file = OrderFile(
            order_id=order_id,
            file_name=filename,
            file_path=os.path.join('uploads', 'orders', str(order_id), unique_filename),
            file_type=file.content_type,
            file_category=file_category,
            is_from_client=False,
        )
        
        db.session.add(order_file)
        db.session.commit()
        notify(current_user,
                title=f"File uploaded to Order #{order.order_number}",
                message=f"File {filename} uploaded successfully.",
                type='info',
                link=url_for('admin.view_order', order_id=order.id))
        notify(order.client,    
                title=f"New file uploaded to your Order #{order.order_number}",
                message=f"File {filename} uploaded successfully.",
                type='info',
                link=url_for('client.view_order', order_id=order.id))
        flash('File uploaded successfully', 'success')
    
    return redirect(url_for('admin.view_order', order_id=order_id))

@admin_bp.route('/orders/<int:order_id>/plagiarism-check', methods=['POST'])
@login_required
@admin_required
def check_plagiarism(order_id):
    """Run a plagiarism check on the content."""
    order = Order.query.get_or_404(order_id)
    content = request.form.get('content')
    
    if not content:
        flash('Content is required for plagiarism check', 'danger')
        return redirect(url_for('admin.view_order', order_id=order_id))
    
    # Mock plagiarism check (in a real app, you would integrate with a plagiarism detection API)
    import random
    similarity_score = round(random.uniform(0.0, 30.0), 2)
    
    # Create mock results
    result = {
        'overall_score': similarity_score,
        'matched_sources': [
            {
                'url': 'https://example.com/source1',
                'match_percentage': round(similarity_score * 0.7, 2),
                'matched_text': content[:50] + '...'
            },
            {
                'url': 'https://example.org/source2',
                'match_percentage': round(similarity_score * 0.3, 2),
                'matched_text': content[-50:] + '...'
            }
        ]
    }
    
    # Save the check to the database
    plagiarism_check = PlagiarismCheck(
        order_id=order_id,
        content=content,
        result=result,
        similarity_score=similarity_score
    )
    
    db.session.add(plagiarism_check)
    db.session.commit()
    
    flash(f'Plagiarism check completed. Similarity score: {similarity_score}%', 'success')
    return redirect(url_for('admin.view_order', order_id=order_id))

@admin_bp.route('/orders/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_order():
    """Create a new order."""
    if request.method == 'POST':
        # Get form data
        client_id = request.form.get('client_id')
        service_id = request.form.get('service_id')
        academic_level_id = request.form.get('academic_level_id')
        deadline_id = request.form.get('deadline_id')
        subject = request.form.get('subject')
        topic = request.form.get('topic')
        instructions = request.form.get('instructions')
        word_count = request.form.get('pages', 1, type=int)
        page_count = word_count * 275  # assuming 275 words per page
        format_style = request.form.get('format_style')
        
        # Generate order number
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Create new order object
        order = Order(
            order_number=order_number,
            client_id=client_id,
            service_id=service_id,
            academic_level_id=academic_level_id,
            deadline_id=deadline_id,
            title=topic,
            description=instructions,
            word_count=word_count,
            page_count=page_count,
            format_style=format_style,
        )
        total_price = order.calculate_price()
        db.session.add(order)
        db.session.commit()
        notify(current_user,
                title=f"Order #{order.order_number} has been created by {current_user.get_name()}",
                message="Order created successfully",
                type='info',
                link=url_for('admin.view_order', order_id=order.id))
        notify(order.client,
                title=f"New order #{order.order_number} has been created",
                message="Order created successfully",
                type='info',
                link=url_for('client.view_order', order_id=order.id))
        flash('Order created successfully', 'success')
        return redirect(url_for('admin.view_order', order_id=order.id))
    
    # GET request - render form
    clients = User.query.filter_by(is_admin=False).all()
    services = Service.query.all()
    academic_levels = AcademicLevel.query.order_by(AcademicLevel.order).all()
    deadlines = Deadline.query.order_by(Deadline.order).all()
    
    return render_template('admin/orders/create.html',
                           clients=clients,
                           services=services,
                           academic_levels=academic_levels,
                           deadlines=deadlines,
                           title='Create New Order')

@admin_bp.route('/orders/<int:order_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_order(order_id):
    """Edit an existing order."""
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        # Update order details
        order.service_id = request.form.get('service_id', order.service_id)
        order.academic_level_id = request.form.get('academic_level_id', order.academic_level_id)
        order.deadline_id = request.form.get('deadline_id', order.deadline_id)
        # order.subject = request.form.get('subject', order.subject)
        order.title = request.form.get('topic', order.topic)
        order.description = request.form.get('instructions', order.instructions)
        order.word_count = request.form.get('pages', order.pages, type=int)
        order.page_count = order.pages * 275  # update word count based on pages
        order.format_style = request.form.get('format_style', order.format_style)
        
        # Recalculate price if needed
        if 'recalculate_price' in request.form:
            order.total_price = order.calculate_price()
        notify(current_user,
                title=f"Order #{order.order_number} has been updated by {current_user.get_name()}",
                message="Order updated successfully",
                type='info',
                link=url_for('admin.view_order', order_id=order.id))
        notify(order.client,
                title=f"Order #{order.order_number} has been updated",
                message="Order updated successfully",
                type='info',
                link=url_for('client.view_order', order_id=order.id))
        db.session.commit()
        flash('Order updated successfully', 'success')
        return redirect(url_for('admin.view_order', order_id=order.id))
    
    # GET request - render form with current values
    clients = User.query.filter_by(is_admin=False).all()
    services = Service.query.all()
    academic_levels = AcademicLevel.query.order_by(AcademicLevel.order).all()
    deadlines = Deadline.query.order_by(Deadline.order).all()
    
    return render_template('admin/orders/edit.html',
                           order=order,
                           clients=clients,
                           services=services,
                           academic_levels=academic_levels,
                           deadlines=deadlines,
                           title=f'Edit Order #{order.order_number}')

@admin_bp.route('/payments/')
@login_required
@admin_required
def list_payments():
    """Display all payments with filtering options."""
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Base query
    query = Payment.query
    
    # Apply filters
    if status_filter:
        query = query.filter(Payment.status == status_filter)
        
    if search_query:
        query = query.join(Order).join(User).filter(
            (Order.order_number.ilike(f'%{search_query}%')) |
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%')) |
            (Payment.transaction_id.ilike(f'%{search_query}%'))
        )
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Payment.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj + timedelta(days=1)  # Include the entire day
            query = query.filter(Payment.created_at < date_to_obj)
        except ValueError:
            pass
    
    # Get the sorted payments
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    if sort_order == 'desc':
        query = query.order_by(getattr(Payment, sort_by).desc())
    else:
        query = query.order_by(getattr(Payment, sort_by).asc())
    
    payments = query.all()
    
    # Get stats for the sidebar
    completed_count = Payment.query.filter_by(status='completed').count()
    pending_count = Payment.query.filter_by(status='pending').count()
    failed_count = Payment.query.filter_by(status='failed').count()
    refunded_count = Payment.query.filter_by(status='refunded').count()
    
    # Calculate total revenue
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter(Payment.status == 'completed').scalar() or 0
    
    return render_template('admin/payments/list.html', 
                           payments=payments,
                           status_filter=status_filter,
                           search_query=search_query,
                           date_from=date_from,
                           date_to=date_to,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           completed_count=completed_count,
                           pending_count=pending_count,
                           failed_count=failed_count,
                           refunded_count=refunded_count,
                           total_revenue=total_revenue,
                           title='Payment Management')

@admin_bp.route('/payments/<int:payment_id>')
@login_required
@admin_required
def view_payment(payment_id):
    """View detailed information about a specific payment."""
    payment = Payment.query.get_or_404(payment_id)
    refunds = Refund.query.filter_by(payment_id=payment_id).all()
    
    return render_template('admin/payments/view.html',
                           payment=payment,
                           refunds=refunds,
                           title=f'Payment Details')

@admin_bp.route('/payments/<int:payment_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_payment_status(payment_id):
    """Update the status of a payment."""
    payment = Payment.query.get_or_404(payment_id)
    new_status = request.form.get('status')
    
    if new_status not in ['pending', 'completed', 'failed', 'refunded']:
        flash('Invalid status value', 'danger')
        return redirect(url_for('admin.view_payment', payment_id=payment_id))
    
    payment.status = new_status
    
    # If marking as completed, set payment date
    if new_status == 'completed' and not payment.payment_date:
        payment.payment_date = datetime.now()
    
    # Update the order's payment status
    if payment.order:
        if new_status == 'completed':
            payment.order.payment_status = 'Paid'
        elif new_status == 'refunded':
            payment.order.payment_status = 'Refunded'
        elif new_status == 'pending':
            payment.order.payment_status = 'Pending'
        elif new_status == 'failed':
            payment.order.payment_status = 'Unpaid'
    
    db.session.commit()
    notify(current_user,
            title=f"Payment #{payment.transaction_id} status updated to {new_status}",
            message="Payment status updated successfully",
            type='info',
            link=url_for('admin.view_payment', payment_id=payment.id))
    notify(payment.user,
            title=f"Your payment #{payment.transaction_id} status updated to {new_status}",
            message="Payment status updated successfully",
            type='info',
            link=url_for('client.view_payment', payment_id=payment.id))
    if payment.order:
        notify(payment.order.client,
                title=f"Your order #{payment.order.order_number} payment status updated to {new_status}",
                message="Payment status updated successfully",
                type='info',
                link=url_for('client.view_order', order_id=payment.order.id))
    
    flash(f'Payment status updated to {new_status}', 'success')
    return redirect(url_for('admin.view_payment', payment_id=payment_id))

@admin_bp.route('/payments/<int:order_id>/record-payment', methods=['POST'])
@login_required
@admin_required
def record_payment(order_id):
    """Record a payment for an order."""
    order = Order.query.get_or_404(order_id)
    amount = request.form.get('amount', 0, type=float)
    payment_method = request.form.get('payment_method', 'manual')
    
    if amount <= 0:
        flash('Invalid payment amount', 'danger')
        return redirect(url_for('admin.view_order', order_id=order_id))
    
    # Create payment record
    payment = Payment(
        order_id=order.id,
        user_id=order.client_id,
        amount=amount,
        payment_method=payment_method,
        transaction_id=f"ORD-{order.order_number}-{uuid.uuid4().hex[:8].upper()}",
        status='completed',
        payment_date=datetime.now(),
        created_at=datetime.now()
    )
    
    db.session.add(payment)
    notify(current_user,
            title=f"Payment for Order #{order.order_number} has been recorded",
            message=f"Payment of ${amount} recorded successfully.",
            type='info',
            link=url_for('admin.view_payment', payment_id=payment.id))
    notify(order.client,
            title=f"Payment for your Order #{order.order_number} has been recorded",
            message=f"Payment of ${amount} recorded successfully.",
            type='info',
            link=url_for('client.view_order', order_id=order.id))
    # Update order payment status
    order.payment_status = 'Paid'
    notify(order.client,
            title=f"Your Order #{order.order_number} payment status updated to Paid",
            message="Payment recorded successfully.",
            type='info',
            link=url_for('client.view_order', order_id=order.id))
    
    db.session.commit()
    
    flash('Payment recorded successfully', 'success')
    return redirect(url_for('admin.view_order', order_id=order_id))

@admin_bp.route('/payments/<int:payment_id>/refund', methods=['GET', 'POST'])
@login_required
@admin_required
def create_refund(payment_id):
    """Process a refund for a payment."""
    payment = Payment.query.get_or_404(payment_id)
    
    # Check if payment can be refunded
    if payment.status != 'completed':
        flash('Only completed payments can be refunded', 'danger')
        return redirect(url_for('admin.view_payment', payment_id=payment_id))
    
    if request.method == 'POST':
        amount = request.form.get('amount', 0, type=float)
        reason = request.form.get('reason', '')
        
        if amount <= 0 or amount > payment.amount:
            flash('Invalid refund amount', 'danger')
            return redirect(url_for('admin.create_refund', payment_id=payment_id))
        
        # Create refund
        refund = Refund(
            payment_id=payment_id,
            amount=amount,
            reason=reason,
            processed_by=current_user.id,
            status='processed',
            refund_date=datetime.now()
        )
        
        db.session.add(refund)
        
        # Update payment status to refunded if full refund
        if amount == payment.amount:
            payment.status = 'refunded'
            if payment.order:
                payment.order.payment_status = 'Refunded'
        
        db.session.commit()
        
        flash('Refund processed successfully', 'success')
        return redirect(url_for('admin.view_payment', payment_id=payment_id))
    
    return render_template('admin/payments/refund.html',
                           payment=payment,
                           title='Process Refund')

@admin_bp.route('/payments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_payment():
    """Create a manual payment record."""
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        user_id = request.form.get('user_id')
        amount = request.form.get('amount', 0, type=float)
        payment_method = request.form.get('payment_method', 'manual')
        status = request.form.get('status', 'completed')
        
        # Validate inputs
        if not order_id or not user_id or amount <= 0:
            flash('Invalid payment details', 'danger')
            return redirect(url_for('admin.create_payment'))
        
        # Create payment record
        payment = Payment(
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            payment_method=payment_method,
            transaction_id=f"MAN-{uuid.uuid4().hex[:8].upper()}",
            status=status,
            payment_date=datetime.now() if status == 'completed' else None,
            created_at=datetime.now()
        )
        
        db.session.add(payment)
        
        # Update order payment status
        order = Order.query.get(order_id)
        if order:
            if status == 'completed':
                order.payment_status = 'Paid'
            elif status == 'pending':
                order.payment_status = 'Pending'
        
        db.session.commit()
        
        flash('Payment created successfully', 'success')
        return redirect(url_for('admin.view_payment', payment_id=payment.id))
    
    # GET request - render form
    orders = Order.query.filter_by(payment_status='Unpaid').all()
    users = User.query.all()
    
    return render_template('admin/payments/create.html',
                           orders=orders,
                           users=users,
                           title='Create Manual Payment')

@admin_bp.route('/payments/discounts')
@login_required
@admin_required
def list_discounts():
    """List all discount codes."""
    discounts = Discount.query.all()
    return render_template('admin/payments/discounts.html',
                           discounts=discounts,
                           title='Discount Codes')

@admin_bp.route('/payments/discounts/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_discount():
    """Create a new discount code."""
    if request.method == 'POST':
        code = request.form.get('code', '').upper()
        description = request.form.get('description', '')
        discount_type = request.form.get('discount_type', 'percentage')
        amount = request.form.get('amount', 0, type=float)
        min_order_value = request.form.get('min_order_value', 0, type=float)
        max_discount_value = request.form.get('max_discount_value', None, type=float)
        usage_limit = request.form.get('usage_limit', None, type=int)
        valid_from = datetime.now()
        valid_to = None
        
        if request.form.get('valid_to'):
            try:
                valid_to = datetime.strptime(request.form.get('valid_to'), '%Y-%m-%d')
            except ValueError:
                pass
        
        # Validate inputs
        if not code or amount <= 0:
            flash('Invalid discount details', 'danger')
            return redirect(url_for('admin.create_discount'))
        
        # Check if code already exists
        if Discount.query.filter_by(code=code).first():
            flash('Discount code already exists', 'danger')
            return redirect(url_for('admin.create_discount'))
        
        # Create discount
        discount = Discount(
            code=code,
            description=description,
            discount_type=discount_type,
            amount=amount,
            min_order_value=min_order_value,
            max_discount_value=max_discount_value,
            valid_from=valid_from,
            valid_to=valid_to,
            usage_limit=usage_limit,
            is_active=True
        )
        
        db.session.add(discount)
        db.session.commit()
        
        flash('Discount code created successfully', 'success')
        return redirect(url_for('admin.list_discounts'))
    
    return render_template('admin/payments/create_discount.html',
                           title='Create Discount Code')

@admin_bp.route('/payments/discounts/<int:discount_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_discount(discount_id):
    """Toggle the active status of a discount code."""
    discount = Discount.query.get_or_404(discount_id)
    discount.is_active = not discount.is_active
    db.session.commit()
    
    status = 'activated' if discount.is_active else 'deactivated'
    flash(f'Discount code {discount.code} {status}', 'success')
    return redirect(url_for('admin.list_discounts'))

@admin_bp.route('/payments/discounts/<int:discount_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_discount(discount_id):
    """Delete a discount code."""
    discount = Discount.query.get_or_404(discount_id)
    db.session.delete(discount)
    db.session.commit()
    
    flash('Discount code deleted successfully', 'success')
    return redirect(url_for('admin.list_discounts'))

@admin_bp.route('/users/')
@login_required
@admin_required
def list_users():
    """Display all users with filtering options."""
    admin_filter = request.args.get('admin', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = User.query
    
    # Apply filters
    if admin_filter == 'true':
        query = query.filter(User.is_admin == True)
    elif admin_filter == 'false':
        query = query.filter(User.is_admin == False)
        
    if search_query:
        query = query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%')) |
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%'))
        )
    
    # Get the sorted users
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    if sort_order == 'desc':
        query = query.order_by(getattr(User, sort_by).desc())
    else:
        query = query.order_by(getattr(User, sort_by).asc())
    
    users = query.all()
    
    # Get stats for the sidebar
    total_users = User.query.count()
    admin_users = User.query.filter_by(is_admin=True).count()
    client_users = User.query.filter_by(is_admin=False).count()
    
    return render_template('admin/users/list.html', 
                           users=users,
                           admin_filter=admin_filter,
                           search_query=search_query,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           total_users=total_users,
                           admin_users=admin_users,
                           client_users=client_users,
                           title='User Management')

@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """View detailed information about a specific user."""
    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(client_id=user_id).all()
    referrals = Referral.query.filter_by(referrer_id=user_id).all()
    
    return render_template('admin/users/view.html',
                           user=user,
                           orders=orders,
                           timedelta=timedelta,
                           referrals=referrals,
                           title=f'User: {user.username}')

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new user."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        is_admin = True if request.form.get('is_admin') == 'true' else False
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('admin.create_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin.create_user'))
        
        # Generate referral code
        referral_code = uuid.uuid4().hex[:8].upper()
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
            referral_code=referral_code,
            email_verified=True  # Admin-created users are pre-verified
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        notify(current_user,
                title=f"New user {user.username} created",
                message="User created successfully",
                type='info',
                link=url_for('admin.view_user', user_id=user.id))
        notify(user,
                title="Welcome to TunedEssays!",
                message="Your account has been created successfully.",
                type='info',
                link=url_for('client.dashboard'))
        flash('User created successfully', 'success')
        return redirect(url_for('admin.view_user', user_id=user.id))
    
    return render_template('admin/users/create.html', title='Create New User')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit an existing user."""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Update user details
        user.username = request.form.get('username', user.username)
        user.email = request.form.get('email', user.email)
        user.first_name = request.form.get('first_name', user.first_name)
        user.last_name = request.form.get('last_name', user.last_name)
        user.is_admin = True if request.form.get('is_admin') == 'true' else False
        user.email_verified = True if request.form.get('email_verified') == 'true' else False
        user.reward_points = request.form.get('reward_points', user.reward_points, type=int)
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password and new_password.strip():
            user.set_password(new_password)
        
        db.session.commit()
        notify(current_user,
                title=f"User {user.username} updated",
                message="User details updated successfully",
                type='info',
                link=url_for('admin.view_user', user_id=user.id))
        notify(user,
                title="Your account details have been updated",
                message="Your account information has been updated successfully.",
                type='info',
                link=url_for('client.dashboard'))
        
        flash('User updated successfully', 'success')
        return redirect(url_for('admin.view_user', user_id=user.id))
    
    return render_template('admin/users/edit.html', user=user, title=f'Edit User: {user.username}')

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting self
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.list_users'))
    notify(current_user,
            title=f"User {user.username} deleted",
            message="User account deleted successfully",
            type='info',
            link=url_for('admin.list_users'))
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/users/<int:user_id>/add-reward-points', methods=['POST'])
@login_required
@admin_required
def add_reward_points(user_id):
    """Add reward points to a user."""
    user = User.query.get_or_404(user_id)
    points = request.form.get('points', 0, type=int)
    
    if points <= 0:
        flash('Points must be a positive number', 'danger')
        return redirect(url_for('admin.view_user', user_id=user.id))
    
    user.reward_points += points
    db.session.commit()
    notify(current_user,
            title=f"Reward points added to {user.username}",
            message=f"{points} reward points added successfully.",
            type='info',
            link=url_for('admin.view_user', user_id=user.id))
    notify(user,
            title="Reward points added to your account",
            message=f"You have received {points} reward points.",
            type='info',
            link=url_for('client.dashboard'))
    flash(f'Added {points} reward points to {user.username}', 'success')
    return redirect(url_for('admin.view_user', user_id=user.id))

@admin_bp.route('/users/<int:user_id>/reset-failed-logins', methods=['POST'])
@login_required
@admin_required
def reset_failed_logins(user_id):
    """Reset failed login attempts for a user."""
    user = User.query.get_or_404(user_id)
    
    user.failed_login_attempts = 0
    user.last_failed_login = None
    db.session.commit()
    notify(current_user,
            title=f"Failed login attempts reset for {user.username}",
            message="Failed login attempts reset successfully.",
            type='info',
            link=url_for('admin.view_user', user_id=user.id))
    notify(user,
            title="Your failed login attempts have been reset",
            message="Your account is now secure.",
            type='info',
            link=url_for('client.dashboard'))
    flash('Failed login attempts reset successfully', 'success')
    return redirect(url_for('admin.view_user', user_id=user.id))

@admin_bp.route('/services')
@login_required
@admin_required
def services_management():
    """
    Display the services management page
    """
    categories = ServiceCategory.query.order_by(ServiceCategory.order).all()
    categories_data = [category.to_dict() for category in categories]
    services = Service.query.all()
    services_data = [service.to_dict() for service in services]
    featured_count = Service.query.filter_by(featured=True).count()
    pricing_categories = PricingCategory.query.order_by(PricingCategory.display_order).all()
    pricing_categories_data = [price_cat.to_dict() for price_cat in pricing_categories]
    # Add services to each category for template rendering
    for category in categories:
        category.services = Service.query.filter_by(category_id=category.id).all()
    
    return render_template(
        'admin/services/services.html',
        categories_data=categories_data,
        services_data=services_data,
        categories=categories,
        services=services,
        featured_count=featured_count,
        pricing_categories=pricing_categories,
        pricing_categories_data=pricing_categories_data,
        title='Services Management'
    )

@admin_bp.route('/services/category/save', methods=['POST'])
@login_required
@admin_required
def save_category():
    """
    Create or update a service category
    """
    category_id = request.form.get('category_id')
    name = request.form.get('name')
    description = request.form.get('description')
    
    
    if not name:
        flash('Category name is required', 'danger')
        return redirect(url_for('admin.services_management'))
    
    # Update existing category
    if category_id:
        category = ServiceCategory.query.get(category_id)
        if not category:
            flash('Category not found', 'danger')
            return redirect(url_for('admin.services_management'))
        
        category.name = name
        category.description = description
        try:
            db.session.commit()
            notify(current_user,
                    title=f"Service category {category.name} updated",
                    message="Category updated successfully",
                    type='info',
                    link=url_for('admin.services_management'))
            flash('Category updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Database error occurred', 'danger')
            return redirect(url_for('admin.services_management'))
    
    # Create new category
    else:
        # Get the highest order value
        max_order = db.session.query(db.func.max(ServiceCategory.order)).scalar() or 0
        category = ServiceCategory(
            name=name,
            description=description,
            order=max_order + 1
        )
        try:
            db.session.add(category)
            db.session.commit()
            notify(current_user,
                    title=f"New service category {category.name} created",
                    message="Category created successfully",
                    type='info',
                    link=url_for('admin.services_management'))
            flash('Category created successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Database error occurred', 'danger')
            return redirect(url_for('admin.services_management'))
    
    # db.session.commit()
    return redirect(url_for('admin.services_management'))

@admin_bp.route('/services/category/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    """
    Delete a service category and all its services
    """
    category = ServiceCategory.query.get_or_404(category_id)
    
    # Delete all services in this category first
    Service.query.filter_by(category_id=category_id).delete()
    
    # Delete the category
    try:
        db.session.delete(category)
        db.session.commit()
        notify(current_user,
                title=f"Service category {category.name} deleted",
                message="Category and its services deleted successfully",
                type='info',
                link=url_for('admin.services_management'))
        flash(f'Category "{category.name}" and all its services have been deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Database error occurred', 'danger')
        return redirect(url_for('admin.services_management'))
    return redirect(url_for('admin.services_management'))

@admin_bp.route('/services/category/order', methods=['POST'])
@login_required
@admin_required
def update_category_order():
    """
    Update the order of categories
    """
    data = request.json
    if not data or 'categories' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    
    categories = data['categories']
    
    try:
        for category_data in categories:
            category_id = category_data.get('id')
            order = category_data.get('order')
            
            category = ServiceCategory.query.get(category_id)
            if category:
                category.order = order
        
        db.session.commit()
        notify(current_user,
                title="Service categories reordered",
                message="Categories reordered successfully",
                type='info',
                link=url_for('admin.services_management'))
        flash('Categories reordered successfully', 'success')
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        notify(current_user,
                title="Error reordering service categories",
                message=str(e),
                type='error',
                link=url_for('admin.services_management'))
        flash('Error reordering categories', 'danger')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/services/service/save', methods=['POST'])
@login_required
@admin_required
def save_service():
    """
    Create or update a service
    """
    service_id = request.form.get('service_id')
    name = request.form.get('name')
    if len(name.strip()) > 100:  
        flash('Service name too long (max 100 characters)', 'danger')
        return redirect(url_for('admin.services_management'))
    description = request.form.get('description')
    category_id = request.form.get('category_id')
    try:
        category_id = int(category_id) if category_id else None
    except ValueError:
        flash('Invalid category selection', 'danger')
        return redirect(url_for('admin.services_management'))
    featured = request.form.get('featured') == '1'
    tags = request.form.get('tags', '').strip()
    pricing_category_id = request.form.get('pricing_category_id')
    if not name:
        flash('Service name is required', 'danger')
        return redirect(url_for('admin.services_management'))
    
    if not category_id:
        flash('Category is required', 'danger')
        return redirect(url_for('admin.services_management'))
    
    if category_id:
        category_exists = ServiceCategory.query.get(category_id)
        if not category_exists:
            flash('Selected category does not exist', 'danger')
            return redirect(url_for('admin.services_management'))
   
    if service_id:
        service = Service.query.get(service_id)
        if not service:
            flash('Service not found', 'danger')
            return redirect(url_for('admin.services_management'))
        
        service.name = name
        service.description = description
        service.category_id = category_id
        service.featured = featured
        service.tags = tags
        service.pricing_category_id = pricing_category_id if pricing_category_id else None
        try:
            db.session.commit()
            notify(current_user,
                    title=f"Service {service.name} updated",
                    message="Service updated successfully",
                    type='info',
                    link=url_for('admin.services_management'))
            flash('Service updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Database error occurred', 'danger')
            return redirect(url_for('admin.services_management'))

    
    # Create new service
    else:
        service = Service(
            name=name,
            description=description,
            category_id=category_id,
            featured=featured,
            tags=tags if tags else None,
            pricing_category_id=pricing_category_id if pricing_category_id else None
        )
        try:
            db.session.add(service)
            db.session.commit()
            notify(current_user,
                    title=f"New service {service.name} created",
                    message="Service created successfully",
                    type='info',
                    link=url_for('admin.services_management'))
            flash('Service created successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Database error occurred', 'danger')
            return redirect(url_for('admin.services_management'))
    
    # db.session.commit()
    return redirect(url_for('admin.services_management'))

@admin_bp.route('/services/service/delete/<int:service_id>', methods=['POST'])
@login_required
@admin_required
def delete_service(service_id):
    """
    Delete a service
    """
    service = Service.query.get_or_404(service_id)
    
    # Get service name before deletion for flash message
    service_name = service.name
    
    # Delete the service
    try:
        db.session.delete(service)
        db.session.commit()
        notify(current_user,
                title=f"Service {service_name} deleted",
                message="Service deleted successfully",
                type='info',
                link=url_for('admin.services_management'))
        flash(f'Service "{service_name}" has been deleted', 'success')
        return redirect(url_for('admin.services_management'))
    except Exception as e:
        db.session.rollback()
        flash('Database error occurred', 'danger')
        return redirect(url_for('admin.services_management'))
MAX_FILE_SIZE = 16 * 1024 * 1024  
  
def get_file_format(filename):
    """Extract file format from filename"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

@admin_bp.route('/delivery/<int:order_id>/upload-additional-files', methods=['POST'])
@login_required
@admin_required
def upload_additional_delivery_files(order_id):
    """
    Upload additional files to an existing delivery without changing status
    """
    try:
        # Verify delivery exists
        # ord_id = Order.query.get_or_404(order_id)
        # if ord_id:

        delivery = OrderDelivery.query.get_or_404(order_id)
        if not delivery:
            try:
                delivery = OrderDelivery(
                        order_id=order_id,
                        delivery_status='delivered',
                        delivered_at=datetime.now()
                    )
            
                db.session.add(delivery)
                db.session.flush()
            except Exception as e:
                import logging 
                db.session.rollback()
                logging.error(f"ERROR occured while creating delivery instance: {e}") 
                return jsonify({
                    'success', False,
                    'message', f'ERROR: {e}'
                })
        
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No files provided'
            }), 400
        
        files = request.files.getlist('files')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({
                'success': False,
                'message': 'No files selected'
            }), 400
        
        # Get form data
        file_type = request.form.get('file_type', 'supplementary')
        description = request.form.get('description', '')
        
        # Validate file type
        if file_type not in ['delivery', 'plagiarism_report', 'supplementary']:
            file_type = 'supplementary'
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'deliveries', str(delivery.order_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        uploaded_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
                
            # Validate file
            if not allowed_file(file.filename):
                errors.append(f"File '{file.filename}' has invalid extension")
                continue
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            
            if file_size > MAX_FILE_SIZE:
                errors.append(f"File '{file.filename}' exceeds maximum size limit (16MB)")
                continue
            
            if file_size == 0:
                errors.append(f"File '{file.filename}' is empty")
                continue
            
            try:
                # Generate unique filename
                original_filename = secure_filename(file.filename)
                file_extension = get_file_format(original_filename)
                unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                file_path = os.path.join(upload_dir, unique_filename)
                
                # Save file
                file.save(file_path)
                
                # Create database record
                delivery_file = OrderDeliveryFile(
                    delivery_id=delivery.id,
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_type=file_type,
                    file_format=file_extension,
                    uploaded_at=datetime.now(),
                    description=description if description else None
                )
                
                db.session.add(delivery_file)
                uploaded_files.append({
                    'filename': original_filename,
                    'size': round(file_size / (1024 * 1024), 2),
                    'type': file_type
                })
                
            except Exception as e:
                errors.append(f"Failed to upload '{file.filename}': {str(e)}")
                # Clean up file if it was saved
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
        
        # Commit changes if any files were uploaded successfully
        if uploaded_files:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # Clean up uploaded files
                for file_info in uploaded_files:
                    file_path = os.path.join(upload_dir, file_info['filename'])
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                
                return jsonify({
                    'success': False,
                    'message': f'Database error: {str(e)}'
                }), 500
        
        # Return response
        if uploaded_files and not errors:
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {len(uploaded_files)} file(s)',
                'uploaded_files': uploaded_files
            }), 200
        elif uploaded_files and errors:
            return jsonify({
                'success': True,
                'message': f'Uploaded {len(uploaded_files)} file(s) with some errors',
                'uploaded_files': uploaded_files,
                'errors': errors
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'No files were uploaded',
                'errors': errors
            }), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error uploading additional delivery files: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred'
        }), 500
    


@admin_bp.route('/request-deadline-extension', methods=['POST'])
@login_required
@admin_required
def request_deadline_extension():
    try:
        # Get data from request
        data = request.get_json()
        order_id = data.get('order_id')
        description = data.get('description', '').strip()
        
        # Validate required fields
        if not order_id:
            return jsonify({
                'success': False, 
                'message': 'Order ID is required'
            }), 400
            
        if not description:
            return jsonify({
                'success': False, 
                'message': 'Description is required'
            }), 400
            
        admin_user_id = current_user.id
        
        # Verify order exists
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False, 
                'message': 'Order not found'
            }), 404
        
        # Check if extension is already requested
        if order.extension_requested:
            return jsonify({
                'success': False, 
                'message': 'Deadline extension has already been requested for this order'
            }), 400
        
        # Update order with extension request
        order.extension_requested = True
        order.extension_requested_at = datetime.now()
        
        # Create support ticket
        support_ticket = SupportTicket(
            order_id=order_id,
            user_id=order.client_id,  # Assign to the order's client
            subject="Deadline Extension Request",
            message=f"Writer has requested a deadline extension for Order #{order.order_number}.\n\nReason: {description}",
            status='open'
        )
        
        # Save to database
        db.session.add(support_ticket)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Deadline extension request submitted successfully',
            'ticket_id': support_ticket.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


@admin_bp.route('/get-extension-status/<int:order_id>', methods=['GET'])
@login_required
@admin_required
def get_extension_status(order_id):
    """Get the current extension request status for an order"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False, 
                'message': 'Order not found'
            }), 404
            
        return jsonify({
            'success': True,
            'extension_requested': order.extension_requested,
            'extension_requested_at': order.extension_requested_at.isoformat() if order.extension_requested_at else None
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500
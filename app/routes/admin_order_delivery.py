from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
from functools import wraps
from app.extensions import db
from app.models.order import  Order
from app.models.order_delivery import OrderDelivery, OrderDeliveryFile
from app.models.user import User

admin_delivery_bp = Blueprint('admin_delivery', __name__)

def admin_required(f):
    """Decorator to ensure only admin users can access these routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    allowed_extensions = {'pdf', 'docx', 'doc', 'txt', 'zip', 'rar', 'pptx', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@admin_delivery_bp.route('/orders/delivery')
@login_required
@admin_required
def delivery_dashboard():
    """Main delivery dashboard showing orders ready for delivery and recent deliveries"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    
    # Base query for orders that can be delivered (completed orders)
    orders_query = Order.query.filter(Order.status.in_(['completed pending review', 'active', 'revision', 'completed']))
    
    # Apply search filter
    if search_query:
        orders_query = orders_query.filter(
            db.or_(
                Order.order_number.ilike(f'%{search_query}%'),
                Order.title.ilike(f'%{search_query}%')
            )
        )
    
    # Filter by delivery status
    if status_filter == 'pending':
        # Orders without deliveries
        orders_query = orders_query.outerjoin(OrderDelivery).filter(OrderDelivery.id.is_(None))
    elif status_filter == 'delivered':
        # Orders with deliveries
        orders_query = orders_query.join(OrderDelivery)
    
    orders = orders_query.order_by(Order.due_date.asc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Recent deliveries for sidebar/overview
    recent_deliveries = OrderDelivery.query.order_by(
        OrderDelivery.delivered_at.desc()
    ).limit(10).all()
    
    # Delivery statistics
    stats = {
        'total_orders': Order.query.filter(Order.status.in_(['completed pending review', 'active', 'revision', 'completed'])).count(),
        'pending_delivery': Order.query.filter(Order.status.in_(['completed pending review', 'active', 'revision']))
                          .outerjoin(OrderDelivery).filter(OrderDelivery.id.is_(None)).count(),
        'delivered_today': OrderDelivery.query.filter(
            OrderDelivery.delivered_at >= datetime.now().date()
        ).count(),
        'revisions_pending': Order.query.filter(Order.status == 'revision').count()
    }
    current_date = datetime.now()
    return render_template('admin/orders/delivery.html',
                         orders=orders,
                         recent_deliveries=recent_deliveries,
                         stats=stats,
                         status_filter=status_filter,
                         current_date=current_date,
                         search_query=search_query)

@admin_delivery_bp.route('/orders/<int:order_id>/deliver', methods=['GET', 'POST'])
@login_required
@admin_required
def deliver_order(order_id):
    """Create or update delivery for an order"""
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        try:
            # Check if this is a new delivery or revision
            existing_delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
            
            if existing_delivery:
                # This is a revision/redelivery
                delivery = OrderDelivery(
                    order_id=order_id,
                    delivery_status='redelivered',
                    delivered_at=datetime.now()
                )
            else:
                # New delivery
                delivery = OrderDelivery(
                    order_id=order_id,
                    delivery_status='delivered',
                    delivered_at=datetime.now()
                )
            
            db.session.add(delivery)
            db.session.flush()  # Get delivery ID
            
            # Handle file uploads
            uploaded_files = request.files.getlist('delivery_files')
            file_descriptions = request.form.getlist('file_descriptions')
            file_types = request.form.getlist('file_types')
            
            upload_folder = current_app.config.get('DELIVERY_UPLOAD_FOLDER', 'uploads/deliveries')
            os.makedirs(upload_folder, exist_ok=True)
            
            for i, file in enumerate(uploaded_files):
                if file and file.filename and allowed_file(file.filename):
                    # Generate unique filename
                    original_filename = secure_filename(file.filename)
                    file_extension = original_filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
                    file_path = os.path.join(upload_folder, unique_filename)
                    
                    # Save file
                    file.save(file_path)
                    
                    # Create delivery file record
                    delivery_file = OrderDeliveryFile(
                        delivery_id=delivery.id,
                        filename=unique_filename,
                        original_filename=original_filename,
                        file_path=file_path,
                        file_type=file_types[i] if i < len(file_types) else 'delivery',
                        file_format=file_extension,
                        description=file_descriptions[i] if i < len(file_descriptions) else None
                    )
                    db.session.add(delivery_file)
            
            # Update order status
            if order.status != 'completed pending review':
                order.status = 'completed pending review'
            
            # Check if client should be notified
            notify_client = request.form.get('notify_client') == 'on'
            if notify_client:
                delivery.client_notified = True
                delivery.client_notified_at = datetime.now()
                # TODO: Add email notification logic here
                flash('Client notification sent successfully.', 'success')
            
            db.session.commit()
            flash(f'Order {order.order_number} delivered successfully!', 'success')
            return redirect(url_for('admin_delivery.delivery_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error delivering order: {str(e)}', 'error')
    
    # GET request - show delivery form
    now = datetime.now()
    existing_delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
    return render_template('admin/orders/deliver_form.html', 
                         order=order, 
                         now=now, 
                         existing_delivery=existing_delivery)
# @admin_delivery_bp.route('/orders/<int:order_id>/deliver', methods=['GET', 'POST'])
# @login_required
# @admin_required
# def deliver_order(order_id):
#     """Create or update delivery for an order"""
#     order = Order.query.get_or_404(order_id)
    
#     if request.method == 'POST':
#         try:
#             # Check if this is a new delivery or revision
#             existing_delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
            
#             if existing_delivery:
#                 # This is a revision/redelivery
#                 delivery = OrderDelivery(
#                     order_id=order_id,
#                     delivery_status='redelivered',
#                     delivered_at=datetime.now()
#                 )
#             else:
#                 # New delivery
#                 delivery = OrderDelivery(
#                     order_id=order_id,
#                     delivery_status='delivered',
#                     delivered_at=datetime.now()
#                 )
            
#             db.session.add(delivery)
#             db.session.flush()  # Get delivery ID
            
#             # Handle file uploads
#             uploaded_files = request.files.getlist('delivery_files')
#             file_descriptions = request.form.getlist('file_descriptions')
#             file_types = request.form.getlist('file_types')
            
#             upload_folder = current_app.config.get('DELIVERY_UPLOAD_FOLDER', 'uploads/deliveries')
#             os.makedirs(upload_folder, exist_ok=True)
            
#             uploaded_file_count = 0
#             for i, file in enumerate(uploaded_files):
#                 if file and file.filename and allowed_file(file.filename):
#                     # Generate unique filename
#                     original_filename = secure_filename(file.filename)
#                     file_extension = original_filename.rsplit('.', 1)[1].lower()
#                     unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
#                     file_path = os.path.join(upload_folder, unique_filename)
                    
#                     # Save file
#                     file.save(file_path)
                    
#                     # Create delivery file record
#                     delivery_file = OrderDeliveryFile(
#                         delivery_id=delivery.id,
#                         filename=unique_filename,
#                         original_filename=original_filename,
#                         file_path=file_path,
#                         file_type=file_types[i] if i < len(file_types) else 'delivery',
#                         file_format=file_extension,
#                         description=file_descriptions[i] if i < len(file_descriptions) else None
#                     )
#                     db.session.add(delivery_file)
#                     uploaded_file_count += 1
            
#             # Update order status (fix typo: "pedning" -> "pending")
#             if order.status != 'completed pending review':
#                 order.status = 'completed pending review'
            
#             # Check if client should be notified
#             notify_client = request.form.get('notify_client') == 'on'
#             if notify_client:
#                 delivery.client_notified = True
#                 delivery.client_notified_at = datetime.now()
#                 # TODO: Add email notification logic here
            
#             db.session.commit()
            
#             # Return JSON response for AJAX
#             return jsonify({
#                 'success': True,
#                 'message': f'Order {order.order_number} delivered successfully!',
#                 'files_uploaded': uploaded_file_count,
#                 'delivery_id': delivery.id
#             })
            
#         except Exception as e:
#             db.session.rollback()
#             return jsonify({
#                 'success': False,
#                 'message': f'Error delivering order: {str(e)}'
#             }), 400
    
#     # GET request - show delivery form
#     existing_delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
#     return render_template('admin/orders/deliver_form.html', 
#                          order=order, 
#                          existing_delivery=existing_delivery)

@admin_delivery_bp.route('/orders/delivery/<int:delivery_id>')
@login_required
@admin_required
def view_delivery(delivery_id):
    """View details of a specific delivery"""
    delivery = OrderDelivery.query.get_or_404(delivery_id)
    return render_template('admin/orders/delivery_detail.html', delivery=delivery)

@admin_delivery_bp.route('/orders/delivery/reports')
@login_required
@admin_required
def delivery_reports():
    """Generate delivery reports and analytics"""
    from sqlalchemy import func, extract
    
    # Get date range from query params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build base query
    query = OrderDelivery.query
    
    if start_date:
        query = query.filter(OrderDelivery.delivered_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(OrderDelivery.delivered_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    
    # Delivery statistics
    total_deliveries = query.count()
    deliveries_by_status = query.with_entities(
        OrderDelivery.delivery_status,
        func.count(OrderDelivery.id)
    ).group_by(OrderDelivery.delivery_status).all()
    
    # Monthly delivery trends
    monthly_deliveries = query.with_entities(
        extract('year', OrderDelivery.delivered_at).label('year'),
        extract('month', OrderDelivery.delivered_at).label('month'),
        func.count(OrderDelivery.id).label('count')
    ).group_by('year', 'month').order_by('year', 'month').all()
    
    # Average delivery time (from order creation to delivery)
    avg_delivery_time = db.session.query(
        func.avg(OrderDelivery.delivered_at - Order.created_at)
    ).join(Order).scalar()
    
    report_data = {
        'total_deliveries': total_deliveries,
        'deliveries_by_status': dict(deliveries_by_status),
        'monthly_deliveries': monthly_deliveries,
        'avg_delivery_time': avg_delivery_time,
        'start_date': start_date,
        'end_date': end_date
    }
    
    return render_template('admin/orders/delivery_reports.html', **report_data)

@admin_delivery_bp.route('/orders/delivery/<int:delivery_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_delivery_status(delivery_id):
    """Update delivery status (delivered, revised, redelivered)"""
    delivery = OrderDelivery.query.get_or_404(delivery_id)
    
    new_status = request.form.get('status')
    if new_status not in ['delivered', 'revised', 'redelivered']:
        return jsonify({'error': 'Invalid status'}), 400
    
    try:
        delivery.delivery_status = new_status
        
        # If marking as revised, update timestamps
        if new_status == 'revised':
            delivery.delivered_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Delivery status updated to {new_status}',
            'new_status': new_status,
            'status_color': delivery.status_color
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_delivery_bp.route('/orders/delivery/<int:delivery_id>/notify-client', methods=['POST'])
@login_required
@admin_required
def notify_client(delivery_id):
    """Send notification to client about delivery"""
    delivery = OrderDelivery.query.get_or_404(delivery_id)
    
    try:
        if not delivery.client_notified:
            delivery.client_notified = True
            delivery.client_notified_at = datetime.now()
            db.session.commit()
            
            # TODO: Implement actual email notification
            # send_delivery_notification_email(delivery.order.client, delivery)
            
            return jsonify({
                'success': True,
                'message': 'Client notified successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Client already notified'
            })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_delivery_bp.route('/orders/delivery/file/<int:file_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_delivery_file(file_id):
    """Delete a delivery file"""
    delivery_file = OrderDeliveryFile.query.get_or_404(file_id)
    
    try:
        # Delete physical file
        if os.path.exists(delivery_file.file_path):
            os.remove(delivery_file.file_path)
        
        # Delete database record
        db.session.delete(delivery_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_delivery_bp.route('/orders/delivery/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_delivery_actions():
    """Handle bulk actions on deliveries"""
    action = request.form.get('action')
    delivery_ids = request.form.getlist('delivery_ids')
    
    if not delivery_ids:
        flash('No deliveries selected.', 'warning')
        return redirect(url_for('admin_delivery.delivery_dashboard'))
    
    try:
        deliveries = OrderDelivery.query.filter(OrderDelivery.id.in_(delivery_ids)).all()
        
        if action == 'notify_clients':
            count = 0
            for delivery in deliveries:
                if not delivery.client_notified:
                    delivery.client_notified = True
                    delivery.client_notified_at = datetime.now()
                    count += 1
            
            db.session.commit()
            flash(f'Notified {count} clients successfully.', 'success')
            
        elif action == 'mark_revised':
            for delivery in deliveries:
                delivery.delivery_status = 'revised'
                delivery.delivered_at = datetime.now()
            
            db.session.commit()
            flash(f'Marked {len(deliveries)} deliveries as revised.', 'success')
        
        else:
            flash('Invalid bulk action.', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error performing bulk action: {str(e)}', 'error')
    
    return redirect(url_for('admin_delivery.delivery_dashboard'))

@admin_delivery_bp.route('/orders/delivery/download/<int:file_id>')
@login_required
@admin_required
def download_delivery_file(file_id):
    """Download a delivery file"""
    from flask import send_file
    
    delivery_file = OrderDeliveryFile.query.get_or_404(file_id)
    
    if not os.path.exists(delivery_file.file_path):
        flash('File not found on server.', 'error')
        return redirect(url_for('admin_delivery.delivery_dashboard'))
    
    return send_file(
        delivery_file.file_path,
        as_attachment=True,
        download_name=delivery_file.original_filename
    )

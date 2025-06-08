from flask import render_template, request, redirect, url_for, flash, abort, Blueprint
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
import logging
from app.extensions import db  
from app.models.order import Order, OrderComment
from app.models.order_delivery import OrderDelivery, OrderDeliveryFile
from app.models.user import User  

logger = logging.getLogger(__name__)
client_results_bp= Blueprint("client_results", __name__)


@client_results_bp.route("/proceessed-orders")
@login_required
def render_order_results_page():
    """
    Render the order results page for clients to review completed orders,
    download files, request revisions, and accept deliveries.
    """
    # Ensure only clients can access this page
    if current_user.is_admin:
        flash('Access denied. This page is for clients only.', 'error')
        return redirect(url_for('admin.dashboard'))  # Redirect admins to their dashboard
    
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 8, type=int)
        
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        search_query = request.args.get('search', '').strip()
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Build the base query for client's orders that are ready for review
        base_query = Order.query.filter(
            Order.client_id == current_user.id,
            Order.status.in_(['completed pending review', 'completed', 'revision'])
        )
        
        # Apply status filter
        if status_filter != 'all':
            if status_filter == 'pending_review':
                base_query = base_query.filter(Order.status == 'completed pending review')
            elif status_filter == 'completed':
                base_query = base_query.filter(Order.status == 'completed')
            elif status_filter == 'revision':
                base_query = base_query.filter(Order.status == 'revision')
        
        # Apply search filter
        if search_query:
            search_pattern = f"%{search_query}%"
            base_query = base_query.filter(
                or_(
                    Order.order_number.ilike(search_pattern),
                    Order.title.ilike(search_pattern),
                    Order.description.ilike(search_pattern)
                )
            )
        
        # Apply date filters
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                base_query = base_query.filter(Order.updated_at >= date_from_obj)
            except ValueError:
                flash('Invalid start date format', 'warning')
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                base_query = base_query.filter(Order.updated_at < date_to_obj)
            except ValueError:
                flash('Invalid end date format', 'warning')
        
        # Order by most recently updated first
        orders_query = base_query.order_by(Order.updated_at.desc())
        
        # Paginate the results
        orders_pagination = orders_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Prepare orders data with additional information
        orders_data = []
        for order in orders_pagination.items:
            # Get latest delivery
            latest_delivery = order.latest_delivery
            
            # Get delivery files count and types
            delivery_files_info = {
                'total_files': 0,
                'has_plagiarism_report': False,
                'main_files_count': 0,
                'file_types': set()
            }
            
            if latest_delivery:
                delivery_files_info['total_files'] = len(latest_delivery.delivery_files)
                delivery_files_info['has_plagiarism_report'] = latest_delivery.has_plagiarism_report
                delivery_files_info['main_files_count'] = latest_delivery.delivery_files_count
                
                for file in latest_delivery.delivery_files:
                    if file.file_format:
                        delivery_files_info['file_types'].add(file.file_format.upper())
            
            # Get recent comments count
            recent_comments_count = OrderComment.query.filter(
                OrderComment.order_id == order.id,
                OrderComment.created_at >= (datetime.now() - timedelta(days=7))
            ).count()
            
            # Calculate days since last update
            days_since_update = (datetime.now() - order.updated_at).days if order.updated_at else 0
            
            orders_data.append({
                'order': order,
                'latest_delivery': latest_delivery,
                'delivery_info': delivery_files_info,
                'recent_comments_count': recent_comments_count,
                'days_since_update': days_since_update,
                'can_request_revision': order.status == 'completed pending review',
                'can_accept': order.status == 'completed pending review',
                'is_completed': order.status == 'completed',
                'needs_revision': order.status == 'revision'
            })
        
        # Get summary statistics
        stats = get_client_order_stats(current_user.id)
        
        # Prepare filter options
        status_options = [
            {'value': 'all', 'label': 'All Statuses', 'selected': status_filter == 'all'},
            {'value': 'pending_review', 'label': 'Pending Review', 'selected': status_filter == 'pending_review'},
            {'value': 'completed', 'label': 'Completed', 'selected': status_filter == 'completed'},
            {'value': 'revision', 'label': 'Under Revision', 'selected': status_filter == 'revision'}
        ]
        
        # Prepare template context
        context = {
            'orders_data': orders_data,
            'pagination': orders_pagination,
            'stats': stats,
            'current_filters': {
                'status': status_filter,
                'search': search_query,
                'date_from': date_from,
                'date_to': date_to
            },
            'status_options': status_options,
            'page_title': 'Order Results',
            'current_page': 'order_results',
            'show_filters': True,
            'empty_message': get_empty_message(status_filter, search_query),
            'client_name': current_user.get_name() or current_user.username,
            'total_orders': orders_pagination.total,
            'current_time': datetime.now()
        }
        
        return render_template('orders/order_results.html', **context)
    
    except Exception as e:
        logger.error(f"Error rendering order results page: {str(e)}")
        flash('An error occurred while loading your orders. Please try again.', 'error')
        return redirect(url_for('client.dashboard'))  # Fallback redirect


# @client_results_bp.route("/processed-order-stats")
# @login_required
def get_client_order_stats(client_id):
    """Get statistical information about client's orders"""
    try:
        # Base query for client's reviewable orders
        base_query = Order.query.filter(
            Order.client_id == client_id,
            Order.status.in_(['completed pending review', 'completed', 'revision'])
        )
        
        # Count orders by status
        pending_review_count = base_query.filter(Order.status == 'completed pending review').count()
        completed_count = base_query.filter(Order.status == 'completed').count()
        revision_count = base_query.filter(Order.status == 'revision').count()
        
        # Count orders with deliveries
        orders_with_deliveries = base_query.join(OrderDelivery).count()
        
        # Count recent orders (last 30 days)
        recent_date = datetime.now() - timedelta(days=30)
        recent_orders_count = base_query.filter(Order.updated_at >= recent_date).count()
        
        # Calculate total value of completed orders
        total_completed_value = db.session.query(
            db.func.sum(Order.total_price)
        ).filter(
            Order.client_id == client_id,
            Order.status not in ['pending', 'cancelled']
        ).scalar() or 0
        
        return {
            'pending_review': pending_review_count,
            'completed': completed_count,
            'revision': revision_count,
            'total_reviewable': pending_review_count + completed_count + revision_count,
            'with_deliveries': orders_with_deliveries,
            'recent_orders': recent_orders_count,
            'total_completed_value': float(total_completed_value),
            'has_pending_actions': pending_review_count > 0
        }
    
    except Exception as e:
        logger.error(f"Error calculating client order stats: {str(e)}")
        return {
            'pending_review': 0,
            'completed': 0,
            'revision': 0,
            'total_reviewable': 0,
            'with_deliveries': 0,
            'recent_orders': 0,
            'total_completed_value': 0.0,
            'has_pending_actions': False
        }


@client_results_bp.route("/empty")
@login_required
def get_empty_message(status_filter, search_query):
    """Get appropriate empty state message based on filters"""
    if search_query:
        return f"No orders found matching '{search_query}'"
    
    messages = {
        'all': "No completed orders found. Orders will appear here once they're ready for review.",
        'pending_review': "No orders are currently pending your review.",
        'completed': "You haven't completed any orders yet.",
        'revision': "No orders are currently under revision."
    }
    
    return messages.get(status_filter, messages['all'])



# Additional helper function for order detail view
@client_results_bp.route("/detail")
@login_required
def render_order_detail_page(order_id):
    """
    Render detailed view of a specific order for review
    """
    if current_user.is_admin:
        flash('Access denied. This page is for clients only.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    try:
        # Get the order and verify ownership
        order = Order.query.filter_by(id=order_id, client_id=current_user.id).first()
        if not order:
            abort(404, description="Order not found")
        
        # Check if order is in a reviewable state
        if order.status not in ['completed pending review', 'completed', 'revision']:
            flash('This order is not ready for review yet.', 'info')
            return redirect(url_for('client.order_results'))
        
        # Get delivery history
        deliveries = OrderDelivery.query.filter_by(order_id=order.id).order_by(
            OrderDelivery.delivered_at.desc()
        ).all()
        
        # Get comments history
        comments = OrderComment.query.filter_by(order_id=order.id).order_by(
            OrderComment.created_at.desc()
        ).limit(10).all()
        
        # Prepare delivery files data
        delivery_files_data = []
        if deliveries:
            latest_delivery = deliveries[0]
            for file in latest_delivery.delivery_files:
                delivery_files_data.append({
                    'file': file,
                    'download_url': url_for('client.download_delivery_file', file_id=file.id),
                    'is_safe_to_download': True  # Add any additional security checks here
                })
        
        context = {
            'order': order,
            'deliveries': deliveries,
            'latest_delivery': deliveries[0] if deliveries else None,
            'delivery_files': delivery_files_data,
            'comments': comments,
            'can_request_revision': order.status == 'completed pending review',
            'can_accept': order.status == 'completed pending review',
            'is_completed': order.status == 'completed',
            'needs_revision': order.status == 'revision',
            'page_title': f'Order {order.order_number} - Review',
            'breadcrumbs': [
                {'text': 'Order Results', 'url': url_for('client.order_results')},
                {'text': f'Order {order.order_number}', 'url': None}
            ]
        }
        
        return render_template('client/order_detail.html', **context)
    
    except Exception as e:
        logger.error(f"Error rendering order detail page: {str(e)}")
        flash('An error occurred while loading the order details. Please try again.', 'error')
        return redirect(url_for('client.order_results'))



from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_file, flash, abort, current_app
from app.extensions import db, socketio
from app.models.order import Order, OrderFile, OrderComment
from app.models.order_delivery import OrderDelivery, OrderDeliveryFile
from app.models.communication import Chat
from app.models.tools import ChatMessage
from app.models.price import PriceRate
from app.models.service import Service
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import zipfile
import io


details_bp = Blueprint('order_details', __name__, url_prefix='/client')
# Comment = OrderComment()
# Delivery = OrderDelivery()
# File = OrderFile()
# DeliveryFile = OrderDeliveryFile()

@details_bp.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    """Display order details page"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    # Get comments ordered by creation date
    comments = OrderComment.query.filter_by(order_id=order_id).order_by(OrderComment.created_at.asc()).all()
    service = Service.query.filter_by(id=order.service_id).first_or_404()
    
    # Get deliveries ordered by delivery date
    deliveries = OrderDelivery.query.filter_by(order_id=order_id).order_by(OrderDelivery.delivered_at.desc()).all()
    price_rate = PriceRate.query.filter_by(
        pricing_category_id=service.pricing_category_id,
        academic_level_id=order.academic_level_id,
        deadline_id=order.deadline_id
    ).first()
    
    # Attach comments and deliveries to order for template
    order.comments = comments
    order.deliveries = deliveries
    
    return render_template(
        'orders/order_details.html', 
        order=order, 
        now=datetime.now(),
        price_per_page=price_rate.price_per_page if price_rate else 0,)

@details_bp.route('/send-message', methods=['POST'])
@login_required
def send_message():
    """Send a message/comment on an order"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        content = data.get('content')
        
        if not order_id or not content:
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Verify the order belongs to the current user
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        # Create new comment
        comment = OrderComment(
            order_id=order_id,
            user_id=current_user.id,
            content=content,
            is_from_admin=False,
            created_at=datetime.now()
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Message sent successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@details_bp.route('/approve-delivery', methods=['POST'])
@login_required
def approve_delivery():
    """Approve a delivery"""
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        
        if not delivery_id:
            return jsonify({'success': False, 'message': 'Missing delivery ID'})
        
        # Get delivery and verify ownership
        delivery = OrderDelivery.query.join(Order).filter(
            OrderDelivery.id == delivery_id,
            Order.client_id == current_user.id
        ).first()
        
        if not delivery:
            return jsonify({'success': False, 'message': 'Delivery not found'})
        
        # Update delivery status
        delivery.approved = True
        delivery.approved_at = datetime.now()
        
        # Update order status if not already completed
        if delivery.order.status != 'completed':
            delivery.order.status = 'completed'
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Delivery approved successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@details_bp.route('/request-revision', methods=['POST'])
@login_required
def request_revision():
    """Request revision for a delivery"""
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        reason = data.get('reason')
        
        if not delivery_id or not reason:
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Get delivery and verify ownership
        delivery = OrderDelivery.query.join(Order).filter(
            OrderDelivery.id == delivery_id,
            Order.client_id == current_user.id
        ).first()
        
        if not delivery:
            return jsonify({'success': False, 'message': 'Delivery not found'})
        
        # Create revision request comment
        comment = OrderComment(
            order_id=delivery.order_id,
            user_id=current_user.id,
            content=f"Revision Request: {reason}",
            is_from_admin=False,
            created_at=datetime.now()
        )
        
        # Update order status to indicate revision needed
        delivery.order.status = 'revision_requested'
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Revision request submitted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@details_bp.route('/download_file/<int:file_id>')
@login_required
def download_file(file_id):
    """Download an order attachment file"""
    file = OrderFile.query.join(Order).filter(
        OrderFile.id == file_id,
        Order.client_id == current_user.id
    ).first_or_404()
    
    # file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
    file_path = os.path.abspath(file.file_path)
    print("DOWNLOADING FILE...")
    if not os.path.exists(file_path):
        abort(404)
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=file.filename
    )

@details_bp.route('/download_delivery_file/<int:file_id>')
@login_required
def download_delivery_file(file_id):
    """Download a delivery file"""
    delivery_file = OrderDeliveryFile.query.join(OrderDelivery).join(Order).filter(
        OrderDeliveryFile.id == file_id,
        Order.client_id == current_user.id
    ).first_or_404()
    
    # file_path = os.path.join(current_app.config['DELIVERY_UPLOAD_FOLDER'], delivery_file.filename)
    file_path = os.path.abspath(delivery_file.file_path)

    
    if not os.path.exists(file_path):
        abort(404)
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=delivery_file.original_filename
    )

@details_bp.route('/download-order-files/<int:order_id>')
@login_required
def download_order_files(order_id):
    """Download all files for an order as a ZIP"""
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    
    # Create a ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add order attachment files
        for file in order.files:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            if os.path.exists(file_path):
                zip_file.write(file_path, f"attachments/{file.original_filename}")
        
        # Add delivery files
        for delivery in order.deliveries:
            for delivery_file in delivery.delivery_files:
                file_path = os.path.join(current_app.config['DELIVERY_UPLOAD_FOLDER'], delivery_file.filename)
                if os.path.exists(file_path):
                    zip_file.write(file_path, f"deliveries/{delivery_file.original_filename}")
    
    zip_buffer.seek(0)
    
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f"order_{order.order_number}_files.zip",
        mimetype='application/zip'
    )

@details_bp.route('/payment/<int:order_id>')
@login_required
def payment(order_id):
    """Redirect to payment page"""
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    
    if order.paid:
        flash('This order has already been paid for.', 'info')
        return redirect(url_for('client.order_details', order_id=order_id))
    
    # Redirect to your payment processor or payment page
    return redirect(url_for('client.payment_process', order_id=order_id))

@details_bp.route('/support')
@login_required
def support():
    """Support/contact page"""
    return render_template('client/support.html')

# Additional helper functions for the template
@details_bp.app_template_filter('file_icon')
def file_icon_filter(file_format):
    """Return appropriate Font Awesome icon class for file format"""
    icons = {
        'pdf': 'fas fa-file-pdf',
        'doc': 'fas fa-file-word',
        'docx': 'fas fa-file-word',
        'xls': 'fas fa-file-excel',
        'xlsx': 'fas fa-file-excel',
        'ppt': 'fas fa-file-powerpoint',
        'pptx': 'fas fa-file-powerpoint',
        'zip': 'fas fa-file-archive',
        'rar': 'fas fa-file-archive',
        'txt': 'fas fa-file-alt',
        'jpg': 'fas fa-file-image',
        'jpeg': 'fas fa-file-image',
        'png': 'fas fa-file-image',
        'gif': 'fas fa-file-image',
    }
    return icons.get(file_format.lower(), 'fas fa-file')
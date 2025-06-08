# routes/api.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.order import Order, OrderFile, OrderComment
from app.models.order_delivery import OrderDelivery, OrderDeliveryFile
from app.models.communication import Chat
from app.models.tools import ChatMessage
from app.extensions import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename

activity_bp = Blueprint('activity', __name__, url_prefix='/api')

@activity_bp.route('/order/<int:order_id>/timeline')
@login_required
def get_order_timeline(order_id):
    """Get chronological timeline of order activities"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    activities = []
    
    # Order creation
    activities.append({
        'type': 'primary',
        'title': 'Order Created',
        'description': f'Order #{order.order_number} was created',
        'timestamp': order.created_at.isoformat()
    })
    
    # Payment status
    if order.paid:
        activities.append({
            'type': 'success',
            'title': 'Payment Received',
            'description': 'Payment has been processed successfully',
            'timestamp': order.payments[0].created_at.isoformat() if order.payments else order.created_at.isoformat()
        })
    else:
        activities.append({
            'type': 'warning',
            'title': 'Payment Pending',
            'description': 'Waiting for payment to be processed',
            'timestamp': order.created_at.isoformat()
        })
    
    # Writer assignment
    if order.writer_is_assigned:
        activities.append({
            'type': 'info',
            'title': 'Writer Assigned',
            'description': 'A qualified writer has been assigned to your order',
            'timestamp': order.writer_assigned_at.isoformat() if order.writer_assigned_at else order.created_at.isoformat()
        })
    
    # File uploads
    for file in order.files:
        activities.append({
            'type': 'info',
            'title': 'File Uploaded',
            'description': f'File "{file.filename}" was uploaded',
            'timestamp': file.uploaded_at.isoformat()
        })
    
    # Deliveries
    for delivery in order.deliveries:
        activities.append({
            'type': 'success',
            'title': 'Order Delivered',
            'description': f'Order has been {delivery.delivery_status} with {delivery.delivery_files_count} file(s)',
            'timestamp': delivery.delivered_at.isoformat()
        })
    
    # Comments/Messages
    for comment in order.comments:
        activities.append({
            'type': 'info',
            'title': 'Message' if not comment.is_admin else 'Admin Response',
            'description': comment.message[:100] + ('...' if len(comment.message) > 100 else ''),
            'timestamp': comment.created_at.isoformat()
        })
    
    # Sort by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({'activities': activities})

@activity_bp.route('/order/<int:order_id>/chat')
@login_required
def get_chat_messages(order_id):
    """Get chat messages for the order"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    # Get or create chat for this order
    chat = Chat.query.filter_by(order_id=order_id, user_id=current_user.id).first()
    if not chat:
        chat = Chat(
            user_id=current_user.id,
            order_id=order_id,
            subject=f'Order #{order.order_number} Discussion'
        )
        db.session.add(chat)
        db.session.commit()
    
    messages = ChatMessage.query.filter_by(chat_id=chat.id).order_by(ChatMessage.created_at).all()
    
    message_data = []
    for message in messages:
        message_data.append({
            'content': message.content,
            'is_admin': message.user.is_admin,
            'created_at': message.created_at.isoformat(),
            'user_name': message.user.get_name()
        })
    
    return jsonify({'messages': message_data})

@activity_bp.route('/order/<int:order_id>/chat', methods=['POST'])
@login_required
def send_chat_message(order_id):
    """Send a chat message"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    data = request.get_json()
    
    if not data or not data.get('message'):
        return jsonify({'success': False, 'error': 'Message is required'}), 400
    
    # Get or create chat for this order
    chat = Chat.query.filter_by(order_id=order_id, user_id=current_user.id).first()
    if not chat:
        chat = Chat(
            user_id=current_user.id,
            order_id=order_id,
            subject=f'Order #{order.order_number} Discussion'
        )
        db.session.add(chat)
        db.session.flush()
    
    # Create message
    message = ChatMessage(
        user_id=current_user.id,
        chat_id=chat.id,
        content=data['message']
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify({'success': True})

@activity_bp.route('/order/<int:order_id>/upload', methods=['POST'])
@login_required
def upload_order_files(order_id):
    """Upload additional files to order"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            # Ensure upload directory exists
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'orders', str(order_id))
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Save to database
            order_file = OrderFile(
                order_id=order_id,
                filename=filename,
                file_path=file_path
            )
            db.session.add(order_file)
            uploaded_files.append(filename)
    
    db.session.commit()
    return jsonify({'success': True, 'uploaded_files': uploaded_files})
@activity_bp.route('/order/<int:order_id>/comments')
@login_required
def get_order_comments(order_id):
    """Get comments for an order"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    comments = []
    for comment in order.comments.filter_by(user_id=current_user.id).order_by(OrderComment.created_at.desc()):
        comments.append({
            'message': comment.message,
            'created_at': comment.created_at.isoformat()
        })
    
    return jsonify({'comments': comments})

@activity_bp.route('/order/<int:order_id>/files')
@login_required
def get_order_files(order_id):
    """Get uploaded files for order"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    files_data = []
    for file in order.files:
        files_data.append({
            'id': file.id,
            'filename': file.filename,
            'size': file.file_size,
            'uploaded_at': file.uploaded_at.isoformat()
        })
    
    return jsonify({'files': files_data})

@activity_bp.route('/order/file/<int:file_id>', methods=['DELETE'])
@login_required
def delete_order_file(file_id):
    """Delete an uploaded file"""
    file = OrderFile.query.join(Order).filter(
        OrderFile.id == file_id,
        Order.client_id == current_user.id
    ).first_or_404()
    
    # Delete file from filesystem
    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        current_app.logger.error(f"Error deleting file: {e}")
    
    # Delete from database
    db.session.delete(file)
    db.session.commit()
    
    return jsonify({'success': True})

@activity_bp.route('/order/<int:order_id>/deadline', methods=['PUT'])
@login_required
def update_order_deadline(order_id):
    """Update order deadline"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    data = request.get_json()
    
    if not data or not data.get('deadline'):
        return jsonify({'success': False, 'error': 'Deadline is required'}), 400
    
    try:
        new_deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
        order.due_date = new_deadline
        order.updated_at = datetime.now()
        
        # Add comment about deadline change
        comment = OrderComment(
            order_id=order_id,
            user_id=current_user.id,
            message=f'Deadline updated to {new_deadline.strftime("%B %d, %Y at %I:%M %p")}',
            is_admin=False
        )
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({'success': True})
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid deadline format'}), 400

@activity_bp.route('/order/<int:order_id>/complete', methods=['POST'])
@login_required
def mark_order_completed(order_id):
    """Mark order as completed"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    if not order.is_delivered:
        return jsonify({'success': False, 'error': 'Order must be delivered before marking as completed'}), 400
    
    order.status = 'completed'
    order.updated_at = datetime.now()
    
    # Add comment
    comment = OrderComment(
        order_id=order_id,
        user_id=current_user.id,
        message='Order marked as completed by client',
        is_admin=False
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({'success': True})

@activity_bp.route('/order/<int:order_id>/revision', methods=['POST'])
@login_required
def request_revision(order_id):
    """Request order revision"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    data = request.get_json()
    
    if not data or not data.get('reason'):
        return jsonify({'success': False, 'error': 'Revision reason is required'}), 400
    
    order.status = 'revision'
    order.updated_at = datetime.now()
    
    # Add comment with revision request
    comment = OrderComment(
        order_id=order_id,
        user_id=current_user.id,
        message=f'Revision requested: {data["reason"]}',
        is_admin=False
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({'success': True})

@activity_bp.route('/order/<int:order_id>/refund', methods=['POST'])
@login_required
def request_refund(order_id):
    """Request order refund"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    data = request.get_json()
    
    if not data or not data.get('reason'):
        return jsonify({'success': False, 'error': 'Refund reason is required'}), 400
    
    if not order.paid:
        return jsonify({'success': False, 'error': 'Cannot refund unpaid order'}), 400
    
    # Add comment with refund request
    comment = OrderComment(
        order_id=order_id,
        user_id=current_user.id,
        message=f'Refund requested: {data["reason"]}',
        is_admin=False
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({'success': True})

def allowed_file(filename):
    """Check if file type is allowed"""
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
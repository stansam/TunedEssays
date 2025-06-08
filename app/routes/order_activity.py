# routes/order_activities.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.order import Order, OrderComment, OrderFile, SupportTicket
from app.models.order_delivery import OrderDelivery, OrderDeliveryFile
from app.models.communication import Chat
from app.models.user import User
from app.models.tools import ChatMessage
from app.extensions import db, socketio
from datetime import datetime
import os
from werkzeug.utils import secure_filename

order_activities_bp = Blueprint('order_activities', __name__)

@order_activities_bp.route('/order/<int:order_id>/activities')
@login_required
def order_activities(order_id):
    """Main order activities page"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    return render_template('orders/order_activities.html', order=order)

# @order_activities_bp.route('/order/<int:order_id>/timeline')
# @login_required
# def get_order_timeline(order_id):
#     """Get timeline activities for an order"""
#     order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
#     activities = []
    
#     # Order creation
#     activities.append({
#         'type': 'created',
#         'title': 'Order Created',
#         'description': f'Order #{order.order_number} was created',
#         'created_at': order.created_at.isoformat(),
#         'files': []
#     })
    
#     # Writer assignment
#     if order.writer_is_assigned and order.writer_assigned_at:
#         activities.append({
#             'type': 'writer_assigned',
#             'title': 'Writer Assigned',
#             'description': 'A writer has been assigned to your order',
#             'created_at': order.writer_assigned_at.isoformat(),
#             'files': []
#         })
    
#     # Chat messages
#     chat = Chat.query.filter_by(order_id=order_id).first()
#     if chat:
#         for message in chat.messages:
#             activities.append({
#                 'type': 'message',
#                 'title': f'Message from {"Admin" if message.user.is_admin else "You"}',
#                 'description': message.content[:100] + ('...' if len(message.content) > 100 else ''),
#                 'created_at': message.created_at.isoformat(),
#                 'files': []
#             })
    
#     # File uploads
#     for file in order.files:
#         activities.append({
#             'type': 'file',
#             'title': 'File Uploaded',
#             'description': f'File "{file.filename}" was uploaded',
#             'created_at': file.uploaded_at.isoformat(),
#             'files': [{
#                 'name': file.filename,
#                 'size': f'{file.file_size / 1024 / 1024:.2f}MB',
#                 'download_url': f'/download/order-file/{file.id}'
#             }]
#         })
    
#     # Deliveries
#     for delivery in order.deliveries:
#         files_info = []
#         for file in delivery.delivery_files:
#             files_info.append({
#                 'name': file.original_filename,
#                 'size': f'{file.file_size_mb}MB',
#                 'download_url': f'/download/delivery-file/{file.id}'
#             })
        
#         activities.append({
#             'type': 'delivery',
#             'title': 'Work Delivered',
#             'description': f'Order work has been delivered with {len(files_info)} file(s)',
#             'created_at': delivery.delivered_at.isoformat(),
#             'files': files_info
#         })
    
#     # Sort activities by date
#     activities.sort(key=lambda x: x['created_at'])
    
#     return jsonify({'activities': activities})
@order_activities_bp.route('/order/<int:order_id>/timeline')
@login_required
def get_order_timeline(order_id):
    """Get timeline activities for an order grouped by date"""
    try:
        order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
        
        # Collect all activities
        activities = []
        # files_info = []
        # for file in order.files:
        #     files_info.append({
        #         'name': file.filename,
        #         'size': f'{file.file_size / 1024 / 1024:.2f}MB',
        #         'download_url': f'/download/delivery-file/{file.id}'
            # })
        # Order creation
        activities.append({
            'type': 'created',
            'title': 'Order Created',
            'description': f'Order #{order.order_number} was created',
            'created_at': order.created_at,
            'icon': 'fas fa-plus-circle',
            'files': []
         })
        
        # Comments
        comments = OrderComment.query.filter_by(order_id=order_id).all()
        for comment in comments:
            activities.append({
                'type': 'comment',
                'title': 'Comment Added' if not comment.is_admin else 'Admin Response',
                'description': comment.message[:100] + ('...' if len(comment.message) > 100 else ''),
                'created_at': comment.created_at,
                'icon': 'fas fa-comment',
                'user_name': comment.user.get_name() if comment.user else 'Unknown',
                'files': []
            })
        
        # Chat messages
        chat = Chat.query.filter_by(order_id=order_id).first()
        if chat:
            messages = ChatMessage.query.filter_by(chat_id=chat.id).all()
            for message in messages:
                activities.append({
                    'type': 'message',
                    'title': 'Message Sent' if not message.user.is_admin else 'Admin Message',
                    'description': message.content[:100] + ('...' if len(message.content) > 100 else ''),
                    'created_at': message.created_at,
                    'icon': 'fas fa-envelope',
                    'user_name': message.user.get_name() if message.user else 'Unknown',
                    'files' : []
                })
        
        # File uploads
        for file in order.files:
            activities.append({
                'type': 'file',
                'title': 'File Uploaded',
                'description': f'File: {file.filename}',
                'created_at': file.uploaded_at,
                'icon': 'fas fa-file-upload',
                'files': [{
                    'name': file.filename,
                    'size': f'{file.file_size / 1024 / 1024:.2f}MB',
                    'download_url': f'/orders/files/{file.id}/download'
                }]
            })
        
        # Deliveries
        for delivery in order.deliveries:
            files_info = []
            for file in delivery.delivery_files:
                files_info.append({
                    'name': file.original_filename,
                    'size': f'{file.file_size_mb}MB',
                    'download_url': f'/order-results/orders/{file.id}/download'
                })
            activities.append({
                'type': 'delivery',
                'title': 'Work Delivered',
                'description': f'{len(delivery.delivery_files)} file(s) delivered',
                'created_at': delivery.delivered_at,
                'icon': 'fas fa-check-circle',
                'files': files_info
            })
        
        # Payment activities
        for payment in order.payments:
            activities.append({
                'type': 'payment',
                'title': 'Payment Processed',
                'description': f'Payment of ${payment.amount:.2f} processed',
                'created_at': payment.created_at,
                'icon': 'fas fa-credit-card',
                'files': []
            })
        
        # Group by date
        from collections import defaultdict
        
        grouped_activities = defaultdict(list)
        for activity in activities:
            date_key = activity['created_at'].date()
            grouped_activities[date_key].append(activity)
        
        # Sort activities within each day
        for date_key in grouped_activities:
            grouped_activities[date_key].sort(key=lambda x: x['created_at'])
        
        # Convert to list and sort by date (newest first)
        timeline_data = []
        for date_key in sorted(grouped_activities.keys(), reverse=True):
            timeline_data.append({
                'date': date_key.strftime('%B %d, %Y'),
                'activities': [
                    {
                        'type': activity['type'],
                        'title': activity['title'],
                        'description': activity['description'],
                        'time': activity['created_at'].strftime('%I:%M %p'),
                        'icon': activity['icon'],
                        'user_name': activity.get('user_name', ''),
                        'files': activity['files']
                    }
                    for activity in grouped_activities[date_key]
                ]
            })
        
        return jsonify({'timeline': timeline_data})
        
    except Exception as e:
        print(f"Error in timeline route: {str(e)}")  # Debug log
        return jsonify({'error': 'Failed to load timeline', 'timeline': []}), 500

@order_activities_bp.route('/order/<int:order_id>/chat')
@login_required
def get_chat_messages(order_id):
    """Get chat messages for an order"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    chat = Chat.query.filter_by(order_id=order_id).first()
    if not chat:
        return jsonify({'messages': []})
    
    messages = []
    for message in chat.messages.order_by(ChatMessage.created_at.asc()):
        messages.append({
            'content': message.content,
            'is_admin': message.user.is_admin,
            'created_at': message.created_at.isoformat()
        })
    socketio.emit('messages_marked_read', {
        'chat_id': chat.id,
        'user_id': current_user.id
    }, room=f"chat_{chat.id}")
    socketio.emit('update_unread_count', {
        'user_id': current_user.id
    }, room=None)
    
    return jsonify({'messages': messages})

@order_activities_bp.route('/order/chat', methods=['POST'])
@login_required
def send_chat_message():
    """Send a chat message"""
    data = request.get_json()
    order_id = data.get('order_id')
    content = data.get('content')
    
    if not order_id or not content:
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    # Get or create chat
    chat = Chat.query.filter_by(order_id=order_id).first()
    if not chat:
        chat = Chat(
            user_id=current_user.id,
            order_id=order_id,
            subject=f'Discussion for Order #{order.order_number}'
        )
        db.session.add(chat)
        db.session.flush()
    
    # Create message
    message = ChatMessage(
        user_id=current_user.id,
        chat_id=chat.id,
        content=content
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({'success': True})

@order_activities_bp.route('/order/<int:order_id>/comments')
@login_required
def get_order_comments(order_id):
    """Get comments for an order"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    # comment_owner = 
    
    comments = []
    for comment in OrderComment.query.filter_by(user_id=current_user.id).order_by(OrderComment.created_at.desc()):
        comments.append({
            'message': comment.message,
            'username': current_user.username,
            'created_at': comment.created_at.isoformat()
        })
    
    return jsonify({'comments': comments})

@order_activities_bp.route('/order/comment', methods=['POST'])
@login_required
def add_order_comment():
    """Add a comment to an order"""
    data = request.get_json()
    order_id = data.get('order_id')
    message = data.get('message')
    
    if not order_id or not message:
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    comment = OrderComment(
        order_id=order_id,
        user_id=current_user.id,
        message=message,
        is_admin=False
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({'success': True})

@order_activities_bp.route('/order/upload', methods=['POST'])
@login_required
def upload_additional_files():
    """Upload additional files for an order"""
    order_id = request.form.get('order_id')
    files = request.files.getlist('files')
    
    if not order_id or not files:
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    uploaded_files = []
    
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'])
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_dir, f"{order_id}_{filename}")
            file.save(file_path)
            
            # Create database record
            order_file = OrderFile(
                order_id=order_id,
                filename=filename,
                file_path=file_path
            )
            
            db.session.add(order_file)
            uploaded_files.append(filename)
    
    db.session.commit()
    
    return jsonify({'success': True, 'uploaded_files': uploaded_files})

@order_activities_bp.route('/order/<int:order_id>/deadline', methods=['PUT'])
@login_required
def update_order_deadline(order_id):
    """Update order deadline"""
    data = request.get_json()
    new_deadline = data.get('deadline')
    
    if not new_deadline:
        return jsonify({'success': False, 'error': 'Missing deadline'})
    
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    try:
        order.due_date = datetime.fromisoformat(new_deadline.replace('Z', '+00:00'))
        order.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True})
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid deadline format'})

@order_activities_bp.route('/order/<int:order_id>/complete', methods=['POST'])
@login_required
def mark_order_complete(order_id):
    """Mark order as completed"""
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    if not order.is_delivered:
        return jsonify({'success': False, 'error': 'Order has not been delivered yet'})
    
    order.status = 'completed'
    order.updated_at = datetime.now()
    db.session.commit()
    
    return jsonify({'success': True})

@order_activities_bp.route('/order/<int:order_id>/revision', methods=['POST'])
@login_required
def request_revision(order_id):
    """Request revision for an order"""
    data = request.get_json()
    reason = data.get('revision_details')
    
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    # Create a comment with the revision request
    comment = OrderComment(
        order_id=order_id,
        user_id=current_user.id,
        message=f"REVISION REQUEST: {reason}",
        is_admin=False
    )
    subject="Revision Request"
    support = SupportTicket(
        order_id=order_id,
        user_id=current_user.id,
        subject=subject,
        message=reason,
        status="open"
    )
    # Update order status
    order.status = 'revision'
    order.updated_at = datetime.now()
    
    db.session.add(comment)
    db.session.commit()

    db.session.add(support)
    db.session.commit()
    
    return jsonify({'success': True})

@order_activities_bp.route('/order/<int:order_id>/refund', methods=['POST'])
@login_required
def request_refund(order_id):
    """Request refund for an order"""
    data = request.get_json()
    reason = data.get('reason')
    
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    if not order.paid:
        return jsonify({'success': False, 'error': 'Order has not been paid yet'})
    
    # Create a comment with the refund request
    comment = OrderComment(
        order_id=order_id,
        user_id=current_user.id,
        message=f"REFUND REQUEST: {reason}",
        is_admin=False
    )
    support = SupportTicket(
        order_id=order_id,
        user_id=current_user.id,
        subject="Refund Request",
        message=reason,
        status="open"
    )
    db.session.add(comment)
    db.session.commit()
    db.session.add(support)
    db.session.commit()
    
    
    return jsonify({'success': True})
@order_activities_bp.route('/order/<int:order_id>/create_chat', methods=['POST'])
@login_required
def create_new_chat(order_id):
    """Create a new chat for an order with initial message"""
    try:
        # Verify order belongs to current user
        order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
        
        # Get request data
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Message content is required', 'success': False}), 400
        
        # Check if chat already exists
        existing_chat = Chat.query.filter_by(order_id=order_id).first()
        if existing_chat:
            return jsonify({
                'error': 'Chat already exists for this order', 
                'success': False,
                'chat_id': existing_chat.id
            }), 400
        
        # Find an admin user (you might want to assign specific admins)
        admin_user = User.query.filter_by(is_admin=True).first()
        if not admin_user:
            return jsonify({
                'error': 'No admin available to handle chat', 
                'success': False
            }), 500
        
        # Create new chat
        new_chat = Chat(
            user_id=current_user.id,
            admin_id=admin_user.id,
            order_id=order_id,
            subject=f"Chat for Order #{order.order_number}",
            status='active'
        )
        
        db.session.add(new_chat)
        db.session.flush()  # Get the chat ID before committing
        
        # Create initial message
        initial_message = ChatMessage(
            user_id=current_user.id,
            chat_id=new_chat.id,
            content=content,
            is_read=False
        )
        
        db.session.add(initial_message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Chat created successfully',
            'chat_id': new_chat.id,
            'initial_message': {
                'content': initial_message.content,
                'is_admin': current_user.is_admin,
                'created_at': initial_message.created_at.isoformat(),
                'user_name': current_user.get_name()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating chat: {str(e)}")  # Debug log
        return jsonify({
            'error': 'Failed to create chat', 
            'success': False,
            'details': str(e)
        }), 500

@order_activities_bp.route('/order/<int:order_id>/chat_status')
@login_required
def get_chat_status(order_id):
    """Check if a chat exists for an order"""
    try:
        # Verify order belongs to current user
        order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
        
        # Check if chat exists
        chat = Chat.query.filter_by(order_id=order_id).first()
        
        return jsonify({
            'success': True,
            'chat_exists': chat is not None,
            'chat_id': chat.id if chat else None,
            'chat_status': chat.status if chat else None
        })
        
    except Exception as e:
        print(f"Error checking chat status: {str(e)}")
        return jsonify({
            'error': 'Failed to check chat status',
            'success': False,
            'chat_exists': False
        }), 500

@order_activities_bp.route('/order/<int:order_id>/send_message_or_create', methods=['POST'])
@login_required
def send_message_or_create_chat(order_id):
    """Send a message to existing chat or create new chat if none exists"""
    try:
        # Verify order belongs to current user
        order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
        
        # Get request data
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Message content is required', 'success': False}), 400
        
        # Check if chat exists
        chat = Chat.query.filter_by(order_id=order_id).first()
        
        if not chat:
            # Create new chat if none exists
            admin_user = User.query.filter_by(is_admin=True).first()
            if not admin_user:
                return jsonify({
                    'error': 'No admin available to handle chat', 
                    'success': False
                }), 500
            
            chat = Chat(
                user_id=current_user.id,
                admin_id=admin_user.id,
                order_id=order_id,
                subject=f"Chat for Order #{order.order_number}",
                status='active'
            )
            
            db.session.add(chat)
            db.session.flush()
        
        # Create message
        message = ChatMessage(
            user_id=current_user.id,
            chat_id=chat.id,
            content=content,
            is_read=False
        )
        
        db.session.add(message)
        db.session.commit()

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
        socketio.emit('new_message', message_data, room=f'chat_{chat.id}')
        
        # Emit to the other user's personal room (for notifications)
        other_user_id = chat.user_id if current_user.id != chat.user_id else chat.admin_id
        socketio.emit('new_message', message_data, room=f'user_{other_user_id}')
        socketio.emit('update_unread_count', {'user_id': other_user_id}, room=f'user_{other_user_id}')
        return jsonify({
            'success': True,
            'message': {
                'content': message.content,
                'is_admin': current_user.is_admin,
                'created_at': message.created_at.isoformat(),
                'user_name': current_user.get_name()
            },
            'chat_created': chat.id if not Chat.query.filter_by(order_id=order_id).first() else False
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error sending message or creating chat: {str(e)}")
        return jsonify({
            'error': 'Failed to send message',
            'success': False,
            'details': str(e)
        }), 500
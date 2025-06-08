from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from flask import request
from app.extensions import db, socketio
from app.models.communication import Chat, Notification
from app.models.tools import ChatMessage
from app.models.user import User
import datetime

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if current_user.is_authenticated:
        # Join a personal room for this user
        join_room(f"user_{current_user.id}")
        
        # Join rooms for all chats this user is part of
        if current_user.is_admin:
            chats = Chat.query.filter_by(admin_id=current_user.id).all()
        else:
            chats = Chat.query.filter_by(user_id=current_user.id).all()
        
        for chat in chats:
            join_room(f"chat_{chat.id}")
    else:
        print("Anonymous user connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if current_user.is_authenticated:
        leave_room(f'user_{current_user.id}')
        print(f"User {current_user.id} disconnected")
    else:
        print("Anonymous user disconnected")

def handle_join(data):
    """Handle joining a room."""
    room = data.get('room')
    if room:
        join_room(room)
        print(f"User {current_user.id if current_user.is_authenticated else 'Anonymous'} joined room {room}")

@socketio.on('join_chat')
def handle_join_chat(data):
    """Join a specific chat room"""
    chat_id = data.get('chat_id')
    if not chat_id:
        return
    
    chat = Chat.query.get(chat_id)
    if not chat:
        return
    
    # Security check - user must be part of the chat
    if not (current_user.id == chat.user_id or current_user.id == chat.admin_id):
        return
    
    join_room(f"chat_{chat_id}")
    emit('status', {'msg': f"{current_user.get_name()} has joined the chat"}, room=f"chat_{chat_id}")

@socketio.on('leave_chat')
def handle_leave_chat(data):
    """Leave a specific chat room"""
    chat_id = data.get('chat_id')
    if chat_id:
        leave_room(f"chat_{chat_id}")

@socketio.on('send_message')
def handle_send_message(data):
    """Handle new message sent"""
    if not current_user.is_authenticated:
        return {'error': 'Unauthorized'}, 401
    
    chat_id = data.get('chat_id')
    content = data.get('content')
    
    if not chat_id or not content or not content.strip():
        return {'error': 'Invalid message data'}, 400
    
    # Get the chat
    chat = Chat.query.get(chat_id)
    if not chat:
        return {'error': 'Chat not found'}, 404
    
    # Security check - user must be part of the chat
    if not (current_user.id == chat.user_id or current_user.id == chat.admin_id):
        return {'error': 'Unauthorized'}, 403
    
    # Create new message
    new_message = ChatMessage(
        user_id=current_user.id,
        chat_id=chat_id,
        content=content,
        is_read=False,
        created_at=datetime.datetime.now()
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    # Determine recipient
    recipient_id = chat.user_id if current_user.id == chat.admin_id else chat.admin_id
    
    # Create a message notification for the recipient
    notification = Notification(
        user_id=recipient_id,
        title="New message",
        message=f"You have a new message from {current_user.get_name()}",
        type="info",
        link=f"/client/{chat_id}",
        is_read=False
    )
    
    db.session.add(notification)
    db.session.commit()
    
    # Broadcast message to the chat room
    message_data = {
        'id': new_message.id,
        'chat_id': chat_id,
        'content': content,
        'user_id': current_user.id,
        'user_name': current_user.get_name(),
        'is_admin': current_user.is_admin,
        'created_at': new_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'is_read': False
    }
    
    # Emit to the specific chat room
    emit('new_message', message_data, room=f"chat_{chat_id}")
    
    # Emit to the recipient's personal room to update unread count
    emit('update_unread_count', {
        'user_id': recipient_id,
        'chat_id': chat_id
    }, room=f"user_{recipient_id}")
    
    return {'success': True, 'message': message_data}

@socketio.on('mark_messages_read')
def handle_mark_messages_read(data):
    """Mark messages as read"""
    if not current_user.is_authenticated:
        return {'error': 'Unauthorized'}, 401
    
    chat_id = data.get('chat_id')
    
    if not chat_id:
        return {'error': 'Chat ID required'}, 400
    
    # Get the chat
    chat = Chat.query.get(chat_id)
    if not chat:
        return {'error': 'Chat not found'}, 404
    
    # Security check - user must be part of the chat
    if not (current_user.id == chat.user_id or current_user.id == chat.admin_id):
        return {'error': 'Unauthorized'}, 403
    
    # Mark all unread messages from others as read
    unread_messages = ChatMessage.query.filter_by(
        chat_id=chat_id,
        is_read=False
    ).filter(ChatMessage.user_id != current_user.id).all()
    
    for message in unread_messages:
        message.is_read = True
    
    db.session.commit()
    
    # Emit event to update UI
    emit('messages_marked_read', {
        'chat_id': chat_id,
        'user_id': current_user.id
    }, room=f"chat_{chat_id}")
    
    # Update unread count for current user
    emit('update_unread_count', {
        'user_id': current_user.id
    }, room=f"user_{current_user.id}")
    
    return {'success': True}
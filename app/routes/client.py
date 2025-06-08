from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask import jsonify
from flask_login import login_required, current_user
from app.models.user import User
from app.models.order import Order, OrderComment, OrderFile, SupportTicket
from app.models.communication import ContactMessage, Notification, Chat
from app.models.content import Testimonial, Sample
from app.models.blog import BlogPost, BlogCategory, BlogComment
from app.models.service import Service, AcademicLevel, Deadline
from app.models.payment import Payment, Refund, Discount
from app.models.tools import PlagiarismCheck, ChatMessage
from app.models.referral import Referral
from app.routes.main import notify
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app.extensions import db, socketio
import logging 


client_bp = Blueprint('client', __name__)


# @client_bp.route('/')
# @login_required
# def dashboard():
#     # Get current user's data
#     user = current_user
    
#     # Get recent orders (last 5)
#     recent_orders = Order.query.filter_by(client_id=user.id)\
#                                .order_by(Order.created_at.desc())\
#                                .limit(5)\
#                                .all()
    
#     # Get active orders (status='in_progress')
#     active_orders = Order.query.filter_by(client_id=user.id, status='active')\
#                               .order_by(Order.due_date.asc())\
#                               .all()
#     pending_orders = Order.query.filter_by(client_id=user.id, status='pending')\
#                               .order_by(Order.due_date.asc())\
#                               .all()
    
#     # Get completed orders
#     completed_orders = Order.query.filter_by(client_id=user.id, status='completed')\
#                                  .order_by(Order.created_at.desc())\
#                                  .limit(5)\
#                                  .all()
    
#     # Get referrals
#     referrals = Referral.query.filter_by(referrer_id=user.id)\
#                              .order_by(Referral.created_at.desc())\
#                              .all()
    
#     # Get unread notifications
#     unread_notifications = Notification.query.filter_by(user_id=user.id, is_read=False)\
#                                             .order_by(Notification.created_at.desc())\
#                                             .limit(5)\
#                                             .all()
    
#     # Calculate stats
#     total_orders = Order.query.filter_by(client_id=user.id).count()
#     total_spent = db.session.query(func.sum(Order.total_price))\
#                           .filter_by(client_id=user.id, paid=True)\
#                           .scalar() or 0.0
    
#     # Get recent messages (last 3)
#     recent_messages = ChatMessage.query.filter_by(email=user.email)\
#                                          .order_by(ChatMessage.created_at.desc())\
#                                          .limit(3)\
#                                          .all()

#     return render_template(
#         'client/dashboard.html',
#         user=user,
#         recent_orders=recent_orders,
#         active_orders=active_orders,
#         completed_orders=completed_orders,
#         referrals=referrals,
#         referral_count=len(referrals),
#         unread_notifications=unread_notifications,
#         total_orders=total_orders,
#         pending_orders=pending_orders,
#         total_spent=total_spent,
#         recent_messages=recent_messages,
#         current_time=datetime.now()
#     )
@client_bp.route('/')
@login_required
def dashboard():
    """
    Enhanced dashboard with comprehensive data aggregation and error handling
    """
    try:
        # user = current_user
        current_time = datetime.now()
        
        # Initialize default values for error handling
        dashboard_data = {
            # 'user': current_user,
            'current_time': current_time,
            'recent_orders': [],
            'active_orders': [],
            'pending_orders': [],
            'completed_orders': [],
            'overdue_orders': [],
            'referrals': [],
            'referral_count': 0,
            'unread_notifications': [],
            'unread_count': 0,
            'total_orders': 0,
            'total_spent': 0.0,
            'avg_order_value': 0.0,
            'completion_rate': 0.0,
            'orders_this_month': 0,
            'spent_this_month': 0.0,
            'reward_points': 0,
            'referral_earnings': 0.0,
            'upcoming_deadlines': [],
            'order_status_counts': {},
            'monthly_order_trend': [],
            'error_message': None
        }
        
        # Get orders with optimized queries
        try:
            # Recent orders (last 10 for better overview)
            recent_orders = Order.query.filter_by(client_id=current_user.id)\
                                     .order_by(Order.created_at.desc())\
                                     .limit(10)\
                                     .all()
            dashboard_data['recent_orders'] = recent_orders
            
            # Orders by status
            pending_orders = Order.query.filter_by(client_id=current_user.id, status='pending')\
                                      .order_by(Order.due_date.asc())\
                                      .all()
            dashboard_data['pending_orders'] = pending_orders
            
            active_orders = Order.query.filter_by(client_id=current_user.id, status='active')\
                                     .order_by(Order.due_date.asc())\
                                     .all()
            dashboard_data['active_orders'] = active_orders
            
            completed_orders = Order.query.filter_by(client_id=current_user.id, status='completed')\
                                         .order_by(Order.created_at.desc())\
                                         .limit(10)\
                                         .all()
            dashboard_data['completed_orders'] = completed_orders
            
            # Overdue orders (active orders past due date)
            overdue_orders = Order.query.filter(
                and_(
                    Order.client_id == current_user.id,
                    Order.status.in_(['active', 'pending']),
                    Order.due_date < current_time
                )
            ).order_by(Order.due_date.asc()).all()
            dashboard_data['overdue_orders'] = overdue_orders
            
            # Upcoming deadlines (next 7 days)
            next_week = current_time + timedelta(days=7)
            upcoming_deadlines = Order.query.filter(
                and_(
                    Order.client_id == current_user.id,
                    Order.status.in_(['active', 'pending']),
                    Order.due_date.between(current_time, next_week)
                )
            ).order_by(Order.due_date.asc()).limit(5).all()
            dashboard_data['upcoming_deadlines'] = upcoming_deadlines
            
        except Exception as e:
            logging.error(f"Error fetching orders for user {current_user.id}: {str(e)}")
            dashboard_data['error_message'] = "Unable to load order information"
        
        # Get referral data
        try:
            referrals = Referral.query.filter_by(referrer_id=current_user.id)\
                                    .order_by(Referral.created_at.desc())\
                                    .all()
            dashboard_data['referrals'] = referrals
            dashboard_data['referral_count'] = len(referrals)
            
            # Calculate referral earnings
            referral_earnings = sum(r.commission for r in referrals if r.status == 'completed')
            dashboard_data['referral_earnings'] = referral_earnings
            
        except Exception as e:
            logging.error(f"Error fetching referrals for user {current_user.id}: {str(e)}")
        
        # Get notifications
        try:
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id, 
                is_read=False
            ).order_by(Notification.created_at.desc()).limit(10).all()
            dashboard_data['unread_notifications'] = unread_notifications
            dashboard_data['unread_count'] = len(unread_notifications)
            
        except Exception as e:
            logging.error(f"Error fetching notifications for user {current_user.id}: {str(e)}")
        
        # Calculate comprehensive statistics
        try:
            # Total orders and spending
            total_orders = Order.query.filter_by(client_id=current_user.id).count()
            dashboard_data['total_orders'] = total_orders
            
            # Total spent (only paid orders)
            total_spent_result = db.session.query(func.sum(Order.total_price))\
                                         .filter_by(client_id=current_user.id, paid=True)\
                                         .scalar()
            total_spent = float(total_spent_result) if total_spent_result else 0.0
            dashboard_data['total_spent'] = total_spent
            
            # Average order value
            if total_orders > 0:
                avg_order_value = total_spent / max(1, Order.query.filter_by(client_id=current_user.id, paid=True).count())
                dashboard_data['avg_order_value'] = avg_order_value
            
            # Completion rate
            completed_count = Order.query.filter_by(client_id=current_user.id, status='completed').count()
            if total_orders > 0:
                completion_rate = (completed_count / total_orders) * 100
                dashboard_data['completion_rate'] = completion_rate
            
            # This month's statistics
            start_of_month = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            orders_this_month = Order.query.filter(
                and_(
                    Order.client_id == current_user.id,
                    Order.created_at >= start_of_month
                )
            ).count()
            dashboard_data['orders_this_month'] = orders_this_month
            
            spent_this_month_result = db.session.query(func.sum(Order.total_price))\
                                               .filter(
                                                   and_(
                                                       Order.client_id == current_user.id,
                                                       Order.paid == True,
                                                       Order.created_at >= start_of_month
                                                   )
                                               ).scalar()
            spent_this_month = float(spent_this_month_result) if spent_this_month_result else 0.0
            dashboard_data['spent_this_month'] = spent_this_month
            
            # Order status counts for charts
            status_counts = db.session.query(
                Order.status, 
                func.count(Order.id).label('count')
            ).filter_by(client_id=current_user.id).group_by(Order.status).all()
            
            dashboard_data['order_status_counts'] = {status: count for status, count in status_counts}
            
        except Exception as e:
            logging.error(f"Error calculating statistics for user {current_user.id}: {str(e)}")
        
        # Get user reward points (if available in user model)
        try:
            dashboard_data['reward_points'] = getattr(current_user, 'reward_points', 0) or 0
        except Exception as e:
            logging.error(f"Error fetching reward points for user {current_user.id}: {str(e)}")
        
        # Monthly trend data (last 6 months)
        try:
            monthly_trend = []
            for i in range(6):
                month_start = (current_time.replace(day=1) - timedelta(days=32*i)).replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
                month_orders = Order.query.filter(
                    and_(
                        Order.client_id == current_user.id,
                        Order.created_at.between(month_start, month_end)
                    )
                ).count()
                
                monthly_trend.append({
                    'month': month_start.strftime('%b %Y'),
                    'orders': month_orders
                })
            
            dashboard_data['monthly_order_trend'] = list(reversed(monthly_trend))
            
        except Exception as e:
            logging.error(f"Error calculating monthly trend for user {current_user.id}: {str(e)}")
        
        return render_template('client/dashboard.html', **dashboard_data)
        
    except Exception as e:
        logging.error(f"Critical error in dashboard for user {getattr(current_user, 'id', 'unknown')}: {str(e)}")
        flash('An error occurred while loading your dashboard. Please try again.', 'error')
        return render_template('client/dashboard.html', 
                            #  user=current_user, 
                             error_message="Unable to load dashboard data",
                             **{k: v for k, v in dashboard_data.items() if k != 'error_message'})

@client_bp.route('/dashboard/refresh')
@login_required
def refresh_dashboard_data():
    """
    AJAX endpoint to refresh dashboard data without full page reload
    """
    try:
        # This could be used for real-time updates if needed
        return redirect(url_for('client.dashboard'))
    except Exception as e:
        logging.error(f"Error refreshing dashboard: {str(e)}")
        flash('Unable to refresh dashboard data', 'error')
        return redirect(url_for('client.dashboard'))


@client_bp.route('/profile')
@login_required
def profile():
    user = current_user
    return render_template('user/profile.html', user=user)

@client_bp.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id)\
                                     .order_by(Notification.created_at.desc())\
                                     .all()
    return render_template('client/notifications.html', notifications=notifications)

@client_bp.route('/referrals')
@login_required
def referrals():
    user = current_user
    referrals = Referral.query.filter_by(referrer_id=user.id).all()
    total_earnings = sum(r.commission for r in referrals if r.status == 'completed')
    
    # Generate referral code if user doesn't have one
    referral_code = user.referral_code
    if not referral_code:
        from app.utils.referral import generate_referral_code
        referral_code = generate_referral_code()
        user.referral_code = referral_code
        db.session.commit()
    
    return render_template(
        'referral/dashboard.html',
        referral_code=referral_code,
        referrals=referrals,
        total_earnings=total_earnings
    )

# @client_bp.route('/chats/<int:chat_id>')
# @login_required
# def view_chat(chat_id):
#     """View a specific chat conversation (client version)."""
#     # Ensure client owns the chat
#     chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
#     messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.asc()).all()
    
#     # Get associated order details if exists
#     order = Order.query.get(chat.order_id) if chat.order_id else None
    
#     return render_template('client/communication/chat_detail.html',
#                            chat=chat,
#                            messages=messages,
#                            order=order,
#                            title=f'Chat with Support')

# @client_bp.route('/chats/<int:chat_id>/send', methods=['POST'])
# @login_required
# def send_chat_message(chat_id):
#     """Send a message in a chat (client version)."""
#     chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
#     content = request.form.get('content')
    
#     if not content:
#         flash('Message cannot be empty', 'danger')
#         return redirect(url_for('client.view_chat', chat_id=chat_id))
    
#     # Create new message from client
#     message = ChatMessage(
#         chat_id=chat_id,
#         user_id=current_user.id,
#         content=content,
#         is_admin=False  # Client messages are not from admin
#     )
    
#     db.session.add(message)
#     db.session.commit()
    
#     flash('Message sent successfully', 'success')
#     return redirect(url_for('client.view_chat', chat_id=chat_id))

# @client_bp.route('/chats/create', methods=['GET', 'POST'])
# @login_required
# def create_chat():
#     """Create a new chat with support (client version)."""
#     if request.method == 'POST':
#         order_id = request.form.get('order_id', None)
#         initial_message = request.form.get('initial_message', '')
        
#         # Validate order belongs to client if specified
#         if order_id:
#             order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
#             if not order:
#                 flash('Invalid order specified', 'danger')
#                 return redirect(url_for('client.create_chat'))
        
#         # Create chat with support
#         chat = Chat(
#             user_id=current_user.id,
#             order_id=order_id,
#             status='active'
#         )
        
#         db.session.add(chat)
#         db.session.flush()
        
#         # Add initial message if provided
#         if initial_message:
#             message = ChatMessage(
#                 chat_id=chat.id,
#                 user_id=current_user.id,
#                 content=initial_message,
#                 is_admin=False
#             )
#             db.session.add(message)
        
#         db.session.commit()
        
#         flash('Chat started successfully', 'success')
#         return redirect(url_for('client.view_chat', chat_id=chat.id))
    
#     # GET request - show form with client's orders
#     orders = Order.query.filter_by(user_id=current_user.id).all()
    
#     return render_template('client/communication/create_chat.html',
#                            orders=orders,
#                            title='Contact Support')

# @client_bp.route('/chats')
# @login_required
# def list_chats():
#     """List all chats for the current client."""
#     chats = Chat.query.filter_by(user_id=current_user.id)\
#                      .order_by(Chat.created_at.desc()).all()
    
#     return render_template('client/communication/chat_list.html',
#                            chats=chats,
#                            title='My Support Chats')


@client_bp.route('/chats')
@login_required
def list_chats():
    """List all chats for the current client user."""
    status_filter = request.args.get('status', '')
    
    # Base query - get all chats for current user
    if current_user.is_admin:
        query = Chat.query.filter_by(admin_id=current_user.id)
    else:
        query = Chat.query.filter_by(user_id=current_user.id)
    
    # Apply status filter if provided
    if status_filter:
        query = query.filter(Chat.status == status_filter)
    
    # Get all chats, most recent first
    chats = query.order_by(Chat.created_at.desc()).all()
    
    return render_template('client/chats/list.html',
                          chats=chats,
                          status_filter=status_filter,
                          title='My Conversations')

@client_bp.route('/<int:chat_id>')
@login_required
def view_chat(chat_id):
    """View a specific chat conversation."""
    # Ensure the chat belongs to the current user
    if current_user.is_admin:
        chat = Chat.query.filter_by(id=chat_id, admin_id=current_user.id).first_or_404()
    else:
        chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    
    # Get messages in chronological order
    messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.asc()).all()
      # Mark all unread messages as read
    
    # If chat is associated with an order, get order details
    order = None
    if chat.order_id:
        order = Order.query.get(chat.order_id)
    
    # Mark as read functionality could be added here
    unread_messages = ChatMessage.query.filter_by(
        chat_id=chat_id,
        is_read=False
    ).filter(ChatMessage.user_id != current_user.id).all()
    for message in unread_messages:
        message.is_read = True
    db.session.commit()
    socketio.emit('messages_marked_read', {
        'chat_id': chat_id,
        'user_id': current_user.id
    }, room=f"chat_{chat_id}")
    socketio.emit('update_unread_count', {
        'user_id': current_user.id
    }, room=None)
    return render_template('client/chats/detail.html',
                          chat=chat,
                          messages=messages,
                          order=order,
                          title='Chat Support')



@client_bp.route('/<int:chat_id>/send', methods=['POST'])
@login_required
def send_chat_message(chat_id):
    """Send a message in a chat."""
    # Ensure the chat belongs to the current user
    if current_user.is_admin:
        chat = Chat.query.filter_by(id=chat_id, admin_id=current_user.id).first_or_404()
    else:
        chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    
    # Check if chat is closed
    if chat.status == 'closed':
        flash('This conversation has been closed.', 'warning')
        return redirect(url_for('client.view_chat', chat_id=chat_id))
    
    content = request.form.get('content')
    
    if not content:
        flash('Message cannot be empty', 'danger')
        return redirect(url_for('client.view_chat', chat_id=chat_id))
    
    # Create new message
    message = ChatMessage(
        chat_id=chat_id,
        user_id=current_user.id,
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
    socketio.emit('new_message', message_data, room=f'chat_{chat_id}')
    
    # Emit to the other user's personal room (for notifications)
    other_user_id = chat.user_id if current_user.id != chat.user_id else chat.admin_id
    socketio.emit('new_message', message_data, room=f'user_{other_user_id}')
    socketio.emit('update_unread_count', {'user_id': other_user_id}, room=f'user_{other_user_id}')
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'success',
            'message': {
                'id': message.id,
                'content': message.content,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_self': True
            }
        })
    
    return redirect(url_for('client.view_chat', chat_id=chat_id))

@client_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_chat():
    """Start a new support chat."""
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        initial_message = request.form.get('initial_message', '')
        subject = request.form.get('subject', 'General Inquiry')
        
        if not initial_message:
            flash('Please provide an initial message', 'danger')
            return redirect(url_for('client.create_chat'))
        
        # Create new chat
        chat = Chat(
            user_id=current_user.id,
            order_id=order_id if order_id and order_id != 'none' else None,
            status='active',
            subject=subject
        )
        
        db.session.add(chat)
        db.session.flush()  # Get the chat ID
        notify(current_user, 
            title=f"You have created a new chat", 
            message="New chat created", 
            type='info', 
            link=url_for('client.view_chat', chat_id=chat.id))
        other = User.query.filter_by(is_admin=True).first()
        notify(other,
            title=f"New chat created by {current_user.get_name()}",
            message="New chat created", 
            type='info', 
            link=url_for('admin.view_chat', chat_id=chat.id))
        # Add initial message
        message = ChatMessage(
            chat_id=chat.id,
            user_id=current_user.id,
            content=initial_message,
            is_read=False
        )

        
        db.session.add(message)
        
        db.session.commit()
        
        flash('Your conversation has been started. Our team will respond shortly.', 'success')
        return redirect(url_for('client.view_chat', chat_id=chat.id))
    
    # GET request - get user's orders for the dropdown
    orders = Order.query.filter_by(client_id=current_user.id).all()
    
    return render_template('client/chats/create.html',
                          orders=orders,
                          title='Start New Conversation')

@client_bp.route('/<int:chat_id>/close', methods=['POST'])
@login_required
def close_chat(chat_id):
    """Close a chat from the client side."""
    # Ensure the chat belongs to the current user
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    
    chat.status = 'closed'
    other = User.query.filter_by(is_admin=True).first()
    notify(other,
            title=f"Chat #{chat.subject} closed {current_user.get_name()}",
            message="Chat closed", 
            type='info', 
            link=None)
    notify(current_user,
            title=f"New chat created by {current_user.get_name()}",
            message="Chat closed", 
            type='info', 
            link=None)
    db.session.commit()
    
    flash('Conversation closed successfully', 'success')
    return redirect(url_for('client.list_chats'))

@client_bp.route('/check-updates', methods=['POST'])
@login_required
def check_updates():
    """AJAX endpoint to check for new messages."""
    chat_id = current_user.user_chats.user_id
    last_message_id = request.form.get('last_message_id', 0, type=int)
    
    # Ensure the chat belongs to the current user
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    new_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    # Get new messages
    new_messages = ChatMessage.query.filter(
        ChatMessage.chat_id == chat_id,
        ChatMessage.id > last_message_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    # Format messages for JSON response
    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_self': msg.user_id == current_user.id,
            'sender_name': msg.user.get_name() if msg.user_id else 'System'
        })
    
    return jsonify({
        'status': 'success',
        'chat_status': chat.status,
        'new_notifications': new_count,
        'new_messages_count': len(new_messages),
        'messages': messages_data
    })

@client_bp.route('/get-notifications', methods=['GET'])
@login_required
def get_notifications():
    # Get the most recent unread notifications (limit to 5)
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.is_read.asc(),  # Unread first
        Notification.created_at.desc()  # Most recent first
    ).limit(5).all()
    
    # Convert to dictionaries for JSON response
    notification_list = [notification.to_dict() for notification in notifications]
    
    return jsonify({
        'status': 'success',
        'notifications': notification_list
    })

@client_bp.route('/mark-notification-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    
    notification.mark_as_read()
    
    return jsonify({
        'status': 'success',
        'message': 'Notification marked as read'
    })
@client_bp.route('/related-to-order/<int:order_id>')
@login_required
def chats_by_order(order_id):
    """View chats related to a specific order."""
    # Ensure the order belongs to the current user
    order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
    # Get chats related to this order
    chats = Chat.query.filter_by(order_id=order_id, user_id=current_user.id).all()
    
    return render_template('client/chats/order_chats.html',
                          order=order,
                          chats=chats,
                          title=f'Conversations for Order #{order.id}')

@client_bp.route('/extension-status/<int:order_id>', methods=['GET'])
@login_required
def get_client_extension_status(order_id):
    """Get extension status and details for client"""
    try:
        # Verify user has access to this order (adjust based on your auth system)
        # if 'user_id' not in session:
        #     return jsonify({
        #         'success': False, 
        #         'message': 'Authentication required'
        #     }), 401
        
        # user_id = session['user_id']
        
        # Get order and verify ownership
        order = Order.query.filter_by(id=order_id, client_id=current_user.id).first()
        if not order:
            logging.error('Order not found or access denied')
            return jsonify({
                'success': False, 
                'message': 'Order not found or access denied'
            }), 404
        
        # If no extension requested, return false
        if not order.extension_requested:
            logging.info("Extension Not requested")
            return jsonify({
                'success': True,
                'extension_requested': False
            }), 200
        
        # Get the support ticket for this extension request
        support_ticket = SupportTicket.query.filter_by(
            order_id=order_id,
            subject=f"Deadline Extension Request"
        ).order_by(SupportTicket.created_at.desc()).first()
        
        # Extract reason from support ticket message
        reason = "No reason provided"
        if support_ticket and support_ticket.message:
            # Extract the reason from the message format
            lines = support_ticket.message.split('.')
            for line in lines:
                if line.startswith('Reason:'):
                    reason = line.replace('Reason:', '').strip()
                    break
                elif 'Reason:' in line:
                    reason = line.split('Reason:')[1].strip()
                    break
        
        return jsonify({
            'success': True,
            'extension_requested': True,
            'extension_requested_at': order.extension_requested_at.isoformat() if order.extension_requested_at else None,
            'reason': support_ticket.message.split("Reason: ", 1)[1] if support_ticket else reason,
            'ticket_id': support_ticket.id if support_ticket else None,
            'ticket_status': support_ticket.status if support_ticket else None
        }), 200
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


@client_bp.route('/acknowledge-extension', methods=['POST'])
@login_required
def acknowledge_extension():
    """Mark extension request as acknowledged by client"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            logging.error('Order ID required')
            return jsonify({
                'success': False,
                'message': 'Order ID is required'
            }), 400
        
        # Verify user has access to this order
        # if 'user_id' not in session:
        #     return jsonify({
        #         'success': False, 
        #         'message': 'Authentication required'
        #     }), 401
        
        # user_id = session['user_id']
        
        # Get order and verify ownership
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            logging.error('Order not found or access denied')
            return jsonify({
                'success': False, 
                'message': 'Order not found or access denied'
            }), 404
        
        # Add acknowledged field to order model if it doesn't exist
        # You might want to add this field to your Order model:
        # extension_acknowledged = db.Column(db.Boolean, default=False)
        # extension_acknowledged_at = db.Column(db.DateTime)
        
        # For now, we'll update the support ticket status
        support_ticket = SupportTicket.query.filter_by(
            order_id=order_id,
            subject="Deadline Extension Request"
        ).order_by(SupportTicket.created_at.desc()).first()
        
        if support_ticket:
            # Add a response to the ticket
            response_message = f"\n\nClient Response ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\nExtension request has been acknowledged by the client."
            support_ticket.message += response_message
            support_ticket.status = 'in_progress'  # or whatever status indicates client has seen it
            support_ticket.updated_at = datetime.now()
        
        # Optional: Add acknowledged fields to order if you have them
        # order.extension_acknowledged = True
        # order.extension_acknowledged_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Extension request acknowledged successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error: {e}")
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


@client_bp.route('/api/client/extension-response', methods=['POST'])
def submit_extension_response():
    """Allow client to respond to extension request"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        response_message = data.get('response', '').strip()
        accept_extension = data.get('accept_extension', False)  # True/False
        
        if not order_id or not response_message:
            logging.error('Order ID and response message are required')
            return jsonify({
                'success': False,
                'message': 'Order ID and response message are required'
            }), 400
        
        # Verify user has access to this order
        
        
        # Get order and verify ownership
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            logging.error('Order not found or access denied')
            return jsonify({
                'success': False, 
                'message': 'Order not found or access denied'
            }), 404
        
        # Get the support ticket
        support_ticket = SupportTicket.query.filter_by(
            order_id=order_id,
            subject=f"Deadline Extension Request for Order #{order_id}"
        ).order_by(SupportTicket.created_at.desc()).first()
        
        if not support_ticket:
            return jsonify({
                'success': False,
                'message': 'Extension request ticket not found'
            }), 404
        
        # Add client response to the ticket
        status_text = "ACCEPTED" if accept_extension else "DECLINED"
        client_response = f"\n\nClient Response ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n"
        client_response += f"Extension Request: {status_text}\n"
        client_response += f"Message: {response_message}"
        
        support_ticket.message += client_response
        support_ticket.status = 'in_progress'
        support_ticket.updated_at = datetime.now()
        
        # Optional: Update order with client's decision
        # You might want to add these fields to your Order model:
        # extension_client_response = db.Column(db.String(20))  # 'accepted', 'declined'
        # extension_client_message = db.Column(db.Text)
        # extension_response_at = db.Column(db.DateTime)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Extension request {status_text.lower()} successfully',
            'ticket_id': support_ticket.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error: {e}")
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500
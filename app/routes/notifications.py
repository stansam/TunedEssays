from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc
from app.models.communication import Notification
from app.extensions import db

# Create notifications blueprint
notifications_bp = Blueprint('notifications_api', __name__, url_prefix='/api/notifications')

@notifications_bp.route('/all', methods=['GET'])
@login_required
def get_all_notifications():
    """Get all notifications for the current user"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Limit per_page to prevent excessive loads
        per_page = min(per_page, 100)
        
        # Query notifications for current user, ordered by newest first
        notifications_query = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(desc(Notification.created_at))
        
        # Get paginated results
        notifications_paginated = notifications_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Convert to dict format
        notifications_data = [notification.to_dict() for notification in notifications_paginated.items]
        
        return jsonify({
            'status': 'success',
            'notifications': notifications_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': notifications_paginated.total,
                'pages': notifications_paginated.pages,
                'has_next': notifications_paginated.has_next,
                'has_prev': notifications_paginated.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching notifications: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to fetch notifications'
        }), 500

@notifications_bp.route('/count', methods=['GET'])
@login_required
def get_notification_count():
    """Get unread notification count and recent notifications for dropdown"""
    try:
        # Get unread count
        unread_count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()
        
        # Get recent notifications (last 5) for dropdown preview
        recent_notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(desc(Notification.created_at)).limit(5).all()
        
        return jsonify({
            'status': 'success',
            'unread_count': unread_count,
            'recent_notifications': [notification.to_dict() for notification in recent_notifications]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching notification count: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to fetch notification count'
        }), 500

@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a specific notification as read"""
    try:
        # Find the notification and verify ownership
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'status': 'error',
                'message': 'Notification not found'
            }), 404
        
        # Mark as read if not already
        if not notification.is_read:
            notification.mark_as_read()
        
        return jsonify({
            'status': 'success',
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error marking notification as read: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to mark notification as read'
        }), 500

@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for the current user"""
    try:
        # Update all unread notifications for current user
        updated_count = db.session.query(Notification).filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Marked {updated_count} notifications as read'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error marking all notifications as read: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to mark all notifications as read'
        }), 500

@notifications_bp.route('/create', methods=['POST'])
@login_required
def create_notification():
    """Create a new notification (admin or system use)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'message']
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: title, message'
            }), 400
        
        # Create notification
        notification = Notification(
            user_id=data.get('user_id', current_user.id),
            title=data['title'],
            message=data['message'],
            type=data.get('type', 'info'),
            link=data.get('link')
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Notification created successfully',
            'notification': notification.to_dict()
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating notification: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to create notification'
        }), 500

@notifications_bp.route('/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Delete a specific notification"""
    try:
        # Find the notification and verify ownership
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'status': 'error',
                'message': 'Notification not found'
            }), 404
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Notification deleted successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting notification: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete notification'
        }), 500

@notifications_bp.route('/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_notifications():
    """Delete multiple notifications"""
    try:
        data = request.get_json()
        notification_ids = data.get('notification_ids', [])
        
        if not notification_ids:
            return jsonify({
                'status': 'error',
                'message': 'No notification IDs provided'
            }), 400
        
        # Delete notifications for current user only
        deleted_count = db.session.query(Notification).filter(
            Notification.id.in_(notification_ids),
            Notification.user_id == current_user.id
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Deleted {deleted_count} notifications'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error bulk deleting notifications: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete notifications'
        }), 500

# Helper function to create notifications (for use in other parts of the app)
def create_notification_for_user(user_id, title, message, notification_type='info', link=None):
    """
    Helper function to create notifications from other parts of the application
    
    Args:
        user_id (int): ID of the user to notify
        title (str): Notification title
        message (str): Notification message
        notification_type (str): Type of notification (info, success, warning, error)
        link (str, optional): Link to redirect when notification is clicked
    
    Returns:
        Notification: Created notification object
    """
    try:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            link=link
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return notification
        
    except Exception as e:
        current_app.logger.error(f"Error creating notification: {str(e)}")
        db.session.rollback()
        return None

# Helper function to create notifications for multiple users
def create_notification_for_users(user_ids, title, message, notification_type='info', link=None):
    """
    Helper function to create notifications for multiple users
    
    Args:
        user_ids (list): List of user IDs to notify
        title (str): Notification title
        message (str): Notification message
        notification_type (str): Type of notification (info, success, warning, error)
        link (str, optional): Link to redirect when notification is clicked
    
    Returns:
        list: List of created notification objects
    """
    try:
        notifications = []
        
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                link=link
            )
            notifications.append(notification)
        
        db.session.add_all(notifications)
        db.session.commit()
        
        return notifications
        
    except Exception as e:
        current_app.logger.error(f"Error creating notifications for multiple users: {str(e)}")
        db.session.rollback()
        return []
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.service import Service, ServiceCategory, AcademicLevel, Deadline
from app.models.communication import Chat
from app.models.blog import BlogPost, BlogCategory
from app.models.tools import ChatMessage
from app.models.price import PriceRate
from datetime import datetime, timedelta
# from app.config import Config 
from flask_caching import Cache


api_bp = Blueprint('api', __name__)

# API endpoint for service categories
@api_bp.route('/categories')
def get_categories():
    categories = ServiceCategory.query.order_by(ServiceCategory.order).all()
    return jsonify([{
        'id': category.id,
        'name': category.name,
        'description': category.description
    } for category in categories])

# API endpoint for services in a category
@api_bp.route('/services')
def get_services():
    services = Service.query.all()
    if not services:
        return jsonify([])
    
    return jsonify([{
        'id': service.id,
        'name': service.name,
    } for service in services])

# API endpoint for academic levels
@api_bp.route('/academic-levels')
def get_academic_levels():
    levels = AcademicLevel.query.order_by(AcademicLevel.order).all()
    return jsonify([{
        'id': level.id,
        'name': level.name,
    } for level in levels])
@api_bp.route('/deadlines', methods=['GET'])
def get_deadlines():
    deadlines = Deadline.query.order_by(Deadline.order.asc()).all()
    return jsonify([d.to_dict() for d in deadlines]), 200


@api_bp.route('/blog/featured', methods=['GET'])
def get_featured_blog_posts():
    """
    API endpoint to get featured blog posts for the homepage carousel
    Returns the most recent published blog posts
    """
    try:
        # Query for published blog posts, ordered by publish date (most recent first)
        posts = BlogPost.query.filter_by(is_published=True) \
                            .order_by(BlogPost.published_at.desc()) \
                            .limit(6) \
                            .all()
        
        # Format the posts for the frontend
        formatted_posts = []
        for post in posts:
            # Get author information
            author_info = None
            if post.author_id:
                author = User.query.get(post.author_id)
                if author:
                    # Use the get_name method from User model
                    full_name = author.get_name()
                    
                    # Create initials from author's name
                    initials = ""
                    if author.first_name and author.last_name:
                        initials = author.first_name[0] + author.last_name[0]
                    else:
                        name_parts = full_name.split()
                        if len(name_parts) >= 2:
                            initials = name_parts[0][0] + name_parts[1][0]
                        elif len(name_parts) == 1:
                            initials = name_parts[0][0]
                    
                    author_info = {
                        'name': full_name,
                        'initials': initials.upper()
                    }
            
            # Get category information
            category_info = None
            if post.category_id:
                category = BlogCategory.query.get(post.category_id)
                if category:
                    category_info = {
                        'name': category.name,
                        'slug': category.slug
                    }
            
            # Format post data
            post_data = {
                'id': post.id,
                'title': post.title,
                'slug': post.slug,
                'excerpt': post.excerpt,
                'tags': post.tags,
                'featured_image': post.featured_image,
                'created_at': post.created_at.isoformat(),
                'published_at': post.published_at.isoformat() if post.published_at else None,
                'author': author_info,
                'category': category_info or {'name': 'Uncategorized', 'slug': 'uncategorized'}
            }
            
            formatted_posts.append(post_data)
        
        return jsonify(formatted_posts)
    
    except Exception as e:
        # Log the error (you should implement proper logging)
        print(f"Error fetching blog posts: {str(e)}")
        return jsonify({"error": "Failed to fetch blog posts"}), 500
    
# API endpoint to get service options by tab type
@api_bp.route('/service-options/<tab_type>')
def get_service_options(tab_type):
    tab_to_category = {
        'writing': 'Writing',
        'proofreading': 'Proofreading',
        'technical': 'Technical'
    }
    
    category_name = tab_to_category.get(tab_type)
    if not category_name:
        return jsonify([])
    
    category = ServiceCategory.query.filter_by(name=category_name).first()
    if not category:
        return jsonify([])
    
    services = Service.query.filter_by(category_id=category.id).all()
    return jsonify([{
        'id': service.id,
        'name': service.name,
        'value': service.name.lower().replace(' ', '-'),
    } for service in services])

# API endpoint for orders (protected)
@api_bp.route('/orders', methods=['GET'])
@login_required
def orders():
    from app.models.order import Order
    
    if request.method == 'GET':
        # Return current user's orders
        orders = Order.query.filter_by(client_id=current_user.id).order_by(Order.created_at.desc()).all()
        return jsonify([{
            'id': order.id,
            'order_number': order.order_number,
            'title': order.title,
            'status': order.status,
            'due_date': order.due_date.isoformat(),
            'total_price': order.total_price,
            'paid': order.paid
        } for order in orders])
    
    return jsonify({'error': 'Method not implemented'}), 501

@api_bp.route('/notifications/messages')
@login_required
@login_required
def get_unread_messages():
    # Fetch unread messages for current user
    unread_messages = (ChatMessage.query
                       .join(Chat)
                       .filter(ChatMessage.user_id != current_user.id)  # Exclude current user's own messages
                       .filter(ChatMessage.is_read == False)
                       .filter((Chat.user_id == current_user.id) | (Chat.admin_id == current_user.id))
                       .order_by(ChatMessage.created_at.desc())
                       .limit(5)
                       .all())
    
    message_count = len(unread_messages)
    messages_data = [{
        'id': m.id,
        'chat_id': m.chat_id,
        'content': m.content[:50] + ("..." if len(m.content) > 50 else ""),
        'timestamp': m.created_at.strftime("%b %d, %H:%M")
    } for m in unread_messages]

    return jsonify({
        'count': message_count,
        'messages': messages_data
    })

@api_bp.route('/chats/unread_count')
@login_required
def get_unread_count():
    """Get unread messages count for current user"""
    if current_user.is_admin:
        count = ChatMessage.query.join(Chat).filter(
            ChatMessage.is_read == False,
            ChatMessage.user_id != current_user.id,
            Chat.admin_id == current_user.id
        ).count()
    else:
        count = ChatMessage.query.join(Chat).filter(
            ChatMessage.is_read == False,
            ChatMessage.user_id != current_user.id,
            Chat.user_id == current_user.id
        ).count()
    
    return jsonify({"unread_count": count})

# @api_bp.route('/chats/recent_messages')
# @login_required
# def get_recent_messages():
#     """Get recent messages for the dropdown"""
#     if current_user.is_admin:
#         recent_messages = ChatMessage.query.join(Chat).filter(
#             Chat.admin_id == current_user.id,
#             ChatMessage.user_id != current_user.id
#         ).order_by(ChatMessage.created_at.desc()).limit(5).all()
#     else:
#         recent_messages = ChatMessage.query.join(Chat).filter(
#             Chat.user_id == current_user.id,
#             ChatMessage.user_id != current_user.id
#         ).order_by(ChatMessage.created_at.desc()).limit(5).all()
    
#     messages_data = []
#     for message in recent_messages:
#         chat = Chat.query.get(message.chat_id)
#         sender = User.query.get(message.user_id)
        
#         # Determine the other user in the chat
#         if current_user.is_admin:
#             other_user = User.query.get(chat.user_id)
#         else:
#             other_user = User.query.get(chat.admin_id)
        
#         messages_data.append({
#             'id': message.id,
#             'chat_id': message.chat_id,
#             'content': message.content[:50] + ('...' if len(message.content) > 50 else ''),
#             'sender_name': sender.get_name() if sender else 'Unknown',
#             'is_read': message.is_read,
#             'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
#             'subject': chat.subject or f"Chat with {other_user.get_name()}" if other_user else "Chat"
#         })
    
#     return jsonify(messages_data)

@api_bp.route('/chats/recent_messages')
@login_required
def get_recent_messages():
    """Get recent messages grouped by chat for the dropdown"""
    from sqlalchemy import func
    
    if current_user.is_admin:
        # Get the latest message per chat for admin
        subquery = db.session.query(
            ChatMessage.chat_id,
            func.max(ChatMessage.created_at).label('latest_created_at')
        ).join(Chat).filter(
            Chat.admin_id == current_user.id,
            ChatMessage.user_id != current_user.id
        ).group_by(ChatMessage.chat_id).subquery()
        
        recent_messages = db.session.query(ChatMessage).join(
            subquery,
            (ChatMessage.chat_id == subquery.c.chat_id) &
            (ChatMessage.created_at == subquery.c.latest_created_at)
        ).order_by(ChatMessage.created_at.desc()).limit(5).all()
        
    else:
        # Get the latest message per chat for regular user
        subquery = db.session.query(
            ChatMessage.chat_id,
            func.max(ChatMessage.created_at).label('latest_created_at')
        ).join(Chat).filter(
            Chat.user_id == current_user.id,
            ChatMessage.user_id != current_user.id
        ).group_by(ChatMessage.chat_id).subquery()
        
        recent_messages = db.session.query(ChatMessage).join(
            subquery,
            (ChatMessage.chat_id == subquery.c.chat_id) &
            (ChatMessage.created_at == subquery.c.latest_created_at)
        ).order_by(ChatMessage.created_at.desc()).limit(5).all()
    
    chats_data = []
    for message in recent_messages:
        chat = Chat.query.get(message.chat_id)
        sender = User.query.get(message.user_id)
        
        # Determine the other user in the chat
        if current_user.is_admin:
            other_user = User.query.get(chat.user_id)
        else:
            other_user = User.query.get(chat.admin_id)
        
        # Count unread messages in this chat
        unread_count = ChatMessage.query.filter(
            ChatMessage.chat_id == chat.id,
            ChatMessage.user_id != current_user.id,
            ChatMessage.is_read == False
        ).count()
        
        chats_data.append({
            'chat_id': chat.id,
            'subject': chat.subject or f"Chat with {other_user.get_name()}" if other_user else "Chat",
            'latest_message': {
                'id': message.id,
                'content': message.content[:50] + ('...' if len(message.content) > 50 else ''),
                'sender_name': sender.get_name() if sender else 'Unknown',
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M')
            },
            'unread_count': unread_count,
            'has_unread': unread_count > 0,
            'other_user_name': other_user.get_name() if other_user else 'Unknown'
        })
    
    return jsonify(chats_data)

@api_bp.route('/chats/check_updates', methods=['POST'])
@login_required
def check_updates():
    """Check for new messages since last check."""
    chat_id = request.form.get('chat_id')
    last_message_id = request.form.get('last_message_id', 0, type=int)
    
    if not chat_id:
        return jsonify({'status': 'error', 'message': 'No chat_id provided'})
    
    # Ensure the chat belongs to the current user
    if current_user.is_admin:
        chat = Chat.query.filter_by(id=chat_id, admin_id=current_user.id).first()
    else:
        chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    
    if not chat:
        return jsonify({'status': 'error', 'message': 'Chat not found'})
    
    # Get new messages
    new_messages = ChatMessage.query.filter(
        ChatMessage.chat_id == chat_id,
        ChatMessage.id > last_message_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    messages_data = []
    for message in new_messages:
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'is_self': message.user_id == current_user.id,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return jsonify({
        'status': 'success',
        'chat_status': chat.status,
        'messages': messages_data
    })

# @api_bp.route('/calculate-price', methods=['POST'])
# def calculate_price():
#     """
#     API endpoint to calculate order price based on service, academic level, deadline, and page count
#     """
#     data = request.json
    
#     try:
#         service_id = int(data.get('service_id'))
#         academic_level_id = int(data.get('academic_level_id'))
#         deadline_data= float (data.get('deadline_data'))
#         # deadline_id = int(data.get('deadline_id'))
#         word_count = int(data.get('word_count', 0))
#         report_type = data.get('report_type')
#         if(report_type):
#                 if(report_type) == "standard":
#                     report_price = 4.99
#                 elif(report_type) == "turnitin":
#                     report_price= 9.99
#                 else:
#                     report_price = 0
#         else:
#             report_price = 0
#         if not deadline_data:
#             return jsonify({"Error": "Deadline not found"}), 404
#         # try:
#         #     deadline_date= datetime.strptime(deadline_data, "%Y, %m, %d, %s")
#         # except ValueError:
#         #     try: 
#         #         deadline_date = datetime.strptime(deadline_data, "%Y-%m-%d, %H:%M")
#         #     except ValueError:
#         #         return jsonify({"error": "Invalid deadline format"}), 400
#         # current_time = datetime.now()
#         if deadline_data <= 0:
#             return jsonify({"error": "Deadline cannot be less than three hours from current time!"})
#         # timeDifference = deadline_date - current_time
#         hoursUntilDeadline = deadline_data

#         deadlines = Deadline.query.order_by(Deadline.hours.asc()).all()
#         deadline_id = None 
#         selected_deadline = None
#         for deadline in deadlines:
#             if(hoursUntilDeadline <= (deadline.hours+1)):
#                 deadline_id = deadline.id
#                 selected_deadline = deadline
#                 break
#         if(deadline_id is None and deadlines):
#             selected_deadline = deadline[-1]
#             deadline_id = selected_deadline.id

#         if(deadline_id is None):
#             return jsonify({"error": "Failed to match deadline"})
        
#         # Calculate page count (assumed 275 words per page)
#         words_per_page = Config.WORDS_PER_PAGE
#         page_count = max(1, round(word_count / words_per_page, 2))
        
#         # Get service
#         service = Service.query.get(service_id)
#         if not service:
#             return jsonify({"error": "Service not found"}), 404
            
#         # Look up the price rate
#         price_rate = PriceRate.query.filter_by(
#             pricing_category_id=service.pricing_category_id,
#             academic_level_id=academic_level_id,
#             deadline_id=deadline_id
#         ).first()
        
#         price_per_page = price_rate.price_per_page
#         pages_price = price_per_page * page_count
#         if report_price > 0:
#             total_price = (pages_price + report_price) 
#         else:
#             total_price = pages_price
        
#         # Get deadline in hours
#         # deadline = Deadline.query.get(deadline_id)
#         # due_date_str = deadline_date.strftime("%Y-%m-%d %H:%M")
        
#         return jsonify({
#             "price_per_page": price_per_page,
#             "page_count": page_count,
#             "total_price": total_price,
#             "selected_deadline" : selected_deadline.to_dict(),
#             # "due_date": due_date_str,
#             "hours_until_deadline": round(hoursUntilDeadline, 2)
#         })
        
#     except Exception as e:
#         current_app.logger.error(f"Error calculating price: {str(e)}")
#         return jsonify({"error": str(e)}), 400

# @api_bp.route('/calculate-price', methods=['POST'])
# def calculate_price():
#     """
#     API endpoint to calculate order price based on service, academic level, deadline, and page count
#     """
#     data = request.json
    
#     try:
#         # Validate required fields
#         if not data:
#             return jsonify({"error": "No data provided"}), 400
            
#         service_id = data.get('service_id')
#         academic_level_id = data.get('academic_level_id')
#         hours_until_deadline = data.get('deadline_data')
#         word_count = data.get('word_count', 0)
#         report_type = data.get('report_type')
        
#         # Validate required fields
#         if service_id is None or academic_level_id is None or hours_until_deadline is None:
#             return jsonify({"error": "Missing required fields: service_id, academic_level_id, deadline_data"}), 400
        
#         # Convert and validate data types
#         try:
#             service_id = int(service_id)
#             academic_level_id = int(academic_level_id)
#             hours_until_deadline = float(hours_until_deadline)
#             word_count = int(word_count)
#         except (ValueError, TypeError):
#             return jsonify({"error": "Invalid data types provided"}), 400
        
#         # Calculate report price
#         if report_type:
#             if report_type == "standard":
#                 report_price = 4.99
#             elif report_type == "turnitin":
#                 report_price = 9.99
#             else:
#                 report_price = 0
#         else:
#             report_price = 0
        
#         # Validate deadline
#         if hours_until_deadline <= 0:
#             return jsonify({"error": "Deadline cannot be less than or equal to zero hours from current time!"}), 400
        
#         # Find appropriate deadline
#         deadlines = Deadline.query.order_by(Deadline.hours.asc()).all()
#         if not deadlines:
#             return jsonify({"error": "No deadlines configured in system"}), 500
            
#         deadline_id = None 
#         selected_deadline = None
        
#         for deadline in deadlines:
#             if hours_until_deadline <= (deadline.hours + 1):
#                 deadline_id = deadline.id
#                 selected_deadline = deadline
#                 break
        
#         # If no matching deadline found, use the longest available deadline
#         if deadline_id is None:
#             selected_deadline = deadlines[-1]  # Fixed: was deadline[-1]
#             deadline_id = selected_deadline.id
        
#         # Calculate page count (with safety check for division by zero)
#         words_per_page = getattr(Config, 'WORDS_PER_PAGE', 275)
#         if words_per_page <= 0:
#             words_per_page = 275  # Default fallback
            
#         page_count = max(1, round(word_count / words_per_page, 2))
        
#         # Get service
#         service = Service.query.get(service_id)
#         if not service:
#             return jsonify({"error": "Service not found"}), 404
        
#         # Look up the price rate
#         price_rate = PriceRate.query.filter_by(
#             pricing_category_id=service.pricing_category_id,
#             academic_level_id=academic_level_id,
#             deadline_id=deadline_id
#         ).first()
        
#         # Validate price rate exists
#         if not price_rate:
#             return jsonify({"error": "Price rate not found for the given combination of service, academic level, and deadline"}), 404
        
#         # Calculate prices
#         price_per_page = price_rate.price_per_page
#         pages_price = price_per_page * page_count
#         total_price = pages_price + report_price
        
#         return jsonify({
#             "price_per_page": price_per_page,
#             "page_count": page_count,
#             "pages_price": pages_price,
#             "report_price": report_price,
#             "total_price": total_price,
#             "selected_deadline": selected_deadline.to_dict(),
#             "hours_until_deadline": round(hours_until_deadline, 2)
#         })
        
#     except Exception as e:
#         current_app.logger.error(f"Error calculating price: {str(e)}")
#         return jsonify({"error": "Internal server error occurred while calculating price"}), 500


# In your api module (e.g., api/routes.py or wherever this endpoint is)

def calculate_price_internal(service_id, academic_level_id, hours_until_deadline, word_count=0, report_type=None):
    """
    Internal function to calculate order price
    Returns: dict with price data or raises exception
    """
    try:
        # Convert and validate data types
        service_id = int(service_id)
        academic_level_id = int(academic_level_id)
        hours_until_deadline = float(hours_until_deadline)
        word_count = int(word_count)
    except (ValueError, TypeError) as e:
        raise ValueError("Invalid data types provided")
    
    # Calculate report price
    if report_type:
        if report_type == "standard":
            report_price = 4.99
        elif report_type == "turnitin":
            report_price = 9.99
        else:
            report_price = 0
    else:
        report_price = 0
    
    # Validate deadline
    if hours_until_deadline <= 0:
        raise ValueError("Deadline cannot be less than or equal to zero hours from current time!")
    
    # Find appropriate deadline
    deadlines = Deadline.query.order_by(Deadline.hours.asc()).all()
    if not deadlines:
        raise RuntimeError("No deadlines configured in system")
        
    deadline_id = None 
    selected_deadline = None
    
    for deadline in deadlines:
        if hours_until_deadline <= (deadline.hours + 1):
            deadline_id = deadline.id
            selected_deadline = deadline
            break
    
    # If no matching deadline found, use the longest available deadline
    if deadline_id is None:
        selected_deadline = deadlines[-1]
        deadline_id = selected_deadline.id
    
    # Calculate page count (with safety check for division by zero)
    # words_per_page = getattr(Config, 'WORDS_PER_PAGE', 275)
    words_per_page = current_app.config.get('WORDS_PER_PAGE', 275)
    if words_per_page <= 0:
        words_per_page = 275  # Default fallback
        
    page_count = max(1, round(word_count / words_per_page, 2))
    
    # Get service
    service = Service.query.get(service_id)
    if not service:
        raise ValueError("Service not found")
    
    # Look up the price rate
    price_rate = PriceRate.query.filter_by(
        pricing_category_id=service.pricing_category_id,
        academic_level_id=academic_level_id,
        deadline_id=deadline_id
    ).first()
    
    # Validate price rate exists
    if not price_rate:
        raise ValueError("Price rate not found for the given combination of service, academic level, and deadline")
    
    # Calculate prices
    price_per_page = price_rate.price_per_page
    pages_price = price_per_page * page_count
    total_price = pages_price + report_price
    
    return {
        "price_per_page": price_per_page,
        "page_count": page_count,
        "pages_price": pages_price,
        "report_price": report_price,
        "total_price": total_price,
        "selected_deadline": selected_deadline.to_dict(),
        "hours_until_deadline": round(hours_until_deadline, 2)
    }


@api_bp.route('/calculate-price', methods=['POST'])
def calculate_price():
    """
    API endpoint to calculate order price based on service, academic level, deadline, and page count
    """
    data = request.json
    
    try:
        # Validate required fields
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        service_id = data.get('service_id')
        academic_level_id = data.get('academic_level_id')
        hours_until_deadline = data.get('deadline_data')
        word_count = data.get('word_count', 0)
        report_type = data.get('report_type')
        
        # Validate required fields
        if service_id is None or academic_level_id is None or hours_until_deadline is None:
            return jsonify({"error": "Missing required fields: service_id, academic_level_id, deadline_data"}), 400
        
        # Call the internal function
        result = calculate_price_internal(
            service_id=service_id,
            academic_level_id=academic_level_id,
            hours_until_deadline=hours_until_deadline,
            word_count=word_count,
            report_type=report_type
        )
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Error calculating price: {str(e)}")
        return jsonify({"error": "Internal server error occurred while calculating price"}), 500

##################################################################################################################################
############################### API Endpoints for Services, Academic Levels, and Deadlines for hero-sec #######################################

@api_bp.route('/get-services')
def api_get_services():
    """
    API endpoint to fetch all services
    Returns services organized by category
    """
    try:
        services = Service.query.all()
        services_data = []
        
        for service in services:
            services_data.append({
                'id': service.id,
                'name': service.name,
                'pricing_category_id': service.pricing_category_id,
                'description': getattr(service, 'description', ''),  # Include if available
                'created_at': service.created_at.isoformat() if hasattr(service, 'created_at') else None
            })
        
        return jsonify(services_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch services',
            'message': str(e)
        }), 500


@api_bp.route('/academic-levels')
def api_get_academic_levels():
    """
    API endpoint to fetch all academic levels
    """
    try:
        academic_levels = AcademicLevel.query.all()
        levels_data = []
        
        for level in academic_levels:
            levels_data.append({
                'id': level.id,
                'name': level.name,
                'description': getattr(level, 'description', ''),  # Include if available
                'order': getattr(level, 'order', level.id)  # Use order if available, otherwise use id
            })
        
        # Sort by order if available
        levels_data.sort(key=lambda x: x['order'])
        
        return jsonify(levels_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch academic levels',
            'message': str(e)
        }), 500


@api_bp.route('/deadlines')
def api_get_deadlines():
    """
    API endpoint to fetch all deadlines
    """
    try:
        deadlines = Deadline.query.all()
        deadlines_data = []
        
        for deadline in deadlines:
            deadlines_data.append({
                'id': deadline.id,
                'name': deadline.name,
                'hours': deadline.hours,
                'order': getattr(deadline, 'order', deadline.id),
                'multiplier': getattr(deadline, 'multiplier', 1.0)  # Include if available
            })
        
        # Sort by order
        deadlines_data.sort(key=lambda x: x['order'])
        
        return jsonify(deadlines_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch deadlines',
            'message': str(e)
        }), 500


@api_bp.route('/form-data')
def api_get_all_form_data():
    """
    API endpoint to fetch all form data in one request
    This is more efficient if you want to minimize API calls
    """
    try:
        # Fetch all required data
        services = Service.query.all()
        academic_levels = AcademicLevel.query.all()
        deadlines = Deadline.query.all()
        
        # Organize services by category
        services_by_category = {
            'writing': [],
            'proofreading': [],
            'technical': [],
            'humanizing_ai': []
        }
        
        for service in services:
            service_data = {
                'id': service.id,
                'name': service.name,
                'pricing_category_id': service.pricing_category_id,
                'description': getattr(service, 'description', '')
            }
            
            if service.pricing_category_id == 1:
                services_by_category['writing'].append(service_data)
            elif service.pricing_category_id == 2:
                services_by_category['proofreading'].append(service_data)
            elif service.pricing_category_id == 3:
                services_by_category['technical'].append(service_data)
            elif service.pricing_category_id == 4:
                services_by_category['humanizing_ai'].append(service_data)
        
        # Prepare academic levels data
        levels_data = []
        for level in academic_levels:
            levels_data.append({
                'id': level.id,
                'name': level.name,
                'description': getattr(level, 'description', ''),
                'order': getattr(level, 'order', level.id)
            })
        levels_data.sort(key=lambda x: x['order'])
        
        # Prepare deadlines data
        deadlines_data = []
        for deadline in deadlines:
            deadlines_data.append({
                'id': deadline.id,
                'name': deadline.name,
                'hours': deadline.hours,
                'order': getattr(deadline, 'order', deadline.id),
                'multiplier': getattr(deadline, 'multiplier', 1.0)
            })
        deadlines_data.sort(key=lambda x: x['order'])
        
        return jsonify({
            'services': services_by_category,
            'academic_levels': levels_data,
            'deadlines': deadlines_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch form data',
            'message': str(e)
        }), 500





@api_bp.route('/services/cached')
# @cache.cached(timeout=300)  # Cache for 5 minutes
def api_get_services_cached():
    """
    Cached version of services endpoint
    """
    return api_get_services()


@api_bp.route('/academic-levels/cached')
# @cache.cached(timeout=300)
def api_get_academic_levels_cached():
    """
    Cached version of academic levels endpoint
    """
    return api_get_academic_levels()


# Error handlers for API endpoints
@api_bp.errorhandler(404)
def api_not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'The requested API endpoint does not exist'
        }), 404
    return error


@api_bp.errorhandler(500)
def api_internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
    return error
import os
from flask import Flask, g, request, render_template
from config import config
import logging
# debug = True
def create_app(config_name="default"):
    """Application factory function"""
    
    # Create the Flask app instance
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    # debug = True
    # Ensure upload folder exists
    if not os.path.exists(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])):
        os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']))
    
    # Initialize extensions
    from app.extensions import (
        db, migrate, csrf, mail, limiter, login_manager, cors, socketio
    )
    
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    #limiter.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # from app.routes import pay_ser
    from app.routes import events
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.orders import orders_bp
    from app.routes.admin import admin_bp
    from app.routes.client import client_bp
    from app.routes.blog import blog_bp
    from app.routes.payment import payment_bp
    from app.routes.api import api_bp
    from app.routes.notifications import notifications_bp
    from app.routes.admin_order_delivery import admin_delivery_bp
    from app.routes.client_results import client_results_bp
    from app.routes.order_results import results_services_bp
    from app.routes.activity import activity_bp
    from app.routes.order_activity import order_activities_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(client_bp, url_prefix='/client') 
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_delivery_bp, prefix='/admin')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    app.register_blueprint(client_results_bp, url_prefix='/delivery')
    app.register_blueprint(results_services_bp, url_prefix='/result-services')
    app.register_blueprint(order_activities_bp, url_prefix='/order-activities')
    app.register_blueprint(activity_bp, url_prefix='/activity')
    uploads_dir = os.path.join(app.static_folder, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(os.path.join(uploads_dir, 'orders'), exist_ok=True)
    os.makedirs(os.path.join(uploads_dir, 'blog'), exist_ok=True)
    os.makedirs(os.path.join(uploads_dir, 'samples'), exist_ok=True)
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    # Shell context processor
    @app.shell_context_processor
    def make_shell_context():
        # Import all models here
        from app.models.user import User
        from app.models.service import Service, ServiceCategory, AcademicLevel, Deadline
        from app.models.order import Order, OrderComment, OrderFile
        from app.models.payment import Payment, Invoice, Transaction, Refund, Discount
        from app.models.referral import Referral
        from app.models.content import Testimonial, Sample, FAQ
        from app.models.tools import PlagiarismCheck, CitationGenerator, ChatMessage
        from app.models.blog import BlogPost, BlogCategory, BlogComment
        from app.models.communication import ContactMessage, Notification, Chat
        from app.models.price import PriceRate, PricingCategory
        
        return {
            'db': db, 
            'User': User, 
            'Service': Service,
            'ServiceCategory': ServiceCategory,
            'Order': Order,
            'Payment': Payment,
            'Invoice': Invoice,
            'AcademicLevel': AcademicLevel,
            'Deadline': Deadline,
            'OrderFile': OrderFile,
            'Referral': Referral,
            'BlogPost': BlogPost,
            'Testimonial': Testimonial,
            'Sample': Sample,
            'ContactMessage': ContactMessage,
            'Notification': Notification,
            'Chat': Chat,
            'PriceRate': PriceRate,
            'PricingCategory': PricingCategory,
            'OrderComment': OrderComment,
            'OrderFile': OrderFile
        }
    
    # Create database tables
    with app.app_context():
        db.create_all()
        logging.basicConfig(
            filename='app.log',
            level=logging.INFO,
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        # Initialize database with default data
        from app.utils.db_init import init_db
        init_db(app, db)
    # @app.after_request
    # def process_notifications(response):
    #     # Only process if there are pending notifications
    #     if hasattr(g, 'pending_chat_notifications') and g.pending_chat_notifications:
    #         try:
    #             chat_we.process_pending_chat_notifications()
    #         except Exception as e:
    #             # Log the error but don't fail the request
    #             app.logger.error(f"Error processing chat notifications: {str(e)}")
        
    #     # Always return the original response
    #     return response
    return app
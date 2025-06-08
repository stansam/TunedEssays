from flask import request, jsonify, send_file, current_app, Blueprint
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound, Forbidden
from datetime import datetime
import os
import logging
from app.extensions import db  # Replace with your actual app import
from app.models.order import Order, OrderComment, SupportTicket
from app.models.user import User
from app.models.order_delivery import OrderDelivery, OrderDeliveryFile

logger = logging.getLogger(__name__)
results_services_bp = Blueprint('results_services', __name__)

class ClientResultsService:
    """Service class for handling client results management operations"""
    
    @staticmethod
    def get_client_completed_orders(client_id, page=1, per_page=10):
        """Get paginated list of client's completed orders ready for review"""
        try:
            orders = Order.query.filter(
                Order.client_id == client_id,
                Order.status.in_(['completed pending review', 'completed', 'revision'])
            ).order_by(Order.updated_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            return {
                'success': True,
                'orders': [ClientResultsService._serialize_order_for_client(order) for order in orders.items],
                'pagination': {
                    'page': orders.page,
                    'pages': orders.pages,
                    'per_page': orders.per_page,
                    'total': orders.total,
                    'has_next': orders.has_next,
                    'has_prev': orders.has_prev
                }
            }
        except Exception as e:
            logger.error(f"Error fetching client completed orders: {str(e)}")
            return {'success': False, 'message': 'Failed to fetch orders'}
    
    @staticmethod
    def get_order_details_for_review(order_id, client_id):
        """Get detailed order information for client review"""
        try:
            order = Order.query.filter_by(id=order_id, client_id=client_id).first()
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            if order.status not in ['completed pending review', 'completed', 'revision']:
                return {'success': False, 'message': 'Order is not ready for review'}
            
            # Get latest delivery
            latest_delivery = order.latest_delivery
            if not latest_delivery:
                return {'success': False, 'message': 'No delivery found for this order'}
            
            return {
                'success': True,
                'order': ClientResultsService._serialize_order_for_review(order),
                'delivery': ClientResultsService._serialize_delivery_for_client(latest_delivery)
            }
        except Exception as e:
            logger.error(f"Error fetching order details for review: {str(e)}")
            return {'success': False, 'message': 'Failed to fetch order details'}
    
    @staticmethod
    def download_delivery_file(file_id, client_id):
        """Allow client to download a delivery file"""
        try:
            # Get the delivery file and verify client access
            delivery_file = OrderDeliveryFile.query.join(OrderDelivery).join(Order).filter(
                OrderDeliveryFile.id == file_id,
                Order.client_id == client_id
            ).first()
            
            if not delivery_file:
                return {'success': False, 'message': 'File not found or access denied'}
            
            # Check if file exists on disk
            if not os.path.exists(delivery_file.file_path):
                return {'success': False, 'message': 'File not found on server'}
            
            return {
                'success': True,
                'file_path': delivery_file.file_path,
                'filename': delivery_file.original_filename,
                'file_info': {
                    'size': delivery_file.file_size,
                    'format': delivery_file.file_format,
                    'type': delivery_file.file_type
                }
            }
        except Exception as e:
            logger.error(f"Error downloading delivery file: {str(e)}")
            return {'success': False, 'message': 'Failed to download file'}
    
    @staticmethod
    def request_revision(order_id, client_id, revision_notes):
        """Client requests revision for an order"""
        try:
            order = Order.query.filter_by(id=order_id, client_id=client_id).first()
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            if order.status != 'completed pending review':
                return {'success': False, 'message': 'Order cannot be revised at this stage'}
            
            # Update order status
            order.status = 'revision'
            order.updated_at = datetime.now()
            
            # Add revision comment
            if revision_notes:
                revision_comment = OrderComment(
                    order_id=order.id,
                    user_id=client_id,
                    comment=revision_notes,
                    comment_type='revision_request',
                    created_at=datetime.now()
                )
                db.session.add(revision_comment)

            
            db.session.commit()
            try:
                support = SupportTicket(
                    order_id=order_id,
                    user_id=client_id,
                    subject='Revision Request',
                    message=revision_notes,
                    status='open'
                )
                db.session.add(support)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.info(f'Support ticket creation failed:{e}')
                pass
            # Log the revision request
            logger.info(f"Revision requested for order {order.order_number} by client {client_id}")
            
            return {
                'success': True,
                'message': 'Revision request submitted successfully',
                'order_status': order.status
            }
        except Exception as e:
            logger.error(f"Error requesting revision: {str(e)}")
            db.session.rollback()
            return {'success': False, 'message': 'Failed to submit revision request'}
    
    @staticmethod
    def accept_delivery(order_id, client_id, feedback=None):
        """Client accepts the delivery and marks order as completed"""
        try:
            order = Order.query.filter_by(id=order_id, client_id=client_id).first()
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            if order.status != 'completed pending review':
                return {'success': False, 'message': 'Order cannot be accepted at this stage'}
            
            # Update order status
            order.status = 'completed'
            order.updated_at = datetime.now()
            
            # Add acceptance feedback if provided
            if feedback:
                feedback_comment = OrderComment(
                    order_id=order.id,
                    user_id=client_id,
                    comment=feedback,
                    comment_type='completion_feedback',
                    created_at=datetime.now()
                )
                db.session.add(feedback_comment)
            
            db.session.commit()
            
            # Log the acceptance
            logger.info(f"Order {order.order_number} accepted by client {client_id}")
            
            return {
                'success': True,
                'message': 'Order completed successfully',
                'order_status': order.status
            }
        except Exception as e:
            logger.error(f"Error accepting delivery: {str(e)}")
            db.session.rollback()
            return {'success': False, 'message': 'Failed to complete order'}
    
    @staticmethod
    def get_order_delivery_history(order_id, client_id):
        """Get delivery history for an order"""
        try:
            order = Order.query.filter_by(id=order_id, client_id=client_id).first()
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            deliveries = OrderDelivery.query.filter_by(order_id=order_id).order_by(
                OrderDelivery.delivered_at.desc()
            ).all()
            
            return {
                'success': True,
                'deliveries': [ClientResultsService._serialize_delivery_for_client(d) for d in deliveries],
                'total_deliveries': len(deliveries)
            }
        except Exception as e:
            logger.error(f"Error fetching delivery history: {str(e)}")
            return {'success': False, 'message': 'Failed to fetch delivery history'}
    
    @staticmethod
    def _serialize_order_for_client(order):
        """Serialize order data for client view"""
        return {
            'id': order.id,
            'order_number': order.order_number,
            'title': order.title,
            'status': order.status,
            'status_color': order.status_color,
            'total_price': order.total_price,
            'due_date': order.due_date.isoformat() if order.due_date else None,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
            'is_delivered': order.is_delivered,
            'word_count': order.word_count,
            'page_count': order.page_count
        }
    
    @staticmethod
    def _serialize_order_for_review(order):
        """Serialize detailed order data for review"""
        return {
            'id': order.id,
            'order_number': order.order_number,
            'title': order.title,
            'description': order.description,
            'status': order.status,
            'status_color': order.status_color,
            'total_price': order.total_price,
            'word_count': order.word_count,
            'page_count': order.page_count,
            'format_style': order.format_style,
            'report_type': order.report_type,
            'due_date': order.due_date.isoformat() if order.due_date else None,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None
        }
    
    @staticmethod
    def _serialize_delivery_for_client(delivery):
        """Serialize delivery data for client view"""
        return {
            'id': delivery.id,
            'delivery_status': delivery.delivery_status,
            'status_color': delivery.status_color,
            'delivered_at': delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            'has_plagiarism_report': delivery.has_plagiarism_report,
            'delivery_files_count': delivery.delivery_files_count,
            'files': [ClientResultsService._serialize_delivery_file(f) for f in delivery.delivery_files]
        }
    
    @staticmethod
    def _serialize_delivery_file(file):
        """Serialize delivery file data"""
        return {
            'id': file.id,
            'filename': file.original_filename,
            'file_type': file.file_type,
            'file_format': file.file_format,
            'file_size': file.file_size,
            'file_size_mb': file.file_size_mb,
            'is_plagiarism_report': file.is_plagiarism_report,
            'file_icon': file.file_icon,
            'description': file.description,
            'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None
        }


@login_required
def get_my_completed_orders():
    """API endpoint to get client's completed orders"""
    if current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    result = ClientResultsService.get_client_completed_orders(
        client_id=current_user.id, 
        page=page, 
        per_page=per_page
    )
    
    status_code = 200 if result['success'] else 400
    return jsonify(result), status_code


@login_required
def get_order_for_review(order_id):
    """API endpoint to get order details for review"""
    if current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    result = ClientResultsService.get_order_details_for_review(
        order_id=order_id, 
        client_id=current_user.id
    )
    
    status_code = 200 if result['success'] else 404
    return jsonify(result), status_code

# @results_services_bp.route("/download/files/<int:file_id>")
# @login_required
# def download_delivery_file(file_id):
#     """API endpoint to download delivery file"""
#     if current_user.is_admin:
#         return jsonify({'success': False, 'message': 'Access denied'}), 403
    
#     result = ClientResultsService.download_delivery_file(
#         file_id=file_id, 
#         client_id=current_user.id
#     )
    
#     if not result['success']:
#         return jsonify(result), 404
    
#     try:
#         return send_file(
#             result['file_path'],
#             as_attachment=True,
#             download_name=result['filename']
#         )
#     except Exception as e:
#         logger.error(f"Error sending file: {str(e)}")
#         return jsonify({'success': False, 'message': 'Failed to send file'}), 500

@results_services_bp.route("/revision-request/<int:order_id>", methods=['POST'])
@login_required
def request_order_revision(order_id):
    """API endpoint to request order revision"""
    if current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    revision_notes = data.get('revision_notes', '') if data else ''
    
    result = ClientResultsService.request_revision(
        order_id=order_id, 
        client_id=current_user.id, 
        revision_notes=revision_notes
    )
    
    status_code = 200 if result['success'] else 400
    return jsonify(result), status_code

@results_services_bp.route("/accept/<int:order_id>")
@login_required
def accept_order_delivery(order_id):
    """API endpoint to accept order delivery"""
    if current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    feedback = data.get('feedback', '') if data else ''
    
    result = ClientResultsService.accept_delivery(
        order_id=order_id, 
        client_id=current_user.id, 
        feedback=feedback
    )
    
    status_code = 200 if result['success'] else 400
    return jsonify(result), status_code


@login_required
def get_order_delivery_history(order_id):
    """API endpoint to get order delivery history"""
    if current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    result = ClientResultsService.get_order_delivery_history(
        order_id=order_id, 
        client_id=current_user.id
    )
    
    status_code = 200 if result['success'] else 400
    return jsonify(result), status_code


from werkzeug.utils import secure_filename
import mimetypes

@results_services_bp.route('/orders/<int:order_id>/delivery-files', methods=['GET'])
@login_required
def get_order_delivery_files(order_id):
    """
    Fetch all delivery files for a specific order
    Returns JSON with delivery information and files
    """
    try:
        # Get the order and verify access permissions
        order = Order.query.get_or_404(order_id)
        
        # Check if user has permission to view this order
        # Client can only view their own orders, admin can view all
        if not current_user.is_admin and order.client_id != current_user.id:
            return jsonify({'error': 'Unauthorized access'}), 403
        
        # Get all deliveries for this order, ordered by most recent first
        deliveries = OrderDelivery.query.filter_by(order_id=order_id)\
                                      .order_by(OrderDelivery.delivered_at.desc())\
                                      .all()
        
        if not deliveries:
            return jsonify({
                'success': True,
                'message': 'No deliveries found for this order',
                'deliveries': []
            }), 200
        
        # Format delivery data
        deliveries_data = []
        for delivery in deliveries:
            # Get delivery files
            files_data = []
            for file in delivery.delivery_files:
                files_data.append({
                    'id': file.id,
                    'filename': file.filename,
                    'original_filename': file.original_filename,
                    'file_type': file.file_type,
                    'file_format': file.file_format,
                    'file_size_mb': file.file_size_mb,
                    'description': file.description,
                    'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None,
                    'is_plagiarism_report': file.is_plagiarism_report,
                    'file_icon': file.file_icon,
                    'download_url': f'/result-services/orders/{file.id}/download'
                })
            
            deliveries_data.append({
                'id': delivery.id,
                'delivery_status': delivery.delivery_status,
                'delivered_at': delivery.delivered_at.isoformat() if delivery.delivered_at else None,
                'client_notified': delivery.client_notified,
                'client_notified_at': delivery.client_notified_at.isoformat() if delivery.client_notified_at else None,
                'has_plagiarism_report': delivery.has_plagiarism_report,
                'delivery_files_count': delivery.delivery_files_count,
                'status_color': delivery.status_color,
                'files': files_data
            })
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_number': order.order_number,
            'deliveries': deliveries_data,
            'total_deliveries': len(deliveries)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An error occurred while fetching delivery files: {str(e)}'
        }), 500


@results_services_bp.route('/orders/<int:file_id>/download', methods=['GET'])
@login_required
def download_delivery_file(file_id):
    """
    Download a specific delivery file
    Handles individual file downloads with proper security checks
    """
    try:
        # Get the delivery file
        delivery_file = OrderDeliveryFile.query.get_or_404(file_id)
        
        # Get the associated order through the delivery relationship
        order = delivery_file.delivery.order
        
        # Check if user has permission to download this file
        # Client can only download files from their own orders, admin can download all
        if not current_user.is_admin and order.client_id != current_user.id:
            return jsonify({'error': 'Unauthorized access'}), 403
        
        # Check if file exists on disk
        file_path = os.path.abspath(delivery_file.file_path)
        print(f"Checking: {file_path}")
        print(f"Exists? {os.path.exists(file_path)}")
        if not os.path.exists(file_path):
            # print(f"File path does not exist, {delivery_file.file_path}")
            return jsonify({
                'error': 'File not found on server',
                'filename': delivery_file.file_path,
                # 'filepath': delivery_file.file_path
            }), 404
        
        # Get MIME type for the file
        mimetype = mimetypes.guess_type(delivery_file.file_path)[0]
        if not mimetype:
            mimetype = 'application/octet-stream'
        
        # Optional: Log the download activity
        # You can add logging here if needed for audit purposes
        
        # Send the file with proper headers
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=delivery_file.original_filename,
            conditional=True  # Enable conditional requests for better performance
        )
        
    except FileNotFoundError:
        return jsonify({
            'error': 'File not found on server',
            'file_id': file_id
        }), 404
        
    except Exception as e:
        return jsonify({
            'error': f'An error occurred while downloading the file: {str(e)}',
            'file_id': file_id
        }), 500


@results_services_bp.route('/orders/<int:order_id>/delivery-files/download-all', methods=['GET'])
@login_required
def download_all_delivery_files(order_id):
    """
    Download all delivery files for an order as a ZIP archive
    Useful when there are multiple files to download
    """
    try:
        import zipfile
        import tempfile
        from datetime import datetime
        
        # Get the order and verify access permissions
        order = Order.query.get_or_404(order_id)
        
        # Check permissions
        if not current_user.is_admin and order.client_id != current_user.id:
            return jsonify({'error': 'Unauthorized access'}), 403
        
        # Get the latest delivery
        latest_delivery = order.latest_delivery
        if not latest_delivery or not latest_delivery.delivery_files:
            return jsonify({'error': 'No delivery files found for this order'}), 404
        
        # Create a temporary ZIP file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        try:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in latest_delivery.delivery_files:
                    if os.path.exists(file.file_path):
                        # Add file to ZIP with its original filename
                        zipf.write(file.file_path, file.original_filename)
            
            # Generate ZIP filename
            zip_filename = f"{order.order_number}_delivery_files_{datetime.now().strftime('%Y%m%d')}.zip"
            
            return send_file(
                temp_zip.name,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )
            
        finally:
            # Clean up temp file after sending (handled by Flask)
            pass
            
    except Exception as e:
        return jsonify({
            'error': f'An error occurred while creating the ZIP file: {str(e)}',
            'order_id': order_id
        }), 500
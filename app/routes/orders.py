from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, abort, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
import mimetypes
import logging
import uuid
from app.routes.main import notify
from app.extensions import db
from app.models.order import Order, OrderFile, SupportTicket
from app.models.user import User
from app.models.service import Service, AcademicLevel, Deadline
from app.routes.api import calculate_price
from app.utils.file_upload import allowed_file
import logging
import requests
from flask_wtf.csrf import generate_csrf



orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/orders')
@login_required
def order_list():
    orders = Order.query.filter_by(client_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('/orders/order.html', orders=orders, title="My Orders")

# @orders_bp.route('/create', methods=['GET', 'POST'])
# @login_required
# def create_order():
#     if request.method == 'POST':
#         try:
#             # Get form data
#             service_id = request.form.get('service')
#             academic_level_id = request.form.get('academic_level')
#             deadline_time = request.form.get('deadline')
#             title = request.form.get('title')
#             description = request.form.get('description')
#             word_count = request.form.get('word_count')
#             citation_style = request.form.get('citation_style')
#             report_type = request.form.get("report_type")
#             due_date = request.form.get('due_date')
#             if not report_type:
#                 report_type = ''
            

#             # Validate required fields
#             if not all([service_id, academic_level_id, deadline_time, title, word_count]):
#                 jsonify({'error' : 'Please fill in all required fields'})
#                 return redirect(url_for('orders.create_order'))

#             # Get related objects
#             service = Service.query.get_or_404(service_id)
#             academic_level = AcademicLevel.query.get_or_404(academic_level_id)
            
#             # Calculate price
#             page_count = (int(word_count) // 275) + 1
#             try:
#                 priceData = requests.post(url_for("api.calculate_price", params={
#                     "deadline_data" : deadline_time,
#                     "academic_level_id" : academic_level.id,
#                     "service_id": service.id,
#                     "word_count": word_count,
#                     "report_type": report_type
#                 } ))
#                 total_price = priceData["total_price"]
#                 selected_date = priceData["selected_deadline"]
#                 if selected_date:
#                     deadline = Deadline.query.get_or_404(selected_date.id)
#                 else:
#                     jsonify({'error':'Please enter a valid deadline'}), 404
#                     return redirect(url_for('orders.create_order'))
#             except Exception as e:
#                 jsonify({'error':f'Failed to fetch price: {str(e)}'}), 400
#                 return redirect(url_for('orders.create_order'))
#             if not due_date:
#                 date_due = datetime.now() + timedelta(hours=deadline.hours)
#             # Create order
#             date_due = datetime.strptime(due_date, "%Y-%m-%d, %H:%M")
#             new_order = Order(
#                 client_id=current_user.id,
#                 service_id=service.id,
#                 academic_level_id=academic_level.id,
#                 deadline_id=deadline.id,
#                 title=title,
#                 description=description,
#                 word_count=word_count,
#                 page_count=page_count,
#                 format_style=citation_style,
#                 report_type=report_type,
#                 due_date=date_due
#             )
#             try:
#                 db.session.add(new_order)
#                 db.session.commit()
#             except Exception as e:
#                 db.session.rollback()
#                 jsonify({'error':f'Database Error {str(e)}'}), 400
#                 return redirect(url_for('orders.create_order'))

#             # Handle file uploads
#             if 'files' in request.files:
#                 from flask import current_app
                
#                 for file in request.files.getlist('files'):
#                     if file and allowed_file(file.filename):
#                         filename = secure_filename(file.filename)
#                         upload_folder = current_app.config['UPLOAD_FOLDER']
#                         os.makedirs(upload_folder, exist_ok=True)
#                         file_path = os.path.join(upload_folder, filename)
#                         file.save(file_path)
                        
#                         order_file = OrderFile(
#                             order=new_order,
#                             filename=filename,
#                             file_path=file_path,
#                         )
#                         try:
#                             db.session.add(order_file)
#                         except Exception as e:
#                             db.session.rollback()
#                             jsonify({'error':f'DB Error {str(e)}'}), 400
#                             return redirect(url_for('orders.create_order'))
#             try:
#                 db.session.add(new_order)
#                 db.session.commit()
#             except Exception as e:
#                 db.session.rollback()
#                 jsonify({'error':f'DB ERROR {str(e)}'})
#                 return redirect(url_for('orders.create_order'))

#             other = User.query.filter_by(is_admin=True).first()
#             notify(current_user,
#                 title=f"You have submitted a new order. #{new_order.order_number}",
#                 message="New order created", 
#                 type='info', 
#                 link=url_for('orders.order_detail', order_number=new_order.order_number))
#             notify(other,
#                 title=f"New order. #{new_order.order_number} submitted by {current_user.get_name()}",
#                 message="New order created", 
#                 type='info', 
#                 link=url_for('admin.view_order', order_id=new_order.id))

#             jsonify({'success':'Order created successfully! Proceed to payment.'})
#             return redirect(url_for('payment.payment_page', order_number=new_order.order_number))

#         except Exception as e:
#             db.session.rollback()
#             import logging
#             logging.error(f'Order creation error: {str(e)}', exc_info=True)
#             flash('Error creating order. Please try again.', 'danger')
#             return redirect(url_for('orders.create_order'))
#     elif request.method == "GET":
#         try:
#             # GET request - show form
#             services = Service.query.all()
#             services_data = [service.to_dict() for service in services]
#             academic_levels = AcademicLevel.query.order_by(AcademicLevel.order).all()
#             levels_data = [level.to_dict() for level in academic_levels]
#             deadlines = Deadline.query.order_by(Deadline.order).all()
#             deadline_data = [deadline.to_dict() for deadline in deadlines]
#             template_vars = {
#                 'services': services_data,
#                 'academic_levels': levels_data,
#                 'deadlines': deadline_data,
#                 'title': "Place Order"
#             }

#             if request.args:
#                 service_id = request.args.get('service_id')
#                 due_date = request.args.get('due_date')
#                 deadline_id = request.args.get('deadline_id')
#                 academic_level_id = request.args.get('academic_level_id')
#                 word_cnt = request.args.get('word_count')
#                 pages = request.args.get('pages')
#                 total_price = request.args.get('total_price').replace('$', '')
#                 selected_service = None
#                 selected_academic_level = None
#                 selected_deadline = None
#                 if service_id:
#                     selected_service = Service.query.get(service_id)
#                     if selected_service:
#                         template_vars['selected_service'] = selected_service.to_dict()

#                 if academic_level_id:
#                     selected_academic_level = AcademicLevel.query.get(academic_level_id)
#                     if selected_academic_level:
#                         template_vars['selected_academic_level'] = selected_academic_level.to_dict()

#                 if deadline_id:
#                     selected_deadline = Deadline.query.get(deadline_id)
#                     if selected_deadline:
#                         template_vars['selected_deadline'] = selected_deadline.to_dict()

#                 # Add pre-population data
#                 if word_cnt:
#                     template_vars['word_count'] = int(word_cnt)
#                 if pages:
#                     template_vars['pages'] = int(pages)
#                 if total_price:
#                     template_vars['total_price'] = float(total_price)
#                 if due_date:
#                     template_vars['due_date'] = due_date

#                 # Update title for completion flow
#                 template_vars['title'] = "Complete Order"

#             return render_template('orders/order.html', **template_vars)
#         except Exception as e:
#             db.session.rollback()
#             import logging
#             logging.error(f'Order completion redirect error: {str(e)}', exc_info=True)
#             jsonify({'error' :'Error redirecting to order page. Please try again.'})
#             return redirect(url_for('orders.create_order'))



def detect_file_type(file):
    """
    Detect if uploaded file is a picture or regular file
    Returns 'picture' or 'file'
    """
    # Get MIME type from the file
    mime_type, _ = mimetypes.guess_type(file.filename)
    
    # Check if it's an image MIME type
    if mime_type and mime_type.startswith('image/'):
        return 'picture'
    
    # Alternative: Check by file extension (more reliable for some cases)
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico'}
    file_ext = os.path.splitext(file.filename.lower())[1]
    
    if file_ext in image_extensions:
        return 'picture'
    
    return 'file'

def validate_file_size(file, max_size_mb=50):
    """
    Validate file size
    Returns True if valid, False otherwise
    """
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_size_bytes

# Updated file validation in your route
def validate_uploaded_files():
    """
    Validate all uploaded files
    Returns (is_valid, error_message, validated_files)
    """
    uploaded_files = request.files.getlist('files') if 'files' in request.files else []
    validated_files = []
    
    for file in uploaded_files:
        if file and file.filename:
            # Check file size first (50MB limit)
            if not validate_file_size(file, max_size_mb=50):
                return False, f'File too large (max 50MB): {file.filename}', []
            
            # Detect file type
            file_type = detect_file_type(file)
            
            # Check if file type is allowed
            if not allowed_file(file.filename, type=file_type):
                return False, f'File type not allowed: {file.filename}', []
            
            validated_files.append((file, file_type))
    
    return True, None, validated_files


@orders_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_order():
    if request.method == 'POST':
        # try:
        #     # Get form data
        #     # csrf_token = generate_csrf()
        #     service_id = request.form.get('service')
        #     academic_level_id = request.form.get('academic_level')
        #     deadline_time = request.form.get('deadline')
        #     title = request.form.get('title')
        #     description = request.form.get('description')
        #     word_count = request.form.get('word_count')
        #     citation_style = request.form.get('citation_style')
        #     report_type = request.form.get("report_type")
        #     due_date = request.form.get('due_date')
            
        #     if not report_type:
        #         report_type = ''

        #     # Validate required fields
        #     if not all([service_id, academic_level_id, deadline_time, title, word_count]):
        #         flash('Please fill in all required fields', 'danger')
        #         return redirect(url_for('orders.create_order'))

        #     # Get related objects
        #     try:
        #         service = Service.query.get_or_404(service_id)
        #         academic_level = AcademicLevel.query.get_or_404(academic_level_id)
        #     except Exception as e:
        #         flash('Invalid service or academic level selected', 'danger')
        #         return redirect(url_for('orders.create_order'))
            
        #     # Calculate price
        #     page_count = (int(word_count) // 275) + 1
        #     try:
        #         # # Fix API call - use proper JSON data
        #         # price_data = {
        #         #     "deadline_data": deadline_time,
        #         #     "academic_level_id": academic_level.id,
        #         #     "service_id": service.id,
        #         #     "word_count": word_count,
        #         #     "report_type": report_type
        #         # }
                
        #         # response = requests.post(
        #         #     url_for("api.calculate_price", _external=True), 
        #         #     json=price_data,
        #         #     headers={'X-CSRFToken': csrf_token}
        #         # )
                
        #         # if response.status_code != 200:
        #         #     flash('Failed to calculate price. Please try again.', 'danger')
        #         #     return redirect(url_for('orders.create_order'))
                
        #         # price_result = response.json()
        #         from app.routes.api import calculate_price_internal  
                
        #         price_result = calculate_price_internal(
        #             service_id=service.id,
        #             academic_level_id=academic_level.id,
        #             hours_until_deadline=float(deadline_time),
        #             word_count=int(word_count),
        #             report_type=report_type
        #         )
        #         total_price = price_result.get("total_price")
        #         selected_date = price_result.get("selected_deadline")
                
        #         if selected_date and selected_date.get('id'):
        #             deadline = Deadline.query.get_or_404(selected_date['id'])
        #         else:
        #             flash('Please enter a valid deadline', 'danger')
        #             return redirect(url_for('orders.create_order'))
                    
        #     except Exception as e:
        #         flash(f'Failed to fetch price: {str(e)}', 'danger')
        #         return redirect(url_for('orders.create_order'))

        #     # Handle due_date logic properly
        #     if due_date:
        #         try:
        #             date_due = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        #         except ValueError:
        #             try:
        #                 # Try alternative format
        #                 date_due = datetime.strptime(due_date, "%Y-%m-%d, %H:%M")
        #             except ValueError:
        #                 flash('Invalid due date format', 'danger')
        #                 return redirect(url_for('orders.create_order'))
        #     else:
        #         date_due = datetime.now() + timedelta(hours=deadline.hours)

        #     # Create order
        #     order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        #     new_order = Order(
        #         order_number=order_number,
        #         client_id=current_user.id,
        #         service_id=service.id,
        #         academic_level_id=academic_level.id,
        #         deadline_id=deadline.id,
        #         title=title,
        #         description=description,
        #         word_count=word_count,
        #         page_count=page_count,
        #         total_price=total_price,
        #         format_style=citation_style,
        #         report_type=report_type,
        #         due_date=date_due
        #     )

        #     # Add order to database
        #     db.session.add(new_order)
        #     db.session.flush()  
            

        #     # Handle file uploads
        #     if 'files' in request.files:
        #         from flask import current_app
                
        #         for file in request.files.getlist('files'):
        #             if file and file.filename and allowed_file(file.filename):
        #                 filename = secure_filename(file.filename)
        #                 upload_folder = current_app.config['UPLOAD_FOLDER']
        #                 os.makedirs(upload_folder, exist_ok=True)
        #                 file_path = os.path.join(upload_folder, filename)
        #                 file.save(file_path)
                        
        #                 order_file = OrderFile(
        #                     order_id=new_order.id,
        #                     filename=filename,
        #                     file_path=file_path,
        #                 )
        #                 db.session.add(order_file)

        #     # Commit all changes
        #     db.session.commit()

        #     # Send notifications
        #     try:
        #         admin_user = User.query.filter_by(is_admin=True).first()
                
        #         notify(current_user,
        #             title=f"You have submitted a new order. #{new_order.order_number}",
        #             message="New order created", 
        #             type='info', 
        #             link=url_for('orders.order_detail', order_number=new_order.order_number))
                
        #         if admin_user:
        #             notify(admin_user,
        #                 title=f"New order. #{new_order.order_number} submitted by {current_user.get_name()}",
        #                 message="New order created", 
        #                 type='info', 
        #                 link=url_for('admin.view_order', order_id=new_order.id))
        #     except Exception as e:
        #         # Log notification errors but don't fail the order creation
        #         import logging
        #         logging.warning(f'Notification error: {str(e)}')

        #     flash('Order created successfully! Confirm the details before proceeding.', 'success')
        #     return redirect(url_for('order_activities.order_activities', order_id=new_order.id))

        # except Exception as e:
        #     db.session.rollback()
        #     import logging
        #     logging.error(f'Order creation error: {str(e)}', exc_info=True)
        #     flash('Error creating order. Please try again.', 'danger')
        #     return redirect(url_for('orders.create_order'))
        if request.method == 'POST':
            try:
                # Get and validate form data
                service_id = request.form.get('service')
                academic_level_id = request.form.get('academic_level')
                deadline_time = request.form.get('deadline')
                title = request.form.get('title')
                description = request.form.get('description')
                word_count = request.form.get('word_count')
                citation_style = request.form.get('citation_style')
                report_type = request.form.get("report_type", '')
                due_date = request.form.get('due_date')

                # Validate required fields
                if not all([service_id, academic_level_id, deadline_time, title, word_count]):
                    flash('Please fill in all required fields', 'danger')
                    return redirect(url_for('orders.create_order'))

                # Validate file uploads before processing
                # uploaded_files = request.files.getlist('files') if 'files' in request.files else []
                # validated_files = []
                
                # for file in uploaded_files:
                #     if file and file.filename:
                #         # if not allowed_file(file.filename):
                #         #     flash(f'File type not allowed: {file.filename}', 'danger')
                #         #     return redirect(url_for('orders.create_order'))
                        
                #         # Check file size (example: 10MB limit)
                #         file.seek(0, 2)  # Seek to end
                #         file_size = file.tell()
                #         file.seek(0)  # Reset to beginning
                        
                #         if file_size > 10 * 1024 * 1024:  # 10MB
                #             flash(f'File too large: {file.filename}', 'danger')
                #             return redirect(url_for('orders.create_order'))
                        
                #         validated_files.append(file)
                is_valid, error_message, validated_files = validate_uploaded_files()
                if not is_valid:
                    flash(error_message, 'danger')
                    return redirect(url_for('orders.create_order'))

                # Start transaction
                try:
                    # Get related objects
                    service = Service.query.get_or_404(service_id)
                    academic_level = AcademicLevel.query.get_or_404(academic_level_id)
                    
                    # Calculate price
                    page_count = (int(word_count) // 275) + 1
                    
                    from app.routes.api import calculate_price_internal  
                    price_result = calculate_price_internal(
                        service_id=service.id,
                        academic_level_id=academic_level.id,
                        hours_until_deadline=float(deadline_time),
                        word_count=int(word_count),
                        report_type=report_type
                    )
                    
                    total_price = price_result.get("total_price")
                    selected_date = price_result.get("selected_deadline")
                    
                    if not selected_date or not selected_date.get('id'):
                        flash('Please enter a valid deadline', 'danger')
                        return redirect(url_for('orders.create_order'))
                    
                    deadline = Deadline.query.get_or_404(selected_date['id'])

                    # Handle due_date
                    if due_date:
                        try:
                            date_due = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
                        except ValueError:
                            try:
                                date_due = datetime.strptime(due_date, "%Y-%m-%d, %H:%M")
                            except ValueError:
                                flash('Invalid due date format', 'danger')
                                return redirect(url_for('orders.create_order'))
                    else:
                        date_due = datetime.now() + timedelta(hours=deadline.hours)

                    # Create order
                    order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                    new_order = Order(
                        order_number=order_number,
                        client_id=current_user.id,
                        service_id=service.id,
                        academic_level_id=academic_level.id,
                        deadline_id=deadline.id,
                        title=title,
                        description=description,
                        word_count=word_count,
                        page_count=page_count,
                        total_price=total_price,
                        format_style=citation_style,
                        report_type=report_type,
                        due_date=date_due
                    )

                    db.session.add(new_order)
                    db.session.flush()  # Get the order ID

                    # Handle file uploads with proper error handling
                    saved_files = []  # Track saved files for cleanup on error
                    
                    for file, file_type in validated_files:
                        try:
                            filename = secure_filename(file.filename)
                            # Add timestamp to prevent filename conflicts
                            name, ext = os.path.splitext(filename)
                            unique_filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
                            
                            upload_folder = current_app.config['UPLOAD_FOLDER']
                            os.makedirs(upload_folder, exist_ok=True)
                            file_path = os.path.join(upload_folder, unique_filename)
                            
                            file.save(file_path)
                            saved_files.append(file_path)  # Track for cleanup
                            
                            order_file = OrderFile(
                                order_id=new_order.id,
                                filename=unique_filename,
                                file_path=file_path,
                            )
                            db.session.add(order_file)
                            
                        except Exception as file_error:
                            # Clean up any files saved so far
                            for saved_file in saved_files:
                                try:
                                    if os.path.exists(saved_file):
                                        os.remove(saved_file)
                                except:
                                    pass
                            raise Exception(f"File upload failed for {file.filename}: {str(file_error)}")

                    # Commit transaction
                    db.session.commit()
                    
                    # Send notifications (after successful commit)
                    try:
                        admin_user = User.query.filter_by(is_admin=True).first()
                        
                        notify(current_user,
                            title=f"You have submitted a new order. #{new_order.order_number}",
                            message="New order created", 
                            type='info', 
                            link=url_for('orders.order_detail', order_number=new_order.order_number))
                        
                        if admin_user:
                            notify(admin_user,
                                title=f"New order. #{new_order.order_number} submitted by {current_user.get_name()}",
                                message="New order created", 
                                type='info', 
                                link=url_for('admin.view_order', order_id=new_order.id))
                    except Exception as notification_error:
                        # Log but don't fail the order
                        import logging
                        logging.warning(f'Notification error: {str(notification_error)}')

                    flash('Order created successfully! Confirm the details before proceeding.', 'success')
                    return redirect(url_for('order_activities.order_activities', order_id=new_order.id))

                except Exception as e:
                    db.session.rollback()
                    import logging
                    logging.error(f'Order creation error: {str(e)}', exc_info=True)
                    flash('Error creating order. Please try again.', 'danger')
                    return redirect(url_for('orders.create_order'))

            except Exception as e:
                import logging
                logging.error(f'Order form processing error: {str(e)}', exc_info=True)
                flash('Error processing form. Please try again.', 'danger')
                return redirect(url_for('orders.create_order'))

    elif request.method == "GET":
        try:
            # GET request - show form
            services = Service.query.all()
            services_data = [service.to_dict() for service in services]
            academic_levels = AcademicLevel.query.order_by(AcademicLevel.order).all()
            levels_data = [level.to_dict() for level in academic_levels]
            deadlines = Deadline.query.order_by(Deadline.order).all()
            deadline_data = [deadline.to_dict() for deadline in deadlines]
            
            template_vars = {
                'services': services_data,
                'academic_levels': levels_data,
                'deadlines': deadline_data,
                'title': "Place Order"
            }

            # Handle query parameters for pre-population
            if request.args:
                service_id = request.args.get('service_id')
                due_date = request.args.get('due_date')
                # deadline_id = request.args.get('deadline_id')
                deadline_data = request.args.get('deadline')
                academic_level_id = request.args.get('academic_level_id')
                word_cnt = request.args.get('word_count')
                pages = request.args.get('pages')
                # total_price = request.args.get('total_price')
                
                # if total_price:
                #     total_price = total_price.replace('$', '')
                
                # Get selected objects
                if service_id:
                    selected_service = Service.query.get(service_id)
                    if selected_service:
                        template_vars['selected_service'] = selected_service.to_dict()

                if academic_level_id:
                    selected_academic_level = AcademicLevel.query.get(academic_level_id)
                    if selected_academic_level:
                        template_vars['selected_academic_level'] = selected_academic_level.to_dict()

                if deadline_data and float(deadline_data) > 3:
                    # if deadline_data > 3:
                    template_vars['hoursUntilDeadline'] = deadline_data

                # Add pre-population data with proper type conversion
                if word_cnt:
                    try:
                        template_vars['word_count'] = int(word_cnt)
                    except (ValueError, TypeError):
                        pass
                        
                if pages:
                    try:
                        template_vars['pages'] = int(pages)
                    except (ValueError, TypeError):
                        pass
                            
                if due_date:
                    template_vars['due_date'] = due_date

                # Update title for completion flow
                template_vars['title'] = "Complete Order"

            return render_template('orders/order.html', **template_vars)
            
        except Exception as e:
            import logging
            logging.error(f'Order form display error: {str(e)}', exc_info=True)
            flash('Error loading order page. Please try again.', 'danger')
            return redirect(url_for('client.dashboard'))  


@orders_bp.route('/<order_number>')
@login_required
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number, client_id=current_user.id).first_or_404()
    days_remaining = (order.due_date - datetime.now()).days
    return render_template('orders/order_detail.html', order=order, days_remaining=days_remaining, datetime=datetime, timedelta=timedelta)

@orders_bp.route('/files/<int:file_id>/download')
@login_required
def download_file(file_id):
    # Retrieve the file record or 404
    order_file = OrderFile.query.get_or_404(file_id)
    # Ensure the associated order belongs to the logged-in user
    order = Order.query.get_or_404(order_file.order_id)
    if order.client_id != current_user.id:
        abort(403)

    # Determine file path
    file_path = order_file.file_path
    if not file_path or not os.path.isfile(file_path):
        abort(404)

    # Send the file as an attachment
    directory, filename = os.path.split(file_path)
    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        attachment_filename=order_file.filename
    )

@orders_bp.route('/support/<int:order_id>', methods=['POST'])
@login_required
def support_ticket(order_id):
    order = Order.query.get_or_404(order_id)
    if order.client_id != current_user.id:
        abort(403)

    # Extract form data
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()

    # Validate input
    if not subject or not message:
        flash('Subject and message are required to submit a support ticket.', 'warning')
        return redirect(url_for('orders.order_detail', order_number=order.order_number))

    # Create and save the support ticket
    ticket = SupportTicket(
        order_id=order.id,
        user_id=current_user.id,
        subject=subject,
        message=message
    )
    db.session.add(ticket)
    db.session.commit()

    flash('Your support ticket has been submitted successfully.', 'success')
    return redirect(url_for('orders.order_detail', order_number=order.order_number))

# routes/order_routes.py (add this to your existing order routes)

# @orders_bp.route('/order/<int:order_id>/activities')
# @login_required
# def order_activities(order_id):
#     """Display order activities page"""
#     order = Order.query.filter_by(id=order_id, client_id=current_user.id).first_or_404()
    
#     # Ensure all relationships are loaded
#     order.files
#     order.deliveries
#     order.comments
#     order.payments
    
#     return render_template('orders/order_activities.html', order=order)
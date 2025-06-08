from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models.blog import BlogPost, BlogCategory
from app.models.service import ServiceCategory, Service
from app.models.content import Sample, Testimonial, FAQ
from app.models.communication import ContactMessage, NewsletterSubscriber, Notification
from app.models.service import AcademicLevel, Deadline
from app.models.price import PriceRate, PricingCategory
import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    services = Service.query.all()
    categories = ServiceCategory.query.all()
    testimonials = Testimonial.query.filter_by(is_approved=True).all()
    samples = Sample.query.filter_by(featured=True).all()
    # deadlines = Deadline.query.all()
    # academic_levels = AcademicLevel.query.all()
    # pricing_categories = PricingCategory.query.all()
    # writing_services = []
    # proofreading_services = []
    # technical_services = []
    # humanizing_ai_service = []
    # for service in services:
    #     if service.pricing_category_id == 1:
    #         writing_services.append(service)
    #     elif service.pricing_category_id == 2:
    #         proofreading_services.append(service)
    #     elif service.pricing_category_id == 3:
    #         technical_services.append(service)
    #     elif service.pricing_category_id == 4:
    #         humanizing_ai_service.append(service)

    
    # today = datetime.date.today()
    # formatted_date = today.strftime("%d-%m-%Y")
    return render_template('home.html', 
                          featured_services=services,
                        #   pricing_category=pricing_categories,
                        #   writing_services=writing_services,
                        #   proofreading_services=proofreading_services,
                        #   technical_services=technical_services,
                        #   humanizing_ai_services=humanizing_ai_service,
                          categories=categories,
                          testimonials=testimonials,
                          samples=samples,
                        #   academic_levels=academic_levels,
                        #   deadlines=deadlines,
                        #   pricing_matrix=pricing_matrix,
                          title="Academic Writing Services")

@main_bp.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.home'))
    
    # Search for services that match the query
    services = Service.query.filter(Service.name.ilike(f'%{query}%')).all()
    
    # Search for categories that match the query
    categories = ServiceCategory.query.filter(ServiceCategory.name.ilike(f'%{query}%')).all()
    blogs = BlogPost.query.filter(BlogPost.title.ilike(f'%{query}%')).all()
    blog_categories = BlogCategory.query.filter(BlogCategory.name.ilike(f'%{query}%')).all()
    
    return render_template('search_results.html',
                          services=services,
                          categories=categories,
                          blogs=blogs,
                          blog_categories=blog_categories,
                          query=query,
                          title=f"Search Results for '{query}'")

@main_bp.route('/services')
def services():
    categories = ServiceCategory.query.all()
    return render_template('services.html', 
                          categories=categories, 
                          title="Our Services")

@main_bp.route('/service/<int:service_id>')
def service_detail(service_id):
    service = Service.query.get_or_404(service_id)
    academic_levels = AcademicLevel.query.order_by("order" )
    return render_template('service_detail.html', 
                           service=service,
                           academic_levels=academic_levels)

@main_bp.route('/about')
def about():
    return render_template('about.html', title="About Us")

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Save the message to the database
        contact_message = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        db.session.add(contact_message)
        db.session.commit()

        flash('Thank you for your message! We will contact you shortly.', 'success')
        return redirect(url_for('main.contact'))

    return render_template('contact.html', title="Contact Us")

@main_bp.route('/samples')
def samples():
    samples = Sample.query.all()
    services = Service.query.all()

    return render_template('samples.html', 
                          samples=samples, 
                          services=services,
                          title="Sample Papers")

@main_bp.route('/samples/<int:sample_id>')
def sample_detail(sample_id):
    sample = Sample.query.get_or_404(sample_id)

    return render_template('sample_detail.html', 
                          sample=sample,
                          title=sample.title)

@main_bp.route('/testimonials')
def testimonials():
    testimonials = Testimonial.query.filter_by(is_approved=True).all()

    return render_template('testimonials.html', 
                          testimonials=testimonials,
                          title="Client Testimonials")

@main_bp.route('/testimonials/submit', methods=['GET', 'POST'])
def submit_testimonial():
    if request.method == 'POST':
        client_name = request.form.get('client_name')
        service_id = request.form.get('service_id')
        content = request.form.get('content')
        rating = request.form.get('rating')

        # Save the testimonial to the database
        testimonial = Testimonial(
            client_name=client_name,
            service_id=service_id,
            content=content,
            rating=int(rating),
            is_approved=False  # Testimonials need approval before being displayed
        )
        db.session.add(testimonial)
        db.session.commit()

        flash('Thank you for your testimonial! It will be displayed after review.', 'success')
        return redirect(url_for('main.testimonials'))

    services = Service.query.all()
    return render_template('submit_testimonial.html', 
                          services=services,
                          title="Submit Testimonial")

@main_bp.route('/faq')
def faq():
    faqs = FAQ.query.order_by(FAQ.category, FAQ.order).all()
    # Group FAQs by category
    faq_categories = {}
    for faq in faqs:
        if faq.category not in faq_categories:
            faq_categories[faq.category] = []
        faq_categories[faq.category].append(faq)

    return render_template('faq.html', 
                          faq_categories=faq_categories,
                          title="Frequently Asked Questions")

@main_bp.route('/legal/terms')
def terms():
    return render_template('legal/terms.html', title="Terms of Service")

@main_bp.route('/legal/privacy')
def privacy():
    return render_template('legal/privacy.html', title="Privacy Policy")

@main_bp.route('/legal/refund')
def refund():
    return render_template('legal/refund.html', title="Refund Policy")

@main_bp.route('/newsletter/subscribe', methods=['POST'])
def newsletter_subscribe():
    email = request.form.get('email')
    name = request.form.get('name', '')

    # Check if already subscribed
    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.session.commit()
            flash('You have been resubscribed to our newsletter!', 'success')
        else:
            flash('You are already subscribed to our newsletter!', 'info')
    else:
        # Add new subscriber
        subscriber = NewsletterSubscriber(email=email, name=name)
        db.session.add(subscriber)
        db.session.commit()
        flash('Thank you for subscribing to our newsletter!', 'success')

    return redirect(request.referrer or url_for('main.home'))

def notify(user, title, message, type='info', link=None):
    n = Notification(user_id=user.id, title=title, message=message, type=type, link=link)
    db.session.add(n)
    db.session.commit()
    return n


from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError

def init_db(app, db):
    """Initialize database with default data if empty"""
    # Import models
    from app.models.user import User
    from app.models.service import Service, ServiceCategory, AcademicLevel, Deadline
    from app.models.order import Order, OrderComment, OrderFile
    from app.models.payment import Payment, Invoice, Transaction, Refund, Discount
    from app.models.referral import Referral
    from app.models.tools import PlagiarismCheck, CitationGenerator, ChatMessage
    from app.models.content import Testimonial, Sample, FAQ
    from app.models.blog import BlogPost, BlogCategory, BlogComment
    from app.models.communication import ContactMessage, Notification, Chat
    from app.models.price import PricingCategory, PriceRate
    
    # Check if admin exists
    admin_exists = User.query.filter_by(is_admin=True).first()
    if not admin_exists:
        try:
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=generate_password_hash("admin123"),  # Change this password!
                first_name="Admin",
                last_name="User",
                gender="male",
                is_admin=True,
                email_verified=True  # Skip verification for admin
            )
            user1 = User(
                username="johndoe",
                email="john@example.com",
                password_hash=generate_password_hash("johnpassword"),
                first_name="John",
                last_name="Doe",
                gender="male",
                is_admin=False,
                email_verified=True
            )

            user2 = User(
                username="janedoe",
                email="jane@example.com",
                password_hash=generate_password_hash("janepassword"),
                first_name="Jane",
                last_name="Doe",
                gender="female",
                is_admin=False,
                email_verified=True
            )
            db.session.add_all([admin, user1, user2])
            db.session.commit()
            app.logger.info("--- ADMIN AND TEST USERS CREATED ---")

            academic_levels = [
                AcademicLevel(name="High School", order=1),
                AcademicLevel(name="Undergraduate", order=2),
                AcademicLevel(name="Personal", order=3),
                AcademicLevel(name="Master's", order=4),
                AcademicLevel(name="Doctorate", order=6),
                AcademicLevel(name="Professional", order=7)
            ]
            
            db.session.add_all(academic_levels)

            # Add deadlines
            deadlines = [
                Deadline(name="3 Hours", hours=3, order=1),
                Deadline(name="6 Hours", hours=6, order=2),
                Deadline(name="12 Hours", hours=12, order=3),
                Deadline(name="24 Hours", hours=24, order=4),
                Deadline(name="48 Hours", hours=48, order=5),
                Deadline(name="3 Days", hours=72, order=6),
                Deadline(name="7 Days", hours=168, order=7),
                Deadline(name="10 Days", hours=240, order=8),
                Deadline(name="14 Days", hours=336, order=9),
                Deadline(name="20 Days", hours=400, order=10)
            ]
            db.session.add_all(deadlines)
            
            db.session.commit()
            app.logger.info("--- INITIAL SERVICE DATA CREATED ---")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating test users: {str(e)}")

    if not PricingCategory.query.first():
        # Create pricing categories
        categories = [
            PricingCategory(name="Writing", description="Standard pricing for all services.", display_order=1),
            PricingCategory(name="Proofreading & Editing", description="Premium pricing for high-demand services.", display_order=2),
            PricingCategory(name="Technical & Calculations", description="Standard pricing for all technical services.", display_order=3),
            PricingCategory(name="Humanizing AI", description="Premium pricing for high-demand services.", display_order=4)
        ]
        
        db.session.add_all(categories)
        db.session.commit()

        academic_levels = {level.name: level for level in AcademicLevel.query.all()}
        deadlines = {deadline.name: deadline for deadline in Deadline.query.all()}
        pricing_categories = {cat.name: cat for cat in PricingCategory.query.all()}


        # Create price rates
        price_rates_data = {
        "Writing" : {
            "20 Days" : [9.00, 11.00, 11.00, 13.00,	15.00, 16.50],
            "14 Days" : [9.50, 11.50, 11.50, 13.50,	15.50, 17.05],
            "10 Days" : [10.00,	12.00, 12.00, 14.00, 16.00,	17.60],
            "7 Days" : [10.50, 12.50, 12.50, 14.50,	16.50, 18.15],
            "3 Days" : [11.00, 13.00, 13.00, 15.00,	17.00, 18.70], 
            "48 Hours" : [11.25, 13.25, 13.25,	15.25,	17.25, 18.98],
            "24 Hours" : [11.50, 13.50, 13.50,	15.50, 17.50, 19.25],
            "12 Hours" : [12.00, 14.00, 14.00, 16.00, 18.00, 19.80],
            "6 Hours" : [12.25,	14.25, 14.25, 16.25, 18.25,	20.08],
            "3 Hours" : [12.50,	14.50, 14.50, 16.50, 18.50,	20.35]
        },
        
        "Proofreading & Editing" : {
            "20 Days" : [3.00, 5.00, 5.00, 7.00, 9.00, 9.90],
            "14 Days" : [3.50, 5.50, 5.50, 7.50, 9.50, 10.45],
            "10 Days" : [4.00, 6.00, 6.00, 8.00, 10.00, 11.00],
            "7 Days": [4.50, 6.50, 6.50, 8.50,	10.50, 11.55],
            "3 Days" : [5.00, 7.00,	7.00, 9.00,	11.00, 12.10],
            "48 Hours" : [5.25,	7.25, 7.25,	9.25, 11.25, 12.38],
            "24 Hours" : [5.50, 7.50, 7.50,	9.50, 11.50, 12.65], 
            "12 Hours" : [6.00,	8.00, 8.00,	10.00, 12.00, 13.20],
            "6 Hours" : [6.25, 8.25, 8.25, 10.25, 12.25, 13.48],
            "3 Hours" : [6.50, 8.50, 8.50, 10.50, 12.50, 13.75]
        },
        "Technical & Calculations" : {
            "20 Days" : [15.00, 7.00, 7.00,	9.00, 11.00, 12.10],
            "14 Days" : [15.50, 7.50, 7.50, 9.50, 11.50,	12.65],
            "10 Days" : [16.00, 8.00, 8.00, 10.00, 12.00, 13.20],
            "7 Days" : [16.50, 8.50,	8.50, 10.50, 12.50,	13.75],
            "3 Days" : [17.00, 9.00,	9.00, 11.00, 13.00,	14.30],
            "48 Hours" : [17.25, 9.25, 9.25, 11.25, 13.25, 14.58],
            "24 Hours" : [17.50, 9.50, 9.50, 11.50, 13.50, 14.85],
            "12 Hours" : [18.00, 10.00, 10.00, 12.00, 14.00, 15.40],
            "6 Hours" : [18.25, 10.25, 10.25, 12.25, 14.25, 15.68],
            "3 Hours" : [18.50, 10.50, 10.50, 12.50, 14.50, 15.95]
        },
        "Humanizing AI" : {
            "20 Days" : [15.00,	22.00, 22.00, 30.00, 40.00,	44.00],
            "14 Days" : [15.50,	22.50, 22.50, 30.50,  40.50, 44.55],
            "10 Days" : [16.00,	23.00, 23.00, 31.00, 41.00,	45.10],
            "7 Days" : [16.50, 23.50, 23.50, 31.50,	41.50, 45.65],
            "3 Days" : [17.00, 24.00, 24.00, 32.00,	42.00, 46.20],
            "48 Hours" : [17.25, 24.25,	24.25, 32.25, 42.25, 46.48],
            "24 Hours" : [17.50, 24.50,	24.50, 32.50, 42.50, 46.75],
            "12 Hours" : [18.00, 25.00,	25.00, 33.00, 43.00, 47.30],
            "6 Hours" : [18.25,	25.25, 25.25, 33.25, 43.25,	47.58],
            "3 Hours" : [18.50,	25.50, 25.50, 33.50, 43.50,	47.85]
        }}
        
        level_names = [
            "High School", 
            "Undergraduate", 
            "Personal", 
            "Master's", 
            "Doctorate", 
            "Professional"
        ]

        # for category, price_rates in category_price_rates:
        #     for deadline_name, prices in price_rates.items():
        #         # Check if deadline exists
        #         if deadline_name not in deadlines:
        #             app.logger.error(f"Deadline '{deadline_name}' not found. Skipping...")
        #             continue
        #         deadline = deadlines[deadline_name]
        #         # Iterate over each academic level and corresponding price
        #         for i, level_name in enumerate(level_names):
        #             if level_name not in academic_levels:
        #                 app.logger.error(f"Academic level '{level_name}' not found. Skipping...")
        #                 continue
        #             academic_level = academic_levels[level_name]

        #             price = prices[i]
        #             price_rate = PriceRate(
        #                 pricing_category=category,
        #                 academic_level=academic_level,
        #                 deadline=deadline,
        #                 price_per_page=price
        #             )
        #             existing_rate = PriceRate.query.filter_by(
        #                 pricing_category_id=category.id,
        #                 academic_level_id=academic_level.id,
        #                 deadline_id=deadline.id
        #             ).first()

        #             if existing_rate:
        #                 continue
        #             db.session.add(price_rate)
        for category_name, deadline_data in price_rates_data.items():
            if category_name not in pricing_categories:
                app.logger.error(f"Pricing category '{category_name}' not found. Skipping...")
                continue
                
            category = pricing_categories[category_name]
            
            for deadline_name, prices in deadline_data.items():
                # Check if deadline exists
                if deadline_name not in deadlines:
                    app.logger.error(f"Deadline '{deadline_name}' not found. Skipping...")
                    continue
                    
                deadline = deadlines[deadline_name]
                
                # Iterate over each academic level and corresponding price
                for i, level_name in enumerate(level_names):
                    if level_name not in academic_levels:
                        app.logger.error(f"Academic level '{level_name}' not found. Skipping...")
                        continue
                        
                    academic_level = academic_levels[level_name]
                    
                    # Check if this price rate already exists
                    existing_rate = PriceRate.query.filter_by(
                        pricing_category_id=category.id,
                        academic_level_id=academic_level.id,
                        deadline_id=deadline.id
                    ).first()

                    if existing_rate:
                        app.logger.info(f"Price rate already exists for {category_name} - {level_name} - {deadline_name}")
                        continue
                    
                    # Get the price for this level (index i)
                    if i < len(prices):
                        price = prices[i]
                        
                        price_rate = PriceRate(
                            pricing_category_id=category.id,
                            academic_level_id=academic_level.id,
                            deadline_id=deadline.id,
                            price_per_page=price
                        )
                        db.session.add(price_rate)
                        app.logger.info(f"Created price rate: {category_name} - {level_name} - {deadline_name} = ${price}")
                    else:
                        app.logger.error(f"No price found for {category_name} - {level_name} - {deadline_name}")
        
        try:
            db.session.commit()
            app.logger.info("--- PRICING DATA CREATED ---")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating pricing data: {str(e)}")
            raise
        
    
    # Add service categories if none exist
    if not ServiceCategory.query.first():
        # Define your categories & sub-services:
        categories = {
            "Proofreading and Editing": [
                ("Proofreading",
                "Covers dissertations, theses, articles, essays, resumes, business documents & more—primarily catching any remaining errors in spelling, grammar, and punctuation before publication."),
                ("Copyediting",
                "Focuses on grammar, spelling, punctuation, consistency, clarity and adherence to style guides—improving readability and sentence structure."),
                ("AI Content Editing",
                "Removal of AI-detected content and humanization of AI-written text."),
                ("Reviewing and Rewriting Services",
                "Rewrite, review, revamp or repurpose your content—ideal for personal statements, manuscripts, plagiarism removal, and clarity."),
                ("Citation and Formatting",
                "Handles APA, MLA, Chicago, Harvard, IEEE, OSCOLA and more."),
            ],
            "Writing": [
                ("Essays",               "Custom essay writing."),
                ("Research Papers",      "In-depth academic research."),
                ("Dissertations",        "Comprehensive dissertation help."),
                ("Case Studies",         "Analytical case studies."),
                ("Courseworks",          "Well-researched coursework."),
                ("Term Papers",          "Academic term paper writing."),
                ("Admission Essays",     "Essays for college admissions."),
                ("College Papers",       "Academic papers across subjects."),
                ("Annotated Bibliographies", "Annotated source lists."),
                ("Literature Review",    "Thorough source reviews."),
                ("Capstone Project",     "Final project support."),
            ],
            "Data Analysis": [
                ("SPSS",    "Statistical analysis using SPSS."),
                ("STATA",   "Econometrics and regressions."),
                ("R",       "Statistical computing with R."),
                ("NVivo",   "Qualitative analysis with NVivo."),
                ("Excel",   "Data modelling and visualization."),
                ("Python",  "Python-based data science."),
                ("Power BI","Interactive dashboards."),
                ("Tableau", "Visual analytics with Tableau."),
            ],
            "Business and Market Research": [
                ("Business Plans",      "Investor-ready business plans."),
                ("Proposals",           "Professional proposals."),
                ("Grant Writing",       "Tailored grant applications."),
                ("Market Research",     "Data-driven market analysis."),
                ("Competitor Analysis", "In-depth competitor landscapes.",       ),
                ("SWOT Analysis",       "SWOT framework analysis."),
                ("PESTLE Analysis",     "Macro-environmental scan."),
            ],
            "Presentations": [
                ("PowerPoint Presentations",      "Custom PowerPoint decks."),
                ("Google Slides Presentations",   "Polished Google Slides decks."),
                ("Academic & Business Pitch Decks","High-impact pitch decks."),
            ],
            "Resume Writing": [
                ("CV & Resume Creation",           "Job-winning CVs & resumes."),
                ("Cover Letters",                  "Compelling cover letters."),
                ("LinkedIn Profile Optimization",  "LinkedIn profile makeover."),
            ],
            "Technical Writing & Calculations": [
                ("Technical reports, manuals, and documentation",
                "Detailed technical writing and documentation."),
                ("Quantitative coursework",
                "Help with Algebra, Calculus, Stats, Accounting, Finance, Engineering problems."),
            ],
        }

        # Group services into pricing categories
        service_to_pricing_category = {
            # Writing services -> "Writing" pricing category
            "Essays": "Writing",
            "Research Papers": "Writing",
            "Dissertations": "Writing",
            "Case Studies": "Writing",
            "Courseworks": "Writing",
            "Term Papers": "Writing",
            "Admission Essays": "Writing",
            "College Papers": "Writing",
            "Annotated Bibliographies": "Writing",
            "Literature Review": "Writing",
            "Capstone Project": "Writing",
            
            # Proofreading and Editing services -> "Proofreading & Editing" pricing category
            "Proofreading": "Proofreading & Editing",
            "Copyediting": "Proofreading & Editing",
            "Reviewing and Rewriting Services": "Proofreading & Editing",
            "Citation and Formatting": "Proofreading & Editing",
            
            # AI Content Editing -> "Humanizing AI" pricing category
            "AI Content Editing": "Humanizing AI",
            
            # Technical services -> "Technical & Calculations" pricing category
            "Technical reports, manuals, and documentation": "Technical & Calculations",
            "Quantitative coursework": "Technical & Calculations",
            
            # Data Analysis services -> "Technical & Calculations" pricing category
            "SPSS": "Technical & Calculations",
            "STATA": "Technical & Calculations",
            "R": "Technical & Calculations",
            "NVivo": "Technical & Calculations",
            "Excel": "Technical & Calculations",
            "Python": "Technical & Calculations",
            "Power BI": "Technical & Calculations",
            "Tableau": "Technical & Calculations",
            
            # Business and Market Research -> "Writing" pricing category
            "Business Plans": "Writing",
            "Proposals": "Writing",
            "Grant Writing": "Writing",
            "Market Research": "Writing",
            "Competitor Analysis": "Writing",
            "SWOT Analysis": "Writing",
            "PESTLE Analysis": "Writing",
            
            # Presentations -> "Writing" pricing category
            "PowerPoint Presentations": "Writing",
            "Google Slides Presentations": "Writing",
            "Academic & Business Pitch Decks": "Writing",
            
            # Resume Writing -> "Writing" pricing category
            "CV & Resume Creation": "Writing",
            "Cover Letters": "Writing",
            "LinkedIn Profile Optimization": "Writing",
        }
        
        existing_pricing_categories = {pc.name: pc for pc in PricingCategory.query.all()}
        # Insert into DB
        for cat_name, svc_list in categories.items():
            cat = ServiceCategory(name=cat_name,
                                description=f"{cat_name} services and subcategories.")
            db.session.add(cat)
            db.session.flush()  # ensure cat.id is set

            for name, desc in svc_list:
                pricing_category_name = service_to_pricing_category.get(name)
                pricing_cat_id = None
                if pricing_category_name and pricing_category_name in existing_pricing_categories:
                    pricing_cat_id = existing_pricing_categories[pricing_category_name].id
                
                svc = Service(
                    name=name,
                    description=desc,
                    category=cat,
                    featured=True,
                    tags=" ".join(name.split()),
                    pricing_category_id=pricing_cat_id
                )
                db.session.add(svc)

        # Add academic levels
        

    if not Sample.query.first():
        # Get services for sample association
        services = Service.query.all()
        service_lookup = {s.name: s for s in services}
        
        samples = [
            Sample(
                title="Edited Journal Article: Linguistic Precision in Sociolinguistics",
                content="<p>This copyedited article refines academic tone, grammar, and consistency while preserving authorial voice...</p><p>Changes adhere to APA style and enhance clarity in theoretical discussions...</p>",
                excerpt="Professional copyediting of a sociolinguistics article focusing on clarity and APA style.",
                service=service_lookup.get("Copyediting"),
                word_count=2200,
                tags="Copy-Editing, article",
                featured=True
            ),
            Sample(
                title="The Role of Civil Disobedience in Democratic Societies",
                content="<p>This essay explores the philosophical and historical implications of civil disobedience with references to Thoreau, Gandhi, and King...</p><p>The argument develops a nuanced stance on lawful protest and moral responsibility...</p>",
                excerpt="An argumentative essay on the legitimacy and legacy of civil disobedience.",
                service=service_lookup.get("Essays"),
                tags="Essay, paper-writing",
                word_count=1800,
                featured=True
            ),
            Sample(
                title="Quantitative Analysis of Student Performance using SPSS",
                content="<p>This SPSS-based research applies descriptive and inferential statistics to educational data...</p><p>Includes regression analysis, ANOVA, and reliability testing...</p>",
                excerpt="A statistical report analyzing academic performance data using SPSS.",
                service=service_lookup.get("SPSS"),
                word_count=2600,
                tags="statistics, research",
                featured=True
            )
        ]
        
        db.session.add_all(samples)
        db.session.commit()
        app.logger.info("--- SAMPLE DATA CREATED ---")
    
    # Add testimonials if none exist
    if not Testimonial.query.first():
        services = Service.query.limit(3).all()
        users = User.query.all()
        
        testimonials = [
            Testimonial(
                user_id=users[2].id,
                service=services[0],
                content="The essay I received was exceptionally well-written and delivered ahead of the deadline. The writer addressed all my requirements and provided valuable insights I hadn't considered.",
                rating=5,
                is_approved=True
            ),
            Testimonial(
                user_id=users[1].id,
                service=services[1],
                content="I was impressed by the depth of research and quality of references in my paper. The structure was logical, and the arguments were well-developed. Highly recommend!",
                rating=5,
                is_approved=True
            ),
            Testimonial(
                user_id=users[0].id,
                service=services[2],
                content="Working with this service on my dissertation was a game-changer. The writer's expertise in my subject area was evident, and they were responsive to all my feedback during the process.",
                rating=4,
                is_approved=True
            )
        ]
        
        db.session.add_all(testimonials)
        db.session.commit()
        app.logger.info("--- TESTIMONIAL DATA CREATED ---")
    
    # Add FAQ entries if none exist
    if not FAQ.query.first():
        faqs = [
            FAQ(
                question="How does the ordering process work?",
                answer="Our ordering process is simple: select the type of paper you need, specify your academic level, choose a deadline, provide your instructions, and make a payment. Once we receive your order, we'll assign it to a writer with expertise in your subject area.",
                category="Ordering",
                order=1
            ),
            FAQ(
                question="Can I communicate with my writer?",
                answer="Yes, you can communicate with your writer through our messaging system. You can provide additional instructions, ask questions, or request updates on your order's progress.",
                category="Communication",
                order=1
            ),
            FAQ(
                question="Are revisions included in the price?",
                answer="Yes, we offer free revisions within 14 days after delivery. If you need any changes to your paper, simply submit a revision request with clear instructions on what needs to be modified.",
                category="Revisions",
                order=1
            )
        ]
        
        db.session.add_all(faqs)
        db.session.commit()
        app.logger.info("--- FAQ DATA CREATED ---")
    
    # Add blog categories and posts if none exist
    if not BlogCategory.query.first():
        # Create blog categories
        categories = [
            BlogCategory(name="Academic Writing", slug="academic-writing", description="Tips and guides for academic writing"),
            BlogCategory(name="Research Methods", slug="research-methods", description="Insights into effective research methodologies"),
            BlogCategory(name="Student Life", slug="student-life", description="Advice for balancing academics and personal life")
        ]
        
        db.session.add_all(categories)
        db.session.commit()
        
        # Get admin user for blog posts
        admin_user = User.query.filter_by(is_admin=True).first()
        
        # Add blog posts
        posts = [
            BlogPost(
                title="How to Write an Effective Thesis Statement",
                slug="how-to-write-effective-thesis-statement",
                content="<p>A strong thesis statement is essential for any academic paper...</p><p>This article provides step-by-step guidance on crafting clear, concise, and compelling thesis statements...</p>",
                excerpt="Learn how to create powerful thesis statements that effectively communicate your paper's main argument.",
                author=admin_user,
                category=categories[0],
                tags="thesis statement, academic writing, essay tips",
                is_published=True,
                published_at=datetime.utcnow()
            ),
            BlogPost(
                title="Quantitative vs. Qualitative Research: Choosing the Right Approach",
                slug="quantitative-vs-qualitative-research",
                content="<p>Understanding the differences between quantitative and qualitative research is crucial for designing effective studies...</p><p>This article compares the methodologies, data collection techniques, and analysis methods of both approaches...</p>",
                excerpt="A comprehensive comparison of quantitative and qualitative research methodologies to help you choose the right approach for your study.",
                author=admin_user,
                category=categories[1],
                tags="quantitative research, qualitative research, research methods",
                is_published=True,
                published_at=datetime.utcnow()
            )
        ]
        
        db.session.add_all(posts)
        db.session.commit()
        app.logger.info("--- BLOG DATA CREATED ---")
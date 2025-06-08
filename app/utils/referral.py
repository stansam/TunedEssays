import random
import string
from app.models.user import User
from app.extensions import db

def generate_referral_code(length=8):
    """
    Generate a unique referral code for a user.
    
    Args:
        length: Length of the referral code (default: 8)
    
    Returns:
        A unique referral code string
    """
    # Characters to use in referral code (excluding confusing characters like 0/O and 1/I)
    chars = string.ascii_uppercase.replace('O', '') + string.digits.replace('0', '').replace('1', '')
    
    # Generate a referral code
    while True:
        code = 'REF-' + ''.join(random.choice(chars) for _ in range(length))
        
        # Check if code already exists
        existing = User.query.filter_by(referral_code=code).first()
        if not existing:
            return code

def process_referral(referred_user, referrer_code):
    """
    Process a referral when a new user signs up using a referral code.
    
    Args:
        referred_user: The new user who was referred
        referrer_code: The referral code used
    
    Returns:
        True if referral was processed successfully, False otherwise
    """
    try:
        # Find the referrer by their code
        referrer = User.query.filter_by(referral_code=referrer_code).first()
        
        if not referrer:
            return False
        
        # Prevent self-referral
        if referrer.id == referred_user.id:
            return False
        
        # Check if this referral already exists
        from app.models.referral import Referral
        existing_referral = Referral.query.filter_by(
            referred_id=referred_user.id,
            referrer_id=referrer.id
        ).first()
        
        if existing_referral:
            return False
        
        # Create the referral record
        referral = Referral(
            referrer_id=referrer.id,
            referred_id=referred_user.id,
            code=referrer_code,
            status='pending',
            commission=0.0  # Commission will be added when referred user makes a purchase
        )
        
        db.session.add(referral)
        db.session.commit()
        
        return True
    except Exception as e:
        import logging
        logging.error(f"Error processing referral: {str(e)}")
        db.session.rollback()
        return False
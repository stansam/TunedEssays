from werkzeug.utils import secure_filename
import os
from flask import current_app

# Set of allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
PIC_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
def allowed_file(filename, type='file'):
    """Check if a file has an allowed extension."""
    if type == 'picture':
        allowed_extensions = PIC_ALLOWED_EXTENSIONS
    else:
        allowed_extensions = ALLOWED_EXTENSIONS
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_file(file, subfolder=''):
    """
    Save uploaded file to configured upload folder.
    
    Args:
        file: The uploaded file object
        subfolder: Optional subfolder within the upload folder
    
    Returns:
        Tuple of (filename, file_path) if successful, or (None, None) if failed
    """
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Get upload folder from app config
        upload_folder = current_app.config['UPLOAD_FOLDER']
        
        # Add subfolder if provided
        if subfolder:
            upload_folder = os.path.join(upload_folder, subfolder)
            
        # Create folder if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Create full file path
        file_path = os.path.join(upload_folder, filename)
        
        # Save the file
        file.save(file_path)
        
        return filename, file_path
    
    return None, None

def delete_file(file_path):
    """
    Delete a file from the filesystem.
    
    Args:
        file_path: Path to the file to delete
    
    Returns:
        True if file was deleted, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        import logging
        logging.error(f"Error deleting file {file_path}: {str(e)}")
        return False
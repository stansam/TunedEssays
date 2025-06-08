import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
PIC_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_PIC_CONTENT_LENGTH = 5 * 1024 * 1024  # 5
def allowed_file(filename, type='file'):
    if type == 'file':
        allowed_extensions = ALLOWED_EXTENSIONS
    elif type == 'picture':
        allowed_extensions = PIC_ALLOWED_EXTENSIONS
    else:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

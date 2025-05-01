import os
import logging
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory, redirect, abort
from werkzeug.utils import secure_filename
from PIL import Image
from model import enhance_image, apply_filter, rotate_image, crop_image
from captioning import generate_caption

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Folders
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
MODEL_FOLDER = 'model'
TEMP_FOLDER = 'temp'

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
os.makedirs(MODEL_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

# Available filters with names and descriptions
AVAILABLE_FILTERS = {
    'none': {
        'name': 'No Filter',
        'description': 'Applies no filtering, showing the original enhanced image.'
    },
    'grayscale': {
        'name': 'Grayscale',
        'description': 'Converts the image to black and white, removing all color information.'
    },
    'sepia': {
        'name': 'Sepia Tone',
        'description': 'Adds a warm brownish tone, giving the image a vintage or antique look.'
    },
    'blur': {
        'name': 'Blur Effect',
        'description': 'Softens the image details, creating a dreamy or foggy appearance. Intensity controls blur strength.'
    },
    'sharpen': {
        'name': 'Sharpen',
        'description': 'Enhances edges and fine details, making the image appear more crisp and defined.'
    },
    'edge_enhance': {
        'name': 'Edge Enhancement',
        'description': 'Emphasizes the boundaries between different areas, highlighting the shapes in the image.'
    },
    'contour': {
        'name': 'Contour Effect',
        'description': 'Creates an outline effect by detecting and emphasizing edges in the image.'
    },
    'emboss': {
        'name': 'Emboss Effect',
        'description': 'Creates a 3D relief effect, making the image appear as if it were stamped on a surface.'
    },
    'brightness': {
        'name': 'Brightness Boost',
        'description': 'Increases the overall luminosity of the image. Intensity controls brightness level.'
    },
    'contrast': {
        'name': 'Contrast Boost',
        'description': 'Enhances the difference between light and dark areas. Intensity controls contrast strength.'
    },
    'saturation': {
        'name': 'Saturation Boost',
        'description': 'Intensifies the colors in the image. Intensity controls how vivid the colors appear.'
    }
}


def allowed_file(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# Add new filters
AVAILABLE_FILTERS.update({
    'invert': {
        'name': 'Invert Colors',
        'description': 'Inverts all the colors in the image, creating a negative effect.'
    },
    'posterize': {
        'name': 'Posterize',
        'description': 'Reduces the number of colors, creating a poster-like effect. Intensity controls the level of reduction.'
    },
    'solarize': {
        'name': 'Solarize',
        'description': 'Inverts all pixels above a threshold value, creating a surreal effect. Intensity controls the threshold.'
    }
})

# In-memory storage for gallery (we'll use a database in production)
GALLERY_IMAGES = []


@app.route('/')
def index():
    # Pass available filters to the template
    return render_template('index.html', filters=AVAILABLE_FILTERS)


@app.route('/gallery')
def gallery():
    """View all previously processed images"""
    # For now, we'll just read images from the results directory
    images = []
    for filename in os.listdir(RESULT_FOLDER):
        if allowed_file(filename):
            images.append({
                'filename': filename,
                'url': url_for('result_file', filename=filename),
                'date': datetime.fromtimestamp(os.path.getmtime(os.path.join(RESULT_FOLDER, filename))).strftime(
                    '%Y-%m-%d %H:%M')
            })

    # Sort by most recent first
    images.sort(key=lambda x: x['date'], reverse=True)

    return render_template('gallery.html', images=images)


@app.route('/enhance', methods=['POST'])
def enhance():
    if 'file' not in request.files:
        logger.error("No file part in the request")
        return jsonify(error="No file submitted"), 400

    file = request.files['file']

    if file.filename == '':
        logger.error("No file selected")
        return jsonify(error="No file selected"), 400

    # Get request parameters
    filter_type = request.form.get('filter', 'none')
    filter_intensity = float(request.form.get('filter_intensity', 1.0))

    # Get rotation and crop data if present
    rotation = int(request.form.get('rotation', 0))
    crop_data = request.form.get('crop_data')

    # Skip caption generation initially (will be done with separate API call)
    generate_caption_flag = request.form.get('generate_caption', 'false') == 'true'
    tone = request.form.get('tone', 'friendly')

    # Validate filter type
    if filter_type not in AVAILABLE_FILTERS and filter_type != 'none':
        logger.warning(f"Unknown filter type: {filter_type}, defaulting to none")
        filter_type = 'none'

    if not file or not allowed_file(file.filename):
        logger.error(f"Invalid file type: {file.filename}")
        return jsonify(error="Invalid file type. Please upload a PNG, JPG, JPEG, or GIF image."), 400

    try:
        # Generate a unique filename to avoid conflicts
        original_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_id = str(uuid.uuid4())[:8]

        fname = f"{unique_id}_{secure_filename(file.filename)}"
        in_path = os.path.join(UPLOAD_FOLDER, fname)
        file.save(in_path)

        out_name = f"enhanced_{fname}"
        out_path = os.path.join(RESULT_FOLDER, out_name)

        # Enhance image with optional filter, rotation, and crop
        enhance_image(
            in_path,
            out_path,
            filter_type=filter_type,
            filter_intensity=filter_intensity,
            rotation=rotation,
            crop_data=crop_data
        )

        caption = ""
        # Generate caption if requested
        if generate_caption_flag:
            try:
                caption = generate_caption(out_path, tone)
            except Exception as e:
                logger.error(f"Error generating caption: {str(e)}")
                caption = "Caption generation failed. Please try again later."

        # Save to our gallery list
        image_info = {
            'id': unique_id,
            'original_filename': file.filename,
            'enhanced_filename': out_name,
            'original_url': url_for('uploaded_file', filename=fname),
            'enhanced_url': url_for('result_file', filename=out_name),
            'filter_used': filter_type,
            'filter_intensity': filter_intensity,
            'caption': caption,
            'rotation': rotation,
            'crop_data': crop_data,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        GALLERY_IMAGES.append(image_info)

        filter_info = AVAILABLE_FILTERS.get(filter_type, {'name': 'No Filter', 'description': ''})
        return jsonify({
            'id': unique_id,
            'original_url': url_for('uploaded_file', filename=fname),
            'enhanced_url': url_for('result_file', filename=out_name),
            'caption': caption,
            'applied_filter': filter_info['name'],
            'filter_description': filter_info['description'],
            'rotation': rotation,
            'crop_data': crop_data
        })
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify(error=f"Error processing image: {str(e)}"), 500


@app.route('/generate-caption', methods=['POST'])
def generate_caption_api():
    """Generate a caption for an already enhanced image"""
    try:
        image_id = request.form.get('image_id')
        if not image_id:
            return jsonify(error="Image ID is required"), 400

        tone = request.form.get('tone', 'friendly')

        # Find the image in our gallery
        image_info = None
        for img in GALLERY_IMAGES:
            if img.get('id') == image_id:
                image_info = img
                break

        if not image_info:
            # Try to find by filename
            enhanced_filename = request.form.get('filename')
            if enhanced_filename:
                out_path = os.path.join(RESULT_FOLDER, enhanced_filename)
                if os.path.exists(out_path):
                    caption = generate_caption(out_path, tone)
                    return jsonify(caption=caption)

            return jsonify(error="Image not found"), 404

        # Generate caption for the image
        out_path = os.path.join(RESULT_FOLDER, image_info['enhanced_filename'])
        caption = generate_caption(out_path, tone)

        # Update the caption in the gallery
        image_info['caption'] = caption

        return jsonify(caption=caption)
    except Exception as e:
        logger.error(f"Error generating caption: {str(e)}")
        return jsonify(error=f"Error generating caption: {str(e)}"), 500


@app.route('/rotate-image', methods=['POST'])
def rotate_image_api():
    """Rotate an image"""
    try:
        if 'file' not in request.files:
            return jsonify(error="No file part"), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify(error="No selected file"), 400

        degrees = int(request.form.get('degrees', 0))

        # Save the uploaded file
        filename = secure_filename(file.filename)
        temp_input = os.path.join(TEMP_FOLDER, f"temp_in_{filename}")
        file.save(temp_input)

        # Generate a temporary filename
        temp_filename = f"temp_{uuid.uuid4().hex[:8]}_{filename}"
        out_path = os.path.join(TEMP_FOLDER, temp_filename)

        # Open the image and rotate it
        img = Image.open(temp_input).convert('RGB')
        rotated_img = rotate_image(img, degrees)
        rotated_img.save(out_path)

        return jsonify({
            'rotated_url': url_for('temp_file', filename=temp_filename),
            'filename': temp_filename,
            'degrees': degrees
        })
    except Exception as e:
        logger.error(f"Error rotating image: {str(e)}")
        return jsonify(error=f"Error rotating image: {str(e)}"), 500


@app.route('/crop-image', methods=['POST'])
def crop_image_api():
    """Crop an image"""
    try:
        filename = request.form.get('filename')
        crop_data = request.form.get('crop_data')

        if not filename or not crop_data:
            return jsonify(error="Filename and crop data are required"), 400

        # Check if the file exists
        in_path = os.path.join(TEMP_FOLDER, filename)
        if not os.path.exists(in_path):
            in_path = os.path.join(UPLOAD_FOLDER, filename)
            if not os.path.exists(in_path):
                return jsonify(error="Image not found"), 404

        # Generate a temporary filename
        temp_filename = f"temp_{uuid.uuid4().hex[:8]}_{filename}"
        out_path = os.path.join(TEMP_FOLDER, temp_filename)

        # Open the image and crop it
        img = Image.open(in_path).convert('RGB')
        cropped_img = crop_image(img, crop_data)
        cropped_img.save(out_path)

        return jsonify({
            'cropped_url': url_for('temp_file', filename=temp_filename),
            'filename': temp_filename,
            'crop_data': crop_data
        })
    except Exception as e:
        logger.error(f"Error cropping image: {str(e)}")
        return jsonify(error=f"Error cropping image: {str(e)}"), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/results/<filename>')
def result_file(filename):
    return send_from_directory(RESULT_FOLDER, filename, as_attachment=False)


@app.route('/temp/<filename>')
def temp_file(filename):
    """Serve files from the temp folder"""
    return send_from_directory(TEMP_FOLDER, filename)


@app.route('/filters')
def get_filters():
    """API endpoint to get available filters"""
    return jsonify(filters=AVAILABLE_FILTERS)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

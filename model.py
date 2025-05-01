import os
import logging
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)

# Define model path
MODEL_PATH = "model/Real-ESRGAN-General-x4v3.onnx"

# Lazy load ONNX runtime and session
SESSION = None
INPUT_NAME = None
INPUT_SHAPE = None

def init_model():
    global SESSION, INPUT_NAME, INPUT_SHAPE
    try:
        import onnxruntime as ort
        
        # Check if model exists
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Model file not found at {MODEL_PATH}")
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
        
        # Load model
        logger.info(f"Loading ONNX model from {MODEL_PATH}")
        SESSION = ort.InferenceSession(MODEL_PATH)
        input_details = SESSION.get_inputs()[0]
        INPUT_NAME = input_details.name
        
        # Get expected input shape from model
        input_shape = input_details.shape
        if len(input_shape) == 4:  # [batch_size, channels, height, width]
            INPUT_SHAPE = (input_shape[2], input_shape[3]) if input_shape[2] > 0 and input_shape[3] > 0 else None
            logger.info(f"Model expects input shape: {INPUT_SHAPE}")
        
        logger.info("Model loaded successfully")
    except ImportError:
        logger.error("ONNX Runtime not installed. Please install with: pip install onnxruntime")
        raise
    except Exception as e:
        logger.error(f"Error initializing model: {str(e)}")
        raise

def apply_filter(img, filter_type=None, intensity=1.0):
    """Apply a specified filter to the image"""
    if filter_type is None or filter_type == 'none':
        return img
    
    # Create a copy to avoid modifying the original
    img_filtered = img.copy()
    
    if filter_type == "grayscale":
        return img_filtered.convert("L").convert("RGB")
    elif filter_type == "sepia":
        # Simple sepia filter
        grayscale = img_filtered.convert("L")
        sepia_toned = Image.merge("RGB", [
            ImageEnhance.Brightness(grayscale).enhance(1.0),
            ImageEnhance.Brightness(grayscale).enhance(0.8),
            ImageEnhance.Brightness(grayscale).enhance(0.6)
        ])
        return sepia_toned
    elif filter_type == "blur":
        return img_filtered.filter(ImageFilter.GaussianBlur(radius=intensity))
    elif filter_type == "sharpen":
        return img_filtered.filter(ImageFilter.UnsharpMask(radius=2, percent=int(intensity * 150), threshold=3))
    elif filter_type == "edge_enhance":
        return img_filtered.filter(ImageFilter.EDGE_ENHANCE_MORE)
    elif filter_type == "contour":
        return img_filtered.filter(ImageFilter.CONTOUR)
    elif filter_type == "emboss":
        return img_filtered.filter(ImageFilter.EMBOSS)
    elif filter_type == "brightness":
        return ImageEnhance.Brightness(img_filtered).enhance(1.0 + intensity * 0.5)
    elif filter_type == "contrast":
        return ImageEnhance.Contrast(img_filtered).enhance(1.0 + intensity * 0.5)
    elif filter_type == "saturation":
        return ImageEnhance.Color(img_filtered).enhance(1.0 + intensity * 0.5)
    elif filter_type == "invert":
        return ImageOps.invert(img_filtered)
    elif filter_type == "posterize":
        return ImageOps.posterize(img_filtered, int(8 - intensity * 6))
    elif filter_type == "solarize":
        threshold = int(255 * (1.0 - intensity * 0.8))
        return ImageOps.solarize(img_filtered, threshold)
    else:
        return img_filtered

def rotate_image(img, degrees):
    """Rotate image by specified degrees"""
    if degrees == 0:
        return img
    
    # Create a copy to avoid modifying the original
    img_rotated = img.copy()
    
    # Rotate the image
    img_rotated = img_rotated.rotate(degrees, expand=True, resample=Image.BICUBIC)
    
    return img_rotated

def crop_image(img, crop_data):
    """Crop image based on crop coordinates"""
    try:
        if not crop_data:
            return img
            
        # Parse the crop data (x, y, width, height)
        crop_coords = [int(c) for c in crop_data.split(',')]
        if len(crop_coords) != 4:
            logger.error(f"Invalid crop data format: {crop_data}")
            return img
            
        x, y, width, height = crop_coords
        
        # Create a copy to avoid modifying the original
        img_cropped = img.copy()
        
        # Crop the image
        img_cropped = img_cropped.crop((x, y, x + width, y + height))
        
        return img_cropped
    except Exception as e:
        logger.error(f"Error cropping image: {str(e)}")
        return img

def enhance_image(input_path: str, output_path: str, filter_type=None, filter_intensity=1.0, 
                 rotation=0, crop_data=None):
    global SESSION, INPUT_NAME, INPUT_SHAPE
    
    # Initialize model if not already initialized
    if SESSION is None or INPUT_NAME is None:
        init_model()
    
    try:
        # Open and process image
        img = Image.open(input_path).convert('RGB')
        
        # Apply cropping if specified
        if crop_data:
            img = crop_image(img, crop_data)
            
        # Apply rotation if specified
        if rotation and rotation != 0:
            img = rotate_image(img, rotation)
        
        # Determine if we need to resize to exact model dimensions
        if INPUT_SHAPE is not None:
            # Resize to the dimensions expected by the model
            img_model = img.resize(INPUT_SHAPE, Image.BICUBIC)
        else:
            # If no specific dimensions are required, just make sure it's divisible by 4
            w, h = img.size
            w -= w % 4; h -= h % 4
            img_model = img.resize((w, h), Image.BICUBIC)
        
        # Convert to numpy array and normalize
        arr = np.array(img_model).astype(np.float32) / 255.0
        
        # Reshape to model input format (1,3,H,W)
        arr = arr.transpose(2, 0, 1)[None, ...]
        
        # Perform inference
        logger.info(f"Enhancing image: {input_path}")
        out = SESSION.run(None, {INPUT_NAME: arr})[0]
        
        # Post-process output
        out = np.clip(out, 0, 1)[0].transpose(1, 2, 0) * 255
        
        # Convert to PIL Image
        enhanced_img = Image.fromarray(out.astype(np.uint8))
        
        # Resize back to original size if needed
        if enhanced_img.size != img.size:
            enhanced_img = enhanced_img.resize((img.size[0] * 2, img.size[1] * 2), Image.BICUBIC)
        
        # Apply filter if specified
        if filter_type and filter_type != 'none':
            logger.info(f"Applying filter: {filter_type} with intensity {filter_intensity}")
            enhanced_img = apply_filter(enhanced_img, filter_type, filter_intensity)
        
        # Save result
        enhanced_img.save(output_path)
        logger.info(f"Enhanced image saved to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error enhancing image: {str(e)}")
        raise

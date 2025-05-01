import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ImageEntry(db.Model):
    """Model for storing processed images in the gallery"""
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    enhanced_filename = db.Column(db.String(255), nullable=False)
    filter_used = db.Column(db.String(50), nullable=True)
    filter_intensity = db.Column(db.Float, nullable=True)
    caption = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    rotation = db.Column(db.Integer, default=0)  # Rotation in degrees
    crop_data = db.Column(db.String(255), nullable=True)  # Store crop coordinates
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'enhanced_filename': self.enhanced_filename,
            'filter_used': self.filter_used,
            'filter_intensity': self.filter_intensity,
            'caption': self.caption,
            'created_at': self.created_at.isoformat(),
            'rotation': self.rotation,
            'crop_data': self.crop_data
        }
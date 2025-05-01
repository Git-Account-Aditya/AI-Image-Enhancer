document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const filePreview = document.getElementById('file-preview');
    const fileNameDisplay = document.getElementById('file-name');
    const editingToolsContainer = document.getElementById('editing-tools-container');
    const uploadButton = document.getElementById('upload-button');
    const loadingSpinner = document.getElementById('loading-spinner');
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    const resultsSection = document.getElementById('results-section');
    const rotationDegreesInput = document.getElementById('rotation-degrees');
    const dropArea = document.getElementById('drop-area');
    const filterIntensity = document.getElementById('filter-intensity');
    const intensityValue = document.getElementById('intensity-value');
    const intensityContainer = document.getElementById('intensity-container');
    const filterSelect = document.getElementById('filter-select');

    let currentImageUrl = null;
    let currentRotation = 0;
    let currentImageId = null;

    // Handle file selection
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                displayFilePreview(file);
            }
        });
    }

    // Handle filter intensity slider
    if (filterIntensity && intensityValue) {
        filterIntensity.addEventListener('input', function() {
            intensityValue.textContent = this.value;
        });
    }

    // Handle filter selection
    if (filterSelect && intensityContainer) {
        filterSelect.addEventListener('change', function() {
            const filterType = this.value;
            if (filterType === 'none') {
                intensityContainer.classList.add('d-none');
            } else {
                intensityContainer.classList.remove('d-none');
            }
        });
    }

    // Handle drag and drop
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });

        dropArea.addEventListener('drop', handleDrop, false);
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        if (file) {
            fileInput.files = dt.files;
            displayFilePreview(file);
        }
    }

    function displayFilePreview(file) {
        if (!file.type.match('image.*')) {
            showError('Please select an image file (PNG, JPG, JPEG, GIF)');
            return;
        }

        if (fileNameDisplay) {
            fileNameDisplay.textContent = file.name;
            fileNameDisplay.classList.remove('d-none');
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            const imageUrl = e.target.result;
            if (filePreview) {
                filePreview.innerHTML = `<img src="${imageUrl}" class="img-fluid preview-image" alt="Preview">`;
                filePreview.classList.remove('d-none');
            }

            if (editingToolsContainer) {
                editingToolsContainer.classList.remove('d-none');
            }

            currentImageUrl = imageUrl;
            currentRotation = 0;
            if (rotationDegreesInput) rotationDegreesInput.value = '0';
            if (uploadButton) uploadButton.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    // Handle form submission
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!fileInput || !fileInput.files || !fileInput.files[0]) {
                showError('Please select an image to enhance');
                return;
            }

            if (loadingSpinner) loadingSpinner.classList.remove('d-none');
            if (errorAlert) errorAlert.classList.add('d-none');
            if (resultsSection) resultsSection.classList.add('d-none');
            if (uploadButton) uploadButton.disabled = true;

            const formData = new FormData(form);
            fetch('/enhance', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Error processing image');
                    });
                }
                return response.json();
            })
            .then(data => {
                displayResults(data);
                if (loadingSpinner) loadingSpinner.classList.add('d-none');
                if (uploadButton) uploadButton.disabled = false;
            })
            .catch(error => {
                if (loadingSpinner) loadingSpinner.classList.add('d-none');
                if (uploadButton) uploadButton.disabled = false;
                showError(error.message || 'Error processing the image. Please try again.');
            });
        });
    }

    function displayResults(data) {
        const originalImage = document.getElementById('original-image');
        const enhancedImage = document.getElementById('enhanced-image');
        const captionElement = document.getElementById('image-caption');
        const appliedFilter = document.getElementById('applied-filter');
        const filterDetail = document.getElementById('filter-detail');

        if (originalImage) originalImage.src = data.original_url;
        if (enhancedImage) enhancedImage.src = data.enhanced_url;

        if (captionElement) {
            captionElement.textContent = data.caption || 'No caption generated. Click the button below to generate one.';
        }

        if (appliedFilter) {
            appliedFilter.textContent = data.applied_filter || 'No Filter';
        }

        if (filterDetail) {
            filterDetail.textContent = data.filter_description || '';
        }

        if (resultsSection) {
            resultsSection.classList.remove('d-none');
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        }

        currentImageId = data.id;
    }

    function showError(message) {
        if (errorMessage) errorMessage.textContent = message;
        if (errorAlert) errorAlert.classList.remove('d-none');
        if (loadingSpinner) loadingSpinner.classList.add('d-none');
    }

    // Handle rotation buttons
    const rotateLeftBtn = document.getElementById('rotate-left-btn');
    const rotateRightBtn = document.getElementById('rotate-right-btn');

    if (rotateLeftBtn) {
        rotateLeftBtn.addEventListener('click', function() {
            rotateImage(-90);
        });
    }

    if (rotateRightBtn) {
        rotateRightBtn.addEventListener('click', function() {
            rotateImage(90);
        });
    }

    // Rotate image function
    function rotateImage(degrees) {
        const fileInput = document.getElementById('file-input');
        const filePreview = document.getElementById('file-preview');
        const loadingSpinner = document.getElementById('loading-spinner');
        const rotationDegreesInput = document.getElementById('rotation-degrees');

        if (!fileInput || !fileInput.files || !fileInput.files[0]) {
            showError('Please select an image first');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('degrees', degrees);

        // Show loading state
        if (loadingSpinner) loadingSpinner.classList.remove('d-none');

        fetch('/rotate-image', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.rotated_url) {
                const previewImage = new Image();
                previewImage.onload = function() {
                    if (filePreview) {
                        filePreview.innerHTML = `<img src="${data.rotated_url}?t=${Date.now()}" class="img-fluid preview-image" alt="Preview">`;
                        currentImageUrl = data.rotated_url;
                        // Update rotation value
                        currentRotation = (currentRotation + degrees) % 360;
                        if (currentRotation < 0) currentRotation += 360;
                        if (rotationDegreesInput) {
                            rotationDegreesInput.value = currentRotation.toString();
                        }
                    }
                    if (loadingSpinner) loadingSpinner.classList.add('d-none');
                };
                previewImage.onerror = function() {
                    showError('Error loading rotated image');
                    if (loadingSpinner) loadingSpinner.classList.add('d-none');
                };
                previewImage.src = data.rotated_url + '?t=' + Date.now();
            }
        })
        .catch(error => {
            console.error('Error rotating image:', error);
            showError('Error rotating image. Please try again.');
            if (loadingSpinner) loadingSpinner.classList.add('d-none');
        });
    }

    // Handle download button
    const downloadButton = document.getElementById('download-button');
    if (downloadButton) {
        downloadButton.addEventListener('click', function(e) {
            const enhancedImage = document.getElementById('enhanced-image');
            if (enhancedImage && enhancedImage.src) {
                this.href = enhancedImage.src;
                this.download = 'enhanced_image.jpg';
            }
        });
    }

    // Handle generate caption button
    const generateCaptionBtn = document.getElementById('generate-caption-btn');
    if (generateCaptionBtn) {
        generateCaptionBtn.addEventListener('click', function() {
            if (!currentImageId) return;

            const toneSelect = document.getElementById('tone-select');
            const formData = new FormData();
            formData.append('image_id', currentImageId);
            formData.append('tone', toneSelect ? toneSelect.value : 'friendly');

            fetch('/generate-caption', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const captionElement = document.getElementById('image-caption');
                if (data.caption && captionElement) {
                    captionElement.textContent = data.caption;
                }
            })
            .catch(error => {
                console.error('Error generating caption:', error);
                showError('Error generating caption. Please try again.');
            });
        });
    }

    // Handle reset button
    const resetButton = document.getElementById('reset-button');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            if (form) form.reset();
            if (filePreview) {
                filePreview.innerHTML = '';
                filePreview.classList.add('d-none');
            }
            if (fileNameDisplay) {
                fileNameDisplay.textContent = '';
                fileNameDisplay.classList.add('d-none');
            }
            if (editingToolsContainer) editingToolsContainer.classList.add('d-none');
            if (resultsSection) resultsSection.classList.add('d-none');
            if (errorAlert) errorAlert.classList.add('d-none');
            if (uploadButton) uploadButton.disabled = true;
            currentRotation = 0;
            currentImageUrl = null;
            currentImageId = null;
            if (rotationDegreesInput) rotationDegreesInput.value = '0';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
});
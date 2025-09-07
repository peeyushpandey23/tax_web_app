// Upload Page JavaScript

class DocumentUploader {
    constructor() {
        this.uploadedFiles = [];
        this.documentType = 'salary_slip_single';
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.maxFiles = 4;
        
        // Wait for CookieManager to be available
        if (typeof CookieManager === 'undefined') {
            console.error('CookieManager not available, retrying in 100ms...');
            setTimeout(() => {
                this.userId = CookieManager.getOrCreateUserId();
                this.initializeAfterCookieManager();
            }, 100);
        } else {
            this.userId = CookieManager.getOrCreateUserId();
            this.initializeAfterCookieManager();
        }
    }
    
    initializeAfterCookieManager() {
        console.log('DocumentUploader initialized with user ID:', this.userId);
        console.log('CookieManager available:', typeof CookieManager !== 'undefined');
        
        this.initializeEventListeners();
        this.updateUploadInterface();
        this.checkForDrafts();
    }
    
    async checkForDrafts() {
        console.log('🚨🚨🚨 CHECKING FOR DRAFTS METHOD CALLED 🚨🚨🚨');
        console.log('User ID:', this.userId);
        
        try {
            console.log('Checking for drafts for user:', this.userId);
            console.log('User ID type:', typeof this.userId);
            console.log('User ID length:', this.userId ? this.userId.length : 'null');
            
            // First test the headers
            const testResponse = await fetch('/api/test-drafts', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': this.userId
                }
            });
            
            console.log('Test response status:', testResponse.status);
            
            if (testResponse.ok) {
                const testData = await testResponse.json();
                console.log('Test endpoint response:', testData);
            } else {
                console.error('Test endpoint failed:', testResponse.status);
            }
            
            // Debug: Check all drafts in database
            const debugResponse = await fetch('/api/debug-drafts', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': this.userId
                }
            });
            
            if (debugResponse.ok) {
                const debugData = await debugResponse.json();
                console.log('Debug drafts response:', debugData);
            }
            
            const response = await fetch('/api/drafts', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': this.userId
                }
            });
            
            console.log('Drafts API response status:', response.status);
            
            if (response.ok) {
                const drafts = await response.json();
                console.log('Drafts received:', drafts);
                console.log('Drafts type:', typeof drafts);
                console.log('Drafts is array:', Array.isArray(drafts));
                console.log('Number of drafts:', drafts.length);
                console.log('First draft:', drafts[0]);
                
                if (drafts && drafts.length > 0) {
                    console.log('Calling showDraftNotification with draft:', drafts[0]);
                    console.log('About to call showDraftNotification...');
                    try {
                        showDraftNotification(drafts[0]); // Show most recent draft
                        console.log('showDraftNotification call completed');
                    } catch (error) {
                        console.error('Error in showDraftNotification:', error);
                    }
                } else {
                    console.log('No drafts found for user');
                }
            } else {
                console.error('Drafts API failed:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Failed to check for drafts:', error);
        }
    }
    
    initializeEventListeners() {
        // Document type selection
        const documentTypeInputs = document.querySelectorAll('input[name="documentType"]');
        documentTypeInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.documentType = e.target.value;
                this.updateUploadInterface();
                this.clearFiles();
            });
        });
        
        // Single file upload
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        
        uploadZone.addEventListener('click', () => fileInput.click());
        uploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadZone.addEventListener('drop', this.handleDrop.bind(this));
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Multiple file upload
        const multipleUploadZone = document.getElementById('multipleUploadZone');
        const multipleFileInput = document.getElementById('multipleFileInput');
        
        multipleUploadZone.addEventListener('click', () => multipleFileInput.click());
        multipleUploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
        multipleUploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        multipleUploadZone.addEventListener('drop', this.handleDrop.bind(this));
        multipleFileInput.addEventListener('change', this.handleMultipleFileSelect.bind(this));
    }
    
    updateUploadInterface() {
        const singleUpload = document.getElementById('singleUpload');
        const multipleUpload = document.getElementById('multipleUpload');
        
        if (this.documentType === 'salary_slip_multiple') {
            singleUpload.style.display = 'none';
            multipleUpload.style.display = 'block';
        } else {
            singleUpload.style.display = 'block';
            multipleUpload.style.display = 'none';
        }
        
        this.updateProcessButton();
        this.updateUploadZoneAppearance();
    }
    
    updateUploadZoneAppearance() {
        const uploadZone = document.getElementById('uploadZone');
        if (!uploadZone) return;
        
        const uploadIcon = uploadZone.querySelector('.upload-icon');
        const uploadTitle = uploadZone.querySelector('h3');
        const uploadSubtitle = uploadZone.querySelector('p');
        
        if (this.uploadedFiles.length > 0) {
            uploadIcon.textContent = '✅';
            uploadTitle.textContent = 'File Selected!';
            uploadSubtitle.textContent = 'Click to change or drag another file';
            uploadZone.classList.add('file-selected');
        } else {
            uploadIcon.textContent = '📁';
            uploadTitle.textContent = 'Drag & Drop PDF here';
            uploadSubtitle.textContent = 'or click to browse';
            uploadZone.classList.remove('file-selected');
        }
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        this.processFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.processFiles(files);
    }
    
    handleMultipleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.processFiles(files);
    }
    
    processFiles(files) {
        const validFiles = files.filter(file => this.validateFile(file));
        
        if (this.documentType === 'salary_slip_multiple') {
            // For multiple files, add to existing list
            this.uploadedFiles = [...this.uploadedFiles, ...validFiles];
            
            // Limit to max files
            if (this.uploadedFiles.length > this.maxFiles) {
                this.uploadedFiles = this.uploadedFiles.slice(0, this.maxFiles);
                this.showError(`Maximum ${this.maxFiles} files allowed. Only first ${this.maxFiles} files will be processed.`);
            }
            this.updateFileList();
        } else {
            // For single file, replace existing
            this.uploadedFiles = validFiles.slice(0, 1);
            this.updateSingleFileStatus();
        }
        
        this.updateProcessButton();
    }
    
    validateFile(file) {
        // Check file type
        if (!file.type.includes('pdf')) {
            this.showError(`${file.name} is not a PDF file. Only PDF files are supported.`);
            return false;
        }
        
        // Check file size
        if (file.size > this.maxFileSize) {
            this.showError(`${file.name} is too large. Maximum file size is 10MB.`);
            return false;
        }
        
        return true;
    }
    
    updateSingleFileStatus() {
        const singleFileStatus = document.getElementById('singleFileStatus');
        const singleFileName = document.getElementById('singleFileName');
        const singleFileSize = document.getElementById('singleFileSize');
        
        if (this.uploadedFiles.length > 0) {
            const file = this.uploadedFiles[0];
            singleFileName.textContent = file.name;
            singleFileSize.textContent = this.formatFileSize(file.size);
            singleFileStatus.style.display = 'block';
            
            // Add success indicator
            singleFileStatus.classList.add('file-selected');
        } else {
            singleFileStatus.style.display = 'none';
            singleFileStatus.classList.remove('file-selected');
        }
        
        // Update upload zone appearance
        this.updateUploadZoneAppearance();
    }
    
    clearSingleFile() {
        this.uploadedFiles = [];
        this.updateSingleFileStatus();
        this.updateProcessButton();
        // Clear the file input
        document.getElementById('fileInput').value = '';
    }
    
    updateFileList() {
        const fileList = document.getElementById('fileList');
        fileList.innerHTML = '';
        
        this.uploadedFiles.forEach((file, index) => {
            const fileItem = this.createFileItem(file, index);
            fileList.appendChild(fileItem);
        });
    }
    
    createFileItem(file, index) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
        const fileSize = this.formatFileSize(file.size);
        
        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-icon">📄</div>
                <div class="file-details">
                    <h4>${file.name}</h4>
                    <p>${fileSize}</p>
                </div>
            </div>
            <button class="file-remove" onclick="documentUploader.removeFile(${index})" title="Remove file">×</button>
        `;
        
        return fileItem;
    }
    
    removeFile(index) {
        this.uploadedFiles.splice(index, 1);
        this.updateFileList();
        this.updateProcessButton();
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    updateProcessButton() {
        const processButton = document.getElementById('processButton');
        const hasFiles = this.uploadedFiles.length > 0;
        
        processButton.disabled = !hasFiles;
        
        if (hasFiles) {
            const fileCount = this.uploadedFiles.length;
            if (this.documentType === 'salary_slip_multiple') {
                processButton.textContent = `Process ${fileCount} Document${fileCount > 1 ? 's' : ''}`;
            } else {
                processButton.textContent = 'Process Document';
            }
        } else {
            processButton.textContent = 'Process Documents';
        }
    }
    
    clearFiles() {
        this.uploadedFiles = [];
        this.updateFileList();
        this.updateSingleFileStatus();
        this.updateProcessButton();
        
        // Clear file inputs
        document.getElementById('fileInput').value = '';
        document.getElementById('multipleFileInput').value = '';
    }
    
    showError(message) {
        const errorMessage = document.getElementById('errorMessage');
        const errorText = document.getElementById('errorText');
        
        errorText.textContent = message;
        errorMessage.style.display = 'flex';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideError();
        }, 5000);
    }
    
    hideError() {
        document.getElementById('errorMessage').style.display = 'none';
    }
    
    async processDocuments() {
        if (this.uploadedFiles.length === 0) {
            this.showError('Please select at least one file to process.');
            return;
        }
        
        try {
            this.showProgress();
            
            // Create FormData for file upload
            const formData = new FormData();
            formData.append('document_type', this.documentType);
            
            this.uploadedFiles.forEach((file, index) => {
                formData.append('files', file);
            });
            
            // Upload files
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'X-User-ID': this.userId
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Store session data and redirect to review form
                sessionStorage.setItem('session_id', result.session_id);
                sessionStorage.setItem('extracted_data', JSON.stringify(result.extracted_data));
                sessionStorage.setItem('processing_summary', JSON.stringify(result.processing_summary));
                
                window.location.href = '/review-form';
            } else {
                throw new Error(result.error || 'Document processing failed');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showError(`Processing failed: ${error.message}`);
            this.hideProgress();
        }
    }
    
    showProgress() {
        const uploadProgress = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        uploadProgress.style.display = 'block';
        
        // Simulate progress
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            
            progressFill.style.width = `${progress}%`;
            
            if (progress < 30) {
                progressText.textContent = 'Uploading files...';
            } else if (progress < 60) {
                progressText.textContent = 'Extracting text...';
            } else if (progress < 90) {
                progressText.textContent = 'Processing with AI...';
            }
        }, 200);
        
        // Store interval for cleanup
        this.progressInterval = interval;
    }
    
    hideProgress() {
        const uploadProgress = document.getElementById('uploadProgress');
        uploadProgress.style.display = 'none';
        
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        const progressFill = document.getElementById('progressFill');
        progressFill.style.width = '0%';
    }
}

// Global functions for HTML onclick handlers
function goBack() {
    window.history.back();
}

function processDocuments() {
    if (documentUploader) {
        documentUploader.processDocuments();
    }
}

function hideError() {
    if (documentUploader) {
        documentUploader.hideError();
    }
}

// Initialize uploader when DOM is loaded
let documentUploader;

document.addEventListener('DOMContentLoaded', () => {
    documentUploader = new DocumentUploader();
    
    // Check for existing draft
    checkForExistingDraft();
});

async function checkForExistingDraft() {
    try {
        const response = await fetch('/api/drafts');
        if (response.ok) {
            const drafts = await response.json();
            if (drafts.length > 0) {
                showDraftNotification(drafts[0]);
            }
        }
    } catch (error) {
        console.log('No existing drafts found');
    }
}

function showDraftNotification(draft) {
    console.log('showDraftNotification called with:', draft);
    console.log('Draft properties:', Object.keys(draft));
    
    const notification = document.createElement('div');
    notification.className = 'draft-notification';
    notification.innerHTML = `
        <div class="draft-content">
            <div class="draft-icon">💾</div>
            <div class="draft-text">
                <h4>Draft Found!</h4>
                <p>You have a saved draft from ${new Date(draft.created_at).toLocaleDateString()}</p>
            </div>
            <button class="btn-secondary" onclick="loadDraft('${draft.draft_id}')">Load Draft</button>
            <button class="btn-secondary" onclick="dismissDraft()">Dismiss</button>
        </div>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        border: 1px solid #667eea;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        max-width: 350px;
    `;
    
    // Add to page
    console.log('Adding notification to DOM...');
    document.body.appendChild(notification);
    console.log('Notification added to DOM, checking if visible...');
    console.log('Notification element:', notification);
    console.log('Notification parent:', notification.parentNode);
    console.log('Notification computed style:', window.getComputedStyle(notification));
    console.log('Notification offset:', notification.offsetWidth, notification.offsetHeight);
    
    // Auto-dismiss after 10 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 10000);
}

async function loadDraft(draftId) {
    try {
        const response = await fetch(`/api/draft/${draftId}`, {
            headers: {
                'X-User-ID': CookieManager.getCurrentUserId()
            }
        });
        if (response.ok) {
            const draft = await response.json();
            
            // Store draft data and redirect to review form
            sessionStorage.setItem('session_id', draft.draft_id);
            sessionStorage.setItem('extracted_data', JSON.stringify(draft.financial_data));
            sessionStorage.setItem('is_draft', 'true');
            
            window.location.href = '/review-form';
        }
    } catch (error) {
        console.error('Failed to load draft:', error);
        alert('Failed to load draft. Please try again.');
    }
}

function dismissDraft() {
    const notification = document.querySelector('.draft-notification');
    if (notification) {
        notification.remove();
    }
}

// Add draft notification styles
const style = document.createElement('style');
style.textContent = `
    .draft-notification {
        animation: slideIn 0.3s ease-out;
    }
    
    .draft-content {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .draft-icon {
        font-size: 2rem;
    }
    
    .draft-text h4 {
        margin: 0 0 0.25rem 0;
        color: #333;
        font-size: 1rem;
    }
    
    .draft-text p {
        margin: 0;
        color: #666;
        font-size: 0.9rem;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);


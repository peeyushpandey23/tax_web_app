// Upload Page JavaScript

class DocumentUploader {
    constructor() {
        this.uploadedFiles = [];
        this.documentType = 'salary_slip_single';
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.maxFiles = 4;
        this.pdfPassword = ''; // Store PDF password
        this.isClearingFiles = false; // Flag to prevent password section from showing during clear
        this.filePasswordStatus = new Map(); // Track password protection status for each file
        
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
        this.initializePasswordHandlers();
        this.updateUploadInterface();
        this.checkForDrafts();
    }
    
    async checkForDrafts() {
        console.log('🚨🚨🚨 CHECKING FOR DRAFTS METHOD CALLED 🚨🚨🚨');
        console.log('User ID:', this.userId);
        
        // Show loading state
        this.showLoadingState();
        
        try {
            console.log('Checking for drafts for user:', this.userId);
            
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
                console.log('Number of drafts:', drafts.length);
                
                if (drafts && drafts.length > 0) {
                    console.log('Showing draft option banner with draft:', drafts[0]);
                    this.showDraftOptionBanner(drafts[0]);
                } else {
                    console.log('No drafts found, showing normal upload interface');
                    this.showUploadInterface();
                }
            } else {
                console.error('Drafts API failed:', response.status, response.statusText);
                this.showUploadInterface();
            }
        } catch (error) {
            console.error('Failed to check for drafts:', error);
            this.showUploadInterface();
        }
    }
    
    showLoadingState() {
        console.log('Showing loading state');
        const loadingState = document.getElementById('loadingState');
        const draftBanner = document.getElementById('draftOptionBanner');
        const uploadInterface = document.getElementById('uploadInterface');
        
        if (loadingState) loadingState.style.display = 'flex';
        if (draftBanner) draftBanner.style.display = 'none';
        if (uploadInterface) uploadInterface.style.display = 'none';
    }
    
    showUploadInterface() {
        console.log('Showing upload interface');
        const loadingState = document.getElementById('loadingState');
        const draftBanner = document.getElementById('draftOptionBanner');
        const uploadInterface = document.getElementById('uploadInterface');
        
        console.log('Elements found:', {
            loadingState: !!loadingState,
            draftBanner: !!draftBanner,
            uploadInterface: !!uploadInterface
        });
        
        if (loadingState) {
            loadingState.style.display = 'none';
            console.log('Hidden loading state');
        }
        if (draftBanner) {
            draftBanner.style.display = 'none';
            console.log('Hidden draft banner');
        }
        if (uploadInterface) {
            uploadInterface.style.display = 'block';
            console.log('Showed upload interface');
        }
    }
    
    showDraftOptionBanner(draft) {
        console.log('showDraftOptionBanner called with:', draft);
        
        // Update draft information
        const draftDateElement = document.querySelector('.draft-date');
        if (draftDateElement) {
            draftDateElement.textContent = new Date(draft.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
        
        // Show draft banner and upload interface
        const loadingState = document.getElementById('loadingState');
        const draftBanner = document.getElementById('draftOptionBanner');
        const uploadInterface = document.getElementById('uploadInterface');
        
        console.log('Elements found for banner:', {
            loadingState: !!loadingState,
            draftBanner: !!draftBanner,
            uploadInterface: !!uploadInterface
        });
        
        if (loadingState) {
            loadingState.style.display = 'none';
            console.log('Hidden loading state');
        }
        if (draftBanner) {
            draftBanner.style.display = 'block';
            draftBanner.style.visibility = 'visible';
            draftBanner.style.opacity = '1';
            console.log('Showed draft banner');
        }
        if (uploadInterface) {
            uploadInterface.style.display = 'block';
            console.log('Showed upload interface');
        }
        
        // Add event listeners with proper binding
        const loadDraftBtn = document.getElementById('loadDraftBtn');
        const discardDraftBtn = document.getElementById('discardDraftBtn');
        const dismissDraftBtn = document.getElementById('dismissDraftBtn');
        const closeDraftBtn = document.getElementById('closeDraftBanner');
        
        console.log('Buttons found:', {
            loadDraftBtn: !!loadDraftBtn,
            discardDraftBtn: !!discardDraftBtn,
            dismissDraftBtn: !!dismissDraftBtn,
            closeDraftBtn: !!closeDraftBtn
        });
        
        if (loadDraftBtn) {
            // Remove any existing event listeners
            loadDraftBtn.removeEventListener('click', this.handleLoadDraft);
            // Add new event listener
            this.handleLoadDraft = () => {
                console.log('Load draft button clicked');
                this.loadDraft(draft.draft_id);
            };
            loadDraftBtn.addEventListener('click', this.handleLoadDraft);
        }
        
        if (discardDraftBtn) {
            // Remove any existing event listeners
            discardDraftBtn.removeEventListener('click', this.handleDiscardDraft);
            // Add new event listener
            this.handleDiscardDraft = () => {
                console.log('Discard draft button clicked');
                this.discardDraft(draft.draft_id);
            };
            discardDraftBtn.addEventListener('click', this.handleDiscardDraft);
        }
        
        if (dismissDraftBtn) {
            // Remove any existing event listeners
            dismissDraftBtn.removeEventListener('click', this.handleDismissDraft);
            // Add new event listener
            this.handleDismissDraft = () => {
                console.log('Dismiss draft button clicked');
                this.dismissDraftBanner();
            };
            dismissDraftBtn.addEventListener('click', this.handleDismissDraft);
        }
        
        if (closeDraftBtn) {
            // Remove any existing event listeners
            closeDraftBtn.removeEventListener('click', this.handleCloseDraft);
            // Add new event listener
            this.handleCloseDraft = () => {
                console.log('Close draft banner clicked');
                this.dismissDraftBanner();
            };
            closeDraftBtn.addEventListener('click', this.handleCloseDraft);
        }
    }
    
    async discardDraft(draftId) {
        console.log('Discarding draft:', draftId);
        
        // Show confirmation dialog
        const confirmed = confirm('Are you sure you want to discard this draft? This action cannot be undone.');
        if (!confirmed) {
            console.log('Draft discard cancelled by user');
            return;
        }
        
        try {
            console.log('Calling DELETE API for draft:', draftId);
            // Call API to delete the draft
            const response = await fetch(`/api/draft/${draftId}`, {
                method: 'DELETE',
                headers: {
                    'X-User-ID': this.userId,
                    'Content-Type': 'application/json'
                }
            });
            
            console.log('Delete API response status:', response.status);
            
            if (response.ok) {
                console.log('Draft discarded successfully');
                // Hide draft banner and show only upload interface
                console.log('Calling showUploadInterface after discard');
                this.showUploadInterface();
                
                // Show success message
                this.showSuccessMessage('Draft discarded successfully!');
            } else {
                const errorText = await response.text();
                console.error('Failed to discard draft, response not ok:', response.status, errorText);
                throw new Error(`Failed to discard draft: ${response.status}`);
            }
        } catch (error) {
            console.error('Failed to discard draft:', error);
            this.showErrorMessage('Failed to discard draft. Please try again.');
        }
    }
    
    dismissDraftBanner() {
        console.log('Dismissing draft banner');
        const draftBanner = document.getElementById('draftOptionBanner');
        if (draftBanner) {
            draftBanner.style.display = 'none';
        }
        // Upload interface should already be visible
    }
    
    async loadDraft(draftId) {
        try {
            console.log('Loading draft:', draftId);
            const response = await fetch(`/api/draft/${draftId}`, {
                headers: {
                    'X-User-ID': this.userId
                }
            });
            
            if (response.ok) {
                const draft = await response.json();
                
                // Store draft data and redirect to review form
                sessionStorage.setItem('session_id', draft.draft_id);
                sessionStorage.setItem('extracted_data', JSON.stringify(draft.financial_data));
                sessionStorage.setItem('is_draft', 'true');
                
                window.location.href = '/review-form';
            } else {
                throw new Error('Failed to load draft');
            }
        } catch (error) {
            console.error('Failed to load draft:', error);
            alert('Failed to load draft. Please try again.');
        }
    }
    
    initializePasswordHandlers() {
        // Single file password handlers
        const singlePasswordToggle = document.getElementById('singlePasswordToggle');
        const singlePasswordInput = document.getElementById('singlePasswordInput');
        
        if (singlePasswordToggle && singlePasswordInput) {
            singlePasswordToggle.addEventListener('click', () => {
                this.togglePasswordVisibility(singlePasswordInput, singlePasswordToggle);
            });
            
            singlePasswordInput.addEventListener('input', (e) => {
                this.pdfPassword = e.target.value;
            });
        }
        
        // Multiple file password handlers
        const multiplePasswordToggle = document.getElementById('multiplePasswordToggle');
        const multiplePasswordInput = document.getElementById('multiplePasswordInput');
        
        if (multiplePasswordToggle && multiplePasswordInput) {
            multiplePasswordToggle.addEventListener('click', () => {
                this.togglePasswordVisibility(multiplePasswordInput, multiplePasswordToggle);
            });
            
            multiplePasswordInput.addEventListener('input', (e) => {
                this.pdfPassword = e.target.value;
            });
        }
    }
    
    togglePasswordVisibility(input, toggle) {
        if (input.type === 'password') {
            input.type = 'text';
            toggle.classList.add('active');
            toggle.textContent = '🙈';
        } else {
            input.type = 'password';
            toggle.classList.remove('active');
            toggle.textContent = '👁️';
        }
    }
    
    showPasswordSection(passwordProtectedFiles = []) {
        const singlePasswordSection = document.getElementById('singlePasswordSection');
        const multiplePasswordSection = document.getElementById('multiplePasswordSection');
        
        if (this.documentType === 'salary_slip_multiple') {
            if (multiplePasswordSection) {
                multiplePasswordSection.style.display = 'block';
                multiplePasswordSection.classList.add('show');
            }
        } else {
            if (singlePasswordSection) {
                singlePasswordSection.style.display = 'block';
                singlePasswordSection.classList.add('show');
            }
        }
        
        // Update help message with specific file information
        if (passwordProtectedFiles.length > 0) {
            const fileList = passwordProtectedFiles.join(', ');
            this.updatePasswordHelpMessage(`🔒 Password-protected files detected: ${fileList}. Please enter the password to proceed.`);
        } else {
            this.updatePasswordHelpMessage('🔒 Password-protected files detected. Please enter the password to proceed.');
        }
    }
    
    hidePasswordSection() {
        console.log('🔒 HIDING PASSWORD SECTION');
        const singlePasswordSection = document.getElementById('singlePasswordSection');
        const multiplePasswordSection = document.getElementById('multiplePasswordSection');
        
        console.log('Single password section found:', !!singlePasswordSection);
        console.log('Multiple password section found:', !!multiplePasswordSection);
        
        if (singlePasswordSection) {
            console.log('Hiding single password section');
            console.log('Before hiding - Single password section display:', singlePasswordSection.style.display);
            console.log('Before hiding - Single password section computed style:', window.getComputedStyle(singlePasswordSection).display);
            
            singlePasswordSection.style.display = 'none';
            singlePasswordSection.classList.remove('show');
            
            console.log('After hiding - Single password section display:', singlePasswordSection.style.display);
            console.log('After hiding - Single password section computed style:', window.getComputedStyle(singlePasswordSection).display);
        }
        
        if (multiplePasswordSection) {
            console.log('Hiding multiple password section');
            console.log('Before hiding - Multiple password section display:', multiplePasswordSection.style.display);
            console.log('Before hiding - Multiple password section computed style:', window.getComputedStyle(multiplePasswordSection).display);
            
            multiplePasswordSection.style.display = 'none';
            multiplePasswordSection.classList.remove('show');
            
            console.log('After hiding - Multiple password section display:', multiplePasswordSection.style.display);
            console.log('After hiding - Multiple password section computed style:', window.getComputedStyle(multiplePasswordSection).display);
        }
        
        console.log('🔒 PASSWORD SECTION HIDDEN');
    }
    
    updatePasswordHelpMessage(message) {
        const singlePasswordHelp = document.getElementById('singlePasswordHelp');
        const multiplePasswordHelp = document.getElementById('multiplePasswordHelp');
        
        if (this.documentType === 'salary_slip_multiple') {
            if (multiplePasswordHelp) {
                multiplePasswordHelp.textContent = message;
            }
        } else {
            if (singlePasswordHelp) {
                singlePasswordHelp.textContent = message;
            }
        }
    }
    
    getCurrentPassword() {
        const singlePasswordInput = document.getElementById('singlePasswordInput');
        const multiplePasswordInput = document.getElementById('multiplePasswordInput');
        
        if (this.documentType === 'salary_slip_multiple') {
            return multiplePasswordInput ? multiplePasswordInput.value : '';
        } else {
            return singlePasswordInput ? singlePasswordInput.value : '';
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
        
        if (uploadZone) {
            uploadZone.addEventListener('click', (e) => {
                console.log('Upload zone clicked');
                console.log('File input element:', fileInput);
                console.log('File input exists:', !!fileInput);
                
                if (fileInput) {
                    console.log('Triggering file input click');
                    console.log('File input disabled:', fileInput.disabled);
                    console.log('File input style:', fileInput.style.display);
                    
                    // Don't prevent default - let the click bubble up
                    fileInput.click();
                } else {
                    console.error('File input not found');
                }
            });
            uploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
            uploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
            uploadZone.addEventListener('drop', this.handleDrop.bind(this));
        }
        
        if (fileInput) {
            fileInput.addEventListener('change', this.handleFileSelect.bind(this));
            // Add direct click handler for debugging
            fileInput.addEventListener('click', (e) => {
                console.log('File input directly clicked');
            });
        }
        
        // Multiple file upload
        const multipleUploadZone = document.getElementById('multipleUploadZone');
        const multipleFileInput = document.getElementById('multipleFileInput');
        
        if (multipleUploadZone) {
            multipleUploadZone.addEventListener('click', (e) => {
                console.log('Multiple upload zone clicked');
                console.log('Multiple file input element:', multipleFileInput);
                console.log('Multiple file input exists:', !!multipleFileInput);
                
                if (multipleFileInput) {
                    console.log('Triggering multiple file input click');
                    console.log('Multiple file input disabled:', multipleFileInput.disabled);
                    console.log('Multiple file input style:', multipleFileInput.style.display);
                    
                    // Don't prevent default - let the click bubble up
                    multipleFileInput.click();
                } else {
                    console.error('Multiple file input not found');
                }
            });
            multipleUploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
            multipleUploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
            multipleUploadZone.addEventListener('drop', this.handleDrop.bind(this));
        }
        
        if (multipleFileInput) {
            multipleFileInput.addEventListener('change', this.handleMultipleFileSelect.bind(this));
            // Add direct click handler for debugging
            multipleFileInput.addEventListener('click', (e) => {
                console.log('Multiple file input directly clicked');
            });
        }
    }
    
    updateUploadInterface() {
        const singleUpload = document.getElementById('singleUpload');
        const multipleUpload = document.getElementById('multipleUpload');
        
        if (this.documentType === 'salary_slip_multiple') {
            if (singleUpload) singleUpload.style.display = 'none';
            if (multipleUpload) multipleUpload.style.display = 'block';
        } else {
            if (singleUpload) singleUpload.style.display = 'block';
            if (multipleUpload) multipleUpload.style.display = 'none';
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
            if (uploadIcon) uploadIcon.textContent = '✅';
            if (uploadTitle) uploadTitle.textContent = 'File Selected!';
            if (uploadSubtitle) uploadSubtitle.textContent = 'Click to change or drag another file';
            uploadZone.classList.add('file-selected');
        } else {
            if (uploadIcon) uploadIcon.textContent = '📁';
            if (uploadTitle) uploadTitle.textContent = 'Drag & Drop PDF here';
            if (uploadSubtitle) uploadSubtitle.textContent = 'or click to browse';
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
        
        console.log('Drop event triggered');
        console.log('DataTransfer files:', e.dataTransfer.files);
        
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const files = Array.from(e.dataTransfer.files);
            console.log('Processing dropped files:', files);
            this.processFiles(files);
        } else {
            console.log('No files in drop event');
        }
    }
    
    handleFileSelect(e) {
        console.log('File select event triggered');
        console.log('Event target:', e.target);
        console.log('Files:', e.target.files);
        
        if (e.target.files && e.target.files.length > 0) {
            const files = Array.from(e.target.files);
            console.log('Processing files:', files);
            this.processFiles(files);
        } else {
            console.log('No files selected');
        }
    }
    
    handleMultipleFileSelect(e) {
        console.log('Multiple file select event triggered');
        console.log('Event target:', e.target);
        console.log('Files:', e.target.files);
        
        if (e.target.files && e.target.files.length > 0) {
            const files = Array.from(e.target.files);
            console.log('Processing multiple files:', files);
            this.processFiles(files);
        } else {
            console.log('No files selected');
        }
    }
    
    async processFiles(files) {
        console.log('📁 PROCESSING FILES - Starting with files:', files.map(f => f.name));
        
        // If we're clearing files, don't process anything
        if (this.isClearingFiles) {
            console.log('📁 PROCESSING FILES - Skipping because files are being cleared');
            return;
        }
        
        const validFiles = files.filter(file => this.validateFile(file));
        console.log('📁 PROCESSING FILES - Valid files:', validFiles.map(f => f.name));
        
        if (this.documentType === 'salary_slip_multiple') {
            console.log('📁 PROCESSING FILES - Using MULTIPLE file path');
            // For multiple files, add to existing list
            this.uploadedFiles = [...this.uploadedFiles, ...validFiles];
            
            // Limit to max files
            if (this.uploadedFiles.length > this.maxFiles) {
                this.uploadedFiles = this.uploadedFiles.slice(0, this.maxFiles);
                this.showError(`Maximum ${this.maxFiles} files allowed. Only first ${this.maxFiles} files will be processed.`);
            }
            this.updateFileList();
        } else {
            console.log('📁 PROCESSING FILES - Using SINGLE file path, document type:', this.documentType);
            // For single file, replace existing
            this.uploadedFiles = validFiles.slice(0, 1);
            this.updateSingleFileStatus();
        }
        
        console.log('📁 PROCESSING FILES - Final uploaded files:', this.uploadedFiles.map(f => f.name));
        
        // Check if any files are password-protected
        if (this.uploadedFiles.length > 0) {
            console.log('📁 PROCESSING FILES - Files present, checking password protection');
            await this.checkPasswordProtection();
        } else {
            console.log('📁 PROCESSING FILES - No files present, hiding password section');
            this.hidePasswordSection();
        }
        
        this.updateProcessButton();
    }
    
    async checkPasswordProtection() {
        console.log('Checking password protection for files:', this.uploadedFiles.map(f => f.name));
        
        let hasPasswordProtectedFiles = false;
        let passwordProtectedFiles = [];
        
        // Show checking message
        this.updatePasswordHelpMessage('Checking password protection...');
        
        try {
            // Check each file for password protection
            for (const file of this.uploadedFiles) {
                console.log(`Checking password protection for: ${file.name}`);
                
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch('/api/check-pdf-password', {
                    method: 'POST',
                    headers: {
                        'X-User-ID': this.userId
                    },
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    console.log(`Password check result for ${file.name}:`, result);
                    
                    // Store password protection status for this file
                    this.filePasswordStatus.set(file.name, result.is_password_protected);
                    
                    if (result.is_password_protected) {
                        hasPasswordProtectedFiles = true;
                        passwordProtectedFiles.push(file.name);
                        console.log(`File ${file.name} is password-protected`);
                    }
                } else {
                    console.warn(`Failed to check password protection for ${file.name}`);
                }
            }
            
            // Show or hide password section based on results
            if (hasPasswordProtectedFiles) {
                console.log('Password-protected files detected, showing password section');
                this.showPasswordSection(passwordProtectedFiles);
            } else {
                console.log('No password-protected files detected, hiding password section');
                this.hidePasswordSection();
            }
            
        } catch (error) {
            console.error('Error checking password protection:', error);
            // On error, show password section as fallback
            this.showPasswordSection(['Unknown files']);
        }
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
            if (singleFileName) singleFileName.textContent = file.name;
            if (singleFileSize) singleFileSize.textContent = this.formatFileSize(file.size);
            if (singleFileStatus) singleFileStatus.style.display = 'block';
            
            // Add success indicator
            if (singleFileStatus) singleFileStatus.classList.add('file-selected');
        } else {
            if (singleFileStatus) singleFileStatus.style.display = 'none';
            if (singleFileStatus) singleFileStatus.classList.remove('file-selected');
        }
        
        // Update upload zone appearance
        this.updateUploadZoneAppearance();
    }
    
    clearSingleFile() {
        console.log('🗑️ CLEARING SINGLE FILE - Starting clearSingleFile method');
        this.uploadedFiles = [];
        this.updateSingleFileStatus();
        this.updateProcessButton();
        
        // Check if password section should be hidden
        this.checkPasswordSectionVisibility();
        
        // Clear the file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
        
        console.log('🗑️ CLEARING SINGLE FILE - Single file cleared');
    }
    
    updateFileList() {
        console.log('📋 UPDATING FILE LIST - Files:', this.uploadedFiles.map(f => f.name));
        const fileList = document.getElementById('fileList');
        console.log('📋 UPDATING FILE LIST - File list element found:', !!fileList);
        
        if (!fileList) return;
        
        fileList.innerHTML = '';
        
        this.uploadedFiles.forEach((file, index) => {
            console.log(`📋 UPDATING FILE LIST - Creating file item for ${file.name} at index ${index}`);
            const fileItem = this.createFileItem(file, index);
            fileList.appendChild(fileItem);
        });
        
        console.log('📋 UPDATING FILE LIST - File list updated, children count:', fileList.children.length);
    }
    
    createFileItem(file, index) {
        console.log(`📄 CREATING FILE ITEM - File: ${file.name}, Index: ${index}`);
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
            <button class="file-remove" onclick="console.log('🗑️ CLOSE BUTTON CLICKED - Index:', ${index}); documentUploader.removeFile(${index})" title="Remove file">×</button>
        `;
        
        console.log(`📄 CREATING FILE ITEM - File item created for ${file.name}`);
        console.log(`📄 CREATING FILE ITEM - Close button onclick: onclick="console.log('🗑️ CLOSE BUTTON CLICKED - Index:', ${index}); documentUploader.removeFile(${index})"`);
        
        return fileItem;
    }
    
    removeFile(index) {
        console.log('🗑️ REMOVING FILE - Index:', index, 'File:', this.uploadedFiles[index]?.name);
        
        // Remove the file
        this.uploadedFiles.splice(index, 1);
        this.updateFileList();
        this.updateProcessButton();
        
        // Check if password section should be hidden
        this.checkPasswordSectionVisibility();
        
        console.log('🗑️ REMOVING FILE - File removed, remaining files:', this.uploadedFiles.map(f => f.name));
    }
    
    checkPasswordSectionVisibility() {
        console.log('🔍 CHECKING PASSWORD SECTION VISIBILITY - Remaining files:', this.uploadedFiles.map(f => f.name));
        console.log('🔍 CHECKING PASSWORD SECTION VISIBILITY - Password status map:', Array.from(this.filePasswordStatus.entries()));
        
        // If no files remain, hide password section
        if (this.uploadedFiles.length === 0) {
            console.log('🔍 CHECKING PASSWORD SECTION VISIBILITY - No files remaining, hiding password section');
            this.hidePasswordSection();
            return;
        }
        
        // Check if any remaining files are password-protected using stored status
        let hasPasswordProtectedFiles = false;
        
        for (const file of this.uploadedFiles) {
            const isProtected = this.filePasswordStatus.get(file.name);
            console.log(`🔍 CHECKING PASSWORD SECTION VISIBILITY - File ${file.name} password status:`, isProtected);
            
            if (isProtected === true) {
                hasPasswordProtectedFiles = true;
                console.log(`🔍 CHECKING PASSWORD SECTION VISIBILITY - File ${file.name} is password-protected`);
                break; // Found at least one protected file, no need to check others
            }
        }
        
        // Show or hide password section based on results
        if (hasPasswordProtectedFiles) {
            console.log('🔍 CHECKING PASSWORD SECTION VISIBILITY - Password-protected files found, keeping password section');
            // Keep password section visible
        } else {
            console.log('🔍 CHECKING PASSWORD SECTION VISIBILITY - No password-protected files found, hiding password section');
            this.hidePasswordSection();
        }
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
        if (!processButton) return;
        
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
        console.log('🗑️ CLEARING FILES - Starting clearFiles method');
        this.isClearingFiles = true; // Set flag to prevent password section from showing
        
        this.uploadedFiles = [];
        this.updateFileList();
        this.updateSingleFileStatus();
        this.updateProcessButton();
        
        console.log('🗑️ CLEARING FILES - About to hide password section');
        this.hidePasswordSection();
        
        // Clear password inputs
        const singlePasswordInput = document.getElementById('singlePasswordInput');
        const multiplePasswordInput = document.getElementById('multiplePasswordInput');
        
        if (singlePasswordInput) singlePasswordInput.value = '';
        if (multiplePasswordInput) multiplePasswordInput.value = '';
        this.pdfPassword = '';
        
        // Clear password status map
        this.filePasswordStatus.clear();
        
        // Clear file inputs
        const fileInput = document.getElementById('fileInput');
        const multipleFileInput = document.getElementById('multipleFileInput');
        if (fileInput) fileInput.value = '';
        if (multipleFileInput) multipleFileInput.value = '';
        
        // Reset flag after a short delay to allow any pending events to complete
        setTimeout(() => {
            this.isClearingFiles = false;
            console.log('🗑️ CLEARING FILES - clearFiles method completed, flag reset');
        }, 100);
    }
    
    showError(message) {
        const errorMessage = document.getElementById('errorMessage');
        const errorText = document.getElementById('errorText');
        
        if (errorText) errorText.textContent = message;
        if (errorMessage) errorMessage.style.display = 'flex';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideError();
        }, 5000);
    }
    
    hideError() {
        const errorMessage = document.getElementById('errorMessage');
        if (errorMessage) errorMessage.style.display = 'none';
    }
    
    showInfoMessage(message) {
        // Create a temporary info message
        const infoDiv = document.createElement('div');
        infoDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #3b82f6;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            z-index: 10000;
            font-weight: 500;
            max-width: 300px;
        `;
        infoDiv.textContent = message;
        document.body.appendChild(infoDiv);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            if (infoDiv.parentNode) {
                infoDiv.remove();
            }
        }, 4000);
    }
    
    showSuccessMessage(message) {
        // Create a temporary success message
        const successDiv = document.createElement('div');
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            z-index: 10000;
            font-weight: 500;
            max-width: 300px;
        `;
        successDiv.textContent = message;
        document.body.appendChild(successDiv);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.remove();
            }
        }, 3000);
    }
    
    showErrorMessage(message) {
        // Create a temporary error message
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ef4444;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
            z-index: 10000;
            font-weight: 500;
            max-width: 300px;
        `;
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
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
            
            // Add PDF password if provided
            const password = this.getCurrentPassword();
            if (password) {
                formData.append('pdf_password', password);
            }
            
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
        
        if (uploadProgress) uploadProgress.style.display = 'block';
        
        // Simulate progress
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            
            if (progressFill) progressFill.style.width = `${progress}%`;
            
            if (progressText) {
                if (progress < 30) {
                    progressText.textContent = 'Uploading files...';
                } else if (progress < 60) {
                    progressText.textContent = 'Extracting text...';
                } else if (progress < 90) {
                    progressText.textContent = 'Processing with AI...';
                }
            }
        }, 200);
        
        // Store interval for cleanup
        this.progressInterval = interval;
    }
    
    hideProgress() {
        const uploadProgress = document.getElementById('uploadProgress');
        if (uploadProgress) uploadProgress.style.display = 'none';
        
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        const progressFill = document.getElementById('progressFill');
        if (progressFill) progressFill.style.width = '0%';
    }
}

// Global functions for HTML onclick handlers
function goBack() {
    window.history.back();
}

function processDocuments() {
    if (window.documentUploader) {
        window.documentUploader.processDocuments();
    }
}

function hideError() {
    if (window.documentUploader) {
        window.documentUploader.hideError();
    }
}

// Initialize the DocumentUploader when the page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing DocumentUploader...');
    window.documentUploader = new DocumentUploader();
});
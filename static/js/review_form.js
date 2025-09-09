// Review Form Page JavaScript

class FinancialDataReview {
    constructor() {
        this.sessionId = null;
        this.extractedData = null;
        this.processingSummary = null;
        this.isDraft = false;
        
        this.initializeForm();
        this.loadData();
        this.initializeEventListeners();
    }
    
    initializeForm() {
        // Set default values
        document.getElementById('standardDeduction').value = '50000';
        
        // Add input validation
        this.addInputValidation();
    }
    
    addInputValidation() {
        const inputs = document.querySelectorAll('input[type="number"]');
        
        inputs.forEach(input => {
            input.addEventListener('input', (e) => {
                this.validateField(e.target);
                this.updateFormValidation();
            });
            
            input.addEventListener('blur', (e) => {
                this.validateField(e.target);
                this.updateFormValidation();
            });
        });
    }
    
    async loadData() {
        try {
            // Check if we have data from session storage
            this.sessionId = sessionStorage.getItem('session_id');
            console.log('Loaded session ID from storage:', this.sessionId);
            const extractedDataStr = sessionStorage.getItem('extracted_data');
            const processingSummaryStr = sessionStorage.getItem('processing_summary');
            this.isDraft = sessionStorage.getItem('is_draft') === 'true';
            console.log('Is draft:', this.isDraft);
            console.log('Session storage contents:', {
                session_id: sessionStorage.getItem('session_id'),
                extracted_data: extractedDataStr ? 'present' : 'missing',
                processing_summary: processingSummaryStr ? 'present' : 'missing',
                is_draft: sessionStorage.getItem('is_draft')
            });
            
            if (extractedDataStr) {
                this.extractedData = JSON.parse(extractedDataStr);
                this.populateForm();
            }
            
            if (processingSummaryStr) {
                this.processingSummary = JSON.parse(processingSummaryStr);
                this.showProcessingSummary();
            }
            
            // If no session data, check for draft
            if (!this.sessionId && !this.isDraft) {
                this.checkForDraft();
            }
            
        } catch (error) {
            console.error('Failed to load data:', error);
            this.showError('Failed to load financial data. Please try uploading again.');
        }
    }
    
    async checkForDraft() {
        try {
            const response = await fetch('/api/drafts');
            if (response.ok) {
                const drafts = await response.json();
                if (drafts.length > 0) {
                    this.showDraftNotification(drafts[0]);
                }
            }
        } catch (error) {
            console.log('No existing drafts found');
        }
    }
    
    populateForm() {
        if (!this.extractedData) return;
        
        // Populate form fields with extracted data
        const fieldMappings = {
            'financial_year': 'financialYear',
            'age': 'age',
            'gross_salary': 'grossSalary',
            'basic_salary': 'basicSalary',
            'hra_received': 'hraReceived',
            'rent_paid': 'rentPaid',
            'lta_received': 'ltaReceived',
            'other_exemptions': 'otherExemptions',
            'deduction_80c': 'deduction80c',
            'deduction_80d': 'deduction80d',
            'deduction_80dd': 'deduction80dd',
            'deduction_80e': 'deduction80e',
            'deduction_80tta': 'deduction80tta',
            'home_loan_interest': 'homeLoanInterest',
            'other_deductions': 'otherDeductions',
            'other_income': 'otherIncome',
            'standard_deduction': 'standardDeduction',
            'professional_tax': 'professionalTax',
            'tds': 'tds'
        };
        
        Object.entries(fieldMappings).forEach(([key, fieldId]) => {
            const field = document.getElementById(fieldId);
            if (field && this.extractedData[key] !== undefined) {
                // Special handling for optional fields that might be 0
                if ((key === 'other_deductions' || key === 'other_income') && this.extractedData[key] === 0) {
                    field.value = ''; // Leave empty for 0 values
                } else {
                    field.value = this.extractedData[key];
                }
                this.validateField(field);
            }
        });
        
        // Update form validation
        this.updateFormValidation();
    }
    
    showProcessingSummary() {
        if (!this.processingSummary) return;
        
        const summarySection = document.getElementById('processingSummary');
        const filesProcessed = document.getElementById('filesProcessed');
        const documentType = document.getElementById('documentType');
        const accuracy = document.getElementById('accuracy');
        const summaryNotes = document.getElementById('summaryNotes');
        
        // Populate summary data
        filesProcessed.textContent = this.processingSummary.files_processed || 'Unknown';
        
        const docType = this.processingSummary.document_type || 'Unknown';
        documentType.textContent = this.formatDocumentType(docType);
        
        const acc = this.processingSummary.estimated_accuracy || 'Unknown';
        accuracy.textContent = this.formatAccuracy(acc);
        
        // Show processing notes
        if (this.processingSummary.processing_notes && this.processingSummary.processing_notes.length > 0) {
            const notesList = this.processingSummary.processing_notes.map(note => `<li>${note}</li>`).join('');
            summaryNotes.innerHTML = `
                <h4>Processing Notes:</h4>
                <ul>${notesList}</ul>
            `;
        }
        
        summarySection.style.display = 'block';
    }
    
    formatDocumentType(docType) {
        const typeMap = {
            'salary_slip': 'Salary Slip',
            'form16': 'Form 16',
            'salary_slip_single': 'Single Salary Slip',
            'salary_slip_multiple': 'Multiple Salary Slips'
        };
        return typeMap[docType] || docType;
    }
    
    formatAccuracy(accuracy) {
        const accuracyMap = {
            'low': 'Low',
            'medium': 'Medium',
            'good': 'Good',
            'very_good': 'Very Good',
            'excellent': 'Excellent'
        };
        return accuracyMap[accuracy] || accuracy;
    }
    
    validateField(field) {
        const value = parseFloat(field.value) || 0;
        const fieldName = field.name;
        
        // Remove existing validation classes
        field.classList.remove('error', 'success');
        const formField = field.closest('.form-field');
        if (formField) {
            formField.classList.remove('error', 'success');
        }
        
        let isValid = true;
        let errorMessage = '';
        
        // Field-specific validation
        switch (fieldName) {
            case 'age':
                if (value < 18 || value > 100) {
                    isValid = false;
                    errorMessage = 'Age must be between 18 and 100 years';
                }
                break;
                
            case 'financial_year':
                const fyPattern = /^\d{4}-\d{2}$/;
                if (!fyPattern.test(field.value)) {
                    isValid = false;
                    errorMessage = 'Financial year must be in format YYYY-YY';
                }
                break;
                
            case 'gross_salary':
                if (value < 300000) {
                    isValid = false;
                    errorMessage = 'Gross salary seems too low for salaried employee';
                }
                break;
                
            case 'basic_salary':
                const grossSalary = parseFloat(document.getElementById('grossSalary').value) || 0;
                if (value > grossSalary) {
                    isValid = false;
                    errorMessage = 'Basic salary cannot be greater than gross salary';
                }
                break;
                
            case 'deduction_80c':
                if (value > 150000) {
                    isValid = false;
                    errorMessage = '80C deduction cannot exceed ₹1,50,000';
                }
                break;
                
            case 'deduction_80d':
                if (value > 25000) {
                    isValid = false;
                    errorMessage = '80D deduction cannot exceed ₹25,000';
                }
                break;
                
            case 'deduction_80dd':
                if (value > 125000) {
                    isValid = false;
                    errorMessage = '80DD deduction cannot exceed ₹1,25,000';
                }
                break;
                
            case 'deduction_80e':
                if (value > 40000) {
                    isValid = false;
                    errorMessage = '80E deduction cannot exceed ₹40,000';
                }
                break;
                
            case 'deduction_80tta':
                if (value > 10000) {
                    isValid = false;
                    errorMessage = '80TTA deduction cannot exceed ₹10,000';
                }
                break;
                
            case 'home_loan_interest':
                if (value > 200000) {
                    isValid = false;
                    errorMessage = 'Home loan interest cannot exceed ₹2,00,000';
                }
                break;
                
            case 'hra_received':
                // HRA validation is informational only - don't mark as invalid
                // All combinations are valid:
                // - HRA > 0, Rent = 0 (living with family/company accommodation)
                // - HRA > 0, Rent > 0 (paying rent)
                // - HRA = 0, Rent = 0 (no HRA claimed)
                // - HRA = 0, Rent > 0 (paying rent but no HRA from employer)
                break;
                
            case 'rent_paid':
                // Rent paid validation - all values are valid (0 or positive)
                // No cross-validation needed since HRA validation is removed
                break;
        }
        
        // Apply validation styling
        if (isValid) {
            field.classList.add('success');
            if (formField) formField.classList.add('success');
            
            // Clear any existing error message
            const helpText = formField ? formField.querySelector('.field-help') : null;
            if (helpText) {
                helpText.textContent = '';
                helpText.style.color = '';
            }
        } else {
            field.classList.add('error');
            if (formField) formField.classList.add('error');
            
            // Show error in help text
            const helpText = formField.querySelector('.field-help');
            if (helpText) {
                helpText.textContent = errorMessage;
                helpText.style.color = '#dc3545';
            }
        }
        
        return isValid;
    }
    
    clearFieldError(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.remove('error');
            const formField = field.closest('.form-field');
            if (formField) {
                formField.classList.remove('error');
                const helpText = formField.querySelector('.field-help');
                if (helpText) {
                    helpText.textContent = '';
                    helpText.style.color = '';
                }
            }
        }
    }
    
    // Debug method to manually trigger validation update
    refreshValidation() {
        const hraField = document.getElementById('hraReceived');
        const rentField = document.getElementById('rentPaid');
        
        if (hraField) this.validateField(hraField);
        if (rentField) this.validateField(rentField);
        
        this.updateFormValidation();
        
        console.log('Validation refreshed');
    }
    
    updateFormValidation() {
        const requiredFields = ['financial_year', 'age', 'gross_salary', 'basic_salary'];
        const submitButton = document.querySelector('button[type="submit"]');
        
        let isValid = true;
        
        // Check required fields
        requiredFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field && (!field.value || parseFloat(field.value) <= 0)) {
                isValid = false;
            }
        });
        
        // Check for validation errors
        const errorFields = document.querySelectorAll('.form-field.error');
        if (errorFields.length > 0) {
            isValid = false;
        }
        
        submitButton.disabled = !isValid;
    }
    
    showValidationMessages() {
        const validationMessages = document.getElementById('validationMessages');
        const validationList = document.getElementById('validationList');
        
        const errors = [];
        
        // Collect all validation errors
        const errorFields = document.querySelectorAll('.form-field.error');
        errorFields.forEach(field => {
            const input = field.querySelector('input');
            const helpText = field.querySelector('.field-help');
            if (helpText && helpText.style.color === 'rgb(220, 53, 69)') {
                errors.push(helpText.textContent);
            }
        });
        
        // Check required fields
        const requiredFields = ['gross_salary', 'basic_salary'];
        requiredFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field || !field.value.trim()) {
                errors.push(`${this.getFieldLabel(fieldName)} is required`);
            }
        });
        
        if (errors.length > 0) {
            validationList.innerHTML = errors.map(error => `<li>${error}</li>`).join('');
            validationMessages.style.display = 'block';
            return false;
        } else {
            validationMessages.style.display = 'none';
            return true;
        }
    }
    
    getFieldLabel(fieldName) {
        const labelMap = {
            'gross_salary': 'Gross Salary',
            'basic_salary': 'Basic Salary',
            'hra_received': 'HRA Received',
            'rent_paid': 'Rent Paid',
            'deduction_80c': '80C Deduction',
            'deduction_80d': '80D Deduction',
            'professional_tax': 'Professional Tax',
            'tds': 'TDS'
        };
        return labelMap[fieldName] || fieldName;
    }
    
    async saveDraft() {
        try {
            const formData = this.getFormData();
            
            const response = await fetch('/api/save-draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.sessionId = result.draft_id;
                sessionStorage.setItem('session_id', this.sessionId);
                
                this.showSuccessMessage('Draft saved successfully!');
            } else {
                throw new Error('Failed to save draft');
            }
            
        } catch (error) {
            console.error('Save draft error:', error);
            this.showError('Failed to save draft. Please try again.');
        }
    }
    
    async submitForm() {
        try {
            if (!this.showValidationMessages()) {
                return;
            }
            
            // Validate session ID before submitting
            if (!this.sessionId || this.sessionId === 'undefined' || this.sessionId === 'null') {
                console.error('Invalid session ID:', this.sessionId);
                this.showErrorMessage('Session expired. Please start over from the upload page.');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
                return;
            }
            
            const formData = this.getFormData();
            
            // Submit to API
            const response = await fetch('/api/submit-financials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Store session data
                this.sessionId = result.session_id;
                sessionStorage.setItem('session_id', this.sessionId);
                
                // Redirect to tax results page
                window.location.href = '/tax-results';
                
            } else {
                throw new Error('Failed to submit financial data');
            }
            
        } catch (error) {
            console.error('Form submission error:', error);
            this.showError('Failed to submit form. Please try again.');
        }
    }
    
    getFormData() {
        const form = document.getElementById('financialForm');
        const formData = new FormData(form);
        
        const data = {};
        
        // Collect all form fields explicitly
        const fieldNames = [
            'financial_year', 'age', 'gross_salary', 'basic_salary',
            'hra_received', 'rent_paid', 'lta_received', 'other_exemptions',
            'deduction_80c', 'deduction_80d', 'deduction_80dd', 'deduction_80e',
            'deduction_80tta', 'home_loan_interest', 'other_deductions',
            'other_income', 'standard_deduction', 'professional_tax', 'tds'
        ];
        
        // Get values from form fields
        fieldNames.forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                if (fieldName === 'financial_year') {
                    data[fieldName] = field.value;
                } else if (fieldName === 'age') {
                    data[fieldName] = parseInt(field.value) || null;
                } else {
                    // For optional fields, use null if empty, otherwise parse as float
                    if (fieldName === 'other_deductions' || fieldName === 'other_income') {
                        data[fieldName] = field.value.trim() === '' ? null : parseFloat(field.value) || 0;
                    } else {
                        data[fieldName] = parseFloat(field.value) || 0;
                    }
                }
            } else {
                console.warn(`Field ${fieldName} not found in form`);
                // Set default values for missing fields
                if (fieldName === 'financial_year') {
                    data[fieldName] = '2024-25';
                } else if (fieldName === 'age') {
                    data[fieldName] = null;
                } else {
                    data[fieldName] = 0;
                }
            }
        });
        
        // Add session and status information
        console.log('Session ID in getFormData:', this.sessionId);
        if (this.sessionId && this.sessionId !== 'undefined' && this.sessionId !== 'null') {
            data.session_id = this.sessionId;
        } else {
            console.error('Invalid session ID in getFormData:', this.sessionId);
        }
        
        data.status = 'completed';
        data.is_draft = false;
        
        console.log('Form data being submitted:', data);
        return data;
    }
    
    showSuccessMessage(message) {
        // Create success notification
        const notification = document.createElement('div');
        notification.className = 'success-notification';
        notification.innerHTML = `
            <div class="success-content">
                <div class="success-icon">✅</div>
                <div class="success-text">
                    <h4>Success!</h4>
                    <p>${message}</p>
                </div>
            </div>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border: 1px solid #28a745;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            max-width: 350px;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }
    
    showError(message) {
        // Create error notification
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.innerHTML = `
            <div class="error-content">
                <div class="error-icon">⚠️</div>
                <div class="error-text">
                    <h4>Error</h4>
                    <p>${message}</p>
                </div>
            </div>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border: 1px solid #dc3545;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            max-width: 350px;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    initializeEventListeners() {
        const form = document.getElementById('financialForm');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitForm();
        });
    }
}

// Global functions for HTML onclick handlers
function goBack() {
    window.history.back();
}

function saveDraft() {
    if (financialReview) {
        financialReview.saveDraft();
    }
}

// Initialize review form when DOM is loaded
let financialReview;

document.addEventListener('DOMContentLoaded', () => {
    financialReview = new FinancialDataReview();
});

// Add notification styles
const style = document.createElement('style');
style.textContent = `
    .success-notification,
    .error-notification {
        animation: slideIn 0.3s ease-out;
    }
    
    .success-content,
    .error-content {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .success-icon {
        font-size: 2rem;
        color: #28a745;
    }
    
    .error-icon {
        font-size: 2rem;
        color: #dc3545;
    }
    
    .success-text h4,
    .error-text h4 {
        margin: 0 0 0.25rem 0;
        font-size: 1rem;
    }
    
    .success-text h4 {
        color: #28a745;
    }
    
    .error-text h4 {
        color: #dc3545;
    }
    
    .success-text p,
    .error-text p {
        margin: 0;
        font-size: 0.9rem;
        color: #666;
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

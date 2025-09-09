// Tax Results Page JavaScript

class TaxResults {
    constructor() {
        this.sessionId = null;
        this.taxResults = null;
        this.selectedRegime = null;
        
        this.initializePage();
    }
    
    async initializePage() {
        try {
            // Get session ID from storage
            this.sessionId = sessionStorage.getItem('session_id');
            
            if (!this.sessionId) {
                this.showError('No session found. Please start from the beginning.');
                return;
            }
            
            // Start tax calculation
            await this.calculateTax();
            
        } catch (error) {
            console.error('Page initialization failed:', error);
            this.showError('Failed to initialize page. Please try again.');
        }
    }
    
    async calculateTax() {
        try {
            this.showLoading();
            
            // Call tax calculation API
            const response = await fetch('/api/calculate-tax', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`Tax calculation failed: ${response.statusText}`);
            }
            
            this.taxResults = await response.json();
            
            console.log('Tax calculation response:', this.taxResults);
            
            // Hide loading and show results
            this.hideLoading();
            
            if (this.taxResults.calculation_details) {
                this.displayResults(this.taxResults.calculation_details);
            } else {
                throw new Error('Invalid response format: missing calculation_details');
            }
            
        } catch (error) {
            console.error('Tax calculation failed:', error);
            this.showError(`Tax calculation failed: ${error.message}`);
        }
    }
    
    showLoading() {
        document.getElementById('loadingState').style.display = 'block';
        document.getElementById('resultsContainer').style.display = 'none';
        document.getElementById('errorState').style.display = 'none';
    }
    
    hideLoading() {
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('resultsContainer').style.display = 'block';
    }
    
    showError(message) {
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('resultsContainer').style.display = 'none';
        document.getElementById('errorState').style.display = 'block';
        document.getElementById('errorMessage').textContent = message;
    }
    
    displayResults() {
        if (!this.taxResults) return;
        
        const details = this.taxResults.calculation_details;
        
        // Update summary section
        this.updateSummarySection(details);
        
        // Update regime comparison
        this.updateRegimeComparison(details);
        
        // Update regime selection options
        this.updateRegimeSelection(details);
        
        // Update recommendations
        this.updateRecommendations(this.taxResults.recommendations);
        
        // Set default selection to best regime
        this.selectedRegime = details.comparison.best_regime;
        document.getElementById(`${this.selectedRegime}RegimeOption`).checked = true;
    }
    
    updateSummarySection(details) {
        try {
            // Gross Income
            const grossIncome = details.old_regime?.gross_total_income || 0;
            document.getElementById('grossIncome').textContent = 
                `₹${grossIncome.toLocaleString('en-IN')}`;
            
            // Best Regime
            const bestRegime = details.comparison?.best_regime || 'old';
            document.getElementById('bestRegime').textContent = 
                bestRegime === 'old' ? 'Old Regime' : 'New Regime';
            
            // Tax Savings
            const savings = details.comparison?.tax_savings || 0;
            document.getElementById('taxSavings').textContent = 
                `₹${savings.toLocaleString('en-IN')}`;
        } catch (error) {
            console.error('Error updating summary section:', error);
            console.log('Details object:', details);
        }
    }
    
    updateRegimeComparison(details) {
        // Old Regime
        this.updateRegimeCard('old', details.old_regime);
        
        // New Regime
        this.updateRegimeCard('new', details.new_regime);
    }
    
    updateRegimeCard(regime, data) {
        try {
            const prefix = regime === 'old' ? 'old' : 'new';
            
            // Tax amount
            const totalTax = data?.total_tax || 0;
            document.getElementById(`${prefix}RegimeTax`).textContent = 
                totalTax.toLocaleString('en-IN');
            
            // Taxable income
            const taxableIncome = data?.taxable_income || 0;
            document.getElementById(`${prefix}TaxableIncome`).textContent = 
                `₹${taxableIncome.toLocaleString('en-IN')}`;
            
            // Total deductions
            const totalDeductions = data?.deductions?.total_deductions || 0;
            document.getElementById(`${prefix}TotalDeductions`).textContent = 
                `₹${totalDeductions.toLocaleString('en-IN')}`;
            
            // Tax amount (before cess)
            const taxAmount = data?.tax_amount || 0;
            document.getElementById(`${prefix}TaxAmount`).textContent = 
                `₹${taxAmount.toLocaleString('en-IN')}`;
            
            // Cess amount
            const cessAmount = data?.cess_amount || 0;
            document.getElementById(`${prefix}CessAmount`).textContent = 
                `₹${cessAmount.toLocaleString('en-IN')}`;
            
            // Deductions breakdown
            if (data?.deductions) {
                this.updateDeductionList(`${prefix}DeductionList`, data.deductions);
            }
            
            // Slab breakdown
            if (data?.slab_breakdown) {
                this.updateSlabList(`${prefix}SlabList`, data.slab_breakdown);
            }
        } catch (error) {
            console.error(`Error updating ${regime} regime card:`, error);
            console.log('Data object:', data);
        }
    }
    
    updateDeductionList(listId, deductions) {
        const listElement = document.getElementById(listId);
        listElement.innerHTML = '';
        
        const deductionItems = [
            { label: 'HRA Exemption', value: deductions.hra_exemption },
            { label: 'Standard Deduction', value: deductions.standard_deduction },
            { label: '80C Investments', value: deductions.section_80c },
            { label: '80D Medical Insurance', value: deductions.section_80d },
            { label: 'Professional Tax', value: deductions.professional_tax }
        ];
        
        deductionItems.forEach(item => {
            if (item.value > 0) {
                const itemElement = document.createElement('div');
                itemElement.className = 'deduction-item';
                itemElement.innerHTML = `
                    <span class="label">${item.label}</span>
                    <span class="value">₹${item.value.toLocaleString('en-IN')}</span>
                `;
                listElement.appendChild(itemElement);
            }
        });
    }
    
    updateSlabList(listId, slabBreakdown) {
        const listElement = document.getElementById(listId);
        listElement.innerHTML = '';
        
        if (slabBreakdown && slabBreakdown.length > 0) {
            slabBreakdown.forEach(slab => {
                const itemElement = document.createElement('div');
                itemElement.className = 'slab-item';
                itemElement.innerHTML = `
                    <span class="label">${slab.slab} (${slab.rate})</span>
                    <span class="value">₹${slab.tax.toLocaleString('en-IN')}</span>
                `;
                listElement.appendChild(itemElement);
            });
        } else {
            const itemElement = document.createElement('div');
            itemElement.className = 'slab-item';
            itemElement.innerHTML = `
                <span class="label">No tax applicable</span>
                <span class="value">₹0</span>
            `;
            listElement.appendChild(itemElement);
        }
    }
    
    updateRegimeSelection(details) {
        // Update tax amounts in selection options
        document.getElementById('oldRegimeOptionTax').textContent = 
            details.old_regime.total_tax.toLocaleString('en-IN');
        
        document.getElementById('newRegimeOptionTax').textContent = 
            details.new_regime.total_tax.toLocaleString('en-IN');
    }
    
    updateRecommendations(recommendations) {
        const container = document.getElementById('recommendationsContainer');
        container.innerHTML = '';
        
        if (recommendations && recommendations.recommendations) {
            recommendations.recommendations.forEach(rec => {
                const itemElement = document.createElement('div');
                itemElement.className = `recommendation-item ${rec.priority}-priority`;
                
                const icon = this.getRecommendationIcon(rec.type);
                
                itemElement.innerHTML = `
                    <div class="recommendation-header">
                        <div class="recommendation-icon">${icon}</div>
                        <h4 class="recommendation-title">${rec.title}</h4>
                    </div>
                    <p class="recommendation-description">${rec.description}</p>
                `;
                
                container.appendChild(itemElement);
            });
        } else {
            // Show default message
            const itemElement = document.createElement('div');
            itemElement.className = 'recommendation-item low-priority';
            itemElement.innerHTML = `
                <div class="recommendation-header">
                    <div class="recommendation-icon">💡</div>
                    <h4 class="recommendation-title">No Specific Recommendations</h4>
                </div>
                <p class="recommendation-description">Your tax calculation is complete. Consider consulting a tax professional for personalized advice.</p>
            `;
            container.appendChild(itemElement);
        }
    }
    
    getRecommendationIcon(type) {
        const iconMap = {
            'regime_choice': '🏆',
            'deduction_optimization': '💰',
            'hra_optimization': '🏠',
            'professional_tax': '📋'
        };
        return iconMap[type] || '💡';
    }
    
    async saveRegimeSelection() {
        try {
            if (!this.selectedRegime) {
                alert('Please select a tax regime first.');
                return;
            }
            
            const response = await fetch('/api/select-regime', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    selected_regime: this.selectedRegime
                })
            });
            
            if (response.ok) {
                this.showSuccessMessage('Regime selection saved successfully!');
            } else {
                throw new Error('Failed to save regime selection');
            }
            
        } catch (error) {
            console.error('Failed to save regime selection:', error);
            this.showErrorMessage('Failed to save regime selection. Please try again.');
        }
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
    
    showErrorMessage(message) {
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
        // Regime selection change
        const regimeOptions = document.querySelectorAll('input[name="regimeSelection"]');
        regimeOptions.forEach(option => {
            option.addEventListener('change', (e) => {
                this.selectedRegime = e.target.value;
            });
        });
    }
}

// Global functions for HTML onclick handlers
function goBack() {
    // Navigate back to review form instead of using browser history
    window.location.href = '/review-form';
}

function saveRegimeSelection() {
    if (taxResults) {
        taxResults.saveRegimeSelection();
    }
}

function proceedToAIAdvisor() {
    // Store selected regime in session storage
    if (taxResults && taxResults.selectedRegime) {
        sessionStorage.setItem('selected_regime', taxResults.selectedRegime);
    }
    
    // Get session ID
    const sessionId = sessionStorage.getItem('session_id');
    
    // Navigate to AI Advisor with session ID
    if (sessionId) {
        window.location.href = `/ai-advisor?session_id=${sessionId}`;
    } else {
        window.location.href = '/ai-advisor';
    }
}

function retryCalculation() {
    if (taxResults) {
        taxResults.calculateTax();
    }
}

// Initialize tax results when DOM is loaded
let taxResults;

document.addEventListener('DOMContentLoaded', () => {
    taxResults = new TaxResults();
    taxResults.initializeEventListeners();
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


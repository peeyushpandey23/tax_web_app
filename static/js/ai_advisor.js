/**
 * AI Advisor Frontend JavaScript
 * Handles conversation flow and recommendation display
 */

class AIAdvisor {
    constructor() {
        this.sessionId = null;
        this.currentRound = 1;
        this.maxRounds = 4;
        this.isProcessing = false;
        this.conversationStarted = false;
        
        this.initializeElements();
        this.attachEventListeners();
        this.startConversation();
    }
    
    initializeElements() {
        // Main elements
        this.financialSummary = document.getElementById('financialSummary');
        this.aiQuestionCard = document.getElementById('aiQuestionCard');
        this.responseInputContainer = document.getElementById('responseInputContainer');
        this.processingScreen = document.getElementById('processingScreen');
        this.recommendationsContainer = document.getElementById('recommendationsContainer');
        this.errorContainer = document.getElementById('errorContainer');
        this.actionButtons = document.getElementById('actionButtons');
        
        // Question elements
        this.questionText = document.getElementById('questionText');
        this.roundIndicator = document.getElementById('roundIndicator');
        
        // Response elements
        this.userResponse = document.getElementById('userResponse');
        this.charCount = document.getElementById('charCount');
        this.submitResponse = document.getElementById('submitResponse');
        
        // Summary elements
        this.grossSalary = document.getElementById('grossSalary');
        this.taxSavings = document.getElementById('taxSavings');
        this.bestRegime = document.getElementById('bestRegime');
        
        // Recommendations elements
        this.conversationSummary = document.getElementById('conversationSummary');
        this.summaryText = document.getElementById('summaryText');
        this.recommendationsList = document.getElementById('recommendationsList');
        
        // Error elements
        this.errorMessage = document.getElementById('errorMessage');
    }
    
    attachEventListeners() {
        // Response input handling
        this.userResponse.addEventListener('input', () => {
            this.updateCharCount();
            this.updateSubmitButton();
        });
        
        this.userResponse.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!this.submitResponse.disabled) {
                    this.submitResponse.click();
                }
            }
        });
        
        // Submit response
        this.submitResponse.addEventListener('click', () => {
            this.submitUserResponse();
        });
    }
    
    async startConversation() {
        try {
            // Get session ID from URL or session storage
            this.sessionId = this.getSessionId();
            if (!this.sessionId) {
                this.showError('Session ID not found. Please start from the tax results page.');
                return;
            }
            
            // Show loading state
            this.showProcessingScreen('Starting conversation...');
            
            // Start conversation with AI
            const response = await fetch('/api/ai-advisor/start-conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.conversationStarted = true;
                this.currentRound = data.round;
                this.displayFinancialSummary(data.financial_summary);
                this.displayQuestion(data.question, data.round);
                this.hideProcessingScreen();
            } else {
                throw new Error('Failed to start conversation');
            }
            
        } catch (error) {
            console.error('Failed to start conversation:', error);
            this.showError('AI Advisor service is temporarily unavailable. Please try again later.');
        }
    }
    
    async submitUserResponse() {
        if (this.isProcessing) return;
        
        const response = this.userResponse.value.trim();
        if (!response) return;
        
        try {
            this.isProcessing = true;
            this.setSubmitButtonLoading(true);
            
            const requestData = {
                session_id: this.sessionId,
                question: this.questionText.textContent,
                response: response,
                round: this.currentRound
            };
            
            const apiResponse = await fetch('/api/ai-advisor/process-response', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (!apiResponse.ok) {
                throw new Error(`HTTP ${apiResponse.status}: ${apiResponse.statusText}`);
            }
            
            const data = await apiResponse.json();
            
            if (data.success) {
                if (data.is_final) {
                    // Show recommendations
                    this.showProcessingScreen('Generating your personalized recommendations...');
                    setTimeout(() => {
                        this.displayRecommendations(data.recommendations, data.conversation_summary);
                        this.hideProcessingScreen();
                    }, 2000);
                } else {
                    // Show next question
                    this.currentRound = data.round;
                    this.displayQuestion(data.question, data.round);
                    this.clearResponse();
                }
            } else {
                throw new Error('Failed to process response');
            }
            
        } catch (error) {
            console.error('Failed to submit response:', error);
            this.showError('AI Advisor service is temporarily unavailable. Please try again later.');
        } finally {
            this.isProcessing = false;
            this.setSubmitButtonLoading(false);
        }
    }
    
    displayFinancialSummary(summary) {
        if (!summary) return;
        
        this.grossSalary.textContent = `₹${summary.gross_salary.toLocaleString()}`;
        this.taxSavings.textContent = `₹${summary.tax_savings.toLocaleString()}`;
        this.bestRegime.textContent = summary.best_regime.toUpperCase();
        
        this.financialSummary.style.display = 'block';
    }
    
    displayQuestion(question, round) {
        this.questionText.textContent = question;
        this.roundIndicator.textContent = `Question ${round}`;
        
        this.aiQuestionCard.style.display = 'flex';
        this.responseInputContainer.style.display = 'block';
        
        // Focus on textarea
        setTimeout(() => {
            this.userResponse.focus();
        }, 300);
    }
    
    displayRecommendations(recommendations, conversationSummary) {
        // Show conversation summary if available
        if (conversationSummary && conversationSummary !== 'AI service temporarily unavailable') {
            this.summaryText.textContent = conversationSummary;
            this.conversationSummary.style.display = 'block';
        }
        
        // Display recommendations
        this.recommendationsList.innerHTML = '';
        
        recommendations.forEach((rec, index) => {
            const recCard = this.createRecommendationCard(rec, index);
            this.recommendationsList.appendChild(recCard);
        });
        
        this.recommendationsContainer.style.display = 'block';
        this.actionButtons.style.display = 'flex';
        
        // Hide conversation elements
        this.aiQuestionCard.style.display = 'none';
        this.responseInputContainer.style.display = 'none';
    }
    
    createRecommendationCard(recommendation, index) {
        const card = document.createElement('div');
        card.className = `recommendation-card ${recommendation.priority}-priority`;
        
        const priorityClass = recommendation.priority === 'high' ? 'high-priority' : 
                             recommendation.priority === 'low' ? 'low-priority' : '';
        
        card.innerHTML = `
            <div class="recommendation-header">
                <h4 class="recommendation-title">${recommendation.title}</h4>
                ${recommendation.estimated_savings > 0 ? 
                    `<span class="recommendation-savings">₹${recommendation.estimated_savings.toLocaleString()}</span>` : 
                    ''
                }
            </div>
            <p class="recommendation-description">${recommendation.description}</p>
            ${recommendation.action_items && recommendation.action_items.length > 0 ? `
                <div class="action-items">
                    <h5>Implementation Steps:</h5>
                    <ul>
                        ${recommendation.action_items.map(item => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        `;
        
        return card;
    }
    
    showProcessingScreen(message = 'Processing...') {
        this.processingScreen.querySelector('h3').textContent = message;
        this.processingScreen.style.display = 'flex';
        
        // Hide other elements
        this.aiQuestionCard.style.display = 'none';
        this.responseInputContainer.style.display = 'none';
        this.recommendationsContainer.style.display = 'none';
        this.errorContainer.style.display = 'none';
    }
    
    hideProcessingScreen() {
        this.processingScreen.style.display = 'none';
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorContainer.style.display = 'flex';
        
        // Hide other elements
        this.aiQuestionCard.style.display = 'none';
        this.responseInputContainer.style.display = 'none';
        this.processingScreen.style.display = 'none';
        this.recommendationsContainer.style.display = 'none';
    }
    
    updateCharCount() {
        const count = this.userResponse.value.length;
        this.charCount.textContent = `${count}/1000`;
        
        if (count > 900) {
            this.charCount.style.color = '#dc3545';
        } else if (count > 700) {
            this.charCount.style.color = '#ffc107';
        } else {
            this.charCount.style.color = '#666';
        }
    }
    
    updateSubmitButton() {
        const hasText = this.userResponse.value.trim().length > 0;
        this.submitResponse.disabled = !hasText || this.isProcessing;
    }
    
    setSubmitButtonLoading(loading) {
        if (loading) {
            this.submitResponse.classList.add('loading');
            this.submitResponse.disabled = true;
        } else {
            this.submitResponse.classList.remove('loading');
            this.updateSubmitButton();
        }
    }
    
    clearResponse() {
        this.userResponse.value = '';
        this.updateCharCount();
        this.updateSubmitButton();
    }
    
    getSessionId() {
        // Try to get session ID from various sources
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get('session_id') || 
                        sessionStorage.getItem('session_id') ||
                        localStorage.getItem('session_id');
        
        console.log('Session ID found:', sessionId);
        return sessionId;
    }
}

// Initialize AI Advisor when page loads
document.addEventListener('DOMContentLoaded', () => {
    new AIAdvisor();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Page became visible, could refresh data if needed
        console.log('AI Advisor page became visible');
    }
});

// Handle beforeunload to warn about leaving
window.addEventListener('beforeunload', (e) => {
    // Only warn if conversation is in progress
    const aiAdvisor = window.aiAdvisor;
    if (aiAdvisor && aiAdvisor.conversationStarted && !aiAdvisor.recommendationsContainer.style.display !== 'none') {
        e.preventDefault();
        e.returnValue = '';
    }
});

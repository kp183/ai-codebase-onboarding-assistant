// AI Codebase Onboarding Assistant Frontend JavaScript

class ChatApp {
    constructor() {
        this.chatMessages = document.getElementById('chat-messages');
        this.chatForm = document.getElementById('chat-form');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.whereToStartBtn = document.getElementById('where-to-start-btn');
        this.errorDisplay = document.getElementById('error-display');
        
        this.isProcessing = false;
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        this.chatForm.addEventListener('submit', (e) => this.handleChatSubmit(e));
        this.whereToStartBtn.addEventListener('click', () => this.handleWhereToStart());
        
        // Auto-resize input and handle enter key
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.chatForm.dispatchEvent(new Event('submit'));
            }
        });
        
        // Clear error when user starts typing
        this.chatInput.addEventListener('input', () => {
            this.hideError();
            this.validateInput();
        });
    }
    
    validateInput() {
        const question = this.chatInput.value.trim();
        const isValid = question.length > 0;
        
        // Update send button state
        this.sendBtn.disabled = !isValid || this.isProcessing;
        
        // Show/hide validation hint
        if (question.length === 0 && this.chatInput.value.length > 0) {
            this.showError('Question cannot be empty or whitespace only');
        } else {
            this.hideError();
        }
        
        return isValid;
    }
    
    async handleChatSubmit(e) {
        e.preventDefault();
        const question = this.chatInput.value.trim();
        
        if (!this.validateInput() || this.isProcessing) return;
        
        this.hideError();
        this.addUserMessage(question);
        this.chatInput.value = '';
        this.setLoading(true);
        this.showTypingIndicator();
        
        try {
            const response = await this.sendChatRequest(question);
            this.hideTypingIndicator();
            this.addAssistantMessage(response);
        } catch (error) {
            this.hideTypingIndicator();
            this.handleError(error);
        } finally {
            this.setLoading(false);
        }
    }
    async handleWhereToStart() {
        if (this.isProcessing) return;
        
        this.hideError();
        this.setLoading(true);
        this.showTypingIndicator();
        
        try {
            const response = await fetch('/api/predefined/where-to-start');
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Server error (${response.status})`);
            }
            
            const data = await response.json();
            this.hideTypingIndicator();
            this.addAssistantMessage(data);
        } catch (error) {
            this.hideTypingIndicator();
            this.handleError(error, 'Failed to load getting started information');
        } finally {
            this.setLoading(false);
        }
    }
    
    handleError(error, customMessage = null) {
        let errorMessage = customMessage || 'An error occurred while processing your request';
        
        if (error.message) {
            if (error.message.includes('422')) {
                errorMessage = 'Please check your input and try again';
            } else if (error.message.includes('500')) {
                errorMessage = 'Server error. Please try again in a moment';
            } else if (error.message.includes('network') || error.message.includes('fetch')) {
                errorMessage = 'Network error. Please check your connection and try again';
            } else if (error.message.includes('timeout')) {
                errorMessage = 'Request timed out. Please try again';
            } else {
                errorMessage = error.message;
            }
        }
        
        this.showError(errorMessage);
        console.error('Request failed:', error);
        
        // Add error message to chat
        this.addErrorMessage(errorMessage);
    }
    
    addErrorMessage(errorText) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message error';
        messageDiv.innerHTML = `
            <div class="message-content">
                <span class="error-icon">⚠️</span>
                ${this.escapeHtml(errorText)}
                <button class="retry-btn" onclick="chatApp.retryLastRequest()">Try Again</button>
            </div>
        `;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    retryLastRequest() {
        // Simple retry - focus input for user to resubmit
        this.chatInput.focus();
        this.hideError();
    }
    
    askDemoQuestion(question) {
        // Simulate user typing the question and submitting
        this.chatInput.value = question;
        this.chatForm.dispatchEvent(new Event('submit'));
    }
    
    handleRepoInput() {
        const repoUrl = document.getElementById('repo-url').value.trim();
        
        if (!repoUrl) {
            this.showError('Please enter a repository URL');
            return;
        }
        
        // Demo version - show friendly message
        this.addSystemMessage(
            `🔍 Repository analysis requested for: ${repoUrl}\n\n` +
            `💡 **Demo Mode**: This demo currently shows a pre-indexed repository (AI Codebase Onboarding Assistant). ` +
            `The repository analysis feature is coming soon!\n\n` +
            `For now, you can explore the current codebase using the questions above or ask your own questions about the code structure, APIs, and functionality.`
        );
        
        // Clear the input
        document.getElementById('repo-url').value = '';
    }
    
    addSystemMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        messageDiv.innerHTML = `
            <div class="message-content">${this.escapeHtml(message).replace(/\n/g, '<br>')}</div>
        `;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    async sendChatRequest(question) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        messageDiv.innerHTML = `
            <div class="message-content">${this.escapeHtml(message)}</div>
        `;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    addAssistantMessage(response) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        
        let sourcesHtml = '';
        if (response.sources && response.sources.length > 0) {
            sourcesHtml = `
                <div class="sources">
                    <h4>📁 Source References (${response.sources.length})</h4>
                    ${response.sources.map((source, index) => `
                        <div class="source-ref" onclick="copyToClipboard('${source.file_path}:${source.start_line}-${source.end_line}')" data-source-index="${index}">
                            <span class="file-icon">📄</span>
                            <span class="file-path" title="${source.file_path}">${this.truncateFilePath(source.file_path)}</span>
                            <span class="line-numbers">${source.start_line}-${source.end_line}</span>
                            <div class="source-ref-tooltip">Click to copy file reference</div>
                        </div>
                    `).join('')}
                    <div class="sources-note">
                        <small>💡 Click any reference to copy the file path and line numbers</small>
                    </div>
                </div>
            `;
        } else {
            // Show a message when there are no sources
            sourcesHtml = `
                <div class="no-sources">
                    <small>ℹ️ No specific source references found for this response</small>
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">${this.formatMessageContent(response.answer)}</div>
            ${sourcesHtml}
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    truncateFilePath(filePath, maxLength = 50) {
        if (filePath.length <= maxLength) return filePath;
        
        const parts = filePath.split('/');
        if (parts.length <= 2) return filePath;
        
        // Show first and last parts with ellipsis in between
        const first = parts[0];
        const last = parts[parts.length - 1];
        const remaining = maxLength - first.length - last.length - 5; // 5 for ".../"
        
        if (remaining > 0) {
            return `${first}/.../${last}`;
        }
        
        // If still too long, just truncate the end
        return filePath.substring(0, maxLength - 3) + '...';
    }
    
    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <span>AI is thinking</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    showError(message) {
        this.errorDisplay.textContent = message;
        this.errorDisplay.style.display = 'block';
    }
    
    hideError() {
        this.errorDisplay.style.display = 'none';
    }
    
    addErrorMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'error-message';
        messageDiv.innerHTML = `
            <strong>⚠️ Error:</strong> ${this.escapeHtml(message)}
        `;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    setLoading(isLoading) {
        this.isProcessing = isLoading;
        this.sendBtn.disabled = isLoading;
        this.chatInput.disabled = isLoading;
        this.whereToStartBtn.disabled = isLoading;
        
        const btnText = this.sendBtn.querySelector('.btn-text');
        const btnLoading = this.sendBtn.querySelector('.btn-loading');
        
        if (isLoading) {
            btnText.style.display = 'none';
            btnLoading.style.display = 'flex';
        } else {
            btnText.style.display = 'flex';
            btnLoading.style.display = 'none';
        }
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatMessageContent(text) {
        // Basic formatting for better readability
        return this.escapeHtml(text)
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>');
    }
}

// Utility function for copying source references
function copyToClipboard(text) {
    // Enhanced copy function with better formatting
    const formattedText = text.includes(':') ? text : `${text}`;
    
    navigator.clipboard.writeText(formattedText).then(() => {
        showCopySuccess(`Copied: ${formattedText}`);
        console.log('Copied to clipboard:', formattedText);
    }).catch(err => {
        console.error('Failed to copy to clipboard:', err);
        // Fallback for older browsers
        fallbackCopyTextToClipboard(formattedText);
    });
}

// Enhanced copy function that can handle different source reference formats
function copySourceReference(sourceElement) {
    const filePath = sourceElement.querySelector('.file-path').textContent;
    const lineNumbers = sourceElement.querySelector('.line-numbers').textContent;
    const fullReference = `${filePath}:${lineNumbers}`;
    
    copyToClipboard(fullReference);
}

// Fallback copy function for older browsers
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showCopySuccess(`Copied: ${text}`);
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
        showCopyError();
    }
    
    document.body.removeChild(textArea);
}

// Show copy success indication
function showCopySuccess(message = '📋 Copied to clipboard!') {
    showToast(message, 'success');
}

// Show copy error indication
function showCopyError() {
    showToast('❌ Failed to copy to clipboard', 'error');
}

// Generic toast notification function
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `copy-toast toast-${type}`;
    toast.textContent = message;
    
    const backgroundColor = type === 'success' ? '#27ae60' : '#e74c3c';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${backgroundColor};
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        font-size: 14px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
        max-width: 300px;
        word-wrap: break-word;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Add CSS animations for toast
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize the chat app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 ChatApp initializing...');
    try {
        window.chatApp = new ChatApp();
        console.log('✅ ChatApp initialized successfully!');
    } catch (error) {
        console.error('❌ ChatApp initialization failed:', error);
    }
});
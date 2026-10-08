// AI Codebase Onboarding Assistant Frontend JavaScript

class ChatApp {
    constructor() {
        this.chatMessages = document.getElementById('chat-messages');
        this.chatForm = document.getElementById('chat-form');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.whereToStartBtn = document.getElementById('where-to-start-btn');
        this.repoAnalyzeBtn = document.querySelector('.repo-analyze-btn');
        this.errorDisplay = document.getElementById('error-display');
        this.repoId = null;
        
        this.isProcessing = false;
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        this.chatForm.addEventListener('submit', (e) => this.handleChatSubmit(e));
        this.whereToStartBtn.addEventListener('click', () => this.handleWhereToStart());
        this.repoAnalyzeBtn.addEventListener('click', () => this.handleRepoInput());
        document.querySelectorAll('[data-demo-question]').forEach((button) => {
            button.addEventListener('click', () => this.askDemoQuestion(button.dataset.demoQuestion));
        });
        
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
            const query = this.repoId ? `?repo_id=${encodeURIComponent(this.repoId)}` : '';
            const response = await fetch(`/api/predefined/where-to-start${query}`);
            
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
        const content = document.createElement('div');
        content.className = 'message-content';
        const icon = document.createElement('span');
        icon.className = 'error-icon';
        icon.textContent = '⚠️';
        const retry = document.createElement('button');
        retry.className = 'retry-btn';
        retry.textContent = 'Try Again';
        retry.addEventListener('click', () => this.retryLastRequest());
        content.append(icon, document.createTextNode(` ${errorText} `), retry);
        messageDiv.appendChild(content);
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
    
    async handleRepoInput() {
        const repoUrl = document.getElementById('repo-url').value.trim();
        
        if (!repoUrl) {
            this.showError('Please enter a repository URL');
            return;
        }
        
        const button = document.querySelector('.repo-analyze-btn');
        button.disabled = true;
        this.addSystemMessage('Cloning and indexing repository…');
        try {
            const response = await fetch('/api/ingest', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({repository_url: repoUrl})
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.detail || `Ingestion failed (${response.status})`);
            this.repoId = data.repo_id;
            const stats = document.querySelectorAll('.stats-bar .stat-value');
            if (stats.length >= 3) {
                stats[0].textContent = 'ingested';
                stats[1].textContent = `${data.chunks_indexed} chunks`;
                stats[2].textContent = `${data.file_count} files`;
            }
            this.addSystemMessage(`Indexed ${data.chunks_indexed} chunks from ${data.file_count} files. Ask questions about this repository now.`);
            document.getElementById('repo-url').value = '';
        } catch (error) {
            this.addSystemMessage(`Repository ingestion failed: ${error.message}`);
        } finally {
            button.disabled = false;
        }
    }
    
    addSystemMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = message;
        content.style.whiteSpace = 'pre-wrap';
        messageDiv.appendChild(content);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    async sendChatRequest(question) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question, repo_id: this.repoId })
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
        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = message;
        content.style.whiteSpace = 'pre-wrap';
        messageDiv.appendChild(content);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    addAssistantMessage(response) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = response.answer || '';
        messageContent.style.whiteSpace = 'pre-wrap';
        messageDiv.appendChild(messageContent);

        if (response.sources && response.sources.length > 0) {
            const sources = document.createElement('div');
            sources.className = 'sources';
            const heading = document.createElement('h4');
            heading.textContent = `📁 Source References (${response.sources.length})`;
            sources.appendChild(heading);
            response.sources.forEach((source) => {
                const reference = document.createElement('div');
                reference.className = 'source-ref';
                const icon = document.createElement('span');
                icon.className = 'file-icon';
                icon.textContent = '📄';
                const path = document.createElement('span');
                path.className = 'file-path';
                path.title = source.file_path;
                path.textContent = this.truncateFilePath(source.file_path);
                const lines = document.createElement('span');
                lines.className = 'line-numbers';
                lines.textContent = `${source.start_line}-${source.end_line}`;
                const tooltip = document.createElement('div');
                tooltip.className = 'source-ref-tooltip';
                tooltip.textContent = 'Click to copy file reference';
                reference.append(icon, path, lines, tooltip);
                reference.addEventListener('click', () => {
                    copyToClipboard(`${source.file_path}:${source.start_line}-${source.end_line}`);
                });
                sources.appendChild(reference);
            });
            const note = document.createElement('div');
            note.className = 'sources-note';
            const small = document.createElement('small');
            small.textContent = '💡 Click any reference to copy the file path and line numbers';
            note.appendChild(small);
            sources.appendChild(note);
            messageDiv.appendChild(sources);
        } else {
            const noSources = document.createElement('div');
            noSources.className = 'no-sources';
            const small = document.createElement('small');
            small.textContent = 'ℹ️ No specific source references found for this response';
            noSources.appendChild(small);
            messageDiv.appendChild(noSources);
        }
        
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
        const label = document.createElement('span');
        label.textContent = 'AI is thinking';
        const dots = document.createElement('div');
        dots.className = 'typing-dots';
        for (let index = 0; index < 3; index += 1) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            dots.appendChild(dot);
        }
        typingDiv.append(label, dots);
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

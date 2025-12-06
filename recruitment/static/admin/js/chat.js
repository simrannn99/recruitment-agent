/**
 * Chat Interface for Django Admin
 * Handles communication with FastAPI chat endpoints
 */

class ChatInterface {
    constructor() {
        this.sessionId = null;
        this.apiUrl = FASTAPI_URL; // Defined in template
        this.messagesContainer = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-btn');
        this.sessionIdDisplay = document.getElementById('session-id');
        this.loadingIndicator = document.getElementById('loading');
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.startSession();
    }
    
    setupEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.handleSend());
        
        // Enter key to send (Shift+Enter for new line)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });
        
        // Enable/disable send button based on input
        this.messageInput.addEventListener('input', () => {
            const hasText = this.messageInput.value.trim().length > 0;
            this.sendButton.disabled = !hasText;
        });
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });
    }
    
    async startSession() {
        try {
            const response = await fetch(`${this.apiUrl}/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: null })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.sessionId = data.session_id;
            
            // Update UI
            this.sessionIdDisplay.textContent = this.sessionId.substring(0, 8) + '...';
            this.loadingIndicator.remove();
            
            // Add welcome message
            this.addMessage('assistant', data.message);
            
            // Enable input
            this.messageInput.disabled = false;
            this.messageInput.focus();
            
        } catch (error) {
            console.error('Failed to start session:', error);
            this.showError('Failed to start conversation. Please refresh the page.');
        }
    }
    
    async handleSend() {
        const text = this.messageInput.value.trim();
        if (!text || !this.sessionId) return;
        
        // Disable input while sending
        this.messageInput.disabled = true;
        this.sendButton.disabled = true;
        
        // Add user message to UI immediately
        this.addMessage('user', text);
        
        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        
        // Show typing indicator
        const typingIndicator = this.showTypingIndicator();
        
        try {
            const response = await fetch(`${this.apiUrl}/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: text
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Remove typing indicator
            typingIndicator.remove();
            
            // Add assistant response
            this.addMessage('assistant', data.message, {
                intent: data.intent,
                confidence: data.confidence
            });
            
        } catch (error) {
            console.error('Failed to send message:', error);
            typingIndicator.remove();
            this.showError('Failed to send message. Please try again.');
        } finally {
            // Re-enable input
            this.messageInput.disabled = false;
            this.messageInput.focus();
        }
    }
    
    addMessage(role, content, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        // Format content (preserve line breaks, handle markdown-like formatting)
        bubble.innerHTML = this.formatMessage(content);
        
        messageDiv.appendChild(bubble);
        
        // Add metadata if present
        if (metadata.intent) {
            const meta = document.createElement('div');
            meta.className = 'message-meta';
            meta.textContent = `${metadata.intent} (${Math.round(metadata.confidence * 100)}%)`;
            messageDiv.appendChild(meta);
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessage(text) {
        // Preserve line breaks
        text = text.replace(/\n/g, '<br>');
        
        // Bold text between **
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Bullet points
        text = text.replace(/•/g, '&bull;');
        
        return text;
    }
    
    showTypingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        messageDiv.id = 'typing-indicator';
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        
        messageDiv.appendChild(typingDiv);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        this.messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

// Initialize chat when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ChatInterface();
});

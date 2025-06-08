// static/js/chat.js
document.addEventListener('DOMContentLoaded', function() {
    // Socket.io connection
    const socket = io();
    let currentChatId = null;
    
    // Get current user ID from a data attribute
    const userIdMeta = document.querySelector('meta[name="user-id"]');
    const currentUserId = userIdMeta ? userIdMeta.getAttribute('content') : null;
    
    // Chat elements 
    const chatMessagesList = document.querySelector('.chat-messages');
    const messageForm = document.querySelector('#message-form');
    const messageInput = document.querySelector('#message-input');
    const chatDropdown = document.querySelector('.js-chat-dropdown');
    const chatBadge = document.querySelector('.js-chat-badge');
    const chatMessagesList_dropdown = document.querySelector('.js-chat-messages-list');
    
    // Connect to socket
    socket.on('connect', function() {
        console.log('Connected to socket server');
        
        // Join personal room
        if (currentUserId) {
            socket.emit('join', {room: `user_${currentUserId}`});
        }
        
        // Join chat room if we're on a chat page
        const chatContainer = document.querySelector('#chat-container');
        if (chatContainer) {
            currentChatId = chatContainer.dataset.chatId;
            if (currentChatId) {
                socket.emit('join_chat', {chat_id: currentChatId});
                // Mark messages as read when joining chat
                socket.emit('mark_messages_read', {chat_id: currentChatId});
            }
        }
    });
    
    // Handle getting unread count on page load
    function updateUnreadCount() {
        fetch('api/chats/unread_count')
            .then(response => response.json())
            .then(data => {
                if (data.unread_count > 0) {
                    chatBadge.textContent = data.unread_count;
                    chatBadge.style.display = 'inline-block';
                } else {
                    chatBadge.style.display = 'none';
                }
            })
            .catch(error => console.error('Error fetching unread count:', error));
    }
    
    // Handle getting recent messages for dropdown
    function updateRecentMessages() {
        fetch('api/chats/recent_messages')
            .then(response => response.json())
            .then(messages => {
                chatMessagesList_dropdown.innerHTML = '';
                
                if (messages.length === 0) {
                    chatMessagesList_dropdown.innerHTML = '<li class="dropdown-item">No new messages</li>';
                    return;
                }
                
                messages.forEach(message => {
                    const messageItem = document.createElement('li');
                    messageItem.classList.add('dropdown-item', 'message-preview');
                    if (!message.is_read) {
                        messageItem.classList.add('unread');
                    }
                    
                    messageItem.innerHTML = `
                        <a href="/chat/${message.chat_id}" class="text-decoration-none text-dark">
                            <div class="d-flex align-items-center">
                                <div class="message-preview-content">
                                    <div class="fw-bold">${message.subject}</div>
                                    <small>${message.sender_name}: ${message.content}</small>
                                    <div class="text-muted small">${message.created_at}</div>
                                </div>
                                ${!message.is_read ? '<span class="badge rounded-pill bg-primary ms-auto">New</span>' : ''}
                            </div>
                        </a>
                    `;
                    
                    chatMessagesList_dropdown.appendChild(messageItem);
                });
            })
            .catch(error => console.error('Error fetching recent messages:', error));
    }
    
    // Initialize unread count and recent messages
    updateUnreadCount();
    updateRecentMessages();
    
    // Handle new messages
    socket.on('new_message', function(message) {
        // Update chat messages if we're on the right chat page
        if (currentChatId && currentChatId == message.chat_id) {
            const messagesContainer = document.querySelector('.chat-messages');
            
            if (messagesContainer) {
                const messageElement = document.createElement('div');
                messageElement.classList.add('message');
                
                // Add classes based on whether message is from current user
                if (message.user_id == currentUserId) {
                    messageElement.classList.add('message-outgoing');
                } else {
                    messageElement.classList.add('message-incoming');
                    // Automatically mark as read if we're viewing the chat
                    socket.emit('mark_messages_read', {chat_id: currentChatId});
                }
                
                messageElement.innerHTML = `
                    <div class="message-content">
                        <div class="message-text">${message.content}</div>
                        <div class="message-time">${message.created_at}</div>
                    </div>
                `;
                
                messagesContainer.appendChild(messageElement);
                
                // Scroll to bottom of chat
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
        
        // If the message is not from the current user, update unread count and recent messages
        if (message.user_id != currentUserId) {
            updateUnreadCount();
            updateRecentMessages();
        }
    });
    
    // Handle updating unread count
    socket.on('update_unread_count', function(data) {
        if (data.user_id == currentUserId) {
            updateUnreadCount();
            updateRecentMessages();
        }
    });
    
    // Handle messages marked as read
    socket.on('messages_marked_read', function(data) {
        if (currentChatId && currentChatId == data.chat_id) {
            // Update UI to show messages as read if needed
            const unreadBadges = document.querySelectorAll('.message-unread-indicator');
            unreadBadges.forEach(badge => badge.remove());
        }
    });
    
    // Send message form handler
    if (messageForm) {
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const content = messageInput.value.trim();
            if (!content) return;
            
            socket.emit('send_message', {
                chat_id: currentChatId,
                content: content
            });
            
            // Clear input
            messageInput.value = '';
        });
    }
    
    // Handle chat dropdown toggle
    const chatToggle = document.querySelector('.js-chat-toggle');
    if (chatToggle) {
        chatToggle.addEventListener('click', function() {
            updateRecentMessages();
        });
    }
});
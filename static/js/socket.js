// WebSocket обработчики для всех страниц

class SocketManager {
    constructor() {
        this.socket = null;
        this.eventHandlers = new Map();
    }
    
    connect() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            this.emit('connected');
            console.log('WebSocket connected');
        });
        
        this.socket.on('disconnect', () => {
            this.emit('disconnected');
            console.log('WebSocket disconnected');
        });
        
        this.socket.on('reconnect', () => {
            this.emit('reconnected');
            console.log('WebSocket reconnected');
        });
        
        // Автоматическая подписка на зарегистрированные обработчики
        this.eventHandlers.forEach((handlers, event) => {
            handlers.forEach(handler => {
                this.socket.on(event, handler);
            });
        });
        
        return this.socket;
    }
    
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event).add(handler);
        
        if (this.socket) {
            this.socket.on(event, handler);
        }
    }
    
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).delete(handler);
        }
        
        if (this.socket) {
            this.socket.off(event, handler);
        }
    }
    
    emit(event, data) {
        if (this.socket) {
            this.socket.emit(event, data);
        }
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }
    
    // Вспомогательные методы для игры
    joinLobby(lobbyId) {
        this.emit('join_lobby', { lobby_id: lobbyId });
    }
    
    createLobby(settings) {
        this.emit('create_lobby', { settings });
    }
    
    startGame(lobbyId) {
        this.emit('start_game', { lobby_id: lobbyId });
    }
    
    sendChatMessage(lobbyId, message) {
        this.emit('chat_message', {
            lobby_id: lobbyId,
            message: message
        });
    }
    
    makeAttack(gameId, cardIndex) {
        this.emit('make_attack', {
            game_id: gameId,
            card_index: cardIndex
        });
    }
    
    makeDefense(gameId, cardIndex) {
        this.emit('make_defense', {
            game_id: gameId,
            card_index: cardIndex
        });
    }
    
    takeCards(gameId) {
        this.emit('take_cards', {
            game_id: gameId
        });
    }
    
    passTurn(gameId) {
        this.emit('pass_turn', {
            game_id: gameId
        });
    }
    
    getSocketId() {
        return this.socket ? this.socket.id : null;
    }
}

// Глобальный экземпляр менеджера сокетов
const socketManager = new SocketManager();

// Утилиты для работы с WebSocket
const SocketUtils = {
    // Проверка подключения
    isConnected() {
        return socketManager.socket && socketManager.socket.connected;
    },
    
    // Получение ID сокета
    getSocketId() {
        return socketManager.socket ? socketManager.socket.id : null;
    },
    
    // Переподключение
    reconnect() {
        if (socketManager.socket) {
            socketManager.socket.connect();
        }
    },
    
    // Подписка на стандартные события
    onConnectionChange(callback) {
        socketManager.on('connect', () => callback(true));
        socketManager.on('disconnect', () => callback(false));
        socketManager.on('reconnect', () => callback(true));
    },
    
    // Обработка ошибок
    onError(callback) {
        socketManager.on('error', callback);
    }
};

// Автоматическое подключение при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    socketManager.connect();
});

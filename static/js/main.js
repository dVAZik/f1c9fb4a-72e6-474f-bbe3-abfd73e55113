// Основные утилиты и функции для главной страницы

let socket = null;
let currentView = 'main';
let isConnected = false;

function initSocket() {
    socket = io({
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
    });
    
    socket.on('connect', function() {
        console.log('Connected to server, socket ID:', socket.id);
        isConnected = true;
        showNotification('Подключено к серверу', 'success');
        updateConnectionStatus();
    });
    
    socket.on('disconnect', function(reason) {
        console.log('Disconnected from server:', reason);
        isConnected = false;
        showNotification('Отключено от сервера', 'error');
        updateConnectionStatus();
    });
    
    socket.on('reconnect', function(attemptNumber) {
        console.log('Reconnected to server after', attemptNumber, 'attempts');
        isConnected = true;
        showNotification('Переподключено к серверу', 'success');
        updateConnectionStatus();
    });
    
    socket.on('lobby_created', function(data) {
        console.log('Lobby created response:', data);
        if (data.success && data.redirect_url) {
            showNotification('Лобби создано! Перенаправление...', 'success');
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 500);
        } else {
            showNotification(data.error || 'Ошибка создания лобби', 'error');
        }
    });

    socket.on('join_success', function(data) {
        console.log('Join lobby response:', data);
        if (data.success && data.redirect_url) {
            showNotification('Успешно присоединились к лобби!', 'success');
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 500);
        } else {
            showNotification(data.error || 'Ошибка присоединения к лобби', 'error');
        }
    });
        
    socket.on('lobby_updated', function(data) {
        console.log('Lobby updated:', data);
    });
    
    socket.on('game_started', function(data) {
        console.log('Game started:', data);
        showNotification('Игра начинается!', 'success');
        setTimeout(() => {
            window.location.href = `/game/${data.game_id}`;
        }, 1000);
    });
    
    socket.on('error', function(data) {
        console.error('Socket error:', data);
        showNotification(data.message || 'Произошла ошибка', 'error');
    });
    
    socket.on('connect_error', function(error) {
        console.error('Connection error:', error);
        showNotification('Ошибка подключения к серверу', 'error');
    });
}

function updateConnectionStatus() {
    const statusElement = document.getElementById('connectionStatus');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const buttons = document.querySelectorAll('.nav-btn');
    
    if (isConnected) {
        statusElement.textContent = `🟢 Подключено (${socket.id.substring(0, 8)}...)`;
        statusElement.className = 'connection-status connected';
        loadingOverlay.style.display = 'none';
    } else {
        statusElement.textContent = '🔴 Отключено';
        statusElement.className = 'connection-status disconnected';
        loadingOverlay.style.display = 'flex';
    }
    
    buttons.forEach(btn => {
        btn.disabled = !isConnected;
        btn.style.opacity = isConnected ? '1' : '0.5';
        btn.style.cursor = isConnected ? 'pointer' : 'not-allowed';
    });
}

function showCreateLobby() {
    if (!isConnected) {
        showNotification('Подождите подключения к серверу', 'error');
        return;
    }
    
    hideAllSections();
    document.getElementById('createLobbySection').style.display = 'block';
    currentView = 'create';
}

function hideCreateLobby() {
    document.getElementById('createLobbySection').style.display = 'none';
    currentView = 'main';
}

function showLobbyList() {
    if (!isConnected) {
        showNotification('Подождите подключения к серверу', 'error');
        return;
    }
    
    hideAllSections();
    document.getElementById('lobbyListSection').style.display = 'block';
    loadLobbies();
    currentView = 'lobbies';
}

function hideLobbyList() {
    document.getElementById('lobbyListSection').style.display = 'none';
    currentView = 'main';
}

function showQuickPlay() {
    if (!isConnected) {
        showNotification('Подождите подключения к серверу', 'error');
        return;
    }
    
    hideAllSections();
    document.getElementById('quickPlaySection').style.display = 'block';
    currentView = 'quickplay';
}

function hideQuickPlay() {
    document.getElementById('quickPlaySection').style.display = 'none';
    currentView = 'main';
}

function hideAllSections() {
    document.getElementById('createLobbySection').style.display = 'none';
    document.getElementById('lobbyListSection').style.display = 'none';
    document.getElementById('quickPlaySection').style.display = 'none';
}

function createLobby() {
    if (!isConnected) {
        showNotification('Нет подключения к серверу', 'error');
        return;
    }
    
    const settings = {
        name: document.getElementById('lobbyName').value || 'Моя игра',
        gameType: document.getElementById('gameType').value,
        maxPlayers: parseInt(document.getElementById('maxPlayers').value) || 4,
        botDifficulty: document.getElementById('botDifficulty').value,
        isPublic: document.getElementById('isPublic').checked,
        enableChat: document.getElementById('enableChat').checked,
        minPlayers: 2
    };
    
    console.log('Creating lobby with settings:', settings);
    console.log('Current socket ID:', socket.id);
    
    socket.emit('create_lobby', { settings: settings });
    
    showNotification('Создание лобби...', 'success');
}

function loadLobbies() {
    if (!isConnected) {
        showNotification('Нет подключения к серверу', 'error');
        return;
    }
    
    fetch('/api/lobbies')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const lobbyList = document.getElementById('lobbyList');
            lobbyList.innerHTML = '';
            
            if (!data.lobbies || data.lobbies.length === 0) {
                lobbyList.innerHTML = `
                    <div class="lobby-card">
                        <div class="lobby-header">
                            <div class="lobby-name">Нет доступных лобби</div>
                        </div>
                        <div class="lobby-settings">Создайте свое лобби!</div>
                    </div>
                `;
                return;
            }
            
            data.lobbies.forEach(lobby => {
                const lobbyCard = document.createElement('div');
                lobbyCard.className = 'lobby-card';
                lobbyCard.onclick = () => joinLobby(lobby.lobby_id);
                
                lobbyCard.innerHTML = `
                    <div class="lobby-header">
                        <div class="lobby-name">${lobby.settings.name}</div>
                        <div class="lobby-players">${lobby.players.length}/${lobby.settings.maxPlayers}</div>
                    </div>
                    <div class="lobby-settings">
                        ${lobby.settings.gameType === 'throw' ? 'Подкидной' : 'Переводной'} | 
                        Уровень: ${getBotLevelName(lobby.settings.botDifficulty)} |
                        ${lobby.settings.isPublic ? 'Публичное' : 'Приватное'}
                    </div>
                `;
                
                lobbyList.appendChild(lobbyCard);
            });
        })
        .catch(error => {
            console.error('Error loading lobbies:', error);
            showNotification('Ошибка загрузки лобби', 'error');
        });
}

function getBotLevelName(level) {
    const levels = {
        'easy': 'Легкий',
        'medium': 'Средний', 
        'hard': 'Сложный'
    };
    return levels[level] || 'Средний';
}

function refreshLobbies() {
    if (!isConnected) {
        showNotification('Нет подключения к серверу', 'error');
        return;
    }
    
    loadLobbies();
    showNotification('Список обновлен', 'success');
}

function joinLobby(lobbyId) {
    if (!isConnected) {
        showNotification('Нет подключения к серверу', 'error');
        return;
    }
    
    console.log('Joining lobby:', lobbyId);
    console.log('Current socket ID:', socket.id);
    
    socket.emit('join_lobby', { lobby_id: lobbyId });
    showNotification('Присоединение к лобби...', 'success');
}

function quickPlay() {
    if (!isConnected) {
        showNotification('Подождите подключения к серверу', 'error');
        return;
    }
    
    showQuickPlay();
}

function quickPlayWithBots() {
    if (!isConnected) {
        showNotification('Нет подключения к серверу', 'error');
        return;
    }
    
    const settings = {
        name: 'Быстрая игра',
        gameType: 'throw',
        maxPlayers: 4,
        botDifficulty: 'medium',
        isPublic: false,
        enableChat: false,
        minPlayers: 2
    };
    
    console.log('Quick play with bots:', settings);
    
    socket.emit('create_lobby', { settings: settings });
    
    showNotification('Создание быстрой игры...', 'success');
}

function findRandomGame() {
    if (!isConnected) {
        showNotification('Нет подключения к серверу', 'error');
        return;
    }
    
    // Загружаем публичные лобби и выбираем случайное
    fetch('/api/lobbies')
        .then(response => response.json())
        .then(data => {
            if (data.lobbies && data.lobbies.length > 0) {
                const randomLobby = data.lobbies[Math.floor(Math.random() * data.lobbies.length)];
                joinLobby(randomLobby.lobby_id);
            } else {
                showNotification('Нет доступных игр', 'error');
            }
        })
        .catch(error => {
            console.error('Error finding random game:', error);
            showNotification('Ошибка поиска игры', 'error');
        });
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// Загрузка статистики игрока
function loadPlayerStats() {
    fetch('/api/player/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(stats => {
            if (stats) {
                document.getElementById('gamesCount').textContent = stats.games_played || 0;
                document.getElementById('winRate').textContent = (stats.win_rate || 0) + '%';
            }
        })
        .catch(error => {
            console.error('Error loading player stats:', error);
        });
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing application...');
    initSocket();
    loadPlayerStats();
    updateConnectionStatus();
    
    // Заглушки для демонстрации
    document.getElementById('onlineCount').textContent = Math.floor(Math.random() * 100) + 50;
});

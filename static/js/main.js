// Основные утилиты и функции для главной страницы

let socket = null;
let currentView = 'main';
let isConnected = false;

function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        isConnected = true;
        showNotification('Подключено к серверу', 'success');
        updateConnectionStatus();
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        isConnected = false;
        showNotification('Отключено от сервера', 'error');
        updateConnectionStatus();
    });
    
    socket.on('lobby_created', function(data) {
        console.log('Lobby created:', data);
        if (data.success && data.redirect_url) {
            showNotification('Лобби создано! Перенаправление...', 'success');
            window.location.href = data.redirect_url;
        } else {
            showNotification('Ошибка создания лобби', 'error');
        }
    });
    
    socket.on('lobby_updated', function(data) {
        console.log('Lobby updated:', data);
    });
    
    socket.on('game_started', function(data) {
        console.log('Game started:', data);
        window.location.href = `/game/${data.game_id}`;
    });
    
    socket.on('error', function(data) {
        console.error('Socket error:', data);
        showNotification(data.message, 'error');
    });
}

function updateConnectionStatus() {
    const statusElement = document.getElementById('connectionStatus');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const buttons = document.querySelectorAll('.nav-btn');
    
    if (isConnected) {
        statusElement.textContent = '🟢 Подключено';
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
            
            if (data.lobbies && data.lobbies.length === 0) {
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
            
            if (data.lobbies) {
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
                            Уровень: ${lobby.settings.botDifficulty} |
                            ${lobby.settings.isPublic ? 'Публичное' : 'Приватное'}
                        </div>
                    `;
                    
                    lobbyList.appendChild(lobbyCard);
                });
            }
        })
        .catch(error => {
            console.error('Error loading lobbies:', error);
            showNotification('Ошибка загрузки лобби', 'error');
        });
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
    
    showNotification('Поиск случайной игры...', 'success');
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
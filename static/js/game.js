// Логика игры для game.html

let socket = null;
let gameState = null;
let myPlayerId = null;
let selectedCardIndex = null;

function initSocket() {
    socket = io();
    
    const gameId = window.location.pathname.split('/').pop();
    
    socket.on('connect', function() {
        console.log('Connected to game');
        loadGameState(gameId);
    });
    
    socket.on('game_update', function(data) {
        gameState = data.game;
        updateGameUI();
    });
    
    socket.on('player_turn', function(data) {
        showNotification(`Ход игрока: ${data.player_name}`);
        updateGameUI();
    });
    
    socket.on('card_played', function(data) {
        showNotification(`${data.player_name} сыграл карту`);
        updateGameUI();
    });
    
    socket.on('defense_success', function(data) {
        showNotification('Защита успешна!', 'success');
        updateGameUI();
    });
    
    socket.on('defense_failed', function(data) {
        showNotification('Защита не удалась', 'error');
        updateGameUI();
    });
    
    socket.on('game_over', function(data) {
        showNotification(`Игра окончена! Победитель: ${data.winner}`);
        setTimeout(() => {
            window.location.href = '/';
        }, 5000);
    });
    
    socket.on('error', function(data) {
        showNotification(data.message, 'error');
    });
}

function loadGameState(gameId) {
    fetch(`/api/game/${gameId}`)
        .then(response => response.json())
        .then(data => {
            gameState = data;
            myPlayerId = socket.id;
            updateGameUI();
        })
        .catch(error => {
            console.error('Error loading game:', error);
            showNotification('Ошибка загрузки игры', 'error');
        });
}

function updateGameUI() {
    if (!gameState) return;
    
    // Обновляем информацию о игре
    document.getElementById('trumpSuit').textContent = gameState.trump_suit;
    document.getElementById('deckCount').textContent = gameState.deck_count;
    
    // Обновляем поле боя
    updateBattleField();
    
    // Обновляем руку игрока
    updateMyHand();
    
    // Обновляем информацию о противниках
    updateOpponents();
    
    // Обновляем кнопки управления
    updateControls();
    
    // Обновляем текущего игрока
    updateCurrentPlayer();
}

function updateBattleField() {
    const battleField = document.getElementById('battleField');
    battleField.innerHTML = '';
    
    gameState.table.forEach((pair, index) => {
        const pairElement = document.createElement('div');
        pairElement.className = 'attack-defense-pair';
        
        if (pair.attack_card) {
            const attackCard = createCardElement(pair.attack_card, 'attack');
            pairElement.appendChild(attackCard);
        }
        
        if (pair.defense_card) {
            const defenseCard = createCardElement(pair.defense_card, 'defense');
            pairElement.appendChild(defenseCard);
        } else {
            // Место для защиты
            const defensePlaceholder = document.createElement('div');
            defensePlaceholder.className = 'card';
            defensePlaceholder.style.opacity = '0.3';
            defensePlaceholder.style.border = '2px dashed var(--text-secondary)';
            defensePlaceholder.innerHTML = '<div class="card-center">?</div>';
            pairElement.appendChild(defensePlaceholder);
        }
        
        battleField.appendChild(pairElement);
    });
}

function updateMyHand() {
    const myHand = document.getElementById('myHand');
    myHand.innerHTML = '';
    
    const myPlayer = gameState.players.find(p => p.sid === myPlayerId);
    if (!myPlayer) return;
    
    selectedCardIndex = null;
    
    myPlayer.cards.forEach((card, index) => {
        const cardElement = createCardElement(card, 'hand');
        cardElement.onclick = () => selectCard(index);
        
        // Проверяем можно ли играть эту карту
        if (isCardPlayable(myPlayer, card, index)) {
            cardElement.classList.add('playable');
        }
        
        myHand.appendChild(cardElement);
    });
}

function updateOpponents() {
    const playersContainer = document.getElementById('playersContainer');
    playersContainer.innerHTML = '';
    
    gameState.players.forEach(player => {
        if (player.sid !== myPlayerId) {
            const playerElement = document.createElement('div');
            playerElement.className = 'player-seat';
            
            playerElement.innerHTML = `
                <div class="player-info">
                    ${player.username} (${player.cards.length})
                    ${player.is_attacker ? '⚔️' : ''}
                    ${player.is_defender ? '🛡️' : ''}
                </div>
                <div class="player-cards">
                    ${Array.from({length: player.cards.length}, () => 
                        '<div class="opponent-card"></div>'
                    ).join('')}
                </div>
            `;
            
            playersContainer.appendChild(playerElement);
        }
    });
}

function updateControls() {
    const myPlayer = gameState.players.find(p => p.sid === myPlayerId);
    if (!myPlayer) return;
    
    const isMyTurn = myPlayer.is_attacker || myPlayer.is_defender;
    const canAttack = myPlayer.is_attacker && selectedCardIndex !== null;
    const canDefend = myPlayer.is_defender && selectedCardIndex !== null && 
                     gameState.table.some(pair => !pair.defense_card);
    
    document.getElementById('btnAttack').disabled = !canAttack;
    document.getElementById('btnDefend').disabled = !canDefend;
    document.getElementById('btnTake').disabled = !isMyTurn;
    document.getElementById('btnPass').disabled = !isMyTurn;
}

function updateCurrentPlayer() {
    const currentPlayer = gameState.players[gameState.current_attacker_index];
    if (currentPlayer) {
        document.getElementById('currentPlayer').textContent = 
            currentPlayer.sid === myPlayerId ? 'Вы' : currentPlayer.username;
    }
}

function createCardElement(cardData, type) {
    const card = document.createElement('div');
    const isRed = cardData.suit === '♥' || cardData.suit === '♦';
    
    card.className = `card ${isRed ? 'red' : 'black'} ${type}`;
    card.innerHTML = `
        <div class="card-top">
            <div class="rank">${cardData.rank}</div>
            <div class="suit">${cardData.suit}</div>
        </div>
        <div class="card-center">
            <div class="suit">${cardData.suit}</div>
        </div>
        <div class="card-bottom">
            <div class="rank">${cardData.rank}</div>
            <div class="suit">${cardData.suit}</div>
        </div>
    `;
    
    return card;
}

function selectCard(cardIndex) {
    const myPlayer = gameState.players.find(p => p.sid === myPlayerId);
    if (!myPlayer) return;
    
    const cards = document.querySelectorAll('#myHand .card');
    
    // Снимаем выделение со всех карт
    cards.forEach(card => card.classList.remove('selected'));
    
    // Проверяем можно ли играть выбранную карту
    if (isCardPlayable(myPlayer, myPlayer.cards[cardIndex], cardIndex)) {
        cards[cardIndex].classList.add('selected');
        selectedCardIndex = cardIndex;
    } else {
        selectedCardIndex = null;
        showNotification('Эту карту нельзя играть сейчас', 'error');
    }
}

function isCardPlayable(player, card, cardIndex) {
    if (player.is_attacker) {
        // Для атаки: можно играть любую карту если стол пустой, 
        // или карту того же достоинства что уже на столе
        if (gameState.table.length === 0) return true;
        
        const ranksOnTable = new Set();
        gameState.table.forEach(pair => {
            if (pair.attack_card) ranksOnTable.add(pair.attack_card.rank);
            if (pair.defense_card) ranksOnTable.add(pair.defense_card.rank);
        });
        
        return ranksOnTable.has(card.rank);
    }
    
    if (player.is_defender) {
        // Для защиты: можно играть карту которая бьет последнюю атакующую карту
        if (!gameState.table.length) return false;
        
        const lastAttack = gameState.table[gameState.table.length - 1].attack_card;
        if (!lastAttack) return false;
        
        const attackCard = { suit: lastAttack.suit, rank: lastAttack.rank, value: lastAttack.value };
        
        return (card.suit === attackCard.suit && card.value > attackCard.value) ||
               (card.suit === gameState.trump_suit && attackCard.suit !== gameState.trump_suit);
    }
    
    return false;
}

function makeAttack() {
    if (selectedCardIndex === null) {
        showNotification('Выберите карту для атаки', 'error');
        return;
    }
    
    socket.emit('make_attack', {
        game_id: gameState.game_id,
        card_index: selectedCardIndex
    });
    
    selectedCardIndex = null;
}

function makeDefense() {
    if (selectedCardIndex === null) {
        showNotification('Выберите карту для защиты', 'error');
        return;
    }
    
    socket.emit('make_defense', {
        game_id: gameState.game_id,
        card_index: selectedCardIndex
    });
    
    selectedCardIndex = null;
}

function takeCards() {
    if (confirm('Вы уверены, что хотите взять карты?')) {
        socket.emit('take_cards', {
            game_id: gameState.game_id
        });
    }
}

function passTurn() {
    socket.emit('pass_turn', {
        game_id: gameState.game_id
    });
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    setTimeout(() => notification.style.display = 'none', 3000);
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    initSocket();
});
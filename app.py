import os
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import json
from datetime import datetime
from typing import Dict, List, Optional

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')
app.config['DEBUG'] = os.environ.get('DEBUG', 'False').lower() == 'true'

socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   logger=True,
                   engineio_logger=True)

# База данных в памяти
games = {}
players = {}
lobbies = {}
player_stats = {}

class Card:
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        self.value = self._get_value()
    
    def _get_value(self) -> int:
        values = {
            '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
            'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        return values.get(self.rank, 0)
    
    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"
    
    def to_dict(self) -> Dict:
        return {
            'suit': self.suit,
            'rank': self.rank,
            'value': self.value
        }
    
    def is_trump(self, trump_suit: str) -> bool:
        return self.suit == trump_suit

class Deck:
    def __init__(self):
        self.cards: List[Card] = []
        self.build()
    
    def build(self) -> None:
        suits = ['♥', '♦', '♣', '♠']
        ranks = ['6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.cards = [Card(suit, rank) for suit in suits for rank in ranks]
    
    def shuffle(self) -> None:
        random.shuffle(self.cards)
    
    def deal(self, num_cards: int) -> List[Card]:
        if num_cards > len(self.cards):
            num_cards = len(self.cards)
        dealt_cards = self.cards[:num_cards]
        self.cards = self.cards[num_cards:]
        return dealt_cards
    
    def is_empty(self) -> bool:
        return len(self.cards) == 0

class Player:
    def __init__(self, sid: str, username: str, is_bot: bool = False):
        self.sid = sid
        self.username = username
        self.is_bot = is_bot
        self.cards: List[Card] = []
        self.position: int = 0
        self.is_attacker: bool = False
        self.is_defender: bool = False
    
    def add_cards(self, new_cards: List[Card]) -> None:
        self.cards.extend(new_cards)
        self.sort_cards()
    
    def sort_cards(self) -> None:
        self.cards.sort(key=lambda card: (card.suit != '♣', card.suit != '♠', 
                                        card.suit != '♦', card.suit != '♥', card.value))
    
    def play_card(self, card_index: int) -> Optional[Card]:
        if 0 <= card_index < len(self.cards):
            return self.cards.pop(card_index)
        return None
    
    def can_beat(self, attack_card: Card, trump_suit: str) -> bool:
        for card in self.cards:
            if (card.suit == attack_card.suit and card.value > attack_card.value) or \
               (card.suit == trump_suit and attack_card.suit != trump_suit):
                return True
        return False
    
    def get_playable_cards(self, table: List[Dict], trump_suit: str) -> List[Card]:
        if not table:
            return self.cards
        
        playable = []
        ranks_on_table = {card['rank'] for card in table}
        
        for card in self.cards:
            if card.rank in ranks_on_table:
                playable.append(card)
        
        return playable if playable else self.cards
    
    def to_dict(self):
        return {
            'sid': self.sid,
            'username': self.username,
            'is_bot': self.is_bot,
            'cards': [card.to_dict() for card in self.cards],
            'position': self.position,
            'is_attacker': self.is_attacker,
            'is_defender': self.is_defender
        }

class Game:
    def __init__(self, game_id: str, settings: Dict):
        self.game_id = game_id
        # Нормализуем настройки
        self.settings = {
            'max_players': settings.get('max_players', 4),
            'min_players': settings.get('min_players', 2),
            'game_type': settings.get('game_type', 'throw'),
            'bot_difficulty': settings.get('bot_difficulty', 'medium')
        }
        self.players: List[Player] = []
        self.deck = Deck()
        self.trump_suit = ''
        self.table: List[Dict] = []
        self.attack_cards: List[Dict] = []
        self.defense_cards: List[Dict] = []
        self.current_attacker_index = 0
        self.current_defender_index = 0
        self.game_state = 'waiting'
        self.winner = None
        self.created_at = datetime.now()
        self.move_history: List[Dict] = []
    
    def add_player(self, player: Player) -> bool:
        if len(self.players) < self.settings['max_players']:
            player.position = len(self.players)
            self.players.append(player)
            return True
        return False
    
    def start_game(self) -> bool:
        if len(self.players) < self.settings['min_players']:
            return False
        
        self.deck.shuffle()
        self.trump_suit = random.choice(['♥', '♦', '♣', '♠'])
        
        # Раздача карт
        for player in self.players:
            player.add_cards(self.deck.deal(6))
        
        # Определение первого атакующего
        first_attacker = self._find_first_attacker()
        self.current_attacker_index = first_attacker
        self.players[first_attacker].is_attacker = True
        
        # Определение защищающегося
        self.current_defender_index = (first_attacker + 1) % len(self.players)
        self.players[self.current_defender_index].is_defender = True
        
        self.game_state = 'playing'
        return True
    
    def _find_first_attacker(self) -> int:
        min_trump_value = 15
        first_attacker = 0
        
        for i, player in enumerate(self.players):
            for card in player.cards:
                if card.suit == self.trump_suit and card.value < min_trump_value:
                    min_trump_value = card.value
                    first_attacker = i
        
        return first_attacker
    
    def make_attack(self, player_sid: str, card_index: int) -> bool:
        player = self.get_player_by_sid(player_sid)
        if not player or not player.is_attacker:
            return False
        
        if card_index < 0 or card_index >= len(player.cards):
            return False
        
        card = player.play_card(card_index)
        if card:
            card_dict = card.to_dict()
            self.attack_cards.append(card_dict)
            self.table.append({
                'attack_card': card_dict,
                'defense_card': None
            })
            
            self.move_history.append({
                'type': 'attack',
                'player': player_sid,
                'card': card_dict,
                'timestamp': datetime.now().isoformat()
            })
            
            return True
        return False
    
    def make_defense(self, player_sid: str, card_index: int) -> bool:
        player = self.get_player_by_sid(player_sid)
        if not player or not player.is_defender:
            return False
        
        if not self.attack_cards:
            return False
        
        if card_index < 0 or card_index >= len(player.cards):
            return False
        
        attack_card_dict = self.attack_cards[-1]
        attack_card = Card(attack_card_dict['suit'], attack_card_dict['rank'])
        defense_card = player.cards[card_index]
        
        # Проверка возможности отбития
        if (defense_card.suit == attack_card.suit and defense_card.value > attack_card.value) or \
           (defense_card.suit == self.trump_suit and attack_card.suit != self.trump_suit):
            
            card = player.play_card(card_index)
            if card:
                card_dict = card.to_dict()
                self.defense_cards.append(card_dict)
                self.table[-1]['defense_card'] = card_dict
                
                self.move_history.append({
                    'type': 'defense',
                    'player': player_sid,
                    'card': card_dict,
                    'timestamp': datetime.now().isoformat()
                })
                
                return True
        
        return False
    
    def complete_defense(self) -> bool:
        """Завершение защиты и переход хода"""
        if not self.table:
            return False
        
        # Очистка стола
        self.table.clear()
        self.attack_cards.clear()
        self.defense_cards.clear()
        
        # Добираем карты
        self._deal_cards_to_players()
        
        # Переход хода к следующему игроку
        self._next_turn()
        
        return True
    
    def take_cards(self, player_sid: str) -> bool:
        """Игрок берет карты со стола"""
        player = self.get_player_by_sid(player_sid)
        if not player:
            return False
        
        # Добавляем все карты со стола игроку
        for pair in self.table:
            if pair['attack_card']:
                player.add_cards([Card(pair['attack_card']['suit'], pair['attack_card']['rank'])])
            if pair['defense_card']:
                player.add_cards([Card(pair['defense_card']['suit'], pair['defense_card']['rank'])])
        
        # Очистка стола
        self.table.clear()
        self.attack_cards.clear()
        self.defense_cards.clear()
        
        # Добираем карты
        self._deal_cards_to_players()
        
        # Переход хода к следующему игроку
        self._next_turn_after_take()
        
        return True
    
    def _deal_cards_to_players(self) -> None:
        """Добор карт игрокам"""
        for player in self.players:
            cards_needed = 6 - len(player.cards)
            if cards_needed > 0 and not self.deck.is_empty():
                new_cards = self.deck.deal(cards_needed)
                player.add_cards(new_cards)
    
    def _next_turn(self) -> None:
        """Переход хода после успешной защиты"""
        # Защищавшийся становится атакующим
        self.players[self.current_defender_index].is_defender = False
        self.players[self.current_defender_index].is_attacker = True
        
        self.current_attacker_index = self.current_defender_index
        self.current_defender_index = (self.current_defender_index + 1) % len(self.players)
        self.players[self.current_defender_index].is_defender = True
    
    def _next_turn_after_take(self) -> None:
        """Переход хода после взятия карт"""
        taking_player_index = next((i for i, p in enumerate(self.players) if p.sid == self.players[self.current_defender_index].sid), 0)
        self.current_attacker_index = (taking_player_index + 1) % len(self.players)
        self.current_defender_index = (self.current_attacker_index + 1) % len(self.players)
        
        # Сброс статусов
        for player in self.players:
            player.is_attacker = False
            player.is_defender = False
        
        self.players[self.current_attacker_index].is_attacker = True
        self.players[self.current_defender_index].is_defender = True
    
    def check_game_over(self) -> Optional[str]:
        """Проверка окончания игры"""
        players_with_cards = [p for p in self.players if p.cards]
        
        if len(players_with_cards) == 1:
            self.winner = players_with_cards[0].sid
            self.game_state = 'finished'
            return self.winner
        
        if self.deck.is_empty() and all(len(p.cards) == 0 for p in self.players):
            self.winner = 'draw'
            self.game_state = 'finished'
            return 'draw'
        
        return None
    
    def get_player_by_sid(self, sid: str) -> Optional[Player]:
        for player in self.players:
            if player.sid == sid:
                return player
        return None
    
    def to_dict(self):
        return {
            'game_id': self.game_id,
            'settings': self.settings,
            'players': [player.to_dict() for player in self.players],
            'trump_suit': self.trump_suit,
            'table': self.table,
            'attack_cards': self.attack_cards,
            'defense_cards': self.defense_cards,
            'current_attacker_index': self.current_attacker_index,
            'current_defender_index': self.current_defender_index,
            'game_state': self.game_state,
            'winner': self.winner,
            'deck_count': len(self.deck.cards),
            'move_history': self.move_history[-10:]
        }

class LobbyManager:
    def __init__(self):
        self.lobbies: Dict[str, Dict] = {}
        self.players_in_lobbies: Dict[str, str] = {}
    
    def create_lobby(self, creator_sid: str, settings: Dict) -> str:
        # Генерируем уникальный ID лобби
        while True:
            lobby_id = f"lobby_{random.randint(1000, 9999)}"
            if lobby_id not in self.lobbies:
                break
        
        lobby = {
            'lobby_id': lobby_id,
            'creator_sid': creator_sid,
            'settings': {
                'name': settings.get('name', 'Моя игра'),
                'gameType': settings.get('gameType', 'throw'),
                'maxPlayers': int(settings.get('maxPlayers', 4)),
                'minPlayers': int(settings.get('minPlayers', 2)),
                'botDifficulty': settings.get('botDifficulty', 'medium'),
                'isPublic': bool(settings.get('isPublic', True)),
                'enableChat': bool(settings.get('enableChat', True))
            },
            'players': [creator_sid],
            'created_at': datetime.now(),
            'game_id': None
        }
        
        self.lobbies[lobby_id] = lobby
        self.players_in_lobbies[creator_sid] = lobby_id
        
        print(f"Lobby created: {lobby_id} with {len(lobby['players'])} players")
        return lobby_id
    
    def join_lobby(self, player_sid: str, lobby_id: str) -> bool:
        if lobby_id not in self.lobbies:
            print(f"Lobby {lobby_id} not found in lobbies: {list(self.lobbies.keys())}")
            return False
        
        lobby = self.lobbies[lobby_id]
        
        # Проверяем максимальное количество игроков
        max_players = lobby['settings']['maxPlayers']
        current_players = len(lobby['players'])
        
        print(f"Lobby {lobby_id}: {current_players}/{max_players} players")
        
        if current_players >= max_players:
            print(f"Lobby {lobby_id} is full")
            return False
        
        # Если игрок уже в лобби, возвращаем True
        if player_sid in lobby['players']:
            return True
        
        # Удаляем игрока из предыдущего лобби если есть
        if player_sid in self.players_in_lobbies:
            old_lobby_id = self.players_in_lobbies[player_sid]
            self.leave_lobby(player_sid, old_lobby_id)
        
        # Добавляем игрока в лобби
        lobby['players'].append(player_sid)
        self.players_in_lobbies[player_sid] = lobby_id
        
        print(f"Player {player_sid} added to lobby {lobby_id}. Now {len(lobby['players'])} players")
        return True
    
    def leave_lobby(self, player_sid: str, lobby_id: str) -> bool:
        if lobby_id not in self.lobbies:
            return False
        
        lobby = self.lobbies[lobby_id]
        
        if player_sid in lobby['players']:
            lobby['players'].remove(player_sid)
            
            if player_sid in self.players_in_lobbies:
                del self.players_in_lobbies[player_sid]
            
            # Если лобби пустое, удаляем его
            if not lobby['players']:
                del self.lobbies[lobby_id]
                print(f"Lobby {lobby_id} deleted (empty)")
            # Если создатель вышел, назначаем нового
            elif lobby['creator_sid'] == player_sid and lobby['players']:
                lobby['creator_sid'] = lobby['players'][0]
                print(f"New creator for lobby {lobby_id}: {lobby['creator_sid']}")
            
            print(f"Player {player_sid} left lobby {lobby_id}. Remaining: {len(lobby['players'])}")
            return True
        
        return False
    
    def get_lobby(self, lobby_id: str) -> Optional[Dict]:
        lobby = self.lobbies.get(lobby_id)
        if lobby:
            # Возвращаем копию, чтобы избежать изменений извне
            return lobby.copy()
        return None
    
    def get_player_lobby(self, player_sid: str) -> Optional[str]:
        return self.players_in_lobbies.get(player_sid)
    
    def get_public_lobbies(self) -> List[Dict]:
        public_lobbies = []
        for lobby in self.lobbies.values():
            if lobby['settings']['isPublic'] and not lobby['game_id']:
                # Возвращаем копию без чувствительной информации
                lobby_copy = lobby.copy()
                public_lobbies.append(lobby_copy)
        return public_lobbies
    
    def set_game_id(self, lobby_id: str, game_id: str) -> bool:
        if lobby_id in self.lobbies:
            self.lobbies[lobby_id]['game_id'] = game_id
            return True
        return False

lobby_manager = LobbyManager()

# WebSocket события
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    player_sid = request.sid
    lobby_id = lobby_manager.get_player_lobby(player_sid)
    if lobby_id:
        lobby_manager.leave_lobby(player_sid, lobby_id)
        lobby = lobby_manager.get_lobby(lobby_id)
        if lobby:
            emit('player_left', {
                'player_sid': player_sid,
                'lobby': lobby
            }, room=lobby_id)

@socketio.on('create_lobby')
def handle_create_lobby(data):
    try:
        settings = data.get('settings', {})
        print(f"Creating lobby with settings: {settings}")
        
        lobby_id = lobby_manager.create_lobby(request.sid, settings)
        
        join_room(lobby_id)
        
        print(f"Lobby created successfully: {lobby_id}")
        
        emit('lobby_created', {
            'success': True,
            'lobby_id': lobby_id,
            'redirect_url': f'/link_game/{lobby_id}'
        })
        
        lobby = lobby_manager.get_lobby(lobby_id)
        emit('lobby_updated', {
            'lobby': lobby
        }, room=lobby_id)
        
    except Exception as e:
        print(f"Error creating lobby: {e}")
        import traceback
        traceback.print_exc()
        emit('lobby_created', {
            'success': False,
            'error': 'Не удалось создать лобби'
        })

@socketio.on('join_lobby')
def handle_join_lobby(data):
    try:
        lobby_id = data.get('lobby_id')
        player_sid = request.sid
        
        print(f"Player {player_sid} trying to join lobby {lobby_id}")
        
        if not lobby_id:
            emit('join_success', {
                'success': False,
                'error': 'ID лобби не указан'
            })
            return
        
        lobby = lobby_manager.get_lobby(lobby_id)
        if not lobby:
            print(f"Lobby {lobby_id} not found")
            emit('join_success', {
                'success': False,
                'error': 'Лобби не найдено'
            })
            return
        
        if lobby_manager.join_lobby(player_sid, lobby_id):
            join_room(lobby_id)
            lobby = lobby_manager.get_lobby(lobby_id)
            
            print(f"Player {player_sid} successfully joined lobby {lobby_id}")
            
            emit('join_success', {
                'success': True,
                'lobby_id': lobby_id,
                'redirect_url': f'/lobby/{lobby_id}',
                'lobby': lobby
            })
            
            emit('player_joined', {
                'player_sid': player_sid,
                'player_name': f'Player_{player_sid[-4:]}',
                'lobby': lobby
            }, room=lobby_id)
            
            emit('lobby_updated', {
                'lobby': lobby
            }, room=lobby_id)
        else:
            print(f"Failed to join lobby {lobby_id} - may be full")
            emit('join_success', {
                'success': False,
                'error': 'Не удалось присоединиться к лобби (возможно, лобби заполнено)'
            })
            
    except Exception as e:
        print(f"Error joining lobby: {e}")
        import traceback
        traceback.print_exc()
        emit('join_success', {
            'success': False,
            'error': f'Ошибка при присоединении к лобби: {str(e)}'
        })

@socketio.on('start_game')
def handle_start_game(data):
    try:
        lobby_id = data.get('lobby_id')
        print(f"Starting game for lobby: {lobby_id}")
        
        lobby = lobby_manager.get_lobby(lobby_id)
        
        if not lobby:
            print(f"Lobby {lobby_id} not found")
            emit('error', {'message': 'Лобби не найдено'})
            return
            
        if request.sid != lobby['creator_sid']:
            emit('error', {'message': 'Только создатель может начать игру'})
            return
        
        game_id = f"game_{random.randint(1000, 9999)}"
        
        # Преобразуем настройки для игры
        game_settings = {
            'max_players': lobby['settings']['maxPlayers'],
            'min_players': lobby['settings']['minPlayers'],
            'game_type': lobby['settings']['gameType'],
            'bot_difficulty': lobby['settings']['botDifficulty']
        }
        
        print(f"Creating game {game_id} with settings: {game_settings}")
        
        game = Game(game_id, game_settings)
        
        # Добавляем реальных игроков
        for player_sid in lobby['players']:
            username = f'Player_{player_sid[-4:]}'
            player = Player(player_sid, username)
            if game.add_player(player):
                print(f"Added player {username} to game")
        
        # Добавляем ботов если нужно
        players_needed = lobby['settings']['minPlayers'] - len(lobby['players'])
        print(f"Players needed: {players_needed}")
        
        for i in range(players_needed):
            bot_sid = f"bot_{i+1}_{game_id}"
            bot_username = f"Bot_{i+1}"
            bot = Player(bot_sid, bot_username, True)
            if game.add_player(bot):
                print(f"Added bot {bot_username} to game")
        
        if game.start_game():
            games[game_id] = game
            lobby_manager.set_game_id(lobby_id, game_id)
            
            print(f"Game {game_id} started successfully")
            
            emit('game_started', {
                'game_id': game_id,
                'game': game.to_dict()
            }, room=lobby_id)
        else:
            print("Failed to start game")
            emit('error', {'message': 'Не удалось начать игру'})
            
    except Exception as e:
        print(f"Error starting game: {e}")
        import traceback
        traceback.print_exc()
        emit('error', {'message': f'Ошибка при запуске игры: {str(e)}'})

@socketio.on('chat_message')
def handle_chat_message(data):
    lobby_id = data.get('lobby_id')
    message = data.get('message')
    player_sid = request.sid
    
    if not lobby_id or not message:
        return
        
    lobby = lobby_manager.get_lobby(lobby_id)
    if lobby and lobby['settings']['enableChat']:
        emit('chat_message', {
            'player': f'Player_{player_sid[-4:]}',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }, room=lobby_id)

@socketio.on('make_attack')
def handle_make_attack(data):
    game_id = data.get('game_id')
    card_index = data.get('card_index')
    player_sid = request.sid
    
    if game_id in games:
        game = games[game_id]
        if game.make_attack(player_sid, card_index):
            emit('game_update', {
                'game': game.to_dict()
            }, room=game_id)
            
            # Проверка окончания игры
            winner = game.check_game_over()
            if winner:
                emit('game_over', {
                    'winner': winner,
                    'game': game.to_dict()
                }, room=game_id)

@socketio.on('make_defense')
def handle_make_defense(data):
    game_id = data.get('game_id')
    card_index = data.get('card_index')
    player_sid = request.sid
    
    if game_id in games:
        game = games[game_id]
        if game.make_defense(player_sid, card_index):
            emit('game_update', {
                'game': game.to_dict()
            }, room=game_id)

@socketio.on('take_cards')
def handle_take_cards(data):
    game_id = data.get('game_id')
    player_sid = request.sid
    
    if game_id in games:
        game = games[game_id]
        if game.take_cards(player_sid):
            emit('game_update', {
                'game': game.to_dict()
            }, room=game_id)

@socketio.on('pass_turn')
def handle_pass_turn(data):
    game_id = data.get('game_id')
    player_sid = request.sid
    
    if game_id in games:
        game = games[game_id]
        if game.complete_defense():
            emit('game_update', {
                'game': game.to_dict()
            }, room=game_id)

# HTTP маршруты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/link_game/<lobby_id>')
def link_game_page(lobby_id):
    """Страница для присоединения к игре по ссылке"""
    return render_template('link_game.html', lobby_id=lobby_id)

@app.route('/lobby/<lobby_id>')
def lobby_page(lobby_id):
    return render_template('lobby.html')

@app.route('/game/<game_id>')
def game_page(game_id):
    return render_template('game.html')

@app.route('/api/lobbies')
def get_lobbies():
    public_lobbies = lobby_manager.get_public_lobbies()
    return jsonify({'lobbies': public_lobbies})

@app.route('/api/lobby/<lobby_id>')
def get_lobby_info(lobby_id):
    """Получить информацию о лобби"""
    lobby = lobby_manager.get_lobby(lobby_id)
    if lobby:
        return jsonify({
            'success': True,
            'lobby': lobby
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Лобби не найдено'
        }), 404

@app.route('/api/game/<game_id>')
def get_game_state(game_id):
    if game_id in games:
        return jsonify(games[game_id].to_dict())
    return jsonify({'error': 'Game not found'}), 404

@app.route('/api/player/stats')
def get_player_stats():
    return jsonify({
        'games_played': 0,
        'games_won': 0,
        'win_rate': 0,
        'rating': 1000
    })

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'lobbies_count': len(lobby_manager.lobbies),
        'games_count': len(games),
        'players_online': len(lobby_manager.players_in_lobbies)
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

from typing import Dict, List, Optional
from datetime import datetime
import random

class LobbyManager:
    def __init__(self):
        self.lobbies: Dict[str, Dict] = {}
        self.players_in_lobbies: Dict[str, str] = {}  # player_sid -> lobby_id
    
    def create_lobby(self, creator_sid: str, settings: Dict) -> str:
        lobby_id = f"lobby_{random.randint(1000, 9999)}"
        
        lobby = {
            'lobby_id': lobby_id,
            'creator_sid': creator_sid,
            'settings': {
                'name': settings.get('name', 'Моя игра'),
                'gameType': settings.get('gameType', 'throw'),
                'maxPlayers': settings.get('maxPlayers', 4),
                'minPlayers': settings.get('minPlayers', 2),
                'botDifficulty': settings.get('botDifficulty', 'medium'),
                'isPublic': settings.get('isPublic', True),
                'enableChat': settings.get('enableChat', True)
            },
            'players': [creator_sid],
            'created_at': datetime.now(),
            'game_id': None
        }
        
        self.lobbies[lobby_id] = lobby
        self.players_in_lobbies[creator_sid] = lobby_id
        
        return lobby_id
    
    def join_lobby(self, player_sid: str, lobby_id: str) -> bool:
        if lobby_id not in self.lobbies:
            return False
        
        lobby = self.lobbies[lobby_id]
        
        if len(lobby['players']) >= lobby['settings']['maxPlayers']:
            return False
        
        if player_sid in lobby['players']:
            return True  # Уже в лобби
        
        # Удаляем игрока из предыдущего лобби если есть
        if player_sid in self.players_in_lobbies:
            old_lobby_id = self.players_in_lobbies[player_sid]
            self.leave_lobby(player_sid, old_lobby_id)
        
        lobby['players'].append(player_sid)
        self.players_in_lobbies[player_sid] = lobby_id
        
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
            # Если создатель вышел, назначаем нового
            elif lobby['creator_sid'] == player_sid and lobby['players']:
                lobby['creator_sid'] = lobby['players'][0]
            
            return True
        
        return False
    
    def get_lobby(self, lobby_id: str) -> Optional[Dict]:
        return self.lobbies.get(lobby_id)
    
    def get_player_lobby(self, player_sid: str) -> Optional[str]:
        return self.players_in_lobbies.get(player_sid)
    
    def get_public_lobbies(self) -> List[Dict]:
        return [lobby for lobby in self.lobbies.values() 
                if lobby['settings']['isPublic'] and not lobby['game_id']]
    
    def set_game_id(self, lobby_id: str, game_id: str) -> bool:
        if lobby_id in self.lobbies:
            self.lobbies[lobby_id]['game_id'] = game_id
            return True
        return False
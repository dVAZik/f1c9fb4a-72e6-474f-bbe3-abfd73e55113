from typing import List, Dict, Optional
from .core import Deck, Player, Card
import random

class Game:
    def __init__(self, game_id: str, settings: Dict):
        self.game_id = game_id
        self.settings = settings
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
        self.created_at = None
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
        self.created_at = __import__('datetime').datetime.now()
        
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
                'timestamp': __import__('datetime').datetime.now().isoformat()
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
                    'timestamp': __import__('datetime').datetime.now().isoformat()
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
        # Следующий игрок после взявшего становится атакующим
        taking_player_index = next(i for i, p in enumerate(self.players) if p.sid == self.get_player_by_sid(self.players[self.current_defender_index].sid).sid)
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
            # Ничья - все без карт
            self.winner = 'draw'
            self.game_state = 'finished'
            return 'draw'
        
        return None
    
    def get_player_by_sid(self, sid: str) -> Optional[Player]:
        for player in self.players:
            if player.sid == sid:
                return player
        return None
    
    def to_dict(self) -> Dict:
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
            'move_history': self.move_history[-10:]  # Последние 10 ходов
        }
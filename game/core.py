import random
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class Card:
    suit: str
    rank: str
    
    def __post_init__(self):
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
    
    def get_best_defense_card(self, attack_card: Card, trump_suit: str) -> Optional[Card]:
        best_card = None
        for card in self.cards:
            if card.suit == attack_card.suit and card.value > attack_card.value:
                if best_card is None or card.value < best_card.value:
                    best_card = card
            elif card.suit == trump_suit and attack_card.suit != trump_suit:
                if best_card is None or card.value < best_card.value:
                    best_card = card
        return best_card
    
    def to_dict(self) -> Dict:
        return {
            'sid': self.sid,
            'username': self.username,
            'is_bot': self.is_bot,
            'cards': [card.to_dict() for card in self.cards],
            'position': self.position,
            'is_attacker': self.is_attacker,
            'is_defender': self.is_defender
        }
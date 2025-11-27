from typing import List, Dict, Optional
from .core import Card, Player
import random

class BotAI:
    def __init__(self, difficulty: str = 'medium'):
        self.difficulty = difficulty
        self.difficulty_weights = {
            'easy': {'random': 0.7, 'smart': 0.3},
            'medium': {'random': 0.3, 'smart': 0.7},
            'hard': {'random': 0.1, 'smart': 0.9}
        }
    
    def choose_attack_card(self, player: Player, table: List[Dict], trump_suit: str) -> Optional[int]:
        """Выбор карты для атаки"""
        playable_cards = player.get_playable_cards(table, trump_suit)
        
        if not playable_cards:
            return None
        
        weights = self.difficulty_weights[self.difficulty]
        
        if random.random() < weights['random']:
            # Случайный выбор
            card_index = random.randint(0, len(playable_cards) - 1)
            return player.cards.index(playable_cards[card_index])
        else:
            # Умный выбор
            return self._smart_attack_choice(player, playable_cards, trump_suit)
    
    def _smart_attack_choice(self, player: Player, playable_cards: List[Card], trump_suit: str) -> int:
        """Умный выбор карты для атаки"""
        # Предпочитаем ненужные карты (не козыри, низкого достоинства)
        non_trump_cards = [card for card in playable_cards if card.suit != trump_suit]
        if non_trump_cards:
            # Выбираем самую слабую ненужную карту
            weakest_card = min(non_trump_cards, key=lambda c: c.value)
            return player.cards.index(weakest_card)
        
        # Если только козыри, выбираем самый слабый
        weakest_card = min(playable_cards, key=lambda c: c.value)
        return player.cards.index(weakest_card)
    
    def choose_defense_card(self, player: Player, attack_card: Card, trump_suit: str) -> Optional[int]:
        """Выбор карты для защиты"""
        weights = self.difficulty_weights[self.difficulty]
        
        if random.random() < weights['random']:
            # Случайная попытка защиты
            for i, card in enumerate(player.cards):
                if (card.suit == attack_card.suit and card.value > attack_card.value) or \
                   (card.suit == trump_suit and attack_card.suit != trump_suit):
                    return i
            return None
        else:
            # Умная защита
            return self._smart_defense_choice(player, attack_card, trump_suit)
    
    def _smart_defense_choice(self, player: Player, attack_card: Card, trump_suit: str) -> Optional[int]:
        """Умный выбор карты для защиты"""
        best_card = None
        best_index = None
        
        for i, card in enumerate(player.cards):
            if (card.suit == attack_card.suit and card.value > attack_card.value) or \
               (card.suit == trump_suit and attack_card.suit != trump_suit):
                
                if best_card is None:
                    best_card = card
                    best_index = i
                else:
                    # Предпочитаем бить ненужной картой
                    if card.suit != trump_suit and best_card.suit == trump_suit:
                        best_card = card
                        best_index = i
                    elif card.suit == best_card.suit and card.value < best_card.value:
                        # В одной масти выбираем меньшую карту
                        best_card = card
                        best_index = i
        
        return best_index
    
    def decide_to_take_cards(self, player: Player, table: List[Dict], trump_suit: str) -> bool:
        """Решение брать карты или нет"""
        weights = self.difficulty_weights[self.difficulty]
        
        if random.random() < weights['random']:
            return random.choice([True, False])
        
        # Умное решение
        return self._smart_take_decision(player, table, trump_suit)
    
    def _smart_take_decision(self, player: Player, table: List[Dict], trump_suit: str) -> bool:
        """Умное решение о взятии карт"""
        total_cards_to_take = len(table) * 2  # Примерное количество карт которые придется взять
        
        # Если у игрока мало карт, лучше не брать
        if len(player.cards) + total_cards_to_take > 10:
            return False
        
        # Если на столе много сильных карт, лучше взять
        strong_cards_count = 0
        for pair in table:
            if pair['attack_card'] and pair['attack_card']['value'] >= 12:  # Q, K, A
                strong_cards_count += 1
            if pair['defense_card'] and pair['defense_card']['value'] >= 12:
                strong_cards_count += 1
        
        if strong_cards_count >= 2:
            return True
        
        return False
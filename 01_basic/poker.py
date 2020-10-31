#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
from collections import Counter

# -----------------
# Реализуйте функцию best_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. У каждой карты есть масть(suit) и
# ранг(rank)
# Масти: трефы(clubs, C), пики(spades, S), червы(hearts, H), бубны(diamonds, D)
# Ранги: 2, 3, 4, 5, 6, 7, 8, 9, 10 (ten, T), валет (jack, J), дама (queen, Q), король (king, K), туз (ace, A)
# Например: AS - туз пик (ace of spades), TH - дестяка черв (ten of hearts), 3C - тройка треф (three of clubs)

# Задание со *
# Реализуйте функцию best_wild_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. Кроме прочего в данном варианте "рука"
# может включать джокера. Джокеры могут заменить карту любой
# масти и ранга того же цвета, в колоде два джокерва.
# Черный джокер '?B' может быть использован в качестве треф
# или пик любого ранга, красный джокер '?R' - в качестве черв и бубен
# любого ранга.

# Одна функция уже реализована, сигнатуры и описания других даны.
# Вам наверняка пригодится itertoolsю
# Можно свободно определять свои функции и т.п.
# -----------------

# Пример покерной 'руки': ['6C', '7C', '8C', '9C', 'TC']


CARDS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['C', 'S', 'H', 'D']
JOKER_SUITS = {'?B': ('C', 'S'),
               '?R': ('H', 'D')}

RANKS = {k: v for v, k in enumerate(CARDS)}
RANKS_INVERSE = {v: k for v, k in enumerate(CARDS)}


def get_card_rank(card):
    rank_symbol = card[0]
    return RANKS[rank_symbol]


def get_rank_symbol(rank):
    return RANKS_INVERSE[rank]


def hand_rank(hand):
    """Возвращает значение определяющее ранг 'руки'"""
    ranks = card_ranks(hand)
    if straight(ranks) and flush(hand):
        return (8, max(ranks))
    elif kind(4, ranks):
        return (7, kind(4, ranks), kind(1, ranks))
    elif kind(3, ranks) and kind(2, ranks):
        return (6, kind(3, ranks), kind(2, ranks))
    elif flush(hand):
        return (5, ranks)
    elif straight(ranks):
        return (4, max(ranks))
    elif kind(3, ranks):
        return (3, kind(3, ranks), ranks)
    elif two_pair(ranks):
        return (2, two_pair(ranks), ranks)
    elif kind(2, ranks):
        return (1, kind(2, ranks), ranks)
    else:
        return (0, ranks)


def card_ranks(hand):
    """Возвращает список рангов (его числовой эквивалент),
    отсортированный от большего к меньшему"""
    return sorted([get_card_rank(card) for card in hand], reverse=True)


def flush(hand):
    """Возвращает True, если все карты одной масти"""
    cards_suits = set(card[1] for card in hand)
    is_flush = len(cards_suits) == 1
    return is_flush


def straight(ranks):
    """Возвращает True, если отсортированные ранги формируют последовательность 5ти,
    где у 5ти карт ранги идут по порядку (стрит)"""
    sorted_ranks = sorted(ranks)
    is_straight = True
    for i in range(1, len(sorted_ranks)):
        if sorted_ranks[i] != sorted_ranks[i-1] + 1:
            is_straight = False
            break
    return is_straight


def kind(n, ranks):
    """Возвращает первый ранг, который n раз встречается в данной руке.
    Возвращает None, если ничего не найдено"""
    c = Counter(ranks)
    for k,v in c.items():
        if v == n:
            return k


def two_pair(ranks):
    """Если есть две пары, то возврщает два соответствующих ранга,
    иначе возвращает None"""
    c = Counter(ranks)
    pair = []
    for k,v in c.items():
        if v == 2:
            pair.append(k)
    if len(pair) == 2:
        return tuple(pair)


def get_hands(hand):
    return [sorted(comb) for comb in itertools.combinations(hand, 5)]


def get_unique_hands(hands):
    hands = set([" ".join(hand) for hand in hands])
    hands = [hand.split() for hand in hands]
    return hands


def get_best_hand(hands):
    hands = get_unique_hands(hands)
    best_hand = hands[0]
    for hand in hands[1:]:
        if compare_hands(hand, best_hand):
            best_hand = hand
    return best_hand


def compare_hands(hand_1, hand_2):
    return hand_rank(hand_1) > hand_rank(hand_2)


def get_jokers_cards(joker):
    """Возвращает все возможние карты соответствующе джокеру """
    if joker not in JOKER_SUITS:
        return [joker]

    joker_cards = list()
    for suit in JOKER_SUITS[joker]:
        suit_cards = [rank + suit for rank in RANKS]
        joker_cards.extend(suit_cards)
    return joker_cards


def get_jokers_combs(hand):
    """Возвращает все комбинации 'руки' с учетом джокера """
    combs = []

    joker = [card for card in hand if "?" in card]
    if not joker:
        return [hand]
    joker = joker[0]

    cards = [card for card in hand if card != joker]

    for joker_card in get_jokers_cards(joker):
        if joker_card not in cards:
            new_hand = cards + [joker_card]
            combs.extend(get_jokers_combs(new_hand))

    return combs


def best_hand(hand):
    """Из "руки" в 7 карт возвращает лучшую "руку" в 5 карт """
    hands = get_hands(hand)
    return get_best_hand(hands)


def best_wild_hand(hand):
    """best_hand но с джокерами"""
    hands = list()
    for comb in get_jokers_combs(hand):
        hands.extend(get_hands(comb))
    return get_best_hand(hands)


def test_best_hand():
    print("test_best_hand...")
    assert (sorted(best_hand("6C 7C 8C 9C TC 5C JS".split()))
            == ['6C', '7C', '8C', '9C', 'TC'])
    assert (sorted(best_hand("TD TC TH 7C 7D 8C 8S".split()))
            == ['8C', '8S', 'TC', 'TD', 'TH'])
    assert (sorted(best_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print('OK')


def test_best_wild_hand():
    print("test_best_wild_hand...")
    assert (sorted(best_wild_hand("6C 7C 8C 9C TC 5C ?B".split()))
            == ['7C', '8C', '9C', 'JC', 'TC'])
    assert (sorted(best_wild_hand("TD TC 5H 5C 7C ?R ?B".split()))
            == ['7C', 'TC', 'TD', 'TH', 'TS'])
    assert (sorted(best_wild_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print('OK')

if __name__ == '__main__':
    test_best_hand()
    test_best_wild_hand()

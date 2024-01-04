import random
import collections
from enum import IntEnum, Enum, auto
from typing import List, Dict, Tuple
from copy import deepcopy

MAX_CLUE_TOKENS = 8
MAX_STRIKES = 3
MAX_TURNS = 100

# from enum import Flag
# class Color(Flag): #this would be cool when things get muddy but too complicated for now
class Color(Enum):
    BLU = auto()
    RED = auto()
    GRN = auto()
    WHI = auto()
    YEL = auto()


class Rank(IntEnum):
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

class Result(IntEnum):
    MAX_TURNS = 0
    STRIKE_OUT = 1
    BOTTOM_OUT = 2
    VICTORY = 3
    NO_PLAYABLES = 4

ColorRank = Tuple[Color, Rank]


class Game():
    def __init__(self, player_count: int = 4, sim: 'Simulator | None' = None, deck: 'Deck | None' = None, debug: bool = False):
        self.deck = deck if deck is not None else Deck.normal_deck()
        self.board = Board()
        for c in self.deck._cards:  # type: ignore
        # for c in Deck.normal_deck()._cards: # type: ignore
            self.board.remaining[c.color, c.rank] += 1
        self.players: List[Player] = [
            Player(x, self) for x in range(player_count)]
        self.clue_tokens = MAX_CLUE_TOKENS
        self.remaining_strikes = MAX_STRIKES
        self.score = 0
        self.player_turn = -1
        self.last_player: int | None = None
        self.turns = -1
        self.sim = sim
        self.debug = debug
        for p in self.players:
            if debug:
                print(f'{p.id} {p.cards}')
        for p in self.players:
            for c in p.cards:
                self.report_draw(p.id, c)

    @property #TODO this probably shoulldn't have to be recalculated
    def eventually_playable(self)-> set[Tuple[Color, Rank]]:
        return self.board.eventually_playable
    
    @property 
    def one_away(self)-> set[Tuple[Color, Rank]]:
        s: set[Tuple[Color, Rank]] = set()
        for _, stack in self.board.stacks.items():
            s |= stack.one_away
        return s
    
    @property 
    def can_discard(self)-> bool:
        return self.clue_tokens != 8
    
    @property 
    def can_clue(self)-> bool:
        return self.clue_tokens != 0

    def play_card(self, card: 'Card'):
        if self.debug:
                print(f'{self.player_turn} plays {card}', end=' ')
        self.process_card_removal(card)
        if self.board.stacks[card.color].play_card(card):
            self.score += 1
            self.board.eventually_playable.remove(card.color_rank)
            if self.debug:
                print('+1')
        else:
            self.remaining_strikes -= 1
            if self.debug:
                print('strike!')
        if self.remaining_strikes == 0:  # GAME_OVER
            if self.debug:
                print('GAME OVER, 3 STRIKES')
            self.game_over(Result.STRIKE_OUT)
            return
        if self.score == 25:  # GAME_OVER
            if self.debug:
                print('YOU WIN')
            self.game_over(Result.VICTORY)
            return
        self.next_player()

    def discard_card(self, card: 'Card'):
        if self.debug:
            print(f'{self.player_turn} discards {card} tokens:{self.clue_tokens}')
        self.clue_tokens += 1
        self.process_card_removal(card)
        self.next_player()

    # Report to players that all copies of a card have been played or exhausted.
    def process_card_removal(self, card: 'Card'):
        self.board.remaining[card.color_rank] -= 1
        if self.board.remaining[card.color_rank] == 0:
            for p in self.players:
                p.exhaust_possibility(card)

    # Called whenever a player draws a card. Not called at game_start because all players are drawing cards.
    def report_draw(self, player_id: int, card: 'Card', game_start: bool = False):
        if game_start:
            return
        for p in self.players:
            if p.id == player_id:
                continue
            p.see_draw(card)

    def give_clue(self, from_: int, to: int, color: Color | None, rank: Rank | None):
        assert not (color is None and rank is None)
        assert self.clue_tokens > 0
        self.clue_tokens -= 1
        if self.debug:
            print(
                f'{from_} clues {to} with {color.name if color else rank} \ttokens:{self.clue_tokens}')
        for p in self.players:
            p.receive_clue(from_, to, color, rank)
        self.next_player()

    def next_player(self):
        self.turns += 1
        if self.turns == MAX_TURNS:
            self.game_over(Result.MAX_TURNS)
            return
        if self.player_turn == self.last_player:  # GAME_OVER
            if self.debug:
                print('GAME OVER, NO MORE CARDS')
            self.game_over(Result.BOTTOM_OUT)
            return
        self.player_turn += 1
        self.player_turn %= len(self.players)
        assert 0 <= self.player_turn < len(self.players)
        self.players[self.player_turn].prompt()

    def game_over(self, result: Result):
        if self.sim:
            self.sim.report(self.score, result)
        else:
            print(f'Final Score:{self.score}')

    def get_neighbors(self, id: int) -> List['Player']:
        return self.players[id+1:] + self.players[:id]


class Player():
    def __init__(self, id: int, game: Game, hand_size: int = 4):
        self.id = id
        self.cards: List[Card] = []
        self.slots: List[Slot] = []
        self.game = game
        self.has_play = False  # probably make that a property
        self.self_exhausts: List[Tuple[Color, Rank]] = []
        for _ in range(hand_size):
            self.draw_card(game_start = True)

    def __str__(self):
        return f'id:{self.id}, cards:{self.cards} slots:{self.slots}'

    def __repr__(self):
        return self.__str__()

    @property
    def chop(self) -> int:  # this ignores chop moves and layered finesse etc.
        for idx, s in enumerate(self.slots):
            if s.clued == False:
                return idx
        return -1  # magic number... really means that hand is blocked

    def draw_card(self, game_start: bool = False):
        card = self.game.deck.draw()
        if card:
            self.game.report_draw(self.id, card, game_start=game_start)
            self.cards.append(card)
            self.slots.append(Slot(self, card))
        else:
            self.game.last_player = self.id

    def play_card(self, idx: int):
        card = self.pop_card(idx)
        self.game.play_card(card)
        pass

    def discard(self, idx: int):
        assert self.game.clue_tokens != MAX_CLUE_TOKENS
        card = self.pop_card(idx)
        self.game.discard_card(card)
        pass

    def pop_card(self, idx: int) -> 'Card':
        assert 0 <= idx < len(self.cards)
        card = self.cards.pop(idx)
        self.slots.pop(idx)
        self.draw_card()
        return card

    # Called when another player receives a draw.
    def see_draw(self, card: 'Card'):
        for s in self.slots:
            s.decrement_possibility(card)

    # Called when a card is guaranteed to not be in your hand, discarded through exhausts, plays or draws.
    # from_self is True if the info comes from the own players hand i.e. if a player had a 5 clue on a card, and then later in the game was marked green, the player should know that their newly marked green cards cannot be green 5, even if they did not have a negative 5 clue on them. This gets complicated since state would have to be refreshed after a clue is received and all cards are marked -- handled by the self_exhausts... technically this would be a recursive flow but I'm not sure
    def exhaust_possibility(self, card: 'Card', from_self: bool = False):
        for s in self.slots:
            if s.card.color_rank == card.color_rank and from_self:
                continue
            assert s.card.color_rank != card.color_rank
            s.exhaust_possibility(card.color_rank)

    def receive_clue(self, from_: int, to: int, color: Color | None = None, rank: Rank | None = None):
        # missing: analyze finesse/bluff
        if from_ == self.id: #tehcnicaly this will analyze self-bluff self-finesse
            return
        if to == self.id:
            for idx, s in enumerate(self.slots):
                s.receive_clue(idx, color, rank)

    def process_self_exhausts(self):
        while len(self.self_exhausts):
            copied_exhausts = deepcopy(self.self_exhausts)
            self.self_exhausts = []
            for cr in copied_exhausts: #deep copy is needed because on rare occasions you might have a recursive loop here
                self.exhaust_possibility(card_from_color_rank(cr), from_self = True)

    def give_clue(self, to: int, color: Color | None = None, rank: Rank | None = None):
        assert not (color is None and rank is None)
        self.game.give_clue(self.id, to, color, rank)

    # Returns the list of cards that woud be touched by a certain clue.
    def touched_cards(self, color: Color | None = None, rank: Rank | None = None)-> List[Tuple['Card',int]]:
        assert not (color is None and rank is None)
        touched_cards: List[Tuple['Card',int]] = []
        for i, c in enumerate(self.cards):
            if c.rank == rank or c.color == color:
                touched_cards.append((c, i))
        return touched_cards
        
    # Returns True if a touch is good i.e. it touches cards that are only eventually playable, cards that are not already clued, identical cards, cards that you may have and already clued.
    # This should not be called when evaluating saves.
    # Exceptions: 
    #    left-to-right play meaning the rest will be trash i.e marking 5y (play) 1y 2y (trash)
    #    marking kt, (like with trash bluff)
    #    stuff that can be handled with sarcastic discard.
    #TODO this shouldn't only look at possibilites since that is mathematic, this should really look at probables i.e. marking a 3 when you were given a 3-save is probably ok.
    # important! slots is passed from the caller
    def is_good_touch(self, touched_cards: List[Tuple['Card',int]], slots: List['Slot'])-> bool:
        # Check to make sure cards are eventually playable, almost certainly not a good touch
        for c, _ in touched_cards:
            if c.color_rank not in self.game.eventually_playable:
                return False

        # Touch contains duplicate cards, almost certainly not a good touch
        if len(set([c.color_rank for c, _ in touched_cards])) != len([c.color_rank for c, _ in touched_cards]):
            return False
        
        # Count of newly touched cards, if it's 0 almost certainly a bad touch. This forbids tempo clues
        new_touches = 0
        for c, idx in touched_cards:
            if not self.slots[idx].clued:
                new_touches += 1
        if new_touches == 0:
            return False
        
        # It can be a good touch, but it's probably not, check to see if you haven't been marked with the card you're trying to touch
        for s in slots:
            if len(s.possibilites) <= 5:
                possible = set(s.possibilites.keys())
                if possible & set(touched_cards):
                    return False
        return True
    
    @property
    def neighbors(self):
        return self.game.get_neighbors(self.id)
    
    @property
    def card_types(self) -> set[ColorRank]:
        return set([(c.color, c.rank) for c in self.cards])

    # Perform a play, discard or clue
    def prompt(self):
        neighbors = self.neighbors
        dist = len(neighbors)+1
        # missing: check if clue tokens are available, check if should clue (i.e. dont waste tokens, dont clue 1s on your neighbor if that means they won't be able to clue 1s on their neighbor's 1 chop which is unrelated to your own clue)
        # 1. respond to possible bluff
        # missing: <stubbed>
        # 2. Look for save, starting backwards because sometimes double or even triple saves are necessary
        for n in neighbors[::-1]:
            if not self.game.can_clue:
                break
            dist -= 1
            def look_for_save(neighor: Player) -> Tuple[int, int | None]:
                saves_needed: set[int] = set()
                save_slot: int | None = None
                if neighor.has_play:
                    return len(saves_needed), save_slot
                # missing: check if n-1 can clue play to neighbor... if n-1 is you, forced clue
                # kind of complicated because ideally there are no bad touches, but sometimes it is more efficient to make a bad touch play-clue than a double/triple-save
                for idx, c in enumerate(neighor.cards):
                    if idx < neighor.chop:
                        continue
                    # ignores double discard
                    if self.game.board.remaining[c.color_rank] == 1:
                        saves_needed.add(c.rank)
                        save_slot = idx if save_slot is None else save_slot
                    else:
                        break
                return len(saves_needed), save_slot

            saves_needed, save_slot = look_for_save(n)
            if saves_needed == dist and save_slot is not None:
                # give number save clue to first save_slot
                self.give_clue(n.id, rank=n.cards[save_slot].rank)
                return
        
        #look for play clue
        for n in neighbors:
            if not self.game.can_clue:
                break
            one_aways = list(n.card_types & self.game.one_away)
            if one_aways:
                #prefer color if even, otherwise probably go for most play clues and then most touches.
                #TODO i don't like referencing color of the Color/Rank with 0 idx
                #TODO we're only looking at the first one_away
                #TODO this doesnt yet observe left-to-right principle
                color = one_aways[0][0]
                color_touches = n.touched_cards(color=color)
                rank = one_aways[0][1]
                rank_touches = n.touched_cards(rank=rank)
                clues = [(color_touches, color, True), (rank_touches, rank, False)]
                if (big_touches and len(color_touches) < len(rank_touches)) or (not big_touches and len(color_touches) >= len(rank_touches)):
                    clues = clues[::-1]
                for c in clues:
                    touches, e, is_color = c
                    if n.is_good_touch(touches, self.slots):
                        self.give_clue(n.id, color=e if is_color else None, rank=e if not is_color else None) #type: ignore
                        return
        
        for i, s in enumerate(self.slots):
            if len(s.possibilites) <= 5 and set(s.possibilites.keys()) & self.game.one_away:
                self.play_card(i)
                return
        
        chop = self.chop if self.chop != -1 else len(self.cards)-1
        if self.game.can_discard:
            self.discard(chop)
            return
        self.play_card(chop)


        # self.play_card(self.chop if self.chop != -1 else 0)


class Slot():
    def __init__(self, player: Player, card: 'Card'):
        self.player = player
        self.card = card
        cards = Deck.normal_deck()._cards  # type: ignore
        # This isn't a simple set because we want to keep track of the number of cards that have been seen of each type. So if you see a r2, there is 1 possibility of your slot being r1 and if you see two r2s, there is 0 possiblity of your slot being r2. It's not so easy to keep track of individual perspectives without this method.
        self.possibilites: dict[Tuple[Color, Rank],
                                int] = collections.defaultdict(int)
        for c in cards:
            self.possibilites[c.color_rank] += 1
        # self.possibilites = set([(c.color, c.rank)
            # for c in Deck.normal_deck()._cards])  # type: ignore
        self.probable: set[Tuple[Color, Rank]] = set()
        self.save = False
        self.play = False
        self.clued = False

    def __str__(self):
        return f'<card:{self.card}, possibly:{self.possibilites if len(self.possibilites) < 10 else "unk"}>'

    def __repr__(self):
        return self.__str__()

    def decrement_possibility(self, card: 'Card'):
        if card.color_rank not in self.possibilites:
            return
        # if self.possibilites[card.color_rank] <= 0:
        #     print(self.possibilites[card.color_rank], card, self.player.id)
        #     assert self.possibilites[card.color_rank] > 0
        self.possibilites[card.color_rank] -= 1
        if self.possibilites[card.color_rank] == 0:
            self.exhaust_possibility(card.color_rank)

    # Called when a card is guaranteed to not be of a certain color/rank. Either through exhausted play/discard or through negative clues.
    def exhaust_possibility(self, color_rank: tuple[Color, Rank]):
        if color_rank in self.possibilites:
            del self.possibilites[color_rank]
        if len(self.possibilites) == 1:
            possibility = list(self.possibilites.keys())[0]
            self.probable = set((possibility,))
            self.player.self_exhausts.append(color_rank)

    def receive_clue(self, idx: int, color: Color | None = None, rank: Rank | None = None):
        assert not (color is None and rank is None)
        clued = self._remove_possibilities(color, rank)
        if clued and rank and idx == self.player.chop:
            if len(self.possibilites) != 1:
                self.save = True

    # Returns true if touched.
    def _remove_possibilities(self, color: Color | None, rank: Rank | None) -> bool:
        assert not (color is None and rank is None)
        if color:
            color_set = set([(color, r) for r in Rank])
            if self.card.color == color:
                removes: set[Tuple[Color, Rank]] = set()
                for key_color, key_rank in self.possibilites.keys():
                    if key_color != color:
                        removes.add((key_color, key_rank))
                for r in removes:
                    del self.possibilites[r]
                # self.possibilites &= color_set
                self.clued = True
            else:
                map(self.exhaust_possibility, color_set)
        elif rank:
            rank_set = set([(c, rank) for c in Color])
            if self.card.rank == rank:
                removes: set[Tuple[Color, Rank]] = set()
                for key_color, key_rank in self.possibilites.keys():
                    if key_rank != rank:
                        removes.add((key_color, key_rank))
                for r in removes:
                    del self.possibilites[r]

                # self.possibilites &= rank_set
                self.clued = True
            else:
                map(self.exhaust_possibility, rank_set)
        return self.clued


class Board():
    def __init__(self):
        self.stacks: Dict[Color, Stack] = Board._normal_board()
        self.remaining: Dict[Tuple[Color, Rank],
                             int] = collections.defaultdict(int)
        self.eventually_playable = set([(c.color, c.rank) for c in Deck.normal_deck()._cards]) # type: ignore

    @staticmethod
    def _normal_board() -> Dict[Color, 'Stack']:
        stacks: Dict[Color, 'Stack'] = {}
        for c in Color:
            stacks[c] = Stack(c)
        return stacks


class Stack():
    def __init__(self, color: Color, rank: Rank = Rank.ZERO):
        self.color: Color = color
        self.rank: Rank = rank

    def play_card(self, card: 'Card') -> bool:
        if card.rank != self.rank + 1:
            return False
        if card.color == self.color:
            self.rank = Rank(self.rank + 1)
            return True
        return False
    
    # @property
    # def eventually_playable(self) -> set[Tuple[Color, Rank]]:
    #     s: set[Tuple[Color, Rank]] = set()
    #     for r in Rank:
    #         if r > self.rank:
    #             s.add((self.color, r))
    #     return s
    
    @property
    def one_away(self) -> set[Tuple[Color, Rank]]:
        s: set[Tuple[Color, Rank]] = set()
        if self.rank != 5:
            s.add((self.color, Rank(self.rank + 1)))
        return s


class Deck():
    def __init__(self, cards: List['Card']):
        self._cards = cards
        self.size = len(self._cards)
        random.shuffle(self._cards)

    def __str__(self):
        return f'[size:{self.size}, cards:{str(self._cards)}]'

    def draw(self) -> 'Card | None':
        if len(self._cards) == 0:
            return None
        return self._cards.pop()

    @staticmethod
    def normal_deck() -> 'Deck':
        cards: List[Card] = []
        for c in Color:
            for r in Rank:
                match r:
                    case Rank.ZERO:
                        times = 0
                    case Rank.ONE:
                        times = 3
                    case Rank.FIVE:
                        times = 1
                    case _:
                        times = 2
                for _ in range(times):
                    cards.append(Card(c, r))
        return Deck(cards)


def card_from_color_rank(color_rank: Tuple[Color, Rank]) -> 'Card':
    return Card(color_rank[0], color_rank[1])


class Card():
    def __init__(self, color: Color, rank: Rank):
        assert rank != 0
        self.color = color
        self.rank = rank

    @property
    def color_rank(self) -> Tuple[Color, Rank]:
        return (self.color, self.rank)

    def __str__(self):
        return f'{self.color.name}-{self.rank}'

    def __repr__(self):
        return self.__str__()


class Simulator():
    def __init__(self, runs: int = 1):
        self.scores: List[int] = []
        self.runs = runs
        self.results: dict[Result, int] = collections.defaultdict(int)
        self._run()

    def _run(self):
        debug = True if self.runs < 10 else False
        increments = 10
        for i in range(self.runs):
            if debug:
                print()
                print('new_game')
            if i % (self.runs/increments) == 0 and i != 0 and not debug:
                print(f'{int(i/self.runs*100)}%')
            deck = None
            deck = Deck.normal_deck()
            deck._cards[-5] = Card(Color.BLU, Rank.ONE) #type: ignore
            deck._cards[-6] = Card(Color.BLU, Rank.ONE) #type: ignore
            g = Game(sim=self, deck=deck, debug=debug)
            g.next_player()
            del g
        avg_score = sum(self.scores)/len(self.scores)
        max_score = max(self.scores)
        strikeout_rate = self.results[Result.STRIKE_OUT] / self.runs
        victory_rate = self.results[Result.VICTORY] / self.runs
        bottomout_rate = self.results[Result.BOTTOM_OUT] / self.runs
        #TODO add statistics for no playables, which is technically a bottomout
        print(f'simulations:{self.runs} average_score:{avg_score} max_score:{max_score} strikeout_rate:{strikeout_rate} bottomout_rate:{bottomout_rate} victory_rate:{victory_rate}')

    def report(self, score: int, result: Result):
        self.scores.append(score)
        self.results[result] += 1


import sys
if len(sys.argv) < 2:
    big_touches = True
    # Simulator(10000)
    big_touches = False
    Simulator(10000)
else:
    big_touches = True
    Simulator(int(sys.argv[1]))
    big_touches = False
    Simulator(int(sys.argv[1]))
# Simulator(10000)
# Simulator(1)


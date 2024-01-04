import random
import collections
from enum import IntEnum, Enum, auto
from typing import List, Dict, Tuple

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


class Game():
    def __init__(self, player_count: int = 4, sim: 'Simulator | None' = None):
        self.deck = Deck.normal_deck()
        self.board = Board()
        for c in self.deck._cards:  # type: ignore
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

    def play_card(self, card: 'Card'):
        print(f'{self.player_turn} plays {card}', end=' ')
        self.process_card_removal(card)
        if self.board.stacks[card.color].play_card(card):
            self.score += 1
            print('+1')
        else:
            self.remaining_strikes -= 1
            print('strike!')
        if self.remaining_strikes == 0:  # GAME_OVER
            self.game_over()
            print('GAME OVER, 3 STRIKES')
            return
        if self.score == 25:  # GAME_OVER
            print('YOU WIN')
            self.game_over()
            return
        self.next_player()

    def discard_card(self, card: 'Card'):
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

    # Called whenever a player draws a card
    def report_draw(self, player_id: int, card: 'Card'):
        for p in self.players:
            if p.id == player_id:
                continue
            p.see_draw(card)
        pass

    def give_clue(self, from_: int, to: int, color: Color | None, rank: Rank | None):
        assert not (color is None and rank is None)
        assert self.clue_tokens > 0
        self.clue_tokens -= 1
        print(
            f'{from_} clues {to} with {color if color else rank} \ttokens:{self.clue_tokens}')
        for p in self.players:
            p.receive_clue(from_, to, color, rank)
        self.next_player()

    def next_player(self):
        self.turns += 1
        if self.turns == MAX_TURNS:
            self.game_over()
            return
        if self.player_turn == self.last_player:  # GAME_OVER
            self.game_over()
            print('GAME OVER, NO MORE CARDS')
            return
        self.player_turn += 1
        self.player_turn %= len(self.players)
        assert 0 <= self.player_turn < len(self.players)
        self.players[self.player_turn].prompt()

    def game_over(self):
        if self.sim:
            self.sim.report(self.score)
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
        # self.chop = 0  # probably make that a proeprty with getting latest unclued card
        self.has_play = False  # probably make that a property
        for _ in range(hand_size):
            self.draw_card()

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

    def draw_card(self):
        card = self.game.deck.draw()
        if card:
            self.game.report_draw(self.id, card)
            self.cards.append(card)
            self.slots.append(Slot(self, card))
        else:
            self.game.last_player = self.id

    # Called when another player receives a draw.
    def see_draw(self, card: 'Card'):
        for s in self.slots:
            s.decrement_possibility(card)

    def play_card(self, idx: int):
        card = self.pop_card(idx)
        self.game.play_card(card)
        pass

    def discard(self, idx: int):
        assert self.game.clue_tokens != MAX_CLUE_TOKENS
        card = self.pop_card(idx)
        self.game.discard_card(card)
        pass

    # Called when a card is guaranteed to not be in your hand, discarded through exhausts, plays or draws.
    def exhaust_possibility(self, card: 'Card'):
        for s in self.slots:
            s.exhaust_possibility(card.color_rank)

    def receive_clue(self, from_: int, to: int, color: Color | None = None, rank: Rank | None = None):
        if from_ == self.id:
            return
        # missing: analyze finesse/bluff
        if to == self.id:
            for idx, s in enumerate(self.slots):
                s.receive_clue(idx, color, rank)

    def pop_card(self, idx: int) -> 'Card':
        assert 0 <= idx < len(self.cards)
        card = self.cards.pop(idx)
        self.slots.pop(idx)
        self.draw_card()
        return card

    def give_clue(self, to: int, color: Color | None = None, rank: Rank | None = None):
        assert not (color is None and rank is None)
        self.game.give_clue(self.id, to, color, rank)

    # Perform a play, discard or clue
    def prompt(self):
        # neighbors = self.game.get_neighbors(self.id)
        # dist = len(neighbors)+1
        # missing: check if can clue, check if should clue
        # 1. respond to possible bluff
        # missing: <stubbed>
        # 2. Look for save
        # for n in neighbors[::-1]:
        #     dist -= 1

        #     def look_for_save(neighor: Player) -> Tuple[int, int | None]:
        #         saves_needed = 0
        #         save_slot: int | None = None
        #         if neighor.has_play:
        #             return saves_needed, save_slot
        #         # missing: if n-1 can clue neighbor
        #         for idx, c in enumerate(neighor.cards):
        #             if idx < neighor.chop:
        #                 continue
        #             if self.game.board.remaining[c.color_rank] == 1:
        #                 saves_needed += 1
        #                 save_slot = idx if save_slot is None else save_slot
        #             else:
        #                 break
        #         return saves_needed, save_slot

        #     saves_needed, save_slot = look_for_save(n)
        #     if saves_needed == dist and save_slot is not None:
        #         # give number save clue to first save_slot
        #         self.give_clue(n.id, rank=n.cards[save_slot].rank)
        #         return

        self.play_card(0)


class Slot():
    def __init__(self, player: Player, card: 'Card'):
        self.player = player
        self.card = card
        cards = Deck.normal_deck()._cards # type: ignore
        self.possibilites: dict[Tuple[Color, Rank], int] = collections.defaultdict(int)
        for c in cards:
            self.possibilites[c.color_rank] += 1
        # self.possibilites = set([(c.color, c.rank)
                                # for c in Deck.normal_deck()._cards])  # type: ignore
        self.probable: set[Tuple[Color, Rank]] = set()
        self.save = False
        self.play = False
        self.clued = False
        # self.is_chop: bool = False #probably make a property

    def __str__(self):
        return f'<card:{self.card}, possibly:{self.possibilites if len(self.possibilites) < 10 else "unk"}>'

    def __repr__(self):
        return self.__str__()
    
    def decrement_possibility(self, card: 'Card'):
        assert self.possibilites[card.color_rank] > 0
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

    def receive_clue(self, idx: int, color: Color | None = None, rank: Rank | None = None):
        assert not (color is None and rank is None)
        # if color and rank:  # only called when all copies are played / trashed
        #     self.remove_possibility((color, rank))
        #     return
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
                for key_color, key_rank in self.possibilites.keys():
                    if key_color != color:
                        del self.possibilites[key_color, key_rank]
                # self.possibilites &= color_set
                self.clued = True
            else:
                map(self.exhaust_possibility, color_set)
        elif rank:
            rank_set = set([(c, rank) for c in Color])
            if self.card.rank == rank:
                for key_color, key_rank in self.possibilites.keys():
                    if key_rank != rank:
                        del self.possibilites[key_color, key_rank]
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
        self._run()

    def _run(self):
        for _ in range(self.runs):
            print()
            print('new_game')
            g = Game(sim=self)
            g.players[2].cards[0] = Card(Color.RED, Rank.FIVE)
            g.players[2].cards[1] = Card(Color.BLU, Rank.FIVE)
            g.next_player()
            del g
        print(
            f'simulations:{self.runs} average_score:{sum(self.scores)/len(self.scores)} max_score:{max(self.scores)}')

    def report(self, score: int):
        self.scores.append(score)


Simulator(1)
# d = Deck.normal_deck()
# print(d)
# s = Stack(Color.RED)
# print(s.next_playable())

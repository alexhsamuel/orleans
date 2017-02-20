import itertools
import random

#-------------------------------------------------------------------------------

def shuffled(items):
    items = list(items)
    random.shuffle(items)
    return items


def fmt_dict(d):
    return " ".join( "{}={}".format(k, v) for k, v in sorted(d.items()) )


def fmt_set(d):
    return " ".join( str(i) for i in sorted(d) )


class Follower:

    NAMES = {
        "boatman",
        "craftsman",
        "farmer",
        "knight",
        "monk",
        "scholar",
        "trader",
    }

    def __init__(self, name, private=False):
        assert name in self.NAMES
        self.name = name
        self.private = private


    def __str__(self):
        return self.name


    def __lt__(self, other):
        return self.name < str(other)


    def __gt__(self, other):
        return self.name > str(other)



class Place:

    def __init__(self, name, slots):
        self.name = name
        self.slots = slots
        self.followers = [ None for s in slots ]


    def __repr__(self):
        return "{}({}, {})".format(
            self.__class__.__name__, self.name, self.followers)


    def __str__(self):
        return self.name


    def __lt__(self, other):
        return self.name < other.name if isinstance(other, Place) else NotImplemented


    @property
    def required(self):
        return [ s for s, f in zip(self.slots, self.followers) if f is None ]


    @property
    def ready(self):
        return all( v is not None for v in self.followers )



class TownHall:

    def __init__(self, slots):
        self.name = "townhall"
        self.slots = slots
        self.followers = set()


    def __repr__(self):
        return "{}({}, {})".format(
            self.__class__.__name__, self.name, fmt_set(self.followers))


    @property
    def ready(self):
        return len(self.followers) > 0
        


def make_board():
    return {
        Place("ship", ["farmer", "boatman", "knight"]),
        Place("wagon", ["farmer", "trader", "knight"]),
        Place("guildhall", ["farmer", "craftsman", "knight"]),
        Place("castle", ["farmer", "boatman", "trader"]),
        Place("scriptorium", ["knight", "scholar"]),
        TownHall(2),
        Place("monastery", ["scholar", "trader"]),
        Place("farmhouse", ["boatman", "farmer"]),
        Place("village", ["farmer", "boatman", "craftsman"]),
        Place("university", ["farmer", "craftsman", "trader"]),
    }


class Player:

    def __init__(self, number):
        self.number = number
        self.bag = {
            Follower(f, private=True)
            for f in (
                "farmer",
                "boatman",
                "craftsman",
                "trader",
            )
        }
        self.market = set()
        self.goods = {
            "wheat": 0,
            "cheese": 0,
            "wine": 0,
            "yarn": 0,
            "brocade": 0,
        }
        self.coins = 5
        self.citizens = set()
        self.tracks = {
            "farmer": 0,
            "boatman": 0,
            "craftsman": 0,
            "trader": 0,
            "knight": 0,
            "scholar": 0,
            "development": 0,
        }
        self.tech = 0
        self.places = make_board()


    @property
    def status(self):
        dev = self.tracks["development"]
        if dev == 30:
            return 6
        elif dev >= 22:
            return 5
        elif dev >= 15:
            return 4
        elif dev >= 9:
            return 3
        elif dev >= 4:
            return 2
        else:
            return 1


    @property
    def points(self):
        return (
            self.coins
            + self.goods["wheat"] * 1
            + self.goods["cheese"] * 2
            + self.goods["wine"] * 3
            + self.goods["yarn"] * 4
            + self.goods["brocade"] * 5
            + (
                len(self.citizens)
                + 0  # FIXME: stations
            ) * self.status
        )


    def format(self):
        yield "number: {}".format(self.number)
        yield "points: {}".format(self.points)
        yield "bag: " + fmt_set(self.bag)
        yield "market: " + fmt_set(self.market)
        yield "goods: " + fmt_dict(self.goods)
        yield "coins: {}".format(self.coins)
        yield "citizens: " + fmt_set(self.citizens)
        yield "tracks: " + fmt_dict(self.tracks)
        yield "status: {}".format(self.status)
        yield "tech: {}".format(self.tech)
        yield "places:"
        for place in sorted(self.places, key=lambda p: p.name):
            if isinstance(place, TownHall):
                yield "  {}: {}".format(
                    place.name, 
                    " ".join(sorted(
                        str(f) for f in place.followers if f is not None )))
            else:
                yield "  {}: {}".format(
                    place.name, 
                    " ".join(
                        "{}={}".format(s, f)
                        for s, f in zip(place.slots, place.followers)
                    )
                )



class Deed:

    def __init__(self, name, coins, slots):
        self.name = name
        self.coins = coins
        self.slots = [ [s, False] for s in slots ]


    @property
    def done(self):
        return all( s[1] for s in self.slots )


    def has_room(self, follower):
        return any( not s[1] for s in self.slots if s[0] == follower )


    def fill(self, follower):
        for slot in self.slots:
            if slot[0] == follower.name and not slot[1]:
                slot[1] = True
                break
        else:
            assert False, "no room for {} in {}".format(follower, self.name)



class Game:

    def __init__(self, num_players):
        self.players = [ Player(p) for p in range(num_players) ]
        self.first = 0
        self.map = None
        self.deeds = None
        self.turn = None
        self.turns = sum(
            ( 
                [card] * 3
                for card in (
                    "pilgrimage", "income", "harvest", "taxes", 
                    "trading", "plague",
                )
            ),
            []
        )
        # FIXME: This is wrong.
        self.coins = 200
        # FIXME: These are wrong.
        # FIXME: Values depend on num_players.
        self.followers = {
            "monk": 12,
            "boatman": 12,
            "craftsman": 12,
            "trader": 12,
            "farmer": 12,
            "scholar": 12,
            "knight": 12,
        }
        # FIXME: These are wrong.
        self.goods = {
            "wheat": 20,
            "cheese": 20,
            "wine": 20,
            "yarn": 20,
            "brocade": 20,
        }
        # First turn is always pilgrimage; others shuffled.
        first_turn = self.turns.pop(0)
        random.shuffle(self.turns)
        self.turns.insert(0, first_turn)
        self.citizens = {
            "knight",
            "boatman",
            "development3",
            "development18",
            "development28",
        }
        self.deeds = {
            Deed(
                "citywall", 1, 
                ["knight"] * 3 
                + ["trader"]
                + ["farmer"] * 3
                + ["craftsman"] * 3
            ),
            Deed(
                "papalconclave", 3, 
                ["monk", "monk", "knight"]
            ),
            Deed(
                "defeatplague", 2, 
                ["scholar"] * 2 + ["boatman", "farmer", "trader"]
            ),
            Deed(
                "astronomy", 1,
                ["scholar", "scholar", "trader"]
            ),
            Deed(
                "boatmanguild", 1,
                ["scholar"] + ["boatman"] * 3
            ),
            Deed(
                "cathedral", 2,
                ["craftsman"] * 2 + ["monk"] * 2 + ["trader"] * 2
            ),
            Deed(
                "peacetreaty", 2, 
                ["monk", "scholar", "knight", "knight"]
            ),
            Deed(
                "canalization", 1,
                ["boatman"] * 3
                + ["trader"] * 2
                + ["farmer"] * 3
                + ["craftsman"] * 2
            ),
        }
        # One citizen available per deed.
        self.citizens.update( d.name for d in self.deeds )


    def format(self):
        yield "turn: {}: {}".format(17 - len(self.turns), self.turn)
        yield "first player: {}".format(self.first)
        # yield map
        yield "deeds:"
        for deed in sorted(self.deeds, key=lambda d: d.name):
            yield deed.name + ": " + " ".join(
                "{}:{}".format(s, "X" if t else "-")
                for s, t in deed.slots
            )
        yield "citizens: " + fmt_set(self.citizens)
        yield "followers: " + fmt_dict(self.followers)
        yield "goods: " + fmt_dict(self.goods)
        for player in self.players:
            yield "player:"
            for line in player.format():
                yield "  " + line


    @property
    def num_players(self):
        return len(self.players)



def log(msg):
    print(msg)


def phase1(game):
    game.turn = game.turns.pop(0)
    log("turn {}: {}".format(17 - len(game.turns), game.turn))


def phase2(game):
    farmers = [ (p.tracks["farmer"], i) for i, p in enumerate(game.players) ]
    farmers.sort()
    if len(game.players) > 2 and farmers[0][0] < farmers[1][0]:
        loser = farmers[0][1]
        log("census: player {} loses".format(loser)) 
        pay_coins(game, game.players[loser], -1)
    if farmers[-2][0] < farmers[-1][0]:
        winner = farmers[-1][1]
        log("census: player {} wins".format(winner))
        pay_coins(game, game.players[winner], 1)


def phase3(game):
    for p, player in enumerate(game.players):
        num_draw = {
            0: 4, 1: 5, 2: 6, 3: 7, 4: 7, 5: 8,
        }[player.tracks["knight"]]

        # Can't draw more than is in the bag.
        num_draw = min(num_draw, len(player.bag))
        # Can't draw more than fits in the market.
        max_market = 8  # FIXME: powder tower
        num_draw = min(num_draw, max_market - len(player.market))

        bag = list(player.bag)
        random.shuffle(bag)
        draw = bag[: num_draw]

        log("followers: player {} draws {}".format(p, ", ".join( str(f) for f in draw )))
        for d in draw:
            player.bag.remove(d)
            player.market.add(d)


def can_fill(game, place, player):
    if place.name == "townhall":
        num_slots = place.slots - len(place.followers)
        return (
            fs 
            for s in range(num_slots)
            for fs in itertools.permutations(player.market, s + 1)
            if all( 
                not f.private
                and any( d.has_room(f.name) for d in game.deeds )
                for f in fs
            )
        )

    # FIXME: Other fungible people.
    def matches(slot, follower):
        return (
            slot == follower.name
            or follower.name == "monk"
        )

    empty_slots = [ 
        s for s, f in zip(place.slots, place.followers) if f is None ]
    return () if len(empty_slots) == 0 else (
        fs
        for fs in itertools.permutations(player.market, len(empty_slots))
        if all( matches(s, f) for s, f in zip(empty_slots, fs) )
    )


def plan(game, player):
    while True:
        try:
            place, followers = random.choice([
                (place, f)
                for place in player.places
                for f in can_fill(game, place, player)
            ])
        except IndexError:
            break
        else:
            log("planning: player {} places {} in {}"
                .format(player.number, fmt_set(followers), place.name))
            if isinstance(place, TownHall):
                for follower in followers:
                    player.market.remove(follower)
                    place.followers.add(follower)
            else:
                for i, follower in zip(range(len(place.followers)), followers):
                    player.market.remove(follower)
                    assert place.followers[i] is None
                    place.followers[i] = follower


def phase4(game):
    # FIXME: Completely random.
    for player in game.players:
        plan(game, player)


TRACK_MAX = {
    "farmer": 8,
    "craftsman": 5,
    "trader": 5,
    "boatman": 5,
    "knight": 5,
    "scholar": 5,
    "development": 30,
}

def pay_coins(game, player, num):
    num = min(num, game.coins)
    log("player {} paid {} coins".format(player.number, num))
    game.coins -= num
    player.coins += num


def advance_development(game, player, num=1):
    for _ in range(num):
        if player.tracks["development"] == TRACK_MAX["development"]:
            break
        player.tracks["development"] += 1
        dev = player.tracks["development"]
        if dev == 3:
            award_citizen(game, player, "development3")
        elif dev == 7:
            pay_coins(game, player, 3)
        elif dev == 12:
            pay_coins(game, player, 4)
        elif dev == 18:
            award_citizen(game, player, "development18")
        elif dev == 25:
            pay_coins(game, player, 5)
        elif dev == 28:
            award_citizen(game, player, "development28")
    log("player {} development: {}"
        .format(player.number, player.tracks["development"]))


def send_to_deeds(game, player, follower):
    deeds = [ d for d in game.deeds if d.has_room(follower.name) ]
    if len(deeds) == 0:
        return False
    else:
        # FIXME: Strategy.
        deed = random.choice(deeds)
        log("player {} send {} to {}"
            .format(player.number, follower, deed.name))
        deed.fill(follower)
        pay_coins(game, player, deed.coins)
        # FIXME: Development for canalization.
        if deed.done:
            log("deed {} done".format(deed.name))
            award_citizen(game, player, deed.name)
        return True


def add_new_follower(game, player, follower):
    if game.followers[follower] > 0:
        log("player {}: adding new {}".format(player.number, follower))
        game.followers[follower] -= 1
        player.bag.add(Follower(follower))
    else:
        log("player {}: no more {}".format(player.number, follower))


def award_citizen(game, player, citizen):
    if citizen in game.citizens:
        log("player {} got citizen {}".format(player.number, citizen))
        game.citizens.remove(citizen)
        player.citizens.add(citizen)


def do_action(game, player, place):
    log("action: player {}: {}".format(player.number, place.name))
    if place.name == "ship":
        # FIXME
        pass

    elif place.name == "wagon":
        # FIXME
        pass

    elif place.name == "guildhall":
        # FIXME
        pass

    elif place.name == "castle":
        add_new_follower(game, player, "knight")
        if player.tracks["knight"] < TRACK_MAX["knight"]:
            player.tracks["knight"] += 1
            if player.tracks["knight"] == 4:
                award_citizen(game, player, "knight")

    elif place.name == "scriptorium":
        advance_development(game, player)

    elif place.name == "townhall":
        for follower in list(place.followers):
            if send_to_deeds(game, player, follower):
                place.followers.remove(follower)

    elif place.name == "monastery":
        add_new_follower(game, player, "monk")

    elif place.name == "farmhouse":
        add_new_follower(game, player, "farmer")
        if player.tracks["farmer"] < TRACK_MAX["farmer"]:
            good = [
                "wheat", "wheat", "cheese", "cheese", "wine", "wine",
                "yarn", "brocade",
            ][player.tracks["farmer"]]
            if game.goods[good] > 0:
                game.goods[good] -= 1
                player.goods[good] += 1
            player.tracks["farmer"] += 1

    elif place.name == "village":
        # FIXME
        follower = random.choice(["boatman", "craftsman", "trader"])
        add_new_follower(game, player, follower)
        if follower == "boatman":
            if player.tracks["boatman"] < TRACK_MAX["boatman"]:
                player.tracks["boatman"] += 1
                coins = [None, 2, 3, 4, 5, 0][player.tracks["boatman"]]
                pay_coins(game, player, coins)
                if player.tracks["boatman"] == 5:
                    award_citizen(game, player, "boatman")

    elif place.name == "university": 
        add_new_follower(game, player, "scholar")
        if player.tracks["scholar"] < TRACK_MAX["scholar"]:
            player.tracks["scholar"] += 1
            advance_development(game, player, 1 + player.tracks["scholar"])

    else:
        assert False, "unknown place: {}".format(place.name)


def do_an_action(game, player):
    ready_places = [ p for p in player.places if p.ready ]

    # Remove townhall places that can't be placed.
    ready_places = [
        p for p in ready_places
        if not (
            isinstance(p, TownHall)
            and all( 
                not any( 
                    d.has_room(f.name)
                    for d in game.deeds
                )
                for f in p.followers
            )
        )
    ]

    if len(ready_places) > 0:
        place = random.choice(ready_places)
        do_action(game, player, place)
        if place.name != "townhall":
            # Move followers from the place to the bag.
            player.bag.update(place.followers)
            place.followers = [None] * len(place.followers)
        return True
    else:
        return False


def phase5(game):
    players = game.players[game.first :] + game.players[: game.first]
    while len(players) > 0:
        player = players.pop(0)
        if do_an_action(game, player):
            players.append(player)

        
def phase6(game):
    # FIXME
    pass


def phase7(game):
    game.first = (game.first + 1) % game.num_players


def log_game(game):
    log("")
    for line in game.format():
        log(line)


def turn(game):
    log("-" * 80)
    phase1(game)
    phase2(game)
    phase3(game)
    phase4(game)
    # log_game(game)
    phase5(game)
    phase6(game)
    phase7(game)
    log_game(game)


def main():
    game = Game(4)
    while len(game.turns) > 0:
        turn(game)


if __name__ == "__main__":
    main()



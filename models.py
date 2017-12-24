from flask import render_template
from string import ascii_lowercase
from random import choice, shuffle


class InvalidConfigurationError(Exception):
    pass


rooms = {} # tablecode : room

# to keep track of which usernames are taken
names = {} # uid : username
nameset = set()


class Roles:
    Lancelots = 'Lancelots'
    GoodLancelot = 'Good Lancelot'
    EvilLancelot = 'Evil Lancelot'
    GenericGood = 'Generic Good'
    GenericEvil = 'Generic Evil'

    # bound to the checkboxes in configure.html
    # careful when changing
    Merlin = 'Merlin'
    Percival = 'Percival'
    Assassin = 'Assassin'
    Morganna = 'Morganna'
    Mordred = 'Mordred'
    Oberron = 'Oberron'


EvilGroup = Roles.Assassin, Roles.Morganna, Roles.Mordred, Roles.GenericEvil
LancelotGroup = Roles.GoodLancelot, Roles.EvilLancelot

MerlinSees = Roles.Assassin, Roles.Morganna, Roles.Oberron, Roles.GenericEvil
PercivalSees = Roles.Morganna, Roles.Merlin

vision_matrix = (
    ((Roles.Merlin,),   MerlinSees,     'evil'),
    ((Roles.Percival,), PercivalSees,   'magicians'),
    (EvilGroup,         EvilGroup,      'evil with you'),
    (LancelotGroup,     LancelotGroup,  'the other Lancelot'))


class Room:
    def __init__(self, code):
        # username : rolename
        self.code = code
        rooms[code] = self

        self.roles = []
        self.assignments = {}     # uid : role
        self.reverse_lookup = {}  # role : uid

        self.rematch = None

    def has(self, s):
        return self.config[s] == 'checked'

    def configure(self, config):
        self.config = config

        if config['Lancelots']:
            self.roles.append(Roles.GoodLancelot)
            self.roles.append(Roles.EvilLancelot)

        good = Roles.Merlin, Roles.Percival
        bad = Roles.Assassin, Roles.Mordred, Roles.Morganna, Roles.Oberron

        for name in good+bad:
            if self.has(name):
                self.roles.append(name)

        for special_names, generic_name in ((bad, Roles.GenericEvil),
                               (good, Roles.GenericGood)):

            if special_names==bad:
                faction_size = (2,3)[config['numPlayers'] > 6]
                special_count = sum(self.has(name) for name in special_names)
                num_generic = faction_size - special_count
            else:
                num_generic = config['numPlayers'] - len(self.roles)

            if num_generic < 0:
                raise InvalidConfigurationError('Too many special roles!!')
            for _ in range(num_generic):
                self.roles.append(generic_name)

        if len(self.roles) != config['numPlayers']:
            raise InvalidConfigurationError('Something went wrong :(')

        self.possibly_make_assignments()

    def render(self, username):
        return render_template(
            'room.html',
            roomcode=self.code,
            players=str(', '.join(self.shuffled_player_names)),
            roles=str(', '.join(self.roles)),
            status=self.status,
            role_info=self.role_info(username),
        )

    @property
    def shuffled_player_names(self):
        p = list(names[k] for k in self.assignments.keys())
        shuffle(p)
        return p

    @property
    def shuffled_player_uids(self):
        p = list(self.assignments.keys())
        shuffle(p)
        return p

    @property
    def status(self):
        return f'{len(self.assignments)}/{len(self.roles)}'

    @property
    def full(self):
        return len(self.assignments) == len(self.roles)

    def try_adding(self, uid):
        self.assignments.setdefault(uid, None)
        self.possibly_make_assignments()

    def possibly_make_assignments(self):
        if self.full and all(r is None for r in self.assignments.values()) and hasattr(self, 'roles'):

            for uid, r in zip(self.shuffled_player_uids, self.roles):
                self.assignments[uid] = r

            self.reverse_lookup = {r:uid for uid,r in self.assignments.items()}

    def role_info(self, your_uid):
        your_role = self.assignments.get(your_uid, None)
        info = []

        if your_role is not None:
            info.append(f'You are {your_role}.')

        for group,target,description in vision_matrix:
            if your_role not in group: continue

            people = [names[uid] for uid in
                      (self.reverse_lookup.get(role,None) for role in target)
                      if uid not in (your_uid,None)]

            l = (f'{people[0]} is',
                 f'{", ".join(people[:-1]) + " and " + people[-1] } are'
                 )[len(people) > 1]

            info.append(f'{l} {description}.')

        # helpful reminders
        if your_role is Roles.Merlin and Roles.Mordred in self.roles:
            info.append('Mordred remains hidden.')
        if your_role in EvilGroup and Roles.Oberron in self.roles:
            info.append('Oberron is out there somewhere.')

        return info


class Configuration:
    @classmethod
    def default(cls, numPlayers=7, Merlin=True, Percival=True, Assassin=True,
                 Morganna=True, Mordred=True, Oberron=False, Lancelots=False):

        numPlayers = int(numPlayers)

        j = {'numPlayers': numPlayers}

        for i in range(5,10):
            j[f'players{i}'] = ('','selected')[i == numPlayers]

        for role in Roles.Merlin,Roles.Percival,Roles.Assassin,Roles.Morganna,Roles.Mordred,Roles.Oberron,Roles.Lancelots:
            j[role] = ('','checked')[bool(eval(role))]

        return j

    @classmethod
    def build(cls, form):
        return Configuration.default(
            form['num_players'],
            Merlin = Roles.Merlin in form,
            Percival = Roles.Percival in form,
            Assassin = Roles.Assassin in form,
            Morganna = Roles.Morganna in form,
            Mordred = Roles.Mordred in form,
            Oberron = Roles.Oberron in form,
            Lancelots = Roles.Lancelots in form,
        )

def invalidRoomCode(code):
    return any((
        type(code) != str,
        len(code) != 4,
        any(l not in ascii_lowercase for l in code)))

def newRoomCode():
    while True:
        tentative = ''.join(choice(ascii_lowercase) for _ in range(4))
        if rooms.get(tentative) is None:
            return tentative

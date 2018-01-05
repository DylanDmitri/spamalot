from flask import render_template, session
from spam import bidirection, names
from random import shuffle

def shuffled(i):
    p = list(i)
    shuffle(p)
    return p

class Role:
    generic_good = 'Generic Good'
    generic_evil = 'Generic Evil'

    good_lancelot = 'Good Lancelot'
    evil_lancelot = 'Evil Lancelot'
    merlin = 'Merlin'
    percival = 'Percival'
    assassin = 'the Assassin'
    morganna = 'Morganna'
    mordred = 'Mordred'
    oberron = 'Oberron'

every_role = {v for k,v in Role.__dict__.items() if not k.startswith('_')}
lancelots = {Role.good_lancelot, Role.evil_lancelot}
good_group = {Role.merlin, Role.percival, Role.generic_good}
evil_group = every_role - lancelots - good_group

vision_matrix = (
    # these people    know that    those people         are     this
    ({Role.merlin},              evil_group-{Role.mordred},    'evil'),
    ({Role.percival},            {Role.merlin, Role.morganna}, 'magical'),
    (evil_group-{Role.oberron},  evil_group-{Role.oberron},    'evil with you'),
    (lancelots,                  lancelots,                    'the other Lancelot'))


class Room:
    def __init__(self):
        self.config = None
        self.assignments = bidirection()
        self.rematch = None

    def assign_roles(self, config):
        self.config = config
        self.possibly_make_assignments()

    def possibly_make_assignments(self):
        if all((self.config, len(self.config.roles)==self.config.num_players,
                all(self.assignments[uid] is None for uid in self.uids))):
            for uid, r in zip(shuffled(self.uids), self.config.roles):
                self.assignments[uid] = r

    @property
    def players(self):
        return [names[uid] for uid in self.uids]

    @property
    def uids(self):
        return [k for k in self.assignments if len(k)>40]

    def render(self, uid):

        self.assignments.setdefault(uid)
        self.possibly_make_assignments()

        return render_template(
            'room.html',
            roomcode = session['room'],
            players=', '.join(shuffled(self.players)),
            roles=', '.join(self.config.roles),
            status=f'{len(self.assignments)}/{len(self.config.roles)}',
            role_info=self.role_info(uid),
        )

    def role_info(self, your_uid):
        your_role = self.assignments.get(your_uid,None)
        info = []

        if your_role is not None:
            info.append(f'You are {your_role}.')

        for group,target,description in vision_matrix:
            if your_role not in group: continue

            people = [names[uid] for uid in
                      (self.assignments.get(role,None) for role in target)
                      if uid not in (your_uid,None)]

            if people:
                l = (f'{people[0]} is',
                     f'{", ".join(people[:-1]) + " and " + people[-1] } are'
                     )[len(people) > 1]
                info.append(f'{l} {description}.')

        if your_role is Role.merlin and Role.mordred in self.config.roles:
            info.append('Mordred remains hidden.')
        if your_role in evil_group and Role.oberron in self.config.roles:
            info.append('Oberron is out there somewhere.')

        return info


class Configuration(dict):

    checkboxes = ((Role.merlin, Role.percival),
                  (Role.assassin, Role.morganna, Role.mordred, Role.oberron),
                  (Role.good_lancelot, Role.evil_lancelot))

    def __init__(self, form):

        # needed by html
        super().__init__(('num_players', form['num_players']))

        # todo :: messy, clean up
        for i in range(5,10):
            self[f'players{i}'] = ('','selected')[i == self['num_players']]

        self.update({
            ('', 'checked')[role in form]
            for g in self.checkboxes for role in g})

        # roles directly from checkboxes
        self.complaints = []
        self.roles = [role for g in self.checkboxes for role in g if self[role]]

        # add in the generics
        size = {'evil':(2,3)[self['num_players'] > 6]}
        size['good'] = self['num_players'] - size['evil']

        for name, size, group, role in (('evil', evil_group, Role.generic_evil),
                                        ('good', good_group, Role.generic_good)):

            special = sum(n in self.roles for n in group)
            generic = size[name] - special

            if generic < 0:
                self.complaints.append(f'Too many {name} roles')

            for _ in range(generic):
                self.roles.append(role)

    @classmethod
    def default(cls):
        return Configuration({
            'num_players' : 7,
            Role.merlin : True,
            Role.percival : True,
            Role.assassin : True,
            Role.morganna : True,
            Role.mordred : True,
            Role.oberron : False,
            Role.evil_lancelot : False,
            Role.good_lancelot : False,
        })
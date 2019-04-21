from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
from random import choice, shuffle, randint
from string import ascii_letters
from collections import Counter, defaultdict
from time import time
import os

filename = os.path.join(os.path.dirname(__file__), 'room_names.txt')
WORDS = tuple(n.strip() for n in open(filename))
NAME_TIMEOUT = 300  # in seconds

# --- globals ---
class Role:
    generic_good = 'Generic good'
    generic_evil = 'Generic evil'

    good_lancelot = 'Good Lancelot'
    evil_lancelot = 'Evil Lancelot'

    single_lancelot_good = 'the Good Lancelot'
    single_lancelot_evil = 'the Evil Lancelot'

    merlin = 'Merlin'
    percival = 'Percival'
    assassin = 'the Assassin'
    morgana = 'Morgana'
    mordred = 'Mordred'
    oberon = 'Oberon'

EVERY_ROLE = {v for k,v in Role.__dict__.items() if not k.startswith('_')}

DISPLAY_OVERRIDE = {
    Role.single_lancelot_good: 'Lancelot',
    Role.single_lancelot_evil: 'Lancelot',
}

DOUBLE_LANCELOTS = {Role.good_lancelot,Role.evil_lancelot}
SINGLE_LANCELOTS = {Role.single_lancelot_good,Role.single_lancelot_evil}

GOOD_ALIGNED = {Role.merlin,Role.percival,Role.generic_good}
EVIL_GROUP = {Role.assassin, Role.mordred, Role.morgana, Role.generic_evil}
EVIL_ALIGNED = {*EVIL_GROUP, Role.oberon}

GOOD_ALIGNED_ALL = {*GOOD_ALIGNED, Role.good_lancelot, Role.single_lancelot_good}
EVIL_ALIGNED_ALL = {*EVIL_ALIGNED, Role.evil_lancelot, Role.single_lancelot_evil}

VISIBLE_EVIL = {*EVIL_ALIGNED, Role.evil_lancelot, Role.single_lancelot_evil, Role.single_lancelot_good} - {Role.mordred}

VISION_MATRIX = (
    # these people    know that    those people       are        this        css_class
    ({Role.merlin},     VISIBLE_EVIL,                 'evil',               'danger'),
    ({Role.percival},   {Role.merlin, Role.morgana},  'Merlin or Morgana',  'warning'),
    (EVIL_GROUP,        EVIL_GROUP,                   'also evil',          'danger'),
    (EVIL_GROUP,        DOUBLE_LANCELOTS,             'the Lancelots',      'warning'),
    (EVIL_GROUP,        SINGLE_LANCELOTS,             'the Lancelot',       'warning'),
    (DOUBLE_LANCELOTS,  DOUBLE_LANCELOTS,             'the other Lancelot', 'warning'),)

DEFAULT_FORM = {'num_players':7, Role.merlin:True, Role.percival:True,
                Role.assassin:True, Role.morgana:True, Role.mordred:True,}
EMPTY_FORM = {'num_players':-1}

# ---- helpers ----

def random_string(length):
    return ''.join(choice(ascii_letters) for _ in range(length))

def newRoomCode():
    for _ in range(50):
        tentative = choice(WORDS)
        if rooms.get(tentative) is None:
            return tentative
    return "BEANS"

def get_secret():
    if 'secret.txt' not in os.listdir('.'):
        open('secret.txt', 'w').write(random_string(100))
    return open('secret.txt').read()

def shuffled(i):
    p = list(i)
    shuffle(p)
    return p

# --- database ---
names = {}
name_last_used = {}
rooms = {}

# --- models ---
class Room:
    def __init__(self, creator_uid):
        self.config = Configuration(EMPTY_FORM)
        self.assignments = {} # uid -> role
        self.role_lookup = defaultdict(lambda: set())
        self.spectators = set()
        self.doing_config = names[session['uid']]

        self.creator_uid = creator_uid

    def configure(self, config):
        self.config = config
        self.possibly_make_assignments()
        self.doing_config = False

    def possibly_make_assignments(self):
        if self.config and self.full and all(self.assignments[uid] is None for uid in self.uids):
            if self.config['prank_mode']:
                for uid in self.uids:
                    self.assignments[uid] = Role.merlin
            else:
                for uid, r in zip(shuffled(self.uids),self.config['roles']):
                    self.assignments[uid] = r
                    self.role_lookup[r].add(uid)

    @property
    def players(self):
        return [names[uid] for uid in self.uids]

    @property
    def uids(self):
        return tuple(self.assignments)

    @property
    def full(self):
        return len(self.assignments) == self.config['num_players']

    def get_role_css_class(self, role):
        if role in GOOD_ALIGNED:
            return 'info'
        elif role in EVIL_ALIGNED:
            return 'danger'
        else:
            return 'warning'

    def render(self,uid):
        if self.full and not (uid in self.uids):
            self.spectators.add(uid)
        else:
            self.assignments.setdefault(uid)
            self.possibly_make_assignments()

        role_counts = Counter(self.config['roles'])
        roles = [{
            'name': DISPLAY_OVERRIDE[name] if name in DISPLAY_OVERRIDE else name,
            'count': count,
            'css_class': self.get_role_css_class(name),
            } for name, count in role_counts.items()]

        return render_template(
            'game.html',
            username=names.get(session['uid'], ''), # hacky
            roomcode=session['room'],
            doing_config=self.doing_config,
            is_creator=session['uid'] == self.creator_uid,
            players=self.players,
            roles=roles,
            status=f'{len(self.players)}/{self.config["num_players"]}',
            role_info=self.role_info(uid),
        )

    def role_info(self, your_uid):
        if your_uid in self.spectators:
            return self.spectator_info()

        your_role = self.assignments.get(your_uid, None)

        info = {
            'messages': [],
            'has_role': True,
            'role_name': '',
            'role_css_class': self.get_role_css_class(your_role),
            'original_is_good': False, # Hack for easy code in alignment sweet alert
            'original_alignment': 'Error',
        }

        if your_role is None:
            info['has_role'] = False
            return info

        info['role_name'] = f'{your_role}'
        if your_role in GOOD_ALIGNED_ALL:
            info['original_alignment'] = 'good'
            info['original_is_good'] = True
        elif your_role in EVIL_ALIGNED_ALL:
            info['original_alignment'] = 'evil'

        for group,target,description,people_css_class in VISION_MATRIX:
            if your_role not in group: continue

            people = [names[uid] for uid in
                      set.union(*[self.role_lookup.get(role,set()) for role in target])
                      if uid not in (your_uid,None)]

            if people:
                info['messages'].append({
                    'people': people,
                    'text': description,
                    'people_css_class': people_css_class,
                })

        if self.config['prank_mode']:
            valid_fakes = self.players
            valid_fakes.remove(names[your_uid])

            num_evil = len(set(self.config['roles']) & set(VISIBLE_EVIL))
            shuffle(valid_fakes)
            fake_evil = valid_fakes[0:num_evil]

            info['messages'].append({
                'people': fake_evil,
                'text': 'evil as shit',
                'people_css_class': 'danger'
            })

        if your_role is Role.merlin and Role.mordred in self.config['roles']:
            info['messages'].append({
                'people': ['Mordred'],
                'text': 'remains hidden',
                'people_css_class': 'danger',
                'custom_message': True,
            })
        if your_role in EVIL_GROUP-{Role.oberon} and Role.oberon in self.config['roles']:
            info['messages'].append({
                'people': ['Oberon'],
                'text': 'is out there somewhere',
                'people_css_class': 'danger',
                'custom_message': True,
            })

        return info

    def spectator_info(self):
        info = {
            'messages': [],
            'has_role': True,
            'role_name': 'spectator',
        }

        for role in EVERY_ROLE:
            if role not in self.role_lookup: continue

            people = [names[uid] for uid in self.role_lookup[role]]

            info['messages'].append({
                'people': people,
                'text': role,
                'people_css_class': self.get_role_css_class(role)
            })

        return info


def Configuration(form):
    """
    Transforms: Checked Options -> List of Roles
    """
    conf = {}

    conf['checkboxes'] = ((Role.merlin,Role.percival),
                          (Role.assassin,Role.morgana,Role.mordred,Role.oberon))

    conf['boxes'] = [r for g in conf['checkboxes'] for r in g]

    # needed by html
    conf['num_players'] = int(form['num_players'])
    conf['num_lancelots'] = int(form.get('num_lancelots', 0))

    conf['selected'] = {r:r in form for r in conf['boxes']}

    conf['prank_mode'] = randint(1, 100) == 1 if form.get('enable_prank_mode') else False

    # generate a list of roles
    conf['complaints'] = []

    conf['roles'] = [role for role in conf['boxes'] if role in form]

    if conf['num_lancelots'] == 1:
        conf['roles'].append(
            choice((Role.single_lancelot_evil, Role.single_lancelot_good)))
    elif conf['num_lancelots'] == 2:
        conf['roles'].append(Role.good_lancelot)
        conf['roles'].append(Role.evil_lancelot)

    size = {'evil':2}
    if conf['num_players'] >= 7:
        size['evil'] = 3
    if conf['num_players'] >= 10:
        size['evil'] = 4

    size['good'] = conf['num_players'] - size['evil'] - conf['num_lancelots']

    for name,group,role in (('evil',EVIL_ALIGNED,Role.generic_evil),
                            ('good',GOOD_ALIGNED,Role.generic_good)):

        special = sum(n in conf['roles'] for n in group)
        generic = size[name] - special

        if generic < 0:
            conf['complaints'].append(f'Too many {name} roles')

        for _ in range(generic):
            conf['roles'].append(role)

    return conf

# --- framework ---
class ComplaintException(Exception):
    pass


app = Flask(__name__)
app.secret_key = get_secret()

@app.route('/bower_components/<path:path>')
def send_js(path):
    return send_from_directory('bower_components', path)

class Carafe:
    def __init__(self):
        self.name = self.__class__.__name__.lower()
        self.path = (f'/{self.name}/', '/')[self.name == 'index']
        self.template = f'{self.name}.html'

        app.add_url_rule(self.path, self.name, self._render, methods=['GET'])
        app.add_url_rule(self.path, self.name+'_p', self.form, methods=['POST'])

        self.complaints = []

    def __init_subclass__(cls, **kwargs):
        cls()  # beaned lmao

    def _render(self):
        if 'uid' not in session:
            session['uid'] = random_string(50)

        if (session['uid'] not in names) and (self.name != 'login'):
            return redirect(url_for('login'))

        if session['uid'] in names:
            name_last_used[names[session['uid']]] = time()

        return self.render()

    def render(self):
        return render_template(self.template, **self._context())

    def form(self):
        try:
            self.complaints = []
            return self.process(request.form)
        except ComplaintException:
            return self.render()

    def complain(self, args):
        if type(args) is str:
            args = (args,)

        if args:
            self.complaints = args[:]
            raise ComplaintException()

    def _context(self):
        return {**(self.context() or {}),
                'complaints':self.complaints,
                'username':names.get(session['uid'], ''),
                'roomcode':session.get('room', '')}

    def context(self):
        return None

    process = NotImplemented

# --------- the pages themselves ----------
class Index(Carafe):
    pass

class Login(Carafe):
    def process(self, form):
        newname = form['user_input'].strip()

        username_taken = False
        if newname in names.values():
            if newname==names.get(session['uid'], None):
                '''then it's your name, and it's okay'''
            elif time() - name_last_used.get(newname, 0) > NAME_TIMEOUT:
                '''then it's timed out, and it's okay'''
            else:
                username_taken = True

        self.complain([message for condition, message in (
                  (username_taken, 'Username is already taken.'),
                  (not (set(newname) < set(ascii_letters + " ")),'No special characters.'),
                  (len(newname)<2, 'Username is too short'),
                  (len(newname)>30,'Username is too long'))
                  if condition])

        # out with the old
        if newname in names.values():
            names[newname] = None

        # in with the new
        name_last_used[newname] = time()
        names[session['uid']] = newname
        return redirect(url_for('index'))

class CreateRandomRoom(Carafe):
    def render(self):
        session['room'] = newRoomCode()
        rooms[session['room']] = Room(session['uid'])
        return redirect(url_for('create'))

class Create(Carafe):
    def context(self):
        return session.get('config', Configuration(DEFAULT_FORM))

    def process(self, form):
        config = Configuration(form)
        session['config'] = config

        self.complain(config['complaints'])

        room = rooms[session['room']]
        room.configure(config)
        return redirect(url_for('game'))

class Join(Carafe):
    def process(self, form):
        session['room'] = ''.join(c for c in form['user_input'] if c in ascii_letters).lower()
        room = rooms.get(session['room'])

        if room is None:
            self.complain('That room does not exist')

        elif room.full and session['uid'] not in room.uids:
            return redirect(url_for('game'))
            # self.complain('That room is already full')

        return redirect(url_for('game'))

class Game(Carafe):
    def render(self):
        room = rooms[session['room']]
        return room.render(session['uid'])

    def process(self, form): # rematch
        roomcode = session['room']
        oldRoom = rooms[roomcode]
        session['config'] = oldRoom.config

        rooms[roomcode] = Room(session['uid'])
        session['room'] = roomcode

        return redirect(url_for('create'))

# and run the darned thing
if __name__ == '__main__':
    app.run(debug=False)

from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
from random import choice, shuffle
from string import ascii_letters
from collections import Counter
import os

WORDS = tuple(open('room_names.txt'))

# --- globals ---
class Role:
    generic_good = 'Generic good'
    generic_evil = 'Generic evil'

    good_lancelot = 'Good Lancelot'
    evil_lancelot = 'Evil Lancelot'

    single_lancelot_good = 'Lancelot'
    single_lancelot_evil = 'Lancelot'

    merlin = 'Merlin'
    percival = 'Percival'
    assassin = 'the Assassin'
    morgana = 'Morgana'
    mordred = 'Mordred'
    oberron = 'Oberon'

EVERY_ROLE = {v for k,v in Role.__dict__.items() if not k.startswith('_')}

DOUBLE_LANCELOTS = {Role.good_lancelot,Role.evil_lancelot}
SINGLE_LANCELOTS = {Role.single_lancelot_good,Role.single_lancelot_evil}

GOOD_ALIGNED = {Role.merlin,Role.percival,Role.generic_good}
EVIL_GROUP = {Role.assassin, Role.mordred, Role.morgana, Role.generic_evil}
EVIL_ALIGNED = {*EVIL_GROUP, Role.oberron}

GOOD_ALIGNED_ALL = {*GOOD_ALIGNED, Role.good_lancelot, Role.single_lancelot_good}
EVIL_ALIGNED_ALL = {*EVIL_ALIGNED, Role.evil_lancelot, Role.single_lancelot_evil}

VISIBLE_EVIL = {*EVIL_ALIGNED, Role.evil_lancelot, Role.single_lancelot_evil, Role.single_lancelot_good} - {Role.mordred}

VISION_MATRIX = (
    # these people    know that    those people       are        this        css_class
    ({Role.merlin},     VISIBLE_EVIL,                 'evil as shit',       'danger'),
    ({Role.percival},   {Role.merlin, Role.morgana},  'Merlin or Morgana',  'warning'),
    (EVIL_GROUP,        EVIL_GROUP,                   'also evil as shit',  'danger'),
    (EVIL_GROUP,        DOUBLE_LANCELOTS,             'the Lancelots',      'warning'),
    (EVIL_GROUP,        SINGLE_LANCELOTS,             'the Lancelot',       'warning'),
    (DOUBLE_LANCELOTS,  DOUBLE_LANCELOTS,             'the other Lancelot', 'warning'),)

DEFAULT_FORM = {'num_players':7, Role.merlin:True, Role.percival:True,
                Role.assassin:True, Role.morgana:True, Role.mordred:True,}
EMPTY_FORM = {'num_players':-1}

# ---- helpers ----
def room():
    return rooms[session['room']]

def random_string(length):
    return ''.join(choice(ascii_letters) for _ in range(length))

def newRoomCode():
    for _ in range(50):
        tentative = choice(WORDS)
        if rooms.get(tentative) is None:
            return tentative

def get_secret():
    if 'secret.txt' not in os.listdir('.'):
        open('secret.txt', 'w').write(random_string(100))
    return open('secret.txt').read()

def shuffled(i):
    p = list(i)
    shuffle(p)
    return p

class bidirection(dict):
    def __setitem__(self, key, value):
        for k in key, self.get(key):
            if k in self:
                del self[k]
        super().__setitem__(key, value)
        super().__setitem__(value, key)

    def setdefault(self, k, d=None):
        if k not in self:
            self[k] = d

# --- database ---
names = bidirection()
rooms = {}

# --- models ---
class Room:
    def __init__(self):
        self.config = Configuration(EMPTY_FORM)
        self.assignments = bidirection()
        self.doing_config = names[session['uid']]

    def configure(self, config):
        self.config = config
        self.possibly_make_assignments()
        self.doing_config = False

    def possibly_make_assignments(self):
        if self.config and self.full and all(self.assignments[uid] is None for uid in self.uids):
            for uid, r in zip(shuffled(self.uids),self.config['roles']):
                self.assignments[uid] = r

    @property
    def players(self):
        return [names[uid] for uid in self.uids]

    @property
    def uids(self):
        return [k for k in self.assignments if type(k) is str and len(k) > 40]

    @property
    def full(self):
        return len(self.uids) == self.config['num_players']

    def get_role_css_class(self, role):
        if role in GOOD_ALIGNED:
            return 'info'
        elif role in EVIL_ALIGNED:
            return 'danger'
        else:
            return ''

    def render(self,uid):
        self.assignments.setdefault(uid)
        self.possibly_make_assignments()
        role_counts = Counter(self.config['roles'])
        roles = roles=[{
            'name': name,
            'count': count,
            'css_class': self.get_role_css_class(name),
            } for name, count in role_counts.items()]
        return render_template(
            'game.html',
            username=names.get(session['uid'], ''), # hacky
            roomcode=session['room'],
            doing_config=self.doing_config,
            players=self.players,
            roles=roles,
            status=f'{len(self.players)}/{self.config["num_players"]}',
            role_info=self.role_info(uid),
        )

    def role_info(self, your_uid):
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
                      (self.assignments.get(role,None) for role in target)
                      if uid not in (your_uid,None)]

            if people:
                # l = (f'{people[0]} is',
                #      f'{", ".join(people[:-1]) + " and " + people[-1] } are'
                #      )[len(people) > 1]
                # info['messages'].append(f'{l} {description}.')
                info['messages'].append({
                    'people': people,
                    'text': description,
                    'people_css_class': people_css_class,
                })

        if your_role is Role.merlin and Role.mordred in self.config['roles']:
            info['messages'].append({
                'people': ['Mordred'],
                'text': 'remains hidden',
                'people_css_class': 'danger',
            })
        if your_role in EVIL_GROUP-{Role.oberron} and Role.oberron in self.config['roles']:
            info['messages'].append({
                'people': ['Oberron'],
                'text': 'is out there somewhere',
                'people_css_class': 'danger',
            })

        return info

def Configuration(form):
    conf = {}

    conf['checkboxes'] = ((Role.merlin,Role.percival),
                          (Role.assassin,Role.morgana,Role.mordred,Role.oberron))

    conf['boxes'] = [r for g in conf['checkboxes'] for r in g]

    # needed by html
    conf['num_players'] = int(form['num_players'])
    conf['num_lancelots'] = int(form.get('num_lancelots', 0))

    conf['selected'] = {r:r in form for r in conf['boxes']}

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

    size['good'] = conf['num_players'] - size['evil']

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

        session['fromc'] = False

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

        self.complain([message for condition, message in (
                  (newname in names and newname!=names.get(session['uid'], None), 'Username is already taken.'),
                  (not (set(newname) < set(ascii_letters + " ")),'No special characters.'),
                  (len(newname)<2, 'Username is too short'),
                  (len(newname)>30,'Username is too long'))
                  if condition])

        names[session['uid']] = newname
        return redirect(url_for('index'))

class Create(Carafe):
    def context(self):
        if not session['fromc']:
            session['room'] = newRoomCode()

        rooms[session['room']] = Room()
        session['fromc'] = True
        return session.get('config', Configuration(DEFAULT_FORM))

    def process(self, form):
        config = Configuration(form)
        session['config'] = config

        self.complain(config['complaints'])

        room().configure(config)
        return redirect(url_for('game'))

class Join(Carafe):
    def process(self, form):
        session['room'] = ''.join(c for c in form['user_input'] if c in ascii_letters).lower()
        target = rooms.get(session['room'])

        if target is None:
            self.complain('That room does not exist')
        elif target.full and session['uid'] not in target:
            self.complain('That room is already full')

        return redirect(url_for('game'))

class Game(Carafe):
    def render(self):
        return room().render(session['uid'])

    def process(self, form):  # rematch
        if room().full:
            session['config'] = room().config
            return redirect(url_for('create'))

        return redirect(url_for('game'))

# and run the darned thing
if __name__ == '__main__':
    app.run(debug=True)

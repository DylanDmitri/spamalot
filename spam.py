from flask import Flask, request, render_template, redirect, url_for, session
from random import choice
from string import ascii_letters
from models import *

# --- database ---
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

names = bidirection()
rooms = {}

# ---- helpers ----
def newRoomCode():
    for _ in range(50):
        tentative = ''.join(choice(ascii_letters) for _ in range(4))
        if rooms.get(tentative) is None:
            return tentative

# --- framework ---

app = Flask(__name__)
app.secret_key = 'MMQUudG1Z7Xa6p4dqb0XcuYVxjT6J746npHCHgbs2zg'

class ComplaintException(Exception): pass

class Carafe:

    pages = []
    @staticmethod
    def run():
        [p() for p in Carafe.pages]
        app.run()

    def __init__(self):
        self.name = self.__class__.__name__.lower()
        self.path = (f'/{self.name}/', '/')[self.name == 'index']
        self.template = f'{self.name}.html'

        app.add_url_rule(self.path, self.name, self._render)
        app.add_url_rule(self.path, self.name+'_post', self.form, methods=['POST'])

        self.complaints = []

    def __init_subclass__(cls, **kwargs):
        Carafe.pages.append(cls)

    def _render(self):
        if 'uid' not in session:
            session['uid'] = ''.join(choice(ascii_letters) for _ in range(50))

        if (session['uid'] not in names) and (self.name != 'login'):
            return redirect(url_for('login'))

        return self.render()

    def render(self):
        return render_template(self.template, **self._context())

    def form(self):
        try:
            return self.process(request.form)
        except ComplaintException:
            return self.render()

    def complain(self, args):
        self.complaints = args[:]    # v important this comes first
        if args:
            raise ComplaintException()

    def _context(self):
        return {**(self.context() or {}),
                'complaints':self.complaints,
                'username':names.get(session['uid'], '-')}

    def context(self):
        return None

    process = NotImplemented

# --------- the pages themselves ----------
class Index(Carafe):
    def context(self):
        session['room'] = None

class Login(Carafe):
    def process(self, form):
        newname = form['user_input']

        self.complain([message for condition, message in (
                  (newname in names, 'Username is already taken.'),
                  (',' in newname, 'No commas in username'),
                  (len(newname)<3, 'Username is too short'),
                  (len(newname)>30,'Username is too long'))
                  if condition])

        names[session['uid']] = newname
        return redirect(url_for('index'))

class Create(Carafe):
    def context(self):
        code = newRoomCode()

        if session.get('room'):
            rooms[session['room']].rematch = code

        session['room'] = code
        rooms[code] = Room()

        return session.get('config', Configuration.default())

    def process(self, form):
        config = Configuration(form)
        session['config'] = config

        self.complain(config.complaints)

        rooms[session['room']].assign_roles(config)
        return redirect(url_for('game'))

class Join(Carafe):
    def process(self, form):
        session['room'] = form['user_input']
        room = rooms.get(session['room'])

        if room is None:
            self.complain(['That room does not exist'])
        if room.full and session['uid'] not in room:
            self.complain(['That room is already full'])

        return redirect(url_for('game'))

class Game(Carafe):
    @property
    def room(self):
        return rooms[session['room']]

    def render(self):
        return self.room.render(session['uid'])

    def process(self):
        if self.room.rematch:
            session['room'] = self.room.rematch
            return redirect(url_for('room'))

        session['config'] = self.room.config
        return redirect(url_for('create'))

if __name__ == '__main__':
    Carafe().run()

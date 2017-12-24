from flask import Flask, request, render_template, redirect, url_for, session
from functools import wraps
from models import *


app = Flask(__name__)
app.secret_key = b'\xd9\x97\x14\x85\xe8\xc7\xf5\xe3\x13\xc1\xfa\xc0\xc3\xa6\xa5'


def mustHaveName(f):
    @wraps(f)
    def present(*args, **kwargs):
        if ('uid' not in session) or (session['uid'] not in names):
            session['uid'] = ''.join(choice(ascii_lowercase) for _ in range(50))
            return redirect(url_for('login'))
        else:
            return f(*args, **kwargs)
    return present

def nameRoute(*route_args, **route_kwargs):

    def outer(action_function):
        @app.route(*route_args, **route_kwargs)
        @mustHaveName
        @wraps(action_function)
        def inner(*f_args, **f_kwargs):
            # if 'name' not in session:
            #     return redirect(url_for('login'))
            return action_function(*f_args, **f_kwargs)
        return inner

    return outer

# ==================== UTILS ====================
# -------------------- INDEX --------------------
@nameRoute('/')
def index():
    return render_template('index.html', username=names[session['uid']])

# -------------------- ERROR --------------------
@app.route('/error/<error>')
def error(error):
    if error.startswith('room'):
        info = f'Room "{error[5:]}" does not exist'
    else:
        info = {
            'hack': 'Stop trying to hack this website please',
            'name': 'That name is already in use.',
            'full': 'All rooms are full.',
        }.get(error, 'Unknown Error')

    return render_template('error.html', info=info)

def error_page(error):
    return redirect(url_for('error', error=error))


# -------------------- LOGIN --------------------
@app.route('/login')
def login():
    return render_template('login.html', complaint='')

@app.route('/login', methods=['POST'])
def login_choose():
    newname = request.form['username']
    if newname in nameset:
        return render_template('login.html', complaint='Username is already taken.')
    elif ',' in newname:
        return render_template('login.html',complaint='No commas in username.')

    oldname = names.get(session['uid'], None)
    if oldname and oldname in nameset:
        nameset.remove(oldname)

    nameset.add(newname)
    names[session['uid']] = newname
    return redirect(url_for('index'))


# ==================== TABLE =====================
# -------------------- CREATE --------------------

@app.route('/configure')
def make():
    if len(rooms) >= 20:
        error_page('full')

    code = newRoomCode()
    Room(code)  # binds to global 'rooms'

    return redirect(url_for('configure_room', code=code))

@nameRoute('/configure/<code>')
def configure_room(code):
    session.setdefault('config', Configuration.default())
    return render_template('configure.html', room=code, config=session['config'], complaint='')

@nameRoute('/configure/<code>', methods=['POST'])
def create_room(code):

    if code not in rooms:
        return error_page('room_'+code)

    config = Configuration.build(request.form)
    session['config'] = config

    try:
        rooms[code].configure(config)
    except InvalidConfigurationError as e:
        return render_template('configure.html',room=code,config=config,complaint=e.args[0])

    return redirect(url_for('room', code=code))

# -------------------- JOIN ----------------------
@nameRoute('/join')
def join():
    return render_template('join_room.html', reject_message='')

@nameRoute('/join', methods=['POST'])
def join_choose():

    roomcode = request.form['room_code']
    if roomcode not in rooms:
        return render_template('join_room.html', complaint="That room does not exist.")

    room = rooms[roomcode]
    if room.full and session['uid'] not in room.players:
        return render_template('join_room.html', complaint="That room is already full.")

    return redirect(url_for('room', code=roomcode))

@nameRoute('/room/<code>')
def room(code):
    if invalidRoomCode(code) or code not in rooms:
        return error_page(f'room_{code}')

    room = rooms[code]
    room.try_adding(session['uid'])

    return room.render(session['uid'])


@nameRoute('/room/<code>', methods=['POST'])
def rematch(code):
    if invalidRoomCode(code) or code not in rooms:
        return error_page(f'room_{code}')

    oldroom = rooms[code]

    # if someone else has rematched already
    if oldroom.rematch:
        return redirect(url_for('room', code=oldroom.rematch))

    newcode = newRoomCode()
    oldroom.rematch = newcode
    session['config'] = oldroom.config

    return redirect(url_for('configure_room', code=newcode))


if __name__ == '__main__':
    print('starting site...')
    app.run()

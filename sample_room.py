import spam

# = = = = = = = = =
# = = testing = = =
# = = = = = = = = =
namegen = iter(('alice', 'bob', 'carol', 'dave', 'edgar', 'francis', 'gerald', 'harry'))

class FakePerson:
    def __init__(self):
        self.uid = spam.random_string(50)
        self.name = next(namegen)

        spam.names[self.uid] = self.name

    def join(self, r):
        spam.names[self.uid] = self.name
        r.assignments.setdefault(self.uid)

# --- build sample room ----
backup = spam.session
spam.session = {'uid': 'tester'}
spam.names['tester'] = 'tester'
r = spam.Room()
r.configure(spam.Configuration(spam.DEFAULT_FORM))
spam.rooms['test'] = r
for _ in range(5):
    FakePerson().join(r)
spam.session = backup

# --- already logged in
spam.names['bRrHUmsqwkMyfBcuizpbGDasIOSDgoIWQDUWvBVVhnMJyoJDvl'] = 'Chrome'
spam.names['BVRTPwTOfXKsoGSWgpwbSNwjeMXoQklPBpghHpBdfcPIlMJYzK'] = 'Firefox'

spam.app.run(debug=True)

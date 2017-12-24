from models import Room, Configuration
from werkzeug.datastructures import ImmutableMultiDict

r = Room('abcd')

r.configure(
    Configuration.build(
    ImmutableMultiDict([
        ('num_players', '7'),
        ('Merlin', 'on'),
        ('Percival', 'on'),
        ('Oberron', 'on'),
        ('Morganna', 'on'),
        ('Mordred', 'on')])))

names = ['Alice', 'Bob', 'Carter', 'Doug', 'Ethan', 'Freya']

for name in names:
    r.try_adding(name)

# print(r.players)
#
# for name in names:
#     print(name, r.role_info(name))

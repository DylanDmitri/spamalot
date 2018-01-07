# SPAMALOT

Better role assignments in Avalon. [Currently running here.](http://dylandmitri.pythonanywhere.com/)

## current features

#### create room 
 - specify roles, number of players
 - generates a room code (eg ```abcd```)
 
#### join room
 - requires the room code
 - when everyone has joined, assigns roles and tells you everything you need to know

#### rematch button
 - to play another one easily

## future work

#### improve role listing  (easy)
- write "2 generic good" rather than "generic good, generic good"

#### quick join (medium)
- on the join page, add additional buttons on the button
- these link to recently created rooms
- and are labeled ```join room "abcd"``` or whatever

#### room garbage collection (medium)
Currently, rooms are never deleted; memory usage rises slowly until server restart. This is bad; fix it

#### role draft (hard)
- Rather than assign roles randomly, players can choose.
- Generate a secret draft order (who goes first, second, etc.)
- At each stage in draft, each player must click their phone. Normally you just click "continue...", but if it's your turn you see the remaining roles and pick one. Continue until all players have a role.



import bottle
import os
import random
import sys

directions = ['up', 'down', 'left', 'right']

DEBUG = False

def debug(msg):
    if DEBUG:
        print msg

@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')


@bottle.post('/start')
def start():
    data = bottle.request.json
    game_id = data['game_id']
    board_width = data['width']
    board_height = data['height']

    head_url = '%s://%s/static/head.png' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    # TODO: Do things with data

    return {
        'color': '#00FF00',
        'taunt': '{} ({}x{})'.format(game_id, board_width, board_height),
        'head_url': head_url,
        'name': 'battlesnake-python'
    }

@bottle.post('/move')
def move():
    data = bottle.request.json
    
    snakes = data['snakes']
    me = next(x for x in snakes if x['id'] == data['you'])
    
    candidates = safe_moves(data)

    debug("Valid moves are "+str(candidates))

    if len(candidates) is 0:
        print "No valid moves, suiciding"
        return {
            'move': inv_dir(direction(me)),
            'taunt': 'oops.'
        }

    move = random.choice(candidates)

    print "Was going "+str(direction(me))+", moving "+str(move)

    return {
        'move': move,
        'taunt': 'I have no idea where I\'m going!'
    }

# Find moves which are safe (i.e. do not kill us immediately)
def safe_moves(data):
    width = data['width']
    height = data['height']
    snakes = data['snakes']
    me = next(x for x in snakes if x['id'] == data['you'])
    others = [x for x in snakes if not x['id'] == data['you']]
    head = me['coords'][0]
    
    moves = ['up', 'down', 'left', 'right']

    debug("Checking up for collisions")

    n_head = list(head)
    n_head[1] -= 1
    if n_head[1] < 0:
        debug("up collides with wall")
        moves.remove('up')
    elif safe_moves_collide(n_head, me, others):
        moves.remove('up')

    n_head = list(head)
    n_head[1] += 1
    if n_head[1] >= height:
        debug("down collides with wall")
        moves.remove('down')
    elif safe_moves_collide(n_head, me, others):
        moves.remove('down')

    n_head = list(head)
    n_head[0] -= 1
    if n_head[0] < 0:
        debug("left collides with wall")
        moves.remove('left')
    elif safe_moves_collide(n_head, me, others):
        moves.remove('left')

    n_head = list(head)
    n_head[0] += 1
    if n_head[0] >= width:
        debug("right collides with wall")
        moves.remove('right')
    elif safe_moves_collide(n_head, me, others):
        moves.remove('right')

    return moves
    
def safe_moves_collide(n_head, me, others):
    body = me['coords'][1:]
    if n_head in body:
            debug("move collides with our body")
            return True
    for snake in others:
        if n_head in snake['coords'][0:-1]:
            debug("move collides with other snake body")
            return True
    return False


# Determine the direction a snake is travelling
def direction(snake):
    coords = snake['coords']
    head = coords[0]
    body = coords[1]
    debug("Head coords "+str(head))
    debug("Body coords "+str(body))

    if head[0] > body[0]:
        return 'right'
    if head[0] < body[0]:
        return 'left'
    if head[1] > body[1]:
        return 'down'
    if head[1] < body[1]:
        return 'up'

# Inverse a direction
def inv_dir(direction):
    if direction is 'up':
        return 'down'
    if direction is 'down':
        return 'up'
    if direction is 'left':
        return 'right'
    if direction is 'right':
        return 'left'

# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()
if __name__ == '__main__':
    if 'debug' in sys.argv[1:]:
        print "Enabled debugging messages"
        DEBUG = True
    bottle.run(application, host=os.getenv('IP', '0.0.0.0'), port=os.getenv('PORT', '8080'))

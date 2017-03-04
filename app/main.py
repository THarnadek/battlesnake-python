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

    food = food_list(data)
    if not len(food) is 0: 
        food_target = food[0]
        for f in food:
            if f[1] > food_target[1]:
                food_target = f
        food_moves = move_toward(me['coords'][0], food_target[0])
        moves = [ x for x in food_moves if x in candidates ]
    
    if moves is None or len(moves) is 0:
        move = random.choice(candidates)
    else:
        move = random.choice(moves)

    print "Was going "+str(direction(me))+", moving "+str(move)

    return {
        'move': move,
        'taunt': 'I have no idea where I\'m going!'
    }

# Prioritize food by distance and other snakes
# Returns weighted list of food (more positive weights are better, 
# more negative weights are more dangerous/worse)
def food_list(data):
    me = next(x for x in data['snakes'] if x['id'] == data['you'])
    others = [x for x in data['snakes'] if not x['id'] == data['you']]
    food = [ [x,0] for x in data['food'] ]
    for x in food:
        our_dist = dist(x[0], me['coords'][0])
        x[1] = data['width'] - our_dist
        for snake in others:
            their_dist = dist(x[0], snake['coords'][0])
            if our_dist < their_dist:
                # Add weight
                if len(snake['coords']) > len(me['coords']) - 1:
                    x[1] += 5 # They are longer
                else:
                    x[1] += 10 # We are longer
            else:
                # Subtract weight
                if len(snake['coords']) > len(me['coords']) - 1:
                    x[1] -= 10 # They are longer
                else:
                    x[1] -= 2 # We are longer
    return food
    
# Returns a list of possible (maybe unsafe) moves which will advance point A to B
def move_toward(A, B):
    x = A[0] - B[0]
    y = A[1] - B[1]
    moves = []
    if x < 0:
        moves.append('right')
    if x > 0:
        moves.append('left')
    if y < 0:
        moves.append('down')
    if y > 0:
        moves.append('up')
    return moves

# Returns the number of moves between two points
def dist(point1, point2):
    x = point1[0] - point2[0]
    y = point1[1] - point2[1]
    if x < 0:
        x *= -1
    if y < 0:
        y *= -1
    return x+y


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

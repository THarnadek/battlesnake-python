import bottle
import os
import random
import sys
import ConfigParser
import copy

directions = ['up', 'down', 'left', 'right']
#placeholder constants
taunts = ['I\m mute', 'I have nothing to say']
CONST_FOOD_CLOSER_SHORTER = 5
CONST_FOOD_CLOSER_LONGER = 10
CONST_FOOD_FURTHER_SHORTER = 10
CONST_FOOD_FURTHER_LONGER = 2
CONST_FOOD_DIST_MODIFIER = 0
CONST_HUNGER_WEIGHT_MODIFIER = 10

# use this to taunt people randomly
#random.choice(taunts)

DEBUG = True

#Loads strings from taunts.txt
def loadTaunts():
	if not os.path.exists('app/taunts.txt'):
		debug("No taunts file, you should include that")
	else:
		global taunts
		taunts = [line.strip() for line in open('app/taunts.txt', 'r')]
		debug('Read the following taunts: ')
		debug(taunts)

#Loads configs from snake.ini file
def loadConfig():
    if not os.path.exists('app/snake.ini'):
        debug("No config file, you should include that")
        #if there's no config file, defaults just get used
    else:
        config = ConfigParser.ConfigParser()
        config.read('app/snake.ini')
        global CONST_FOOD_CLOSER_SHORTER
        global CONST_FOOD_CLOSER_LONGER
        global CONST_FOOD_FURTHER_SHORTER
        global CONST_FOOD_FURTHER_LONGER
        global CONST_FOOD_DIST_MODIFIER
        global CONST_HUNGER_WEIGHT_MODIFIER

        CONST_FOOD_CLOSER_SHORTER = config.getint('FOODWEIGHT', 'CloserAndShorter')
        CONST_FOOD_CLOSER_LONGER = config.getint('FOODWEIGHT', 'CloserAndLonger')
        CONST_FOOD_FURTHER_SHORTER = config.getint('FOODWEIGHT', 'FurtherAndShorter')
        CONST_FOOD_FURTHER_LONGER = config.getint('FOODWEIGHT', 'FurtherAndLonger')
        CONST_FOOD_DIST_MODIFIER = config.getint('FOODWEIGHT', 'DistanceModifier')
        CONST_HUNGER_WEIGHT_MODIFIER = config.getint('FOODWEIGHT','HungerWeightModifier')

        debug('Read the following configs: ')
        debug('CONST_FOOD_CLOSER_SHORTER:  {}'.format(CONST_FOOD_CLOSER_SHORTER))
        debug('CONST_FOOD_CLOSER_LONGER:   {}'.format(CONST_FOOD_CLOSER_LONGER))
        debug('CONST_FOOD_FURTHER_SHORTER: {}'.format(CONST_FOOD_FURTHER_SHORTER))
        debug('CONST_FOOD_FURTHER_LONGER:  {}'.format(CONST_FOOD_FURTHER_LONGER))
        debug('CONST_FOOD_DIST_MODIFIER:   {}'.format(CONST_FOOD_DIST_MODIFIER))
        debug('CONST_FOOD_FURTHER_LONGER:  {}'.format(CONST_HUNGER_WEIGHT_MODIFIER))

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

#    head_url = '%s://%s/static/head.png' % (
#        bottle.request.urlparts.scheme,
#        bottle.request.urlparts.netloc
#    )
    head_url = 'http://cultofthepartyparrot.com/parrots/hd/parrot.gif'

    loadConfig()
    loadTaunts()

    return {
        'color': '#00FF00',
        'taunt': '{} ({}x{})'.format(game_id, board_width, board_height),
        'head_url': head_url,
        'name': 'PartyParrot-Snek'
    }

@bottle.post('/move')
def move():
    data = bottle.request.json

    snakes = data['snakes']
    me = next(x for x in snakes if x['id'] == data['you'])

    candidates = safe_moves(data)

    debug("Valid moves are "+str(candidates))

    if len(candidates) is 0:
        debug("No valid moves, suiciding")
        return {
            'move': inv_dir(direction(me)),
            'taunt': 'oops.'
        }
    else:
        moves = candidates

    debug("Found potentially good moves (need to test for traps): "+str(moves))
    # Test the moves for traps
    moves_tested = list(candidates)
    for m in moves:
        debug("Testing "+str(m))
        new_snake = apply_move(me, m)
        new_moves = safe_moves(data, new_snake)
        debug("Going to fill test: "+str(new_moves))
        new_moves_tested = list(new_moves)
        for n in new_moves:
            temp = space_size(data, apply_move(new_snake, n)['coords'][0])
            if space_size(data, apply_move(new_snake, n)['coords'][0]) <= len(me['coords']):
                debug("Fill test failed for potential next move "+n)
                new_moves_tested.remove(n)
        if len(new_moves_tested) is 0:
            debug("Rejecting move "+str(m)+", next gen space fill fails")
            moves_tested.remove(m)


    move = hunger_move(data, moves_tested)

    if move is None:
        debug("Found no good move, using all candidates")
        move = random.choice(candidates)

    debug("Was going "+str(direction(me))+", moving "+str(move))

    return {
        'move': move,
        'taunt': 'I have no idea where I\'m going!'
    }

# Return our best move for eating
def hunger_move(data, moves_tested):
    me = next(x for x in data['snakes'] if x['id'] == data['you'])
    food = food_list(data)
    if not len(food) is 0:
        food_target = food[0]
        for f in food:
            if f[1] > food_target[1]:
                food_target = f
        possible_food_moves = move_toward(me['coords'][0], food_target[0])
        safe_food_moves = [ x for x in possible_food_moves if x in moves_tested ]

    if safe_food_moves is None or len(safe_food_moves) is 0:
        moves = moves_tested
    else:
        moves = safe_food_moves
    return random.choice(moves)

def hunger_weight(data):
    me = next(x for x in snakes if x['id'] == data['you'])
    return (100 - me['health'])/CONST_HUNGER_WEIGHT_MODIFIER

# Prioritize food by distance and other snakes
# Returns weighted list of food (more positive weights are better,
# more negative weights are more dangerous/worse)
def food_list(data):
    me = next(x for x in data['snakes'] if x['id'] == data['you'])
    others = [x for x in data['snakes'] if not x['id'] == data['you']]
    food = [ [x,0] for x in data['food'] ]
    for x in food:
        our_dist = dist(x[0], me['coords'][0])
        x[1] = data['width'] - our_dist + CONST_FOOD_DIST_MODIFIER
        for snake in others:
            their_dist = dist(x[0], snake['coords'][0])
            if our_dist < their_dist:
                # Add weight
                if len(snake['coords']) > len(me['coords']) - 1:
                    x[1] += CONST_FOOD_CLOSER_SHORTER # They are longer
                else:
                    x[1] += CONST_FOOD_CLOSER_LONGER # We are longer
            else:
                # Subtract weight
                if len(snake['coords']) > len(me['coords']) - 1:
                    x[1] -= CONST_FOOD_FURTHER_SHORTER # They are longer
                else:
                    x[1] -= CONST_FOOD_CLOSER_LONGER # We are longer
    return food

# Returns the snake with a move applied
def apply_move(snake, move):
    new_head = list(snake['coords'][0])
    if move is 'up':
        new_head[1] -= 1
    elif move is 'down':
        new_head[1] += 1
    elif move is 'left':
        new_head[0] -= 1
    elif move is 'right':
        new_head[0] += 1
    result = copy.deepcopy(snake)
    result['coords'] = [new_head]
    for x in snake['coords'][:-1]:
        result['coords'].append(x)
    return result

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

# Use flood filling to determine the size of a region
def space_size(data, space):
    edges = []
    for x in range(-1,data['width']):
        edges.append([x,-2])
        edges.append([x,data['height']])
    for x in range(0,data['height']-1):
        edges.append([-1,x])
        edges.append([data['width'],x])
    for x in data['snakes']:
        for y in x['coords']:
            edges.append(y)

    me = next(x for x in data['snakes'] if x['id'] == data['you'])
    our_len = len(me['coords']) + 2
    count = 0
    explore = [space]
    edges.append(space)
    count += 1
    while not len(explore) is 0 and len(explore) < our_len:
        new_explore = []
        for x in explore:
            if not [x[0]+1, x[1]] in edges:
                new_explore.append([x[0]+1, x[1]])
                edges.append([x[0]+1, x[1]])
                count += 1
            if not [x[0]-1, x[1]] in edges:
                new_explore.append([x[0]-1, x[1]])
                edges.append([x[0]-1, x[1]])
                count += 1
            if not [x[0], x[1]+1] in edges:
                new_explore.append([x[0], x[1]+1])
                edges.append([x[0], x[1]+1])
                count += 1
            if not [x[0], x[1]-1] in edges:
                new_explore.append([x[0], x[1]-1])
                edges.append([x[0], x[1]-1])
                count += 1
        explore = new_explore
    debug("Found "+str(count)+" tiles free after flood fill")
    return count



# Find moves which are safe (i.e. do not kill us immediately)
def safe_moves(data, new_snake=None):
    width = data['width']
    height = data['height']
    snakes = data['snakes']
    me = next(x for x in snakes if x['id'] == data['you'])
    if not new_snake is None:
        debug("Using new_snake for collision check")
        me = new_snake
    others = [x for x in snakes if not x['id'] == data['you']]
    head = me['coords'][0]

    moves = ['up', 'down', 'left', 'right']

    n_head = list(head)
    n_head[1] -= 1
    if n_head[1] < 0:
        debug("up collides with wall")
        moves.remove('up')
    elif safe_moves_collide(n_head, me, others):
        debug("up collides with snake")
        moves.remove('up')

    n_head = list(head)
    n_head[1] += 1
    if n_head[1] >= height:
        debug("down collides with wall")
        moves.remove('down')
    elif safe_moves_collide(n_head, me, others):
        debug("down collides with snake")
        moves.remove('down')

    n_head = list(head)
    n_head[0] -= 1
    if n_head[0] < 0:
        debug("left collides with wall")
        moves.remove('left')
    elif safe_moves_collide(n_head, me, others):
        debug("left collides with snake")
        moves.remove('left')

    n_head = list(head)
    n_head[0] += 1
    if n_head[0] >= width:
        debug("right collides with wall")
        moves.remove('right')
    elif safe_moves_collide(n_head, me, others):
        debug("right collides with snake")
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

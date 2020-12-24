'''
ALl this bot does is steal pickups and cling to the opponent.
It is not a very good bot.

'''

import time
import random
import timeit

class agent:

    def __init__(self):
        pass

    # player_state contains: id, ammo, hp, location, reward, power
    # game_state contains: tick_number, size, bombs, ammo, all_blocks, soft_blocks, ore_blocks, indestructible_blocks
    # opponents(id)
    # entity_at(location)
    def next_move(self, game_state, player_state):
        start = timeit.default_timer ()

        """
		This method is called each time the agent is required to choose an action
		"""
        ########################
        ###    VARIABLES     ###
        ########################

        # list of all possible actions to take
        actions = ['', 'u', 'd', 'l', 'r', 'p']

        # store some information about the environment
        # game map is represented in the form (x,y)
        self.cols = game_state.size[0]
        self.rows = game_state.size[1]

        self.game_state = game_state  # for us to refer to later

        self.location = player_state.location
        self.id = player_state.id

        ammo = player_state.ammo

        bombs = game_state.bombs

        ########################
        ###      AGENT       ###
        ########################

        # chase down opponents in spare time
        for player_location in game_state.opponents(-1):
            if player_location != self.location:
                opponent_location = player_location

        next_djikstra_location = self.djikstra_to_location(opponent_location, game_state)
        action = self.move_to_tile(self.location, next_djikstra_location)

        stop = timeit.default_timer()
        # print('runtime: ', stop - start)

        return action

        ########################
        ###     HELPERS      ###
        ########################

    # given current location and direction, calculate path there in l/r/u/d config
    # target_location is now just some default
    def djikstra_to_location(self, target_location, game_state):
        # calculate values
        djikstra_tiles = self.djikstra_costing(target_location, game_state)
        #print("mylocation value")
        #print(self.get_location_cost(unvisited_tiles, self.location[0], self.location[1]))

        # TODO: survival check is highest priority

        # TODO: ore is higher priority

        # valuable locations - treasure, bombs
        pickup_locations = self.find_pickups(game_state)
        pickup_tiles = []
        for pickup_location in pickup_locations:
            pickup_tiles.append(self.get_tile(djikstra_tiles, pickup_location[0], pickup_location[1]))

        # get the nearest pickup
        if len(pickup_tiles) > 0:
            nearest_pickup = pickup_tiles[0]
            for pickup_tile in pickup_tiles:
                if (nearest_pickup[2] > pickup_tile[2]):
                    nearest_pickup = pickup_tile
            target_tile = nearest_pickup
        else:
            # evaluate the next location to go to, use target_location for now
            # probably just chase the user lol
            target_tile = self.get_tile (djikstra_tiles, target_location[0], target_location[1])

        #game_state.entity_at(location)
        #print('testing stuff')
        #print(game_state.bombs)

        # TODO: boxes if running out of time?

        # find the path to the target location
        action_tile = target_tile
        next_tile = target_tile
        # stop just before hitting self
        while((next_tile[0], next_tile[1])!= (self.location[0], self.location[1])):
            action_tile = next_tile
            surrounding_tile_locations = self.get_surrounding_tiles((action_tile[0], action_tile[1]))
            for tile_location in surrounding_tile_locations:
                surround_tile = self.get_tile(djikstra_tiles, tile_location[0], tile_location[1])
                if surround_tile[2] < next_tile[2]:
                    next_tile = surround_tile

            print('action_tile:')
            print(action_tile)

        # find the next step to the ideal location
        return (action_tile[0], action_tile[1])
        #return self.location

    def find_pickups(self, game_state):
        valuable_list = []
        for xIndex in range(self.cols):
            for yIndex in range(self.rows):
                if (game_state.entity_at((xIndex, yIndex)) == 't'):
                    #treasure
                    valuable_list.append((xIndex, yIndex))
                elif (game_state.entity_at((xIndex, yIndex)) == 'a'):
                    #ammo
                    valuable_list.append((xIndex, yIndex))
        return valuable_list


    def djikstra_costing(self, target_location, game_state):

        max_cost = (self.cols + 1) * (self.rows + 1) * (109) + 1  # 109 = ore cost = 3 explosions and 4 jumps

        # initialise tiles
        unvisited_tiles = []
        minPQ = []
        visited_tiles = []
        for xIndex in range(self.cols):
            for yIndex in range(self.rows):
                unvisited_tiles.append((xIndex, yIndex, max_cost))

        # start node, current location
        start_tile = self.get_tile(unvisited_tiles, self.location[0], self.location[1])
        print('current location')
        print(self.location)
        minPQ.append((start_tile[0], start_tile[1], 0));

        # loop for while minPQ not empty
        while (len(minPQ) != 0):
        #for test in range(3):
            self.process_minPQ(unvisited_tiles, minPQ, visited_tiles, game_state, max_cost)
        # visited_tiles at this point contains all the costs.

        return visited_tiles

    def process_minPQ(self, unvisited_tiles, minPQ, visited_tiles, game_state, max_cost):
        # Take the smallest minPQ item
        minPQ_smallest = minPQ[0]
        for temp_tile in minPQ:
            if (temp_tile[2] < minPQ_smallest[2]):
                minPQ_smallest = temp_tile

        # Add adjacent nodes to minPQ, remove from unvisited
        valid_next_locations = self.get_surrounding_tiles((minPQ_smallest[0], minPQ_smallest[1]))
        for next_location in valid_next_locations:
            # Ignore nodes already visited
            next_tile = self.get_tile(unvisited_tiles, next_location[0], next_location[1])
            if (next_tile != 'tile not found'):
                # Calculate the cost of the next adjacent node
                # Cost: Ore = 109, Wood = 36, Indestructible ~= ?
                if(self.get_tile(game_state.all_blocks, next_location[0], next_location[1]) == 'tile not found'):
                    new_tile = (next_location[0], next_location[1], minPQ_smallest[2] + 1)
                else:
                    new_tile = (next_location[0], next_location[1], minPQ_smallest[2] + max_cost)

                # Only add the tile to minpq if it adds a shorter path.
                pq_tile = self.get_tile(minPQ, next_tile[0], next_tile[1])
                if pq_tile == 'tile not found':
                    minPQ.append(new_tile)
                elif new_tile[2] < pq_tile[2]:
                    minPQ.remove(pq_tile)
                    minPQ.append(new_tile)
        #print('minpq:')
        #print(minPQ)

        # Move smallest item to visited
        visited_tiles.append(minPQ_smallest)
        unvisited_tiles.remove(self.get_tile(unvisited_tiles, minPQ_smallest[0], minPQ_smallest[1]))
        minPQ.remove(minPQ_smallest)

    def get_tile(self, tileset, x, y):
        for tile in tileset:
            if (tile[0] == x) & (tile[1] == y):
                return tile
        return ('tile not found')

    # given a tile location as an (x,y) tuple, this function
    # will return the surrounding tiles up, down, left and to the right as a list
    # (i.e. [(x1,y1), (x2,y2),...])
    # as long as they do not cross the edge of the map
    def get_surrounding_tiles(self, location):

        # find all the surrounding tiles relative to us
        # location[0] = col index; location[1] = row index
        tile_up = (location[0], location[1] + 1)
        tile_down = (location[0], location[1] - 1)
        tile_left = (location[0] - 1, location[1])
        tile_right = (location[0] + 1, location[1])

        # combine these into a list
        all_surrounding_tiles = [tile_up, tile_down, tile_left, tile_right]

        # we'll need to remove tiles that cross the border of the map
        # start with an empty list to store our valid surrounding tiles
        valid_surrounding_tiles = []

        # loop through our tiles
        for tile in all_surrounding_tiles:
            # check if the tile is within the boundaries of the game
            if self.game_state.is_in_bounds(tile):
                # if yes, then add them to our list
                valid_surrounding_tiles.append(tile)

        return valid_surrounding_tiles

    # given a list of tiles
    # return the ones which are actually empty
    def get_empty_tiles(self, tiles):

        # empty list to store our empty tiles
        empty_tiles = []

        for tile in tiles:
            if not self.game_state.is_occupied(tile):
                # the tile isn't occupied, so we'll add it to the list
                empty_tiles.append(tile)

        return empty_tiles

    # given an adjacent tile location, move us there
    def move_to_tile(self, location, tile):

        actions = ['', 'u', 'd', 'l', 'r', 'p']

        # see where the tile is relative to our current location
        diff = tuple(x - y for x, y in zip(self.location, tile))

        # return the action that moves in the direction of the tile
        if diff == (0, 1):
            action = 'd'
        elif diff == (1, 0):
            action = 'l'
        elif diff == (0, -1):
            action = 'u'
        elif diff == (-1, 0):
            action = 'r'
        else:
            action = ''  # do nothing?
        # I think p is place bomb

        return action

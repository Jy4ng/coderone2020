'''
This is not a very good bot.

They chase pickups, and then just drops them everywhere!

I think they want a hug.
'''

import time
import random
import timeit


class agent:
    def __init__(self):
        self.bombs_tracked = []
        self.ore_tracked = []
        self.prev_ticks = 0
        self.suspended_treasure = []
        self.current_target = (-1, -1)
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

        self.update_bombs_tracked (game_state)

        self.update_treasure_tracked (game_state)

        ########################
        ###      AGENT       ###
        ########################

        # chase down opponents in spare time
        opponent_location = self.get_opponent_location (game_state)

        next_djikstra_location = self.djikstra_to_location (game_state)

        action = self.move_to_tile (self.location, next_djikstra_location)
        # Override action in the case of block, as bomb is not included above
        next_block = game_state.entity_at(next_djikstra_location)
        # Note bomb masks player
        if (next_block == 'ob') or (next_block == 'sb'):
            if(player_state.ammo > 0):
                if((self.current_target[0], self.current_target[1]) != (opponent_location[0], opponent_location[1])):
                    # Only bomb blocks to get to treasures
                    action = 'b'
                    # if single block bombed, leave it alone - add suspended treasures list,
                    self.suspended_treasure.append((self.current_target[0], self.current_target[1], 35))
                # else:
                    # Enemy is running from you. Leave it.
        elif next_block == 'ib':
            print('WARN unexpected metal at: ')
            print(next_djikstra_location)
        elif (next_block == 1) or (next_block == 0) or (next_block == 'b'):
            if (next_block == 'b') and ((next_djikstra_location[0], next_djikstra_location[1]) != (opponent_location)):
                # Bomb
                print('Placeholder? Lone bomb detected')
            else:
                # Enemy
                print('Enemy detected')
                # TODO: Murder = adhoc decision during pursuit, process after djikstra selection
                if self.is_opponent_surrounded (game_state):
                    action = 'b'
        elif (next_block != None) and (next_block != 'a') and (next_block != 't'):
            print('WARN unexpected block: ')
            print(next_block)

        stop = timeit.default_timer ()
        print ('runtime: ', stop - start)

        return action

        ########################
        ###     HELPERS      ###
        ########################

    # given current location and direction, calculate path there in l/r/u/d config
    # target_location is now just some default
    def djikstra_to_location(self, game_state):
        # Initial calculate djikstra values
        djikstra_tiles = self.djikstra_costing (game_state, [], [])

        # second round djikstra
        # determine new obstacles by comparing predictive blast radius
        new_obstacles = []
        # TODO - Stretch : track disappearing blocks as well as appearing blast obstacles, should tie into suspended blocks by loading into costing
        new_removal = []
        # i.e. Loop over djikstra to factor future blasts and (possibly) bomb tick-down
        # Assess from closest issues up to furthest
        recalculate = False #Track whether new changes introduced, warranting recalculation
        for future_step in range(35):

            # Extract blasts with timing value matching the future_step
            relevant_blasts = []
            for this_blast in self.get_blast_locations(game_state):
                if this_blast[2] == future_step:
                    relevant_blasts.append(this_blast)
            # Match to djikstra costings/tiles with the same future_vale
            for djikstra_tile in djikstra_tiles:
                for relevant_blast in relevant_blasts:
                    # Blast/tile location match
                    if ((djikstra_tile[0], djikstra_tile[1]) == (relevant_blast[0], relevant_blast[1])):
                        # Timing close enough match
                        if abs(djikstra_tile[2]-relevant_blast[2]) < 3:
                            new_obstacles.append((djikstra_tile[0], djikstra_tile[1]))
                            recalculate = True
            if recalculate:
                #print ('new_obstacles')
                #print (new_obstacles)
                djikstra_tiles = self.djikstra_costing(game_state, new_obstacles, new_removal)
                recalculate = False

        # print("mylocation value")
        # print(self.get_location_cost(unvisited_tiles, self.location[0], self.location[1]))


        # PRIORITY LOWEST - GET TREASURE AND ZONE ENEMY
        # target_tile is our goal
        # valuable locations - treasure, bombs
        pickup_locations = self.find_pickups (game_state)
        pickup_tiles = []
        for pickup_location in pickup_locations:
            # do not consider suspended pieces
            if self.get_tile(self.suspended_treasure, pickup_location[0], pickup_location[1]) == 'tile not found':
                pickup_tiles.append (self.get_tile (djikstra_tiles, pickup_location[0], pickup_location[1]))
        opponent_location = self.get_opponent_location (game_state)
        # get the nearest pickup
        if len (pickup_tiles) > 0:
            nearest_pickup = pickup_tiles[0]
            for pickup_tile in pickup_tiles:
                if (nearest_pickup[2] > pickup_tile[2]):
                    nearest_pickup = pickup_tile
            target_tile = nearest_pickup
        else:
            # evaluate the next location to go to, use target_location for now
            # probably just chase the user lol
            target_tile = self.get_tile (djikstra_tiles, opponent_location[0], opponent_location[1])

        # TODO: Hunt boxes if running out of time/opportunity/excess of bombs?

        # TODO: Ore is higher priority than boxes

        # PRIORITY HIGHEST - DON'T DIE
        # Check if on bomb or blast threat (relevant_blast)
        run = False
        if self.get_tile(game_state.bombs, self.location[0], self.location[1]) != 'tile not found':
            run = True
        elif self.get_tile(new_obstacles, self.location[0], self.location[1]) != 'tile not found':
            run = True
        if run:
            # don't initialise with own location
            nearest_safe = djikstra_tiles[0]
            if nearest_safe[2] == 0:
                nearest_safe = djikstra_tiles[1]
            # Scan djikstra for the nearest valid area (barring ourselves?)
            for djikstra_tile in djikstra_tiles:
                if (nearest_safe[2] > djikstra_tile[2]) and (djikstra_tile[2] != 0):
                    nearest_safe = djikstra_tile
            target_tile = nearest_safe

        # find the path to the target location
        action_tile = target_tile
        next_tile = target_tile
        # stop just before hitting self
        while ((next_tile[0], next_tile[1]) != (self.location[0], self.location[1])):
            action_tile = next_tile
            surrounding_tile_locations = self.get_surrounding_tiles ((action_tile[0], action_tile[1]))
            for tile_location in surrounding_tile_locations:
                surround_tile = self.get_tile (djikstra_tiles, tile_location[0], tile_location[1])
                # Get the smallest surrounding tile.
                if surround_tile[2] < next_tile[2]:
                    next_tile = surround_tile
            # If the smallest surrounding tile is the same tile, then you're stuck. Don't move.
            if (next_tile[0], next_tile[1]) == (action_tile[0], action_tile[1]):
                (next_tile[0], next_tile[1]) = (self.location[0], self.location[1])
                (action_tile[0], action_tile[1]) = (self.location[0], self.location[1])

        self.current_target = target_tile
        # find the next step to the ideal location
        return (action_tile[0], action_tile[1])
        # return self.location

    # Returns true if YOU have surrounded the enemy
    def is_opponent_surrounded(self, game_state):
        opponent_location = self.get_opponent_location(game_state)
        # Check that the enemy is adjacent
        # Same x axis (left or right)
        enemy_adjacent = False
        if self.location[0] == opponent_location[0]:
            if (self.location[1] - opponent_location[1]) == -1:
                # Opponent on right
                enemy_adjacent = True
            elif (self.location[1] - opponent_location[1]) == 1:
                # Opponent on left
                enemy_adjacent = True
        # Same y axis (above or below)
        elif self.location[1] == opponent_location[1]:
            if (self.location[0] - opponent_location[0]) == -1:
                # Opponent above
                enemy_adjacent = True
            elif (self.location[0] - opponent_location[0]) == 1:
                # Opponent below
                enemy_adjacent = True

        if enemy_adjacent and self.is_blocked_around(game_state, opponent_location[0], opponent_location[1]):
            return True
        else:
            return False

    def is_blocked_around(self, game_state, x, y):
        if (self.is_blocked(game_state, x-1, y)) and (self.is_blocked(game_state, x+1, y)) and (self.is_blocked(game_state, x, y-1)) and (self.is_blocked(game_state, x, y+1)):
            return True
        else:
            return False

    def is_blocked(self, game_state, x, y):
        if (game_state.entity_at((x,y)) == 'ib') or (game_state.entity_at((x,y)) == 'sb') or (game_state.entity_at((x,y)) == 'ob') or (game_state.entity_at((x,y)) == 'b'):
            return True
        elif (game_state.entity_at((x,y)) == 1) or (game_state.entity_at((x,y)) == 0):
            return True
        elif game_state.is_in_bounds((x,y)) == False:
            return True
        else:
            return False

    # Wrote this cause the opponents() function call was dodge
    def get_opponent_location(self, game_state):
        for player_location in game_state.opponents (-1):
            if player_location != self.location:
                opponent_location = player_location
        return opponent_location

    # Return a list of the pickups
    def find_pickups(self, game_state):
        valuable_list = []
        for xIndex in range (self.cols):
            for yIndex in range (self.rows):
                if (game_state.entity_at ((xIndex, yIndex)) == 't'):
                    # treasure
                    valuable_list.append ((xIndex, yIndex))
                elif (game_state.entity_at ((xIndex, yIndex)) == 'a'):
                    # ammo
                    valuable_list.append ((xIndex, yIndex))
        return valuable_list

    # Make the djikstra cost map and return it
    # new_obstacles override with new nodes to avoid
    # new_removal override with free spaces
    # Note: new_obstacles should have priority over new_removal
    def djikstra_costing(self, game_state, new_obstacles, new_removal):

        max_cost = (self.cols + 1) * (self.rows + 1) * (109) + 1  # 109 = ore cost = 3 explosions and 4 jumps

        # initialise tiles
        unvisited_tiles = []
        minPQ = []
        visited_tiles = []
        for xIndex in range (self.cols):
            for yIndex in range (self.rows):
                unvisited_tiles.append ((xIndex, yIndex, max_cost))

        # start node, current location
        start_tile = self.get_tile (unvisited_tiles, self.location[0], self.location[1])
        minPQ.append ((start_tile[0], start_tile[1], 0));

        # loop for while minPQ not empty
        while (len (minPQ) != 0):
            # for test in range(3):
            self.process_minPQ (unvisited_tiles, minPQ, visited_tiles, game_state, max_cost, new_obstacles, new_removal)
        # visited_tiles at this point contains all the costs.

        return visited_tiles

    # Helper function for the djikstra calcs, this is really the bulk of it
    def process_minPQ(self, unvisited_tiles, minPQ, visited_tiles, game_state, max_cost, new_obstacles, new_removal):
        # Take the smallest minPQ item
        minPQ_smallest = minPQ[0]
        for temp_tile in minPQ:
            if (temp_tile[2] < minPQ_smallest[2]):
                minPQ_smallest = temp_tile

        # Add adjacent nodes to minPQ, remove from unvisited
        valid_next_locations = self.get_surrounding_tiles ((minPQ_smallest[0], minPQ_smallest[1]))
        for next_location in valid_next_locations:
            # Ignore nodes already visited
            next_tile = self.get_tile (unvisited_tiles, next_location[0], next_location[1])
            if (next_tile != 'tile not found'):
                # Calculate the cost of the next adjacent node
                # Cost: Ore = 109, Wood = 36, Indestructible ~= ?
                if self.get_tile (new_obstacles, next_location[0], next_location[1]) != 'tile not found':
                    # Overriding obstacle
                    new_tile = (next_location[0], next_location[1], max_cost)
                elif self.get_opponent_location (game_state) == (next_location[0], next_location[1]):
                    # Opponent
                    new_tile = (next_location[0], next_location[1], max_cost)
                elif self.get_tile (game_state.bombs, next_location[0], next_location[1]) != 'tile not found':
                    # Bomb
                    new_tile = (next_location[0], next_location[1], max_cost)
                elif (self.get_tile (game_state.all_blocks, next_location[0], next_location[1]) != 'tile not found'):
                    # Is a block
                    block_type = game_state.entity_at ((next_location[0], next_location[1]))
                    if block_type == 'ib':
                        # Metal/Indestructible block
                        new_tile = (next_location[0], next_location[1], max_cost)
                    elif block_type == 'sb':
                        # Soft block - bombing costs 35 ticks + 1 placement + 2 running steps towards
                        new_tile = (next_location[0], next_location[1], minPQ_smallest[2] + 38)
                    elif block_type == 'ob':
                        # Ore blocks - several bombs may be needed for given ore
                        bombs_needed = self.get_tile (self.ore_tracked, next_location[0], next_location[1])[2]
                        # Just in case my tracking is off
                        if bombs_needed != 'tile not found':
                            new_tile = (next_location[0], next_location[1], 38 * bombs_needed)
                        else:
                            print ('djikstra ore tracking mismatch')
                            print (self.ore_tracked)
                            new_tile = (next_location[0], next_location[1], minPQ_smallest[2] + max_cost)
                else:
                    # Not any of the above, must be free
                    new_tile = (next_location[0], next_location[1], minPQ_smallest[2] + 1)

                # Only add the tile to minpq if it adds a shorter path.
                pq_tile = self.get_tile (minPQ, next_tile[0], next_tile[1])
                if pq_tile == 'tile not found':
                    minPQ.append (new_tile)
                elif new_tile[2] < pq_tile[2]:
                    minPQ.remove (pq_tile)
                    minPQ.append (new_tile)

        # Done processing smallest minPQ itme - move it to visited
        visited_tiles.append (minPQ_smallest)
        unvisited_tiles.remove (self.get_tile (unvisited_tiles, minPQ_smallest[0], minPQ_smallest[1]))
        minPQ.remove (minPQ_smallest)

    # This function defines the locations on the board which will be subject to future blast
    # Calculated based on projected detonations and block positioning
    # Locations can occur more than once(i.e. be subject to multiple bombs)
    def get_blast_locations(self, game_state):
        # Initialise blast list
        blast_list = []

        # Copy block data to determine blasts
        calc_soft_blocks = game_state.soft_blocks.copy ()  # 1
        calc_ore_blocks = self.ore_tracked.copy ()  # 3 Ore blocks must be tracked
        # game_state.indestructible_blocks #INF

        # Run through bombs and register blasts to blast_list
        ordered_bombs_tracked = sorted (self.bombs_tracked, key=lambda x: x[2])
        for bomb_tracked in ordered_bombs_tracked:
            # left
            left_location = (bomb_tracked[0] - 1, bomb_tracked[1])
            left_two_location = (bomb_tracked[0] - 2, bomb_tracked[1])
            if self.get_tile (calc_ore_blocks, left_location[0], left_location[1]) != 'tile not found':
                # Ore block - delete/damage
                calc_ore_block = self.get_tile (calc_ore_blocks, left_location[0], left_location[1])
                calc_ore_blocks.append ((calc_ore_block[0], calc_ore_block[1], calc_ore_block[2] - 1))
                calc_ore_blocks.remove (calc_ore_block)
            elif self.get_tile (calc_soft_blocks, left_location[0], left_location[1]) != 'tile not found':
                # Soft block - delete
                calc_soft_blocks.remove (self.get_tile (calc_soft_blocks, left_location[0], left_location[1]))
            elif self.get_tile (game_state.indestructible_blocks, left_location[0],
                                left_location[1]) == 'tile not found':
                # No block proven by lack of indestructible block - register and...
                new_blast = (left_location[0], left_location[1], bomb_tracked[2])
                blast_list.append (new_blast)
                # ... progress to "left_two"
                if self.get_tile (calc_ore_blocks, left_two_location[0], left_two_location[1]) != 'tile not found':
                    # Ore block - delete/damage
                    calc_ore_block = self.get_tile (calc_ore_blocks, left_two_location[0], left_two_location[1])
                    calc_ore_blocks.append ((calc_ore_block[0], calc_ore_block[1], calc_ore_block[2] - 1))
                    calc_ore_blocks.remove (calc_ore_block)
                elif self.get_tile (calc_soft_blocks, left_two_location[0], left_two_location[1]) != 'tile not found':
                    # Soft block - delete
                    calc_soft_blocks.remove (
                        self.get_tile (calc_soft_blocks, left_two_location[0], left_two_location[1]))
                elif self.get_tile (game_state.indestructible_blocks, left_two_location[0],
                                    left_two_location[1]) == 'tile not found':
                    # No block - register blast
                    new_blast = (left_two_location[0], left_two_location[1], bomb_tracked[2])
                    blast_list.append (new_blast)

            # right
            right_location = (bomb_tracked[0] + 1, bomb_tracked[1])
            right_two_location = (bomb_tracked[0] + 2, bomb_tracked[1])
            if self.get_tile (calc_ore_blocks, right_location[0], right_location[1]) != 'tile not found':
                # Ore block - delete/damage
                calc_ore_block = self.get_tile (calc_ore_blocks, right_location[0], right_location[1])
                calc_ore_blocks.append ((calc_ore_block[0], calc_ore_block[1], calc_ore_block[2] - 1))
                calc_ore_blocks.remove (calc_ore_block)
            elif self.get_tile (calc_soft_blocks, right_location[0], right_location[1]) != 'tile not found':
                # Soft block - delete
                calc_soft_blocks.remove (self.get_tile (calc_soft_blocks, right_location[0], right_location[1]))
            elif self.get_tile (game_state.indestructible_blocks, right_location[0],
                                right_location[1]) == 'tile not found':
                # No block proven by lack of indestructible block - register and...
                new_blast = (right_location[0], right_location[1], bomb_tracked[2])
                blast_list.append (new_blast)
                # ... progress to "right_two"
                if self.get_tile (calc_ore_blocks, right_two_location[0], right_two_location[1]) != 'tile not found':
                    # Ore block - delete/damage
                    calc_ore_block = self.get_tile (calc_ore_blocks, right_two_location[0], right_two_location[1])
                    calc_ore_blocks.append ((calc_ore_block[0], calc_ore_block[1], calc_ore_block[2] - 1))
                    calc_ore_blocks.remove (calc_ore_block)
                elif self.get_tile (calc_soft_blocks, right_two_location[0], right_two_location[1]) != 'tile not found':
                    # Soft block - delete
                    calc_soft_blocks.remove (
                        self.get_tile (calc_soft_blocks, right_two_location[0], right_two_location[1]))
                elif self.get_tile (game_state.indestructible_blocks, right_two_location[0],
                                    right_two_location[1]) == 'tile not found':
                    # No block - register blast
                    new_blast = (right_two_location[0], right_two_location[1], bomb_tracked[2])
                    blast_list.append (new_blast)

            # up
            up_location = (bomb_tracked[0], bomb_tracked[1] + 1)
            up_two_location = (bomb_tracked[0], bomb_tracked[1] + 2)
            if self.get_tile (calc_ore_blocks, up_location[0], up_location[1]) != 'tile not found':
                # Ore block - delete/damage
                calc_ore_block = self.get_tile (calc_ore_blocks, up_location[0], up_location[1])
                calc_ore_blocks.append ((calc_ore_block[0], calc_ore_block[1], calc_ore_block[2] - 1))
                calc_ore_blocks.remove (calc_ore_block)
            elif self.get_tile (calc_soft_blocks, up_location[0], up_location[1]) != 'tile not found':
                # Soft block - delete
                calc_soft_blocks.remove (self.get_tile (calc_soft_blocks, up_location[0], up_location[1]))
            elif self.get_tile (game_state.indestructible_blocks, up_location[0], up_location[1]) == 'tile not found':
                # No block proven by lack of indestructible block - register and...
                new_blast = (up_location[0], up_location[1], bomb_tracked[2])
                blast_list.append (new_blast)
                # ... progress to "up_two"
                if self.get_tile (calc_ore_blocks, up_two_location[0], up_two_location[1]) != 'tile not found':
                    # Ore block - delete/damage
                    calc_ore_block = self.get_tile (calc_ore_blocks, up_two_location[0], up_two_location[1])
                    calc_ore_blocks.append ((calc_ore_block[0], calc_ore_block[1], calc_ore_block[2] - 1))
                    calc_ore_blocks.remove (calc_ore_block)
                elif self.get_tile (calc_soft_blocks, up_two_location[0], up_two_location[1]) != 'tile not found':
                    # Soft block - delete
                    calc_soft_blocks.remove (self.get_tile (calc_soft_blocks, up_two_location[0], up_two_location[1]))
                elif self.get_tile (game_state.indestructible_blocks, up_two_location[0],
                                    up_two_location[1]) == 'tile not found':
                    # No block - register blast
                    new_blast = (up_two_location[0], up_two_location[1], bomb_tracked[2])
                    blast_list.append (new_blast)

            # down
            down_location = (bomb_tracked[0], bomb_tracked[1] - 1)
            down_two_location = (bomb_tracked[0], bomb_tracked[1] - 2)
            if self.get_tile (calc_ore_blocks, down_location[0], down_location[1]) != 'tile not found':
                # Ore block - delete/damage
                calc_ore_block = self.get_tile (calc_ore_blocks, down_location[0], down_location[1])
                calc_ore_blocks.append ((calc_ore_block[0], calc_ore_block[1], calc_ore_block[2] - 1))
                calc_ore_blocks.remove (calc_ore_block)
            elif self.get_tile (calc_soft_blocks, down_location[0], down_location[1]) != 'tile not found':
                # Soft block - delete
                calc_soft_blocks.remove (self.get_tile (calc_soft_blocks, down_location[0], down_location[1]))
            elif self.get_tile (game_state.indestructible_blocks, down_location[0],
                                down_location[1]) == 'tile not found':
                # No block proven by lack of indestructible block - register and...
                new_blast = (down_location[0], down_location[1], bomb_tracked[2])
                blast_list.append (new_blast)
                # ... progress to "down_two"
                if self.get_tile (calc_ore_blocks, down_two_location[0], down_two_location[1]) != 'tile not found':
                    # Ore block - delete/damage
                    calc_ore_block = self.get_tile (calc_ore_blocks, down_two_location[0], down_two_location[1])
                    calc_ore_blocks.append ((calc_ore_block[0], calc_ore_block[1], calc_ore_block[2] - 1))
                    calc_ore_blocks.remove (calc_ore_block)
                elif self.get_tile (calc_soft_blocks, down_two_location[0], down_two_location[1]) != 'tile not found':
                    # Soft block - delete
                    calc_soft_blocks.remove (
                        self.get_tile (calc_soft_blocks, down_two_location[0], down_two_location[1]))
                elif self.get_tile (game_state.indestructible_blocks, down_two_location[0],
                                    down_two_location[1]) == 'tile not found':
                    # No block - register blast
                    new_blast = (down_two_location[0], down_two_location[1], bomb_tracked[2])
                    blast_list.append (new_blast)

        # remove tiles not in bounds of the game
        valid_blast_list = []
        for blast_tile in blast_list:
            if self.game_state.is_in_bounds ((blast_tile[0], blast_tile[1])):
                valid_blast_list.append (blast_tile)

        return valid_blast_list

    # Update suspended treasures
    def update_treasure_tracked(self, game_state):
        new_list = []
        for suspended_piece in self.suspended_treasure:
            if(suspended_piece[2] > 1):
                new_list.append((suspended_piece[0], suspended_piece[1], suspended_piece[2]-1))
        self.suspended_treasure = new_list

    # Updates the bombs
    # Also updates the ores
    def update_bombs_tracked(self, game_state):
        ticks_passed = game_state.tick_number - self.prev_ticks
        self.prev_ticks = game_state.tick_number

        # Check if there are ores that we missed
        for ore_block in game_state.ore_blocks:
            if (self.get_tile (self.ore_tracked, ore_block[0], ore_block[1]) == 'tile not found'):
                self.ore_tracked.append ((ore_block[0], ore_block[1], 3))

        # TODO Stretch - Check ore_tracked against game_state

        bomb_locations = game_state.bombs
        update_bomb_locations = []
        # Burn the fuses of the known bombs
        for bomb_tracked in self.bombs_tracked:
            if bomb_tracked[2] < 1:
                # Bomb fuse has gone
                # Damage ores appropriately, before removing the bomb.
                # Left
                left_item = game_state.entity_at ((bomb_tracked[0] - 1, bomb_tracked[1]))
                left_ore_two = self.get_tile (self.ore_tracked, bomb_tracked[0] - 2, bomb_tracked[1])
                if left_item == 'ob':
                    # ore block - damage just the one
                    left_ore = self.get_tile (self.ore_tracked, bomb_tracked[0] - 1, bomb_tracked[1])
                    self.ore_tracked.append ((left_ore[0], left_ore[1], left_ore[2] - 1))
                    self.ore_tracked.remove (left_ore)
                elif (left_item != 'ib') & (left_item != 'sb'):
                    # nothing in the way - proceed to check the second block
                    if left_ore_two != 'tile not found':
                        self.ore_tracked.append ((left_ore_two[0], left_ore_two[1], left_ore_two[2] - 1))
                        self.ore_tracked.remove (left_ore_two)
                # Right

                right_item = game_state.entity_at ((bomb_tracked[0] + 1, bomb_tracked[1]))
                right_ore_two = self.get_tile (self.ore_tracked, bomb_tracked[0] + 2, bomb_tracked[1])
                if right_item == 'ob':
                    # ore block - damage just the one
                    right_ore = self.get_tile (self.ore_tracked, bomb_tracked[0] + 1, bomb_tracked[1])
                    self.ore_tracked.append ((right_ore[0], right_ore[1], right_ore[2] - 1))
                    self.ore_tracked.remove (right_ore)
                elif (right_item != 'ib') & (right_item != 'sb'):
                    # nothing in the way - proceed to check the second block
                    if right_ore_two != 'tile not found':
                        self.ore_tracked.append ((right_ore_two[0], right_ore_two[1], right_ore_two[2] - 1))
                        self.ore_tracked.remove (right_ore_two)

                # Down
                down_item = game_state.entity_at ((bomb_tracked[0], bomb_tracked[1] - 1))
                down_ore_two = self.get_tile (self.ore_tracked, bomb_tracked[0], bomb_tracked[1] - 2)
                if down_item == 'ob':
                    # ore block - damage just the one
                    down_ore = self.get_tile (self.ore_tracked, bomb_tracked[0], bomb_tracked[1] - 1)
                    self.ore_tracked.append ((down_ore[0], down_ore[1], down_ore[2] - 1))
                    self.ore_tracked.remove (down_ore)
                elif (down_item != 'ib') & (down_item != 'sb'):
                    # nothing in the way - proceed to check the second block
                    if down_ore_two != 'tile not found':
                        self.ore_tracked.append ((down_ore_two[0], down_ore_two[1], down_ore_two[2] - 1))
                        self.ore_tracked.remove (down_ore_two)
                # Up
                up_item = game_state.entity_at ((bomb_tracked[0], bomb_tracked[1] + 1))
                up_ore_two = self.get_tile (self.ore_tracked, bomb_tracked[0], bomb_tracked[1] + 2)
                if up_item == 'ob':
                    # ore block - damage just the one
                    up_ore = self.get_tile (self.ore_tracked, bomb_tracked[0], bomb_tracked[1] + 1)
                    self.ore_tracked.append ((up_ore[0], up_ore[1], up_ore[2] - 1))
                    self.ore_tracked.remove (up_ore)
                elif (up_item != 'ib') & (up_item != 'sb'):
                    # nothing in the way - proceed to check the second block
                    if up_ore_two != 'tile not found':
                        self.ore_tracked.append ((up_ore_two[0], up_ore_two[1], up_ore_two[2] - 1))
                        self.ore_tracked.remove (up_ore_two)

            else:
                # Update the bomb
                updated_bomb = (bomb_tracked[0], bomb_tracked[1], bomb_tracked[2] - ticks_passed)
                update_bomb_locations.append (updated_bomb)

        self.bombs_tracked = update_bomb_locations

        # Remove destroyed ores
        for ore_track in self.ore_tracked:
            if ore_track[2] == 0:
                self.ore_tracked.remove (ore_track)

        # Check if any bombs tracked down without being triggered:
        for bomb_tracked in self.bombs_tracked:
            if bomb_tracked[2] < -1:
                print ('[blast radius] ERROR: Bomb did not detonate')
                print (bomb_tracked)

        # ID the new bombs
        for bomb_location in bomb_locations:
            # Add the bomb if it doesn't already exist
            already_tracked = False
            for bomb_tracked in self.bombs_tracked:
                if (bomb_tracked[0], bomb_tracked[1]) == (bomb_location[0], bomb_location[1]):
                    already_tracked = True
            if already_tracked == False:
                # Bomb is determined not to be tracked, and should be added
                new_bomb = (bomb_location[0], bomb_location[1], 35)
                for bomb_tracked in self.bombs_tracked:  # - check its location against existing blast radii before setting fuse timer
                    if (self.in_blast_radius (bomb_tracked, new_bomb, game_state)):
                        # If it is in the blast radius of another tracked bomb, it matches that bombs timer + 1
                        # Match the bomb closest to exploding
                        if (new_bomb[2] > bomb_tracked[2]):
                            new_bomb = (bomb_location[0], bomb_location[1], bomb_tracked[2] + 1)
                # Add bomb to tracking
                self.bombs_tracked.append (new_bomb)

    # Return whether a checked location is in the blast radius of a bomb location
    def in_blast_radius(self, bomb_location, check_location, game_state):
        if (bomb_location == check_location):
            print ('WARN: Matching locations')
        # Matching x-axis
        if check_location[0] == bomb_location[0]:
            if abs (check_location[1] - bomb_location[1]) < 2:
                return True  # Adjacent
            if abs (check_location[1] - bomb_location[1]) == 2:
                # Check for wooden, ore, metal blocks in between
                inbetween_location = (check_location[0], (check_location[1] + bomb_location[1]) / 2)
                if (self.get_tile (game_state.all_blocks, inbetween_location[0],
                                   inbetween_location[1]) == 'tile not found'):
                    return True  # No tile blocking = blast
                else:
                    return False  # Block blocking = no blast
        # Matching y-axis
        if check_location[1] == bomb_location[1]:
            if abs (check_location[0] - bomb_location[0]) < 2:
                return True  # Adjacent
            if abs (check_location[0] - bomb_location[0]) == 2:
                # Check for wooden, ore, metal blocks in between
                inbetween_location = ((check_location[0] + bomb_location[0]) / 2, check_location[1])
                if (self.get_tile (game_state.all_blocks, inbetween_location[0],
                                   inbetween_location[1]) == 'tile not found'):
                    return True  # No tile blocking = blast
                else:
                    return False  # Block blocking = no blast

    # Scan an array of tiles for a given x/y
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
            if self.game_state.is_in_bounds (tile):
                # if yes, then add them to our list
                valid_surrounding_tiles.append (tile)

        return valid_surrounding_tiles

    # given a list of tiles
    # return the ones which are actually empty
    def get_empty_tiles(self, tiles):

        # empty list to store our empty tiles
        empty_tiles = []

        for tile in tiles:
            if not self.game_state.is_occupied (tile):
                # the tile isn't occupied, so we'll add it to the list
                empty_tiles.append (tile)

        return empty_tiles

    # given an adjacent tile location, move us there
    def move_to_tile(self, location, tile):

        actions = ['', 'u', 'd', 'l', 'r', 'p']

        # see where the tile is relative to our current location
        diff = tuple (x - y for x, y in zip (self.location, tile))

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

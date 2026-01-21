import random
import pygame
import numpy as np
import copy
from perlin import generate_fractal_noise
from perlin import get_permutation_table

P_TABLE = get_permutation_table(42)

# initialize pygame
pygame.init()
random.seed() # seed with system time

# window size
WIDTH, HEIGHT = 300, 300
PX = 3 #upscale resolution
screen = pygame.display.set_mode((WIDTH*PX, HEIGHT*PX))
window_title = "Procedural Terrain Generator"

clock = pygame.time.Clock()

##################################

block_size = 20
scale = 0.005
terrain_map = {} # empty dict
def generate_chunk(X:int, Y:int):
    # vectorized grid generation
    x_range = np.arange(X * block_size, (X + 1) * block_size) * scale
    y_range = np.arange(Y * block_size, (Y + 1) * block_size) * scale
    # create a 2D grid of coordinates
    xx, yy = np.meshgrid(x_range, y_range, indexing='ij')

    # single call for the entire chunk (it was a nested for loop before optimization)
    value = generate_fractal_noise(xx, yy, P_TABLE, octaves=7, persistence=0.4, lacunarity=3)
    
    # normalize and clip
    value = (value + 1) / 2
    tmax, tmin = 0.75, 0.25 
    value = (value - tmin) / (tmax - tmin)
    terrain_map[(X,Y)] = np.clip(value, 0, 1)

sprite_map = {} # empty dict
def draw_chunk(X:int, Y:int): # generates color array from given block's terrain map
    random.seed(X + 200*Y)
    sprite = np.zeros((block_size*PX, block_size*PX, 3), dtype=np.uint8) # create empty block

    cliff_threshold = 0.65
    for x in range(block_size):
        for y in range(block_size):
            value = terrain_map[(X,Y)][x, y]
            value = max(min(1, value), 0)
            xslope, yslope = 0, 0
            unitdist = 2 * (scale ** 0.92)
            if 0 < x < block_size - 1:
                xslope = (terrain_map[(X,Y)][x+1, y] - terrain_map[(X,Y)][x-1, y]) / 2 / unitdist
            else:
                if x == 0:
                    xslope = (terrain_map[(X,Y)][x+1, y] - terrain_map[(X,Y)][x, y]) / unitdist
                if x == block_size - 1:
                    xslope = (terrain_map[(X,Y)][x, y] - terrain_map[(X,Y)][x-1, y]) / unitdist
            if 0 < y < block_size - 1:
                yslope = (terrain_map[(X,Y)][x, y+1] - terrain_map[(X,Y)][x, y-1]) / 2 / unitdist
            else:
                if y == 0:
                    yslope = (terrain_map[(X,Y)][x, y+1] - terrain_map[(X,Y)][x, y]) / unitdist
                if y == block_size - 1:
                    yslope = (terrain_map[(X,Y)][x, y] - terrain_map[(X,Y)][x, y-1]) / unitdist
            gradient_sqr = xslope * xslope + yslope * yslope

            r, g, b = int(value*255), int(value*180), 50 # default color
            if value == 0: # void
                r, g, b = 15, 0, 40
                # shine
                if (2*x + y) % 10 == 0:
                    r, g, b = 60, 20, 80
            elif value < 0.10: # abbys
                r, g, b = 44, 9, 84
                # shine
                if (2*x + y) % 10 == 0 and random.random() < 0.7:
                    r, g, b = 80, 60, 120
            elif value < 0.26: # deep sea level
                r, g, b = 60, 30, 150
                # shine
                if (2*x + y) % 10 == 0 and random.random() < 0.4:
                    r, g, b = 160, 160, 200
            elif value < 0.32: # sea level
                r, g, b = 80, 80, 200
            elif value < 0.38: # shallow sea level
                r, g, b = 90, 150, 255
            elif value < 0.40: # foam?
                r, g, b = 184, 210, 255
            elif value < 0.50: # shoreline
                r, g, b = 242, 216, 189
                # rocks
                l1 = 0.420
                if ((l1 - 0.005 < value < l1 or l1 + 0.005 < value < l1 + 0.010) and random.random() < 0.4) or (l1 < value < l1 + 0.005):
                    r, g, b = 97, 79, 61
            elif value < 0.62: # meadows
                r, g, b = 115, 191, 99
                # flowers
                if gradient_sqr < 0.09: # flats
                    r, g, b = 153, 69, 209
                if (x+y)%2 == 0 and random.random() < 0.05: # rand
                    r, g, b = 106, 101, 240
            elif value < 0.72: # forest
                r, g, b = 54, 156, 83
                if gradient_sqr > cliff_threshold: # hillsides
                    r, g, b = 120, 70, 50
            elif value < 0.82: # mountain
                r, g, b = 18, 102, 57
                if gradient_sqr > cliff_threshold: # cliffs
                    r, g, b = 92, 53, 37
            elif value < 0.95: # high mountain
                r, g, b = 7, 77, 43
                if gradient_sqr > cliff_threshold: # cliffs
                    r, g, b = 66, 38, 32
            elif value < 1: # peaks
                r, g, b = 200, 200, 220
            else:
                r, g, b = 230, 230, 250

            sprite[x*PX : (x+1)*PX, y*PX : (y+1)*PX, :] = r, g, b
    sprite_map[(X,Y)] = pygame.surfarray.make_surface(sprite)

##################################

cameraX, cameraY = 0, 0 # points to the top left corner of the window

def out_of_bound(key, left, right, top, bottom):
    return key[0] < left or key[0] > right or key[1] < top or key[1] > bottom

scaled = False
def make_data(): # handle data loading / unloading
    # corner pixel positions -> which chunk are they in
    top, left     = (cameraY) // block_size,              (cameraX) // block_size
    bottom, right = (cameraY + HEIGHT - 1) // block_size, (cameraX + WIDTH - 1) // block_size

    #unload useless data
    for key in list(terrain_map.keys()):
        if out_of_bound(key, left, right, top, bottom):
            del terrain_map[key]
    for key in list(sprite_map.keys()):
        if out_of_bound(key, left, right, top, bottom):
            del sprite_map[key]

    # generate missing data
    for X in range(left, right+1):
        for Y in range(top, bottom+1):
            if ((X, Y) not in terrain_map) or scaled:
                generate_chunk(X, Y)
            if ((X, Y) not in sprite_map) or scaled:
                draw_chunk(X, Y)
                # real time draw
                draw_to_screen(single=True, Xi=X, Yi=Y)
                pygame.display.flip()

def draw_to_screen(single=False, Xi=0, Yi=0):
    # corner pixel positions -> which chunk are they in
    top, left     = (cameraY) // block_size,              (cameraX) // block_size
    bottom, right = (cameraY + HEIGHT - 1) // block_size, (cameraX + WIDTH - 1) // block_size

    # draw every chunk
    if not single:
        for X in range(left, right+1):
            for Y in range(top, bottom+1):
                x = (((X - left) * block_size) - (cameraX % block_size)) * PX
                y = (((Y - top) * block_size) - (cameraY % block_size)) * PX
                screen.blit(sprite_map[(X,Y)], (x,y))
    else:
        X, Y = Xi, Yi
        x = (((X - left) * block_size) - (cameraX % block_size)) * PX
        y = (((Y - top) * block_size) - (cameraY % block_size)) * PX
        screen.blit(sprite_map[(X,Y)], (x,y))

##################################
cameraX, cameraY = random.randint(-50000, 50000), random.randint(-50000, 50000)
running = True
cinematic = False
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            cameraX, cameraY = random.randint(-50000, 50000), random.randint(-50000, 50000)

        if event.type == pygame.KEYDOWN and (event.key == pygame.K_q or event.key == pygame.K_e):
            # save values
            center_noise_x = (cameraX + WIDTH / 2) * scale
            center_noise_y = (cameraY + HEIGHT / 2) * scale
            # change scale
            if event.key == pygame.K_q:
                scale /= 2
            else:
                scale *= 2
            scaled = True
            # adjust position by applying inverse transformation
            cameraX = int((center_noise_x / scale) - (WIDTH / 2))
            cameraY = int((center_noise_y / scale) - (HEIGHT / 2))

        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            cinematic = not cinematic
        
    # camera movement
    keys = pygame.key.get_pressed()
    h_ax = keys[pygame.K_d] - keys[pygame.K_a]
    v_ax = keys[pygame.K_s] - keys[pygame.K_w]
    if not cinematic:
        cameraX += h_ax * 6
        cameraY += v_ax * 6
    else:
        # cinematic scroll
        cameraX += 2
        cameraY += 1

    pygame.display.set_caption(f"{window_title} :: {int(clock.get_fps())} fps") # update title with fps
    clock.tick(60) # cap the frame rate to 60 fps

    make_data()
    scaled = False
    draw_to_screen()

    pygame.display.flip() # update window

pygame.quit()

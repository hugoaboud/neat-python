"""

    neat-python hoverboard visualize tool

    Small tool for watching neat-python genomes play the hoverboard game,
    and also make some nice little plots.
    It takes the genomes from checkpoints generated by the evolve-<>.py files.

    # USAGE:
    > python visualize.py <EXPERIMENT> <ANGLE>
    > python visualize.py --help

    @author: Hugo Aboud (@hugoaboud)

"""

import os
import argparse
from scipy.spatial import Delaunay

##  DEBUG
##  Uses local version of neat-python
import sys
sys.path.append('../../')
##  DEBUG
import neat
from neat.math_util import mean

import random
import math

from matplotlib import pyplot as plt
from matplotlib import gridspec as gridspec
from hoverboard import Game
from gui import NeuralNetworkGUI

# General Parameters

GAME_TIME_STEP = 0.001

# CLI Parameters

GAME_START_ANGLE = 0
FAST_FORWARD = False
JUST_PLOT = False
WATCH_LAST = False
EXPERIMENT = 'time'

##
#   Reporter
#   Used to watch the game after each evaluation
##

class GameReporter(neat.reporting.BaseReporter):
    def __init__(self, population, step, angle, dir_input = False):
        self.population = population
        self.step = step
        self.angle = angle
        self.dir_input = dir_input
        self.best = None
        self.gen = 0
    def post_evaluate(self, config, population, species, best_genome):
        # If best genome has changed, watch it
        if (not self.best or best_genome != self.best):
            self.best = best_genome
            species = self.population.species.get_species_id(self.best.key)
            watch(config, self.step, self.gen, species, self.best, self.angle, self.dir_input)
        self.gen += 1

##
#   Data
#   parse populations from checkpoints
##

def load_checkpoints(folder):
    print("Loading checkpoints from {0}...".format(folder))
    # load generations from file
    checkpoints = []
    files = os.listdir(folder)
    # progress bar vars
    step = len(files)/46
    t = 0
    print('[', end='', flush=True)
    for filename in files:
        # load checkpoint and append to list
        checkpoint = neat.Checkpointer.restore_checkpoint(os.path.join(folder,filename))
        checkpoints.append(checkpoint)
        # update progress bar
        t += 1
        if (t > step):
            t -= step
            print('.', end='', flush=True)
    print(']')
    # Sort checkpoints by generation id
    checkpoints.sort(key = lambda g: g.generation)
    return checkpoints

##
#   Plot Fitness
#   Best and Average
##

def plot_fitness(checkpoints, name):
    gens = [c.generation for c in checkpoints]
    bests = [c.best_genome.fitness for c in checkpoints]
    avgs = [mean([f.fitness for _, f in c.population.items()]) for c in checkpoints]

    fig, ax = plt.subplots(figsize = (10,5))
    ax.set_title(name+" - Fitness over Generations")
    ax.plot(gens, bests, color='blue', linewidth=1, label="Best")
    ax.plot(gens, avgs, color='black', linewidth=1, label="Average")
    ax.legend()

    ax.set_xlabel('Generation')
    ax.set_ylabel('Fitness (Flight Time)')

    plt.tight_layout()
    fig.savefig(name+'.png', format='png', dpi=300)
    plt.show()
    plt.close()

##
#   Plot Species
#   Stackplot of species member count over generations
##

def plot_species(checkpoints, name):
    gens = [c.generation for c in checkpoints]
    species = [c.species.species for c in checkpoints]

    max_species = max(max(id for id,_ in sps.items()) for sps in species)+1
    species = [[(len(sps[s].members) if (s in sps) else 0) for sps in species] for s in range(1,max_species)]

    fig, ax = plt.subplots(figsize = (10,5))
    ax.set_title(name+" - Species over Generations")
    ax.stackplot(gens, species)

    ax.set_xlabel('Generation')
    ax.set_ylabel('Number of Genomes')

    plt.tight_layout()
    fig.savefig(name+'_species.png', format='png', dpi=300)
    plt.show()
    plt.close()

##
#   Plot Pareto 2D
#   Scatter plot of 2 dimensional fitness, to evaluate pareto optimization
##

def plot_pareto_2d(checkpoints, label0, label1, max0, max1, name, min=0, max=-1, invert=True):
    fitnesses = [[f.fitness for _, f in c.population.items()] for c in checkpoints[min:max]]
    bests = [c.best_genome.fitness for c in checkpoints[min:max]]

    fig, ax = plt.subplots(figsize = (10,5))
    ax.set_title(name+" - Solution Space")

    if (invert):
        ax.set_xlabel(label1)
        ax.set_ylabel(label0)
    else:
        ax.set_xlabel(label0)
        ax.set_ylabel(label1)

    # scatter
    for gen in fitnesses:
        x = [f.values[0] if (f.values[0] < max0) else max0 for f in gen]
        y = [f.values[1] if (f.values[1] < max1) else max1 for f in gen]
        r = lambda: random.randint(0,255)
        color = '#%02X%02X%02X' % (r(),r(),r())
        if (invert):
            ax.scatter(y, x, s=3, c=color)
        else:
            ax.scatter(x, y, s=3, c=color)
        # triangulation
        tri = Delaunay(list(zip(y,x)))
        for t in tri.simplices:
            x = [gen[i].values[0] if (gen[i].values[0] < max0) else max0 for i in t]
            y = [gen[i].values[1] if (gen[i].values[1] < max1) else max1 for i in t]
            ax.fill(y,x,linewidth=0.2,c=color,alpha=0.05)

    x = [f.values[0] if (f.values[0] < max0) else max0 for f in bests]
    y = [f.values[1] if (f.values[1] < max1) else max1 for f in bests]
    ax.plot(y,x,linewidth=1,c='#000000',label="best genome")

    ax.legend()

    plt.tight_layout()
    fig.savefig(name+'_pareto.png', format='png', dpi=300)
    plt.show()
    plt.close()

##
#   Watch
#   watch a genome play the game
##
def watch(config, time_step, generation, species, genome, start_angle, dir_input = False):
    # create a recurrent network
    net = neat.nn.RecurrentNetwork.create(genome, config)
    # create a network GUI to render the topology and info
    ui = NeuralNetworkGUI(generation, genome, species, net)
    # create a Game with frontend enabled, and the GUI above
    game = Game(start_angle,True,ui)
    # run the game until reset
    while(True):
        if (dir_input):
            dir = [0.5-game.hoverboard.x, 0.5-game.hoverboard.y]
            norm = math.sqrt(dir[0]**2+dir[1]**2)
            # activate network
            output = net.activate([game.hoverboard.velocity[0], game.hoverboard.velocity[1], game.hoverboard.ang_velocity, game.hoverboard.normal[0], game.hoverboard.normal[1], dir[0], dir[1]])
        else:
            output = net.activate([game.hoverboard.velocity[0], game.hoverboard.velocity[1], game.hoverboard.ang_velocity, game.hoverboard.normal[0], game.hoverboard.normal[1]])
        # output to hoverboard thrust
        game.hoverboard.set_thrust(output[0], output[1])
        # update game manually from time step
        game.update(time_step)
        # if game reseted, break
        if (game.reset_flag): break

##
#   Main
##

def main():
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description='Tool for visualizing the neat-python checkpoints playing the hoverboard game.')
    parser.add_argument('angle', help="Starting angle of the platform")
    parser.add_argument('experiment', help="Experiment prefix: (time,rundvnc), default: time", const='time', nargs='?')
    parser.add_argument('-f', '--fastfwd', help="Fast forward the game preview (2x)", nargs='?', const=True, type=bool)
    parser.add_argument('-p', '--just_plot', help="Don't watch the game, just plot", nargs='?', const=True, type=bool)
    parser.add_argument('-l', '--watch_last', help="Watch the last game", nargs='?', const=True, type=bool)
    args = parser.parse_args()

    # Store global parameters
    global GAME_START_ANGLE
    global FAST_FORWARD
    global JUST_PLOT
    global WATCH_LAST
    GAME_START_ANGLE = float(args.angle)
    FAST_FORWARD = bool(args.fastfwd)
    JUST_PLOT = bool(args.just_plot)
    WATCH_LAST = bool(args.watch_last)

    # Check experiment argument
    global EXPERIMENT
    if (args.experiment is not None):
        EXPERIMENT = str(args.experiment)
        if (EXPERIMENT not in ('time','timedist')):
            print("ERROR: Invalid experiment '" + EXPERIMENT + "'")
            return

    # load data
    checkpoints = load_checkpoints('checkpoint-'+EXPERIMENT)

    # create neat config from file
    cfg_file = {'time':'config-default',
                'timedist':'config-nsga2'}[EXPERIMENT]
    repro = {'time':neat.DefaultReproduction,
             'timedist':neat.nsga2.NSGA2Reproduction}[EXPERIMENT]
    config = neat.Config(neat.DefaultGenome, repro, neat.DefaultSpeciesSet, neat.DefaultStagnation, cfg_file)

    # run game for the best genome of each checkpoint
    # if it's not the same as the last one
    last_genome = None
    for checkpoint in checkpoints:
        # skip repeated genomes
        if (checkpoint.best_genome.key != last_genome):
            last_genome = checkpoint.best_genome.key
        else:
            continue
        # get species id
        species = checkpoint.species.get_species_id(checkpoint.best_genome.key)
        # watch the genome play
        if (not JUST_PLOT and not WATCH_LAST):
            watch(config, GAME_TIME_STEP*(2 if FAST_FORWARD else 1), checkpoint.generation, species, checkpoint.best_genome, GAME_START_ANGLE, EXPERIMENT in ['timedist'])

    # watch the last game
    if (WATCH_LAST):
        watch(config, GAME_TIME_STEP*(2 if FAST_FORWARD else 1), checkpoint.generation, species, checkpoint.best_genome, GAME_START_ANGLE, EXPERIMENT in ['timedist'])

    # scientific plot
    plot_fitness(checkpoints, EXPERIMENT)
    plot_species(checkpoints, EXPERIMENT)
    if (EXPERIMENT in ['timedist']):
        plot_pareto_2d(checkpoints, 'Flight Time', 'Average Squared Distance from Center', 100, 0, EXPERIMENT)

if __name__ == "__main__":
   main()

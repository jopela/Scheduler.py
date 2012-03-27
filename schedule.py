#!/usr/bin/python
# File: schedule.py.
# Description: Program to create a schedule for the Montreal symphonic 
# orchestra.
# Author: Jonathan Pelletier (http://0xff.info)
# Date: Sun Nov 27 18:35:36 EST 2011

import argparse
import random
import time
import sys
import math
import numpy as np
from termcolor import *

def main():

    parser = argparse.ArgumentParser(description='Schedules an orchestra'\
            ' rehearsal using the simulated annealing algorithm')

    parser.add_argument(
            'filename',
            help='Name of the file containing the problem instance to solve'
            )

    parser.add_argument(
            'tlimit',
            help='Time budget allocated for computation in seconds',
            type=int
            )

    arguments = parser.parse_args()

    filename = arguments.filename
    tlimit = arguments.tlimit
    
    # read the problem from file.
    problem = Problem()
    problem.read_from_file(filename)

    # call the simulated annealing method.
    print colored("Solving %s with simulated annealing ...",'green') % filename
    cost, sol = simulated_annealing(problem, cost_function, hypertan, gibbs,
            tlimit)

    # print the solution cost.
    print colored(cost,'green')
    # print the solution elements (joined with ,)
    print colored(",".join([str(i) for i in sol]),'green')

    return


def simulated_annealing(problem, energy, schedule, pdist ,tlimit):
    """ Minimize the energy function using a simulated annealing algorithm."""

    # initialise the random number generator and values used in random 
    # number generation.
    random.seed()

    # this fraction of the time will be allocated to computing to make sure we 
    # finish in time.
    compute_fraction = 0.95

    # problem size.
    n = problem.nbr_pieces

    # start with an initial state and make it the best current state.
    scurr = random_state(n)
    sbest = scurr
    ecurr = energy(problem,scurr)
    ebest = ecurr

    # record the time at which we start to compute and compute the end time.
    stime = time.time()
    etime = stime + (compute_fraction * tlimit)

    ctime = time.time()
    report = ctime

    temperature_function = hypertan(stime, etime)
    progress(50,0)

    while(ctime < etime):
        # pick a neighbour from the current state
        snew = neighbour(scurr)
        enew = energy(problem, snew)

        # update the system temparature
        temp = temperature_function(time.time())

        # makes a state transition if probability distribution allows it
        p = pdist(ecurr, enew, temp)
        if  p > random.random():
            scurr = snew
            ecurr = enew
        
        # if the energy of the state is lower then it used to be, it becomes
        # our new best state.
        if enew < ebest:
            # print "found better! %d->%d" % (ebest, enew)
            sbest = snew
            ebest = enew

        ctime = time.time()

        if (ctime - report) > 1:
            percent = (ctime-stime)/(etime-stime)*100
            if percent < 100:
                progress(50, percent)
            report = ctime

    progress(49, 100)
    # return both the best energy and the solution associated with it.
    return ebest, sbest


def hypertan(start, end):
    """ computes the current temperature with an hyperbolic tangent cooling
    shedule."""

    # we set the initial temperature to "infinity" (system maximum value)
    temp0 = sys.maxint
    # the final temperature must be 0.
    temp1 = 0

    t0 = start
    t1 = end

    f = lambda t : 0.5 * (temp0 - temp1) * (1 - np.tanh( (10.0/(t1-t0)) *  \
            (t - (t0+t1)/2.0))) + temp1

    return f


def gibbs(e1, e2, temperature):
    """ Returns a probability given by a gibbs distribution. """

    # this is the "textbook" implementation of the acceptance
    if e2 < e1:
        return 1.0

    param = 100000000

    p = np.exp(10000000*(e1-e2)/float(temperature) )
    return p


def random_state(n):
    """ Generates a random solution of size n for the orchestra scheduling
    problem."""
    state = []
    candidates = range(n)

    while(candidates):
        c = random.choice(candidates)
        state.append(c)
        candidates.remove(c)

    return state

def neighbour(s):
    """ Generates a new state that is in the "neighboorhood" of the state
    given in entry. This state is generated at random."""

    candidate_indexes = range(len(s))

    n = s[:]
    i1 = random.choice(candidate_indexes)
    candidate_indexes.remove(i1)


    i2 = random.choice(candidate_indexes)

    n[i1], n[i2] = n[i2], n[i1]
    return n


def cost_function(problem, state):
    """ Evaluates the cost of a state for a given problem."""

    cost = 0
    w = compute_wait_time(problem, state)

    cost = dot_product(problem.salaries, w)
    return cost


def dot_product(v1, v2):
    """ Computes the dot product of two vectors. """

    l = min(len(v1), len(v2))
    value = 0
    for i in range(l):
        value += v1[i] * v2[i]

    return value

def compute_wait_time(problem, state):
    """ Computes the total "worked" time for each solists given a solution and
    a particular problem. """

    # compute the wait matrix (for each candidate for each piece, 1 == waiting
    # and 0 == no waiting).
    wait_matrix = []
    row = [0] * problem.nbr_pieces
    w = [0] * problem.nbr_solists
    last_needed = [0] * problem.nbr_solists
    first_needed = [0] * problem.nbr_solists

    # initialize the wait matrix.
    for i in range(problem.nbr_solists):
        wait_matrix.append(row[:])


    # compute first needed.
    for i in range(problem.nbr_solists):
        index = 0
        for j in range(problem.nbr_pieces):
            index_piece = state[j]
            if problem.need_matrix[i][index_piece] == 1:
                index = j
                break

        first_needed[i] = index

    # compute last needed index.
    for i in range(problem.nbr_solists):
        index = 0
        for j in range(problem.nbr_pieces):
            index_piece = state[j]
            if problem.need_matrix[i][index_piece] == 1:
                index = j

        last_needed[i] = index

    # compute the wait matrix.
    for i in range(problem.nbr_solists):
        for j in range(problem.nbr_pieces):
            index_piece = state[j]
            if (problem.need_matrix[i][index_piece] == 0) and\
                    (j > first_needed[i]) and (j < last_needed[i]):
                wait_matrix[i][index_piece] = 1

    # compute the final wait vector.
    for i in range(problem.nbr_solists):
        w[i] = dot_product(wait_matrix[i], problem.pieces_length)

    return w

class Problem:
    """ Represents a problem instance: the number of pieces to be played,
    the wage of musicians, the lenght of a piece and a 0-1 matrix representing
    weither or not a musician is needed for a given piece."""

    def __init__(self):
        self.nbr_pieces = 0
        self.nbr_solists = 0
        self.need_matrix = []
        self.pieces_length = []
        self.salaries = []

        return

    def read_from_file(self, filename):
        """ Read a problem instance from a file."""

        try:
            f = open(filename, 'r')
        except IOError:
            print "could not read problem file"
            exit(-1)

        l = f.readline().strip()

        nbr_values = l.split()
        self.nbr_solists = int(nbr_values[0])
        self.nbr_pieces = int(nbr_values[1])

        for i in range(self.nbr_solists):
            l = f.readline().strip().split()
            self.salaries.append(int(l[-1]))
            del(l[-1])
            self.need_matrix.append([int(i) for i in l])

        l = f.readline().strip().split()
        self.pieces_length.extend([int(i) for i in l])

        f.close()
        return

    def __str__(self):
        s = [
                "number of solists: %d" % self.nbr_solists,
                "number of pieces: %d" % self.nbr_pieces,
                "need matrix: %s" % "\n".join([
                    str(i) for i in self.need_matrix]),
                "salaries: %s" % str(self.salaries),
                "pieces length: %s" %str(self.pieces_length)
                ]

        return "\n".join(s)

def progress(width, percent):
    """ Prints a progress bar on std out."""
    marks = math.floor(width * (percent / 100.0))
    spaces = math.floor(width - marks)
    
    loader = '[' + ('=' * int(marks)) +'>' + (' ' * int(spaces-1) ) + ']'
      
    sys.stdout.write(colored("%s %d%%\r",'blue') % (loader, percent))
    if percent >= 100:
        sys.stdout.write("\n")
    sys.stdout.flush()

if __name__ == "__main__":
    main()

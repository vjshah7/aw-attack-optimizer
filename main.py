#!/usr/bin/env python3

from ortools.sat.python import cp_model


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        for ind in range(len(self.__variables)):
            print("Queen {}: {},{}".format(ind, self.Value(self.__variables[ind]), ind))

        print()

    def solution_count(self):
        return self.__solution_count


'''
1. A "character" is an integer, lower bound 0, upper bound is variable but around 250.
2. There are 10 "rosters" of characters. A character can exist in multiple rosters. Each roster can only have one of a 
given character. e.g.: 
legal: roster 1 has characters 2,3,4, roster 2 has characters 4,5,6. 
illegal: roster 1 has characters 2,2,3
3. A "target" is an integer in the range 0-1MM (1,048,576)
4. 50 "targets" are specified. All targets are unique.
5. The 50 targets each belong to one of a small number (~15) of "target groups" of size 1-4. Each target exists in one 
and only one target group. Each target group has a sequence number. Multiple target groups may have the same sequence 
number. A target group may optionally also have a “side” number.
e.g.:
target group 1: targets 20230, 12311, seq number 1
target group 2: targets 23353, 354623, seq number 1
target group 3: targets 2342341, seq number 2, side number 1
target group 4: targets 14343, seq number 3, side number 2
target group 5: targets 83282, seq number 4, side number 1
6. There are 10 "character groups" with a 1 to 1 mapping to the 10 rosters. Each character group has a fixed 
size of 3. A character group can only consist of characters from its corresponding roster. A character group cannot 
have duplicate characters. Multiple character groups can have the same character, if the corresponding rosters all have 
that character.
7. Every target must be assigned a character from a character group. Different targets can be assigned the same character
from the same character group. Any target group must have all of its characters assigned from the same character group.
Characters from a character group cannot be assigned to multiple targets belonging to different target groups if those
target groups have the same sequence number. If a target group has a side number, then characters from a character 
group assigned to targets in that target group cannot be assigned to any targets in another target group with a
different side number.
8. "Effectiveness" is an integer between 0-100. There is a function that will return the effectiveness of a 
character and target combination. i.e.:
int effectiveness(int target, int character);
9. Objective: maximize the sum of the effectiveness values for character/target assignments.
'''

model = cp_model.CpModel()
board_size = 8

# model/constraints:
# a piece's place on a chessboard can be specified by a row (x) coordinate and a column (y) coordinate.
# in order to simplify the model, the number of each queen identifies its column, as we know each queen must
# be in different columns. the value for each queen will repesent the row.
# coordinates must always be between 1 and <board_size> inclusive

queens = list()
for ii in range(1, board_size + 1):
    queens.append(model.NewIntVar(1, board_size, "Q{}-X".format(ii)))

model.AddAllDifferent(queens)

# no two queens can be on the same diagonal... trickier constraint
# observation - if 2 queens are in the same '\' line, then their x&y coordinates are different by the same constant.
# e.g. (3,2) and (5,4) are in the same '\' diagonal... 5-3=2 and 4-2=2. we can capture this constraint by saying that
# no two queen coordinate pairs can have the same (y-x) value.
# if two queens are in the same '/' line, then as you traverse up and to the right along the diagonal, the x coordinate
# gets incremented by one and the y coordinate gets decremented by one, therefore, the sum of the x & y coordinates
# stay constant along the diagonal. the sum of x&y coordinates is also distinct on every diagonal.
diag_ul_lr = list()
diag_ll_ur = list()
for ii in range(board_size):
    derived_value_1 = model.NewIntVar(-board_size, board_size, "diag_ul_lr_{}".format(ii))
    model.Add(derived_value_1 == queens[ii] - ii)
    diag_ul_lr.append(derived_value_1)
    derived_value_2 = model.NewIntVar(0, 2 * board_size, "diag_ll_ur_{}".format(ii))
    model.Add(derived_value_2 == queens[ii] + ii)
    diag_ll_ur.append(derived_value_2)

model.AddAllDifferent(diag_ul_lr)
model.AddAllDifferent(diag_ll_ur)

# model.AddAllDifferent(queens[ii] + ii for ii in range(board_size))
# model.AddAllDifferent(queens[ii] - ii for ii in range(board_size))

solver = cp_model.CpSolver()
printer = SolutionPrinter(queens)
solver.parameters.enumerate_all_solutions = True
status = solver.Solve(model, printer)

print("status: {}, num solutions: {}, time: {} ms"
      .format(solver.StatusName(status), printer.solution_count(), solver.WallTime()))

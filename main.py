#!/usr/bin/env python3
from typing import Any
import itertools
import AWConfig
import DefenseConfig
import DefenderCounterConfig
import RosterSet

from ortools.sat.python import cp_model

'''
1. A "CHAMPION" is an integer, lower bound 1, upper bound is not permanently fixed but around 250.
2. 10 "ROSTERS" of champions are specified. A roster must have at least 3 champions. The same champion can exist in 
 multiple rosters. Each roster can only have one of a given champion. e.g.: 
 legal: roster 1 has champions 2,3,4,5. roster 2 has champions 4,5,6. 
 illegal: roster 1 has champions 2,2,3
3. There are 10 "TEAMS" with a 1 to 1 mapping to the 10 rosters. Each team has exactly 3 champions assigned. 
 A team can only consist of champions from its corresponding roster. A team cannot have duplicate champions. Different
 teams can have the same champion, if the corresponding rosters all have that champion.
4. The purpose of the teams/champions is to attack "DEFENDERS". Defenders are a concept that is not directly modeled.
 Following are descriptions of other concepts associated with defenders that are modeled.
5. 50 defenders are specified. All defenders are unique.
6. Each defender is associated with a set of up to 5 unique specified champions, called "VALID COUNTERS".
7. The 50 defenders each belong to one of a small number (~15) of "DEFENSE GROUPS" of size 1-4. Each defender exists in
 one and only one defense group. Each defense group has a sequence number. Multiple defense groups may have the same 
 sequence number. A defense group may optionally also have a “side” number.
8. Every defender is associated with an attacking team and an attacking champion. The attacking team
 must be one of the 10 teams described above. The attacking champion must be one of the 3 champions on that team.
 The attacking champion must be equal to one of the valid counters for the defender. A champion may be assigned as the
 attacker for more than one defender.
9. Defenders in different defense groups with the same sequence number cannot be assigned the same attacking team. 
 For any 2 defense groups with specified, distinct side numbers: the assigned attacking team for the defenders in one 
 defense group cannot be the same as the assigned attacking team for defenders in the other defense group.
'''

aw_config = AWConfig.AWConfig(250)
all_champions = aw_config.get_all_champions()
num_rosters = aw_config.get_num_rosters()

defense_config = DefenseConfig.load_defense_config_from_file('dc-2.json')
roster_set = RosterSet.load_roster_set_from_file('rosterset-1.json')
roster_ids = roster_set.get_all_roster_ids()
counter_config = DefenderCounterConfig.load_counters_from_file('defendercounter-1.json')

model = cp_model.CpModel()

# construct teams, with constraints on only allowing champs from the respective roster and ensuring all 3 team members
#  are different
teams = list()
for ii in range(num_rosters):
    team_champs = list()
    for jj in range(aw_config.get_team_size()):
        team_champs.append(model.NewIntVar(1, max(all_champions), "team{}-spot{}".format(ii, jj)))
    for champ in team_champs:
        roster_champs = roster_set.get_roster(ii)
        model.AddAllowedAssignments([champ], list((x,) for x in roster_champs))
    # TODO eventually support different rarities. for now, all champs must be unique
    model.AddAllDifferent(team_champs)
    teams.append(team_champs)

# attacker/team assignments for defenders, along with valid counter constraints
defender_assignments: dict[Any, Any] = {}
section_names = defense_config.get_all_sections()
for section_name in section_names:
    section = defense_config.get_section(section_name)
    for node in section.get_nodes():
        defender_assignments[node] = {}
        defender_assignments[node]['attacker'] = model.NewIntVar(1, max(all_champions), "{}-node{}-att"
                                                                 .format(section_name, node))
        counters = counter_config.get_node_counters(node)
        model.AddAllowedAssignments([defender_assignments[node]['attacker']],
                                    list((x,) for x in counters))
        defender_assignments[node]['team'] = model.NewIntVar(0, num_rosters - 1,
                                                             "{}-node{}-team".format(section_name, node))

# DEFENSE GROUP TEAM ASSIGNMENT CONSISTENCY CHECKS
# bools to tell if each defender in a group is assigned to a particular team
defender_team_ass_checks: dict[Any, Any] = {}
for section_name in section_names:
    section = defense_config.get_section(section_name)
    defender_team_ass_checks[section_name] = {}
    for node in section.get_nodes():
        defender_team_ass_checks[section_name][node] = {}
        for team in range(num_rosters):
            defender_team_ass_checks[section_name][node][team] = model.NewBoolVar("{} node {} assigned to team {}?"
                                                                                  .format(section_name, node, team))
            model.Add(defender_assignments[node]['team'] == team) \
                .OnlyEnforceIf(defender_team_ass_checks[section_name][node][team])
            model.Add(defender_assignments[node]['team'] != team) \
                .OnlyEnforceIf(defender_team_ass_checks[section_name][node][team].Not())
# all defenders in a group must be assigned to the same team. so the defender team assignment bools should
#  either be all true or all false for every node in a dg
for dg in list(defense_config.keys()):
    for team in range(num_rosters):
        for ii in range(len(defense_config[dg]['nodes']) - 1):
            node1 = defense_config[dg]['nodes'][ii]
            node2 = defense_config[dg]['nodes'][ii + 1]
            model.Add(defender_team_ass_checks[dg][node1][team] == defender_team_ass_checks[dg][node2][team])
# master bools to tell whether an entire def group is assigned to a particular team
dg_team_ass_checks: dict[Any, Any] = {}
for dg in list(defense_config.keys()):
    dg_team_ass_checks[dg] = {}
    for team in range(num_rosters):
        dg_team_ass_checks[dg][team] = model.NewBoolVar("{} all def assigned to team {}?".format(dg, team))
        model.AddBoolAnd(list(defender_team_ass_checks[dg][node][team] for node in defense_config[dg]['nodes'])) \
            .OnlyEnforceIf(dg_team_ass_checks[dg][team])
        model.AddBoolAnd(list(defender_team_ass_checks[dg][node][team].Not() for node in defense_config[dg]['nodes'])) \
            .OnlyEnforceIf(dg_team_ass_checks[dg][team].Not())
# a defense group cannot be assigned to multiple teams. iow for each defense group, exactly 1 of the team assignment
#  check bools defined above will be true. so for each team, we check that if the team assignment check for the dg
#  is true, then the other 9 team assignment checks are all false
for dg in list(defense_config.keys()):
    # at least one of the team assignment checks is true for the dg
    model.AddBoolOr(list(dg_team_ass_checks[dg][team] for team in range(num_rosters)))
    teams_lst = list(dg_team_ass_checks[dg].keys())
    for ii in range(len(teams_lst)):
        # if this team's assignment check for the dg is true, all others are false
        cur_team_ass_check = dg_team_ass_checks[dg][teams_lst[ii]]
        other_teams_ass_check_lst = teams_lst[:ii] + teams_lst[ii + 1:]
        model.AddBoolAnd(list(dg_team_ass_checks[dg][team].Not() for team in other_teams_ass_check_lst)) \
            .OnlyEnforceIf(cur_team_ass_check)

# ATTACKER ASSIGNMENT/TEAM MEMBERSHIP consistency checks
att_team_ass_checks: dict[Any, Any] = {}
for dg in list(defense_config.keys()):
    att_team_ass_checks[dg] = {}
    for node in defense_config[dg]['nodes']:
        att_team_ass_checks[dg][node] = {}
        for team in range(num_rosters):
            att_team_ass_checks[dg][node][team] = {}
            for slot in range(team_size):
                # check if attacker assignment for a defender in a particular group matches a particular team member
                att_team_ass_checks[dg][node][team][slot] = \
                    model.NewBoolVar("{} node {} attacker matches team {} slot {}?"
                                     .format(dg, node, team, slot))
                model.Add(defender_assignments[node]['attacker'] == teams[team][slot]) \
                    .OnlyEnforceIf(att_team_ass_checks[dg][node][team][slot])
                model.Add(defender_assignments[node]['attacker'] != teams[team][slot]) \
                    .OnlyEnforceIf(att_team_ass_checks[dg][node][team][slot].Not())
            # an attacker assignment must match one of the attackers on team x if team x was assigned
            model.AddBoolOr(list(att_team_ass_checks[dg][node][team][slot] for slot in range(team_size))) \
                .OnlyEnforceIf(defender_team_ass_checks[dg][node][team])
            # NO constraint for the inverse, because the same champ can be on multiple teams, so we could
            #  have a assigned attacker match a member on team x even if team x is not assigned

# sequence number constraints
dgs_by_seq_num: dict[Any, Any] = {}
for dg in list(defense_config.keys()):
    seq_num = defense_config[dg]['sequence_num']
    if seq_num in dgs_by_seq_num:
        dgs_by_seq_num[seq_num].append(dg)
    else:
        dgs_by_seq_num[seq_num] = [dg]
for seq_num in dgs_by_seq_num:
    # the same team cannot be assigned to any 2 defense groups with the same sequence number
    # we don't have a var for the team assigned to a defense group, but because of other constraints, we can
    #  just use the team assigned to the first node in a defense group to represent the group assignment
    dg_first_nodes = list(defense_config[dg]['nodes'][0] for dg in dgs_by_seq_num[seq_num])
    model.AddAllDifferent(list(defender_assignments[node]['team'] for node in dg_first_nodes))

# # side number constraints
# dgs_by_side_num: dict[Any, Any] = {}
# for dg in list(defense_config.keys()):
#     side_num = defense_config[dg]['side_num']
#     if side_num >= 0:
#         if side_num in dgs_by_side_num:
#             dgs_by_side_num[side_num].append(dg)
#         else:
#             dgs_by_side_num[side_num] = [dg]
# side_num_lst = list(dgs_by_side_num.keys())
# # a team cannot be assigned to any 2 defense groups with different side numbers
# #  go through the first n-1 elements of the dgs_by_side_num key list and set up inequalities for the team assignment
# #  between the "current" dg and each dg from the following side numbers
# for ii in range(len(side_num_lst) - 1):
#     cur_dgs = dgs_by_side_num[side_num_lst[ii]]
#     remaining_side_nums_lst = side_num_lst[ii+1:]
#     remaining_dgs_2d = list(dgs_by_side_num[side_num] for side_num in remaining_side_nums_lst)
#     remaining_dgs = list(itertools.chain(*remaining_dgs_2d))
#     print("cur dgs: {}, remaining dgs: {}".format(cur_dgs, remaining_dgs))
#     remaining_dgs_first_nodes = list(defense_config[dg]['nodes'][0] for dg in remaining_dgs)
#     for dg in cur_dgs:
#         first_node = defense_config[dg]['nodes'][0]
#         for remaining_dg_first_node in remaining_dgs_first_nodes:
#             # we don't have a var for the team assigned to a defense group, but because of other constraints, we can
#             #  just use the team assigned to the first node in a defense group to represent the group assignment
#             model.Add(defender_assignments[first_node]['team'] != defender_assignments[remaining_dg_first_node]['team'])

# SOLVER
solver = cp_model.CpSolver()
# solver.parameters.enumerate_all_solutions = True
status = solver.Solve(model)

print("status: {}, time: {} s"
      .format(solver.StatusName(status), solver.WallTime()))
if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
    for team_num in range(len(teams)):
        print("team {}:".format(team_num))
        for slot in teams[team_num]:
            print("\t{}"
                  .format(solver.Value(slot)))
    print("")

    for dg in defense_config:
        print("dg {}:".format(dg))
        for node in defense_config[dg]['nodes']:
            print("\tnode {}: team {}, attacker {}".format(node,
                                                           solver.Value(defender_assignments[node]['team']),
                                                           solver.Value(defender_assignments[node]['attacker'])))

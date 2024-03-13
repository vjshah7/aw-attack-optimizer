#!/usr/bin/env python3

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
7. The 50 defenders each belong to one of a small number (~15) of "DEFENSE SECTIONS" of size 1-4. Each defender exists
 in one and only one defense section. Each defense section has a sequence number. Multiple defense sections may have the 
 same sequence number. A defense section may optionally also have a “side” number.
8. Every defender is associated with an attacking team and an attacking champion. The attacking team
 must be one of the 10 teams described above. The attacking champion must be one of the 3 champions on that team.
 The attacking champion must be equal to one of the valid counters for the defender. A champion may be assigned as the
 attacker for more than one defender.
9. Defenders in different defense sections with the same sequence number cannot be assigned the same attacking team. 
 For any 2 defense sections with specified, distinct side numbers: the assigned attacking team for the defenders in one 
 defense section cannot be the same as the assigned attacking team for defenders in the other defense section.
'''

aw_config = AWConfig.AWConfig(250)
all_champions = aw_config.get_all_champions()
num_rosters = aw_config.get_num_rosters()
team_size = aw_config.get_team_size()

defense_config = DefenseConfig.load_defense_config_from_file('dc-2.json')
roster_set = RosterSet.load_roster_set_from_file('rosterset-1.json')
roster_ids = roster_set.get_all_roster_ids()
counter_config = DefenderCounterConfig.load_counters_from_file('defendercounter-1.json')

model = cp_model.CpModel()

# construct teams, with constraints on only allowing champs from the respective roster and ensuring all 3 team members
#  are different
teams = list()
for roster_id in roster_ids:
    team_champs = list()
    for jj in range(team_size):
        team_champs.append(model.NewIntVar(1, max(all_champions), "team {} - slot {}".format(roster_id, jj)))
    for champ in team_champs:
        roster_champs = roster_set.get_roster(roster_id)
        model.AddAllowedAssignments([champ], list((x,) for x in roster_champs))
    # TODO eventually support different rarities. for now, all champs must be unique
    model.AddAllDifferent(team_champs)
    teams.append(team_champs)

# attacker/team assignments for defenders, along with valid counter constraints
defender_assignments: dict[int, dict[str, cp_model.IntVar]] = {}
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
# bools to tell if each defender in a section is assigned to a particular team
defender_team_ass_checks: dict[str, dict[int, dict[int, cp_model.IntVar]]] = {}
for section_name in section_names:
    section = defense_config.get_section(section_name)
    defender_team_ass_checks[section_name] = {}
    for node in section.get_nodes():
        defender_team_ass_checks[section_name][node] = {}
        for roster_id in roster_ids:
            defender_team_ass_checks[section_name][node][roster_id] = model.NewBoolVar("{} node {} assigned to team {}?"
                                                                                       .format(section_name, node,
                                                                                               roster_id))
            model.Add(defender_assignments[node]['team'] == roster_id) \
                .OnlyEnforceIf(defender_team_ass_checks[section_name][node][roster_id])
            model.Add(defender_assignments[node]['team'] != roster_id) \
                .OnlyEnforceIf(defender_team_ass_checks[section_name][node][roster_id].Not())
# broader bools ("SRAC"s) to tell if any defender in a section is assigned to a particular team
section_roster_ass_checks: dict[str, dict[int, cp_model.IntVar]] = {}
for section_name in section_names:
    section_nodes = defense_config.get_section(section_name).get_nodes()
    section_roster_ass_checks[section_name] = {}
    for roster_id in roster_ids:
        section_roster_ass_checks[section_name][roster_id] = model.NewBoolVar("team {} traveling to {}?"
                                                                              .format(roster_id, section_name))
        model.AddBoolOr(list(defender_team_ass_checks[section_name][node][roster_id] for node in section_nodes)) \
            .OnlyEnforceIf(section_roster_ass_checks[section_name][roster_id])
        model.AddBoolAnd(list(defender_team_ass_checks[section_name][node][roster_id].Not()
                              for node in section_nodes)) \
            .OnlyEnforceIf(section_roster_ass_checks[section_name][roster_id].Not())

# ATTACKER ASSIGNMENT/TEAM MEMBERSHIP consistency checks
att_roster_ass_checks: dict[str, dict[int, dict[int, dict[int, cp_model.IntVar]]]] = {}
for section_name in section_names:
    section = defense_config.get_section(section_name)
    att_roster_ass_checks[section_name] = {}
    for node in section.get_nodes():
        att_roster_ass_checks[section_name][node] = {}
        for roster_id in roster_ids:
            att_roster_ass_checks[section_name][node][roster_id] = {}
            for slot in range(team_size):
                # check if attacker assignment for a defender in a particular section matches a particular team member
                att_roster_ass_checks[section_name][node][roster_id][slot] = \
                    model.NewBoolVar("{} node {} attacker matches team {} slot {}?"
                                     .format(section_name, node, roster_id, slot))
                model.Add(defender_assignments[node]['attacker'] == teams[roster_id][slot]) \
                    .OnlyEnforceIf(att_roster_ass_checks[section_name][node][roster_id][slot])
                # NO constraint for the inverse, because the same champ can be on multiple teams, so it's ok to have
                # an assigned attacked match a member on team x even if team x is not assigned
            # an attacker assignment must match one of the attackers on team x if team x was assigned
            model.AddBoolOr(list(att_roster_ass_checks[section_name][node][roster_id][slot]
                                 for slot in range(team_size))) \
                .OnlyEnforceIf(defender_team_ass_checks[section_name][node][roster_id])
            # NO constraint for the inverse, because the same champ can be on multiple teams, so we could
            #  have a assigned attacker match a member on team x even if team x is not assigned

# sequence number constraints
sections_by_seq_num: dict[int, list] = {}
for section_name in section_names:
    seq_num = defense_config.get_section(section_name).get_sequence_num()
    if seq_num in sections_by_seq_num:
        sections_by_seq_num[seq_num].append(section_name)
    else:
        sections_by_seq_num[seq_num] = [section_name]
# the same team cannot be assigned to any 2 nodes in different defense groups with the same sequence number
for seq_num in sections_by_seq_num:
    seq_sections = sections_by_seq_num[seq_num]
    num_sections = len(seq_sections)
    # if we look at the set of the section team assignments checks for this team, for all sections with this sequence
    #  number - at most 1 of the check vars can be true.
    for roster_id in roster_ids:
        # assemble the set of section roster assignment checks for this team for all sections with this seq number
        srac_bools = list(section_roster_ass_checks[section_name][roster_id] for section_name in seq_sections)
        # cp model bool var is just an int var that can only be 0 or 1
        # create a tuple of the form (1, 0, 0, ...), where the number of 0s ("False"s) is 1 less than the number of
        #  sections
        base_rep_single_true = tuple(x for x in [1] + [0] * (num_sections - 1))
        # use itertools to create all permutations of that tuple (eg (1, 0, 0, ...), (0, 1, 0, ...), (0, 0, 1, ...),
        #  ...)
        # put into a set and then back into a list to remove dupes
        all_perms = list(set(itertools.permutations(base_rep_single_true)))
        # enforce that at most one assignment can be true for this team for sections in this seq num. need to add on
        #  the case of all false (this team is not assigned to any sections in this seq number)
        model.AddAllowedAssignments(srac_bools, all_perms + [tuple(x for x in [0] * num_sections)])

# side number constraints
sections_by_side_num: dict[int, list] = {}
for section_name in section_names:
    side_num = defense_config.get_section(section_name).get_side_num()
    if DefenseConfig.is_valid_side_num(side_num):
        if side_num in sections_by_side_num:
            sections_by_side_num[side_num].append(section_name)
        else:
            sections_by_side_num[side_num] = [section_name]
side_num_lst = list(sections_by_side_num.keys())
# a team cannot be assigned to any 2 defense sections with different side numbers
#  go through the first n-1 elements of the sections_by_side_num key list and make sure no assignments exist for each
#  team for each section from the remaining side numbers if there is an assigment for that team in a section in the
#  "current" side num
for ii in range(len(side_num_lst) - 1):
    cur_sections = sections_by_side_num[side_num_lst[ii]]
    remaining_side_nums_lst = side_num_lst[ii + 1:]
    remaining_sections_2d = list(sections_by_side_num[side_num] for side_num in remaining_side_nums_lst)
    remaining_sections = list(itertools.chain(*remaining_sections_2d))
    print("sections in side num {}: {}, sections in other side nums: {}"
          .format(side_num_lst[ii], cur_sections, remaining_sections))
    for roster_id in roster_ids:
        remaining_sections_srac_bools = list(section_roster_ass_checks[section_name][roster_id]
                                             for section_name in remaining_sections)
        for section_name in cur_sections:
            model.AddBoolAnd(list(x.Not() for x in remaining_sections_srac_bools)) \
                .OnlyEnforceIf(section_roster_ass_checks[section_name][roster_id])

# SOLVER
solver = cp_model.CpSolver()
# solver.parameters.enumerate_all_solutions = True
status = solver.Solve(model)

print("status: {}, time: {} s"
      .format(solver.StatusName(status), solver.WallTime()))
if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
    for ii in range(len(roster_ids)):
        print("team {}:".format(roster_ids[ii]))
        for slot in teams[ii]:
            print("\t{}"
                  .format(solver.Value(slot)))
    print("")

    for section_name in section_names:
        print("section {}:".format(section_name))
        for node in defense_config.get_section(section_name).get_nodes():
            print("\tnode {}: team {}, attacker {}".format(node,
                                                           solver.Value(defender_assignments[node]['team']),
                                                           solver.Value(defender_assignments[node]['attacker'])))

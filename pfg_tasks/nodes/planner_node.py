#!/usr/bin/env python

"""
planner_node.py - Version 0.7 2015-04-13

Executes a robot using behaviour trees and a HTN planner

Copyright (c) 2015 Jose Angel Segura Muros.  All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""


from __future__ import print_function

import rospy

from pyhop import hop
from user_files.factory_methods import *
from user_files.factory_operators import *
from pi_trees_lib.pi_trees_lib import *
#from pfg_tasks.task_setup import * 
from pfg_tasks import global_vars
from user_files.robot_config import *
from pfg_tasks.core_tasks import *




def makeRutines():
	rutines = Sequence("routines")
	for i in range(len(global_vars.black_board.routinesList)):
		rutines.add_child(global_vars.black_board.routinesList[i])

	return rutines

		
def makeTree(plan):

	tree = Sequence("Tree")

	tree.add_child(makeRutines())

	execPlan = Sequence("execPlan")

	lastPlace = "storehouse"

	for i in range(len(plan)):
		if plan[i][0] == global_vars.black_board.movementTask:
			coord = global_vars.black_board.getCoords(plan[i][1])
			execPlan.add_child(goToTask("MoveToTask: " + plan[i][1], coord))
			lastPlace = plan[i][1]
			
		else:
			task = global_vars.black_board.getTask(plan[i][0])
			if task != False:
					
				coords = global_vars.black_board.getCoords(lastPlace)
				moveToLasPositionTask = goToTask("MoveToTaskLastPosition: " + lastPlace, coords)
				checkLocationTask = CheckLocation(lastPlace)

				NavigationTask = Selector("NavRoutine", [checkLocationTask, moveToLasPositionTask])

				execPlan.add_child(Sequence("Task "+ plan[i][0], [NavigationTask, task]))
		
	tree.add_child(execPlan)


	return tree


def runRobot():
 	"""Runs the robot

 	Initializes all the variables needed for the application, calls for a plan,
 	makes the behaviour tree and runs it.
 	"""
 	#Initialize the first state of the problem
	state = hop.State('state')
	state.types={'piece1':'type1'}
	state.position={'piece1':'storehouse', 'robot':'storehouse'}
	state.ocupied={'robot':False, 'workstation1':False}
	state.stationAcepts={'workstation1':'type1'}
	state.stationProduces={'workstation1':'type2'}

	#Initialize the goal state of the problem
	goal = hop.Goal('goal')
	goal.types={'piece1':'type2'}
	goal.position={'piece1':'storehouse', 'robot':'storehouse'}
	goal.ocupied={'robot':False, 'workstation1':False}


	#Calculates the plan for the given state and goal
	plan = hop.plan(state,[('work', goal)], hop.get_operators(), 
		hop.get_methods(), verbose=0)

	print('** result =',plan,'\n')
	
	#Launchs the ros node, and set it the shutdown function
	rospy.init_node("planner_node", anonymous=False)

	rospy.on_shutdown(shutdown)

	#Initializes the simulator 
	#setup_task_environment(self)

	#Sets the Global variables and the user defined robot configuration
	global_vars.init()
	getConfig()

	#Computes the behaviour tree
	Tree = makeTree(plan)
	print_tree(Tree)

	#Runs the tree
	while not rospy.is_shutdown():
		Tree.run()
		rospy.sleep(0.1)


def shutdown():
	"""Shutdown function for rospy

	Cancels all the goals given to move_base, stops the robot
	"""
	rospy.loginfo("Stopping the robot...")
	self.move_base.cancel_all_goals()

	self.cmd_vel_pub.publish(Twist())

	rospy.sleep(1)


if __name__ == '__main__':
	"""Main funcion of the node
	
	"""
    try:
        runRobot()
    except rospy.ROSInterruptException:
        rospy.loginfo("Robot running finished.")
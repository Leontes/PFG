#!/usr/bin/env python

"""
planner_node.py - Version 1.0 2015-04-14

Creates a behaviour tree from a plan given by a HTN planner, 
and executes it

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
import copy

from pyhop import hop
from parserlib import parser
from pi_trees_lib.pi_trees_lib import *
from description.enviroment_setup import * 
from tasks import global_vars
from user_files.robot_config import *
from tasks.core_tasks import *
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from atp_msgs.srv import *

		
def makeTree(plan, initialState):
	""" Creates a behaviour tree from a list of routines and a plan

	Keyword arguments:
	plan -- Plan sequence of task generated by the HTN planner
	"""

	#The initial node of the behaviour tree
	tree = Sequence("Tree")

	#Added the routines from the black board
	tree.add_child(global_vars.black_board.makeRoutines())

	#The node of the plan
	planTask = Sequence("Plan")

	#Initialize the first place where the robot starts
	lastPlace = global_vars.black_board.getRobotOrigin()

	#Set all the posible tasks in the black board to be executed
	global_vars.black_board.taskDone = [False for i in range(len(plan))]

	state = copy.deepcopy(initialState)

	#For every task in the plan...
	for i in range(len(plan)):
		#If the task is the movement task
		if plan[i][0] == global_vars.black_board.movementTask:
			coord = global_vars.black_board.getCoords(plan[i]
				[global_vars.black_board.destArg])
			if coord != False:
				#Creates a super node to hold the task 
				actionTask = Sequence("Action " + str(i+1))

				function = hop.operators[plan[i][0]]

				#Creates a movement task and adds it to the actionTask 
				#with the corresponding setDoneTask
				actionTask.add_child(goToTask("MoveToTask: " + 
					plan[i][global_vars.black_board.destArg], coord))
				actionTask.add_child(setDoneTask("SetDoneTask "+ str(i+1), i, 
					function, plan[i][1:]))

				#Updates the robot position
				lastPlace = plan[i][2]

				checkDone = checkDoneTask("CheckDoneTask "+ str(i+1), i, copy.deepcopy(state))
				#Adds a node that first checks if the task has been executed, 
				#and if not executes it
				planTask.add_child(Selector("Task "+ plan[i][0], [checkDone, actionTask]))
				state = function(copy.deepcopy(state), *plan[i][1:])


			else:
				raise ValueError("Place not defined in the black board")
			
		#If not is the movement task
		else:
			#Request the executable task to the black board
			task = global_vars.black_board.getTask(plan[i][0])
			if task != False:

				#Creates a super node to hold the task 
				actionTask = Sequence("Action " + str(i+1))

				function = hop.operators[plan[i][0]]

				#Adds the task and his setDoneTask to the actionTask
				actionTask.add_child(task)
				actionTask.add_child(setDoneTask("SetDoneTask "+ str(i+1), i, 
					function, plan[i][1:]))

				#Subroutine to check the robots position and returns to the work place
				coords = global_vars.black_board.getCoords(lastPlace)
				if coords != False:

					checkLocation = checkLocationTask(lastPlace)
					moveToLasPositionTask = goToTask("MoveToTaskLastPosition: " + lastPlace, coords)

					#The subroutine first checks the location of the robot, and then if necesary moves it
					NavigationTask = Selector("NavSubroutine", [checkLocation, moveToLasPositionTask])

					#Creates a node with all the executable leaf nodes
					execTask = Sequence("Executable", [NavigationTask, actionTask])
				else:
					raise ValueError("Place not defined in the black board")
				

				checkDone = checkDoneTask("CheckDoneTask "+ str(i+1), i, copy.deepcopy(state))
				#Adds a node that first checks if the task has been executed, 
				#and if not executes it
				planTask.add_child(Selector("Task "+ plan[i][0], [checkDone, execTask]))
				state = function(copy.deepcopy(state), *plan[i][1:])
			else:
				raise ValueError("Task not defined in the black board")
	
	#Add the plan to the tree and returns it
	tree.add_child(planTask)
	global_vars.black_board.setReplan(False)

	return tree


def runRobot():
 	"""Runs the robot

 	Initializes all the variables needed for the application, calls for a plan,
 	makes the behaviour tree and runs it.
 	"""
	

	domain = parser.parse(sys.argv[1], sys.argv[2])

	hop.declare_operators(*(domain.taskList))
	for k in domain.methodList.keys():
			hop.declare_methods(k, domain.methodList[k])

	#Calculates the plan for the given state and goal
	plan = hop.plan(copy.deepcopy(domain.state),domain.getGoals(),
		hop.get_operators(),hop.get_methods(),verbose=0)

	if plan != None:

		print('PLAN =',plan,'\n')
		
		#Launchs the ros node, and set it the shutdown function
		rospy.init_node("planner_node", anonymous=False)

		rospy.on_shutdown(shutdown)

		#Sets the Global variables and the user defined robot configuration
		global_vars.init()

		getConfig()

		#Initializes the simulator 
		init_environment()

		initBattery = rospy.ServiceProxy("battery_simulator/set_battery_level", SetBatteryLevel)
		initBattery(100)


		#Computes the behaviour tree
		global_vars.black_board.setWorld(copy.deepcopy(domain.state))

		Tree = makeTree(plan, domain.state)
		print_tree(Tree)
		
		
		#Runs the tree
		while not rospy.is_shutdown() and global_vars.black_board.finished() == False:
			while not rospy.is_shutdown() and global_vars.black_board.finished() == False and global_vars.black_board.rePlanNeeded() == False:
				Tree.run()
				rospy.sleep(0.1)

			if global_vars.black_board.rePlanNeeded() == True:
				print ("Replanning...")
				global_vars.move_base.cancel_all_goals()
				global_vars.cmd_vel_pub.publish(Twist())
				
				plan = hop.plan(copy.deepcopy(global_vars.black_board.getWorld()),
					domain.getGoals(),hop.get_operators(),hop.get_methods(),verbose=0)
				if plan != None:
					print('** New plan =',plan,'\n')
					Tree = makeTree(plan, copy.deepcopy(global_vars.black_board.getWorld()))
					print_tree(Tree)
				else: 
					print("Empty plan generated")
					raise ValueError("Empty plan generated")

	else:
		print("Empty plan generated")
		raise ValueError("Empty plan generated")



def shutdown():
	"""Shutdown function for rospy

	Cancels all the goals given to move_base, stops the robot
	"""
	rospy.loginfo("Stopping the robot...")
	global_vars.move_base.cancel_all_goals()

	global_vars.cmd_vel_pub.publish(Twist())

	rospy.sleep(1)


if __name__ == '__main__':
	"""Main funcion of the node
	
	"""
	if len(sys.argv) < 3:
		print("Usage: rosrun pfg_tasks planner_node.py domain.pddl problem.pddl")
	else:
		try:
			runRobot()
		except ValueError, rospy.ROSInterruptException:
			rospy.loginfo("Robot running finished.")
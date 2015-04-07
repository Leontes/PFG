import rospy
from pi_trees_ros.pi_trees_ros import *
from move_base_msgs.msg import MoveBaseGoal, MoveBaseAction
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32
from pfg_msgs.srv import *



class pickUpTask(Task):
	"""docstring for pickUpTask"""
	def __init__(self, name, timer, *args):
		super(pickUpTask, self).__init__(name, children = None, *args)
		self.name = name
		self.timer = timer
		self.finished = False

		self.cmd_vel_pub = rospy.Publisher('cmd_vel',Twist, queue_size = 10)
		self.cmd_vel_msg = Twist()
		self.cmd_vel_msg.linear.x = 0
		self.cmd_vel_msg.angular.z = 1.5


	def run(self):
		if self.finished:
			return TaskStatus.SUCCESS
		else:

			self.cmd_vel_pub.publish(self.cmd_vel_msg)
			self.timer -= 1
			rospy.sleep(0.1)
			if(self.timer == 0):
				self.finished = True
				self.cmd_vel_pub.publish(Twist())
			return TaskStatus.RUNNING
			


class putDownTask(Task):
	"""docstring for pickUpTask"""
	def __init__(self, name, timer, *args):
		super(putDownTask, self).__init__(name, children = None, *args)
		self.name = name
		self.timer = timer
		self.finished = False

		self.cmd_vel_pub = rospy.Publisher('cmd_vel',Twist, queue_size = 10)
		self.cmd_vel_msg = Twist()
		self.cmd_vel_msg.linear.x = 0
		self.cmd_vel_msg.angular.z = -1.5


	def run(self):
		if self.finished:
			return TaskStatus.SUCCESS
		else:
			self.cmd_vel_pub.publish(self.cmd_vel_msg)
			self.timer -= 1
			rospy.sleep(0.1)
			if(self.timer == 0):
				self.finished = True
				self.cmd_vel_pub.publish(Twist())
			return TaskStatus.RUNNING


class sleepTask(Task):
	"""docstring for pickUpTask"""
	def __init__(self, name, timer, *args):
		super(sleepTask, self).__init__(name, children = None, *args)
		self.name = name
		self.sleep = timer
		self.finished = False


	def run(self):
		if self.sleep == 0:
			self.finished = True

		if self.finished:
			return TaskStatus.SUCCESS
		else:
			self.sleep -= 1
			rospy.sleep(1)
			return TaskStatus.RUNNING


class goToTask(SimpleActionTask):
	def __init__(self, name, coords):
		goal = MoveBaseGoal()
		goal.target_pose.header.frame_id = 'map'
		goal.target_pose.header.stamp = rospy.Time.now()
		goal.target_pose.pose = coords
		super(goToTask, self).__init__(name, "move_base", MoveBaseAction, goal, reset_after=False, feedback_cb=update_robot_position)

	def run(self):
		return super(goToTask, self).run()


class CheckLocation(Task):
    def __init__(self, place, *args, **kwargs):
        name = "checkLocation"
        super(CheckLocation, self).__init__(name)    
        self.name = name
        self.place = place

    def run(self):
        wp = black_board.getCoords(self.place)
        cp = black_board.getCoords("robot")
        
        distance = sqrt((wp.x - cp.x) * (wp.x - cp.x) +
                        (wp.y - cp.y) * (wp.y - cp.y) +
                        (wp.z - cp.z) * (wp.z - cp.z))
                                
        if distance < 0.15:
            status = TaskStatus.SUCCESS
        else:
            status = TaskStatus.FAILURE
            
        return status



''' Routines '''


low_battery_threshold = rospy.get_param('~low_battery_threshold', 50)

def check_battery(msg):
		if msg.data is None:
			return TaskStatus.RUNNING
		else:
			if msg.data < low_battery_threshold:
				rospy.loginfo("LOW BATTERY - level: " + str(int(msg.data)))
				return TaskStatus.FAILURE
			else:
				return TaskStatus.SUCCESS
    
	
def recharge_cb(result):
	rospy.loginfo("BATTERY CHARGED!")


def update_robot_position(msg):
	black_board.setCoords("robot", msg.base_position.pose.position.x, msg.base_position.pose.position.y)


def batteryRoutine(black_board):
	# The "stay healthy" rutine
	stayHealthyTask = Selector("stayHealthy")

	with stayHealthyTask:
		# Add the check battery condition (uses MonitorTask)
		checkBatteryTask = MonitorTask("checkBattery", "battery_level", Float32, check_battery)



		# Add the recharge task (uses ServiceTask)
		chargeRobotTask = ServiceTask("chargeRobot", "battery_simulator/set_battery_level", SetBatteryLevel, 100, result_cb=recharge_cb)

		# Add the movement routine to the dock
		coords = black_board.getCoords('dock')
		goal = MoveBaseGoal()
		goal.target_pose.header.frame_id = 'map'
		goal.target_pose.header.stamp = rospy.Time.now()
		goal.target_pose.pose = coords
		
		moveToDockTask = SimpleActionTask("MoveToDock", "move_base", MoveBaseAction, goal, reset_after=True,  feedback_cb=update_robot_position)
		checkLocationTask = CheckLocation("dock")

		NavigationTask = Selector("Nav", [checkLocationTask, moveToDockTask] )

		# Build the recharge sequence using inline syntax
		rechargeTask = Sequence("recharge", [NavigationTask, chargeRobotTask])



		# Add the check battery and recharge tasks to the stay healthy selector
		stayHealthyTask.add_child(checkBatteryTask)
		stayHealthyTask.add_child(rechargeTask)

	black_board.setRoutine(stayHealthyTask)
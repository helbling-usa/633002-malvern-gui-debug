
from config.motor_Linear import motor_Linear 
import time

# /*	Movement parameters	*/
position = -100000000	#	/* position command [drive internal position units, encoder counts] */
home_position = 1000	#	/* the homing position [drive internal position units, encoder counts] */
cap_position = 0		#	/* the position captures at HIGH-LOW transition of negative limit switch */
high_speed = 10	    	#	/* the homing travel speed [drive internal speed units, encoder counts/slow loop sampling]*/
low_speed = 1.0 		#	/* the homing brake speed [drive internal speed units, encoder counts/slow loop sampling] */
acceleration = 0.6		#/* acceleration rate [drive internal acceleration units, encoder counts/slow loop sampling^2] */



if __name__ == "__main__":

    AXIS_ID = 1    
    
    Larger_actutator= b"LEFS32"
    smaller_actuator= b"LEFS25"
    motor = motor_Linear(b"COM9", AXIS_ID, smaller_actuator)
    

    #/*	Setup and initialize the axis */	
    if (motor.InitAxis()==False):
        print("Failed to start up the drive")

    

    
    motor.homing()
    # motor.homing_ESM()





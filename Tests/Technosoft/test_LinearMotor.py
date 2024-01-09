
from config.motor_Linear import motor_Linear 
import time


if __name__ == "__main__":

    AXIS_ID = 1    
    
    Larger_actutator= b"LEFS32"
    smaller_actuator= b"LEFS25"
    motor = motor_Linear(b"COM9", AXIS_ID, smaller_actuator)
    

    #/*	Setup and initialize the axis */	
    if (motor.InitAxis()==False):
        print("Failed to start up the drive")


    # # print("---------get FM VER -------------------")
    # motor.get_firmware_version()

    print("----------set position-----------------")
    motor.set_position()

    # print("------------set int var ------------------------------")
    # motor.set_POSOKLIM(1)

    # # print("------------get int var ------------------------------")
    # motor.get_POSOKLIM()



    #print("----------MOVE Relative-----------------")
    speed = 1#15.0;		#/* jogging speed [drive internal speed units, encoder counts/slow loop sampling] */
    acceleration = 1.0#0.015;#/* acceleration rate [drive internal acceleration units, encoder counts/slow loop sampling^2] */
    rel_pos = -12000
    motor.move_relative_position(rel_pos, speed, acceleration)
    # motor.move_relative_position(rel_pos, speed, acceleration)

    # time.sleep(3)
    # speed = 30.0
    # rel_pos = -2000 # 5000/800 *6 = 0.0075*5000=3.25mm
    # motor.move_relative_position(rel_pos, speed, acceleration)

    # time.sleep(3)
    # abs_pos = 0
    # motor.move_absolute_position(abs_pos, speed, acceleration)


    print("------------Read actual position ------------------------------")

    time.sleep(1)
    p = motor.read_actual_position()
    print('actual position = {} '.format(p))

    p = motor.read_target_position()
    print('Target position = {} '.format(p))
    # print("------------get int var ------------------------------")
    # motor.get_POSOKLIM()

    motor.disable_motor()
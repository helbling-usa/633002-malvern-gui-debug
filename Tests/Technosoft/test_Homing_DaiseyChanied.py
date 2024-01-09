from ctypes import *
import time
from config.motor_2axes import motor_2axes as Motors



# mydll1 =CDLL("./config/TML_LIB.dll")
AXIS_ID_01 = 24     #mixer motor
AXIS_ID_02 = 1      #LEFS25
com_port = b"COM7"  #com prot for mixer controller 
primary_axis =  b"Mixer"    #mixer controller is the master controller


if __name__ == "__main__":

    m1 = Motors(com_port, AXIS_ID_01, AXIS_ID_02, primary_axis)
    

    #/*	Setup and initialize the axis */	
    if (m1.InitAxis()==False):
        print("Failed to start up the drive")


    m1.select_axis(AXIS_ID_02)
    m1.set_POSOKLIM(2)
    m1.homing(AXIS_ID_02)
    
    print("moving to 0 position")
    
    speed = 10.0
    acceleration = 1.0
    rel_pos = 0 # 5000/800 *6 = 0.0075*5000=3.25mm
    print("after homing, the limit switch position is set to:",m1.read_actual_position())
    
    m1.move_absolute_position(1000 , speed, acceleration)
    # m1.move_relative_position(1000 , speed, acceleration)
    time.sleep(3)
    # print("----------set position-----------------")
    tt = m1.read_actual_position()
    print('position is:{}'.format(tt))





    m1.close_port()
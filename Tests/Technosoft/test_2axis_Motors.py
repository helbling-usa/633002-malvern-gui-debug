from ctypes import *
import time
from config.motor_2axes import motor_2axes as Motors



# mydll1 =CDLL("./config/TML_LIB.dll")
AXIS_ID_01 = 24
AXIS_ID_02 = 1
com_port = b"COM7"
primary_axis =  b"Mixer"


if __name__ == "__main__":

    m1 = Motors(com_port, AXIS_ID_01, AXIS_ID_02, primary_axis)
    print("class:", type(m1))

    #/*	Setup and initialize the axis */	
    if (m1.InitAxis()==False):
        print("Failed to start up the drive")



    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    m1.select_axis(AXIS_ID_01)
    speed =3000
    acceleration = 1
    m1.set_speed(speed,acceleration)
    time.sleep(3)
    

    speed =0    
    m1.set_speed(speed,acceleration)
    time.sleep(3)

    
    m1.select_axis(AXIS_ID_02)

        # print("---------get FM VER -------------------")
    m1.get_firmware_version()

    # print("----------set position-----------------")
    m1.set_position()

    # print("------------set int var ------------------------------")
    m1.set_POSOKLIM(2)

    # # print("------------get int var ------------------------------")
    # m1.get_POSOKLIM()


    time.sleep(1)
    speed = 30.0
    rel_pos = -2000 # 5000/800 *6 = 0.0075*5000=3.25mm
    m1.move_relative_position(rel_pos, speed, acceleration)
    time.sleep(3)
    # print("----------set position-----------------")
    tt = m1.read_actual_position()
    print('position is:{}'.format(tt))

    
    rel_pos = 2000 # 5000/800 *6 = 0.0075*5000=3.25mm
    m1.move_relative_position(rel_pos, speed, acceleration)

    # print("----------set position-----------------")
    tt = m1.read_actual_position()
    print('Now the position is:{}'.format(tt))
    print('motion is completed-----------------------------------')
    
    
    m1.close_port()



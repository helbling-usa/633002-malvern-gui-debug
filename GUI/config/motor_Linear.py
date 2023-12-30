from ctypes import *
import time

# Constants used as values for 'MoveMoment' parameters
UPDATE_NONE			=-1
UPDATE_ON_EVENT		=0
UPDATE_IMMEDIATE	=1    
FROM_MEASURE	=0
FROM_REFERENCE	=1
NO_ADDITIVE		=0
ADDITIVE		=1
WAIT_EVENT		=1
NO_STOP			=0
STOP			=1
NO_CHANGE_POS	=0
NO_CHANGE_ACC	=0
NO_CHANGE_SPD	=0

REG_SRL =3
CHANNEL_TYPE = 0 #for rs232
HOST_ID	= 0
BAUDRATE = 115200
POWER_ON = 1



class motor_Linear():
    global FROM_REFERENCE
    global NO_ADDITIVE
    global ADDITIVE
    global WAIT_EVENT
    global NO_STOP
    global REG_SRL
    global CHANNEL_TYPE
    global HOST_ID	
    global BAUDRATE 
    global POWER_ON 


    def __init__(self, CHANNEL_NAME, AXIS_ID_01, motor_type) -> None:
        self.CHANNEL_NAME = CHANNEL_NAME
        self.AXIS_ID_01 = AXIS_ID_01 
        self.mydll1 =CDLL("./config/TML_LIB.dll")
        #/*	Load the *.t.zip with setup data generated with EasyMotion Studio or EasySetUp */
        config_file = b"./config/"+motor_type + b".t.zip"
        print('\tloading setup file: ', config_file)
        # self.idxSetup = self.mydll1.TS_LoadSetup(b"./config/LEFS25.t.zip")
        self.idxSetup = self.mydll1.TS_LoadSetup(config_file)


        if (self.idxSetup < 0):
            print('cannot load setup')
            return False
        else:
            print("\tsetup loaded sucessfully")

        # print("---------initialize the motor  -------------------")
        print("\tOpening com port:", self.CHANNEL_NAME)
        if self.InitCommunicationChannel() == False:
            print("Commumication error!", self.mydll1.TS_GetLastErrorText())
        else:
            print("\tCommunication established")

        # self.set_position()
        # # print("------------set int var ------------------------------")
        # self.set_POSOKLIM(2)

        
        
    def InitCommunicationChannel(self):
        # /*	Open the comunication channel: COM1, RS232, 1, 115200 */
        if (self.mydll1.TS_OpenChannel (self.CHANNEL_NAME, CHANNEL_TYPE, HOST_ID, BAUDRATE) < 0):
                return False

        return True



    def InitAxis(self):
        #/*	Setup the axis based on the setup data previously loaded */
        tt = self.mydll1.TS_SetupAxis(self.AXIS_ID_01, self.idxSetup)
        if (tt==0):
            print("can setup axis")
            return False
        else:
            print('\tsetup axis: done')

        #	Select the destination axis of the TML commands 
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_01)
        if (tt==0):
            print("can find axis")
            return False
        else:
            print('\tselect dest. axis: done')

        time.sleep(.5)
        #/*	Execute the initialization of the drive (ENDINIT) */
        tt = self.mydll1.TS_DriveInitialisation()
        if (tt==0):
            print("Can't init. drive")
            return False
        else:
            print('\tinit successful ')

        #/*	Enable the power stage of the drive (AXISON) */ 
        tt = self.mydll1.TS_Power(POWER_ON)
        if (tt==0):
            print("Can't power on")
        else:
            print('\tPower On successful')

        # Wait for power stage to be enabled */        
        y = self.mydll1.TS_ReadStatus   # Read drive/motor status info.
        y.restype = c_bool
        y.argtypes = [c_int,POINTER(c_int)]
        p = c_int()
        
        while ((p.value & (1<<15)) == 0):
            tt = y(REG_SRL,  byref(p))
            # print("tt-->", tt)            
        # print('(h){:X}  = (b){:b} '.format(p.value,p.value))

        return True


    def get_firmware_version(self):
        # print("---------get FM VER -------------------")
        y = self.mydll1.TS_GetFirmwareVersion
        y.restype = c_bool
        y.argtypes = [POINTER(c_int)]
        p = c_int()
        tt = y(byref(p))
        # print("tt-->", tt)        
        print('firmware version: {:X}'.format(p.value))


    def set_position(self):
        # print("----------set position-----------------")
        x = self.mydll1.TS_SetPosition
        x.restype = c_bool
        x.argtypes = [c_long]
        tt = x(0)
        # if (tt==True):
        #     print('position is set')
        return tt


    def move_relative_position(self, rel_pos, speed, acceleration):
        # print("----------MOVE Relative-----------------")
        x = self.mydll1.TS_MoveRelative
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double, c_bool, c_short, c_short]

        tt = x(rel_pos, speed, acceleration,NO_ADDITIVE,UPDATE_IMMEDIATE,FROM_REFERENCE)
        
        # if (tt==True):
        #     print("moving to relative position is done")
        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(WAIT_EVENT,NO_STOP) == False):
            print("error in set event on motion complete")

    
    def move_absolute_position(self, abs_pos, speed, acceleration):
        # print("----------MOVE Relative-----------------")
        x = self.mydll1.TS_MoveAbsolute
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double,  c_short, c_short]

        tt = x(abs_pos, speed, acceleration,UPDATE_IMMEDIATE,FROM_REFERENCE)
        
        # if (tt==True):
        #     print("moving to absolute position is done")
        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(WAIT_EVENT,NO_STOP) == False):
            print("error in set event on motion complete")


    def read_actual_position(self):
        # print("------------Read actual position ------------------------------")
        y = self.mydll1.TS_GetLongVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, POINTER(c_long)]
        p = c_long()
        tt = y(b"APOS",  byref(p))
        # print("tt-->", tt)        
        # print('actual position = {} '.format(p.value))
        return p.value

    def read_target_position(self):
        # print("------------Read target position ------------------------------")
        y = self.mydll1.TS_GetLongVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, POINTER(c_long)]
        p = c_long()
        tt = y(b"TPOS",  byref(p))
        # print("tt-->", tt)        
        # print('target position = {} '.format(p.value))
        return p.value


    def set_POSOKLIM(self, limit):
        # print("------------set  posoklim ------------------------------")
        y = self.mydll1.TS_SetIntVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, c_int]
        tt = y(b"POSOKLIM",  limit)
        # print("tt-->", tt)        
        # print('POSOKLIM = {} '.format(p.value))

    def get_POSOKLIM(self):
        # print("------------get posoklim ------------------------------")
        y = self.mydll1.TS_GetIntVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, POINTER(c_int)]
        p = c_int()
        tt = y(b"POSOKLIM",  byref(p))
        # print("tt-->", tt)        
        print('POSOKLIM = {} '.format(p.value))



if __name__ == "__main__":

    # self.mydll1 =CDLL("./TML_LIB.dll")
    # fd = self.mydll1.TS_OpenChannel(b"COM6",0, AXIS_ID_01, 115200)
    # print("result:", fd)

    motor = motor_Linear()

    # # print("---------initialize the motor  -------------------")
    # if motor.InitCommunicationChannel() == False:
    #     print("Commumication error!")
    # else:
    #      print("Communication established")


    #/*	Setup and initialize the axis */	
    if (motor.InitAxis()==False):
        print("Failed to start up the drive")





    # print("---------get FM VER -------------------")
    motor.get_firmware_version()

    # print("----------set position-----------------")
    motor.set_position()

    # print("------------set int var ------------------------------")
    motor.set_POSOKLIM(2)

    # print("------------get int var ------------------------------")
    motor.get_POSOKLIM()



    #print("----------MOVE Relative-----------------")
    speed = 15.0;		#/* jogging speed [drive internal speed units, encoder counts/slow loop sampling] */
    acceleration = 1.0#0.015;#/* acceleration rate [drive internal acceleration units, encoder counts/slow loop sampling^2] */
    rel_pos = -5000
    motor.move_relative_position(rel_pos, speed, acceleration)

    time.sleep(3)
    speed = 30.0
    rel_pos = 5000 # 5000/800 *6 = 0.0075*5000=3.25mm
    motor.move_relative_position(rel_pos, speed, acceleration)





    # print("------------Read actual position ------------------------------")
    motor.read_actual_position()

    motor.read_target_position()




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
BAUDRATE = 115200
POWER_ON = 1
TIM_LIB_PATH = "./config/TML_LIB.dll"


class motor_2axes():
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
    global TIM_LIB_PATH


    def __init__(self, CHANNEL_NAME, AXIS_ID_01, AXIS_ID_02, motor_type) -> None:
        self.CHANNEL_NAME = CHANNEL_NAME
        self.AXIS_ID_01 = AXIS_ID_01 
        self.AXIS_ID_02 = AXIS_ID_02
        self.mydll1 =CDLL(TIM_LIB_PATH)
        #/*	Load the *.t.zip with setup data generated with EasyMotion Studio or EasySetUp */
        config_file = b"./config/"+motor_type + b".t.zip"
        print('\tconfig file = ', config_file)
        # self.idxSetup = self.mydll1.TS_LoadSetup(b"./config/LEFS25.t.zip")
        self.idxSetup = self.mydll1.TS_LoadSetup(config_file)
        if (self.idxSetup < 0):
            print('\tcannot load setup')
            return False
        else:
            print("\tsetup loaded sucessfully")

        # print("---------initialize the motor  -------------------")
        print("connecting to com porst:",self.CHANNEL_NAME)
        if self.InitCommunicationChannel() == False:
            print("\tCommumication error!", self.mydll1.TS_GetLastErrorText())
        else:
            print("\tCommunication established")

        # self.set_position()
        # # print("------------set int var ------------------------------")
        # self.set_POSOKLIM(2)

        
        
    def InitCommunicationChannel(self):
        # /*	Open the comunication channel: COM1, RS232, 1, 115200 */
        if (self.mydll1.TS_OpenChannel (self.CHANNEL_NAME, CHANNEL_TYPE, self.AXIS_ID_01, BAUDRATE) < 0):
                return False

        return True



    def InitAxis(self):
        #----------------------axis 1 -------------------------------------------       
        config_file1 = b".\config\Mixer.t.zip"
        # print('config file path:', config_file1)
        idxSetup1 = self.mydll1.TS_LoadSetup(config_file1)

        if (idxSetup1 < 0):
            # print('cannot load setup 1')
            return False
        else:
            print("\tsetup 1 loaded sucessfully")

        #/*	Setup the axis based on the setup data previously loaded */
        tt = self.mydll1.TS_SetupAxis(self.AXIS_ID_01, idxSetup1)
        if tt<=0:
            print("\tFailed to setup axis 1")
            return False
        # print('\tsetup axis 1:', tt)

        #	Select the destination axis of the TML commands 
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_01)
        if tt<=0:
            print("\tFailed to select axis 1")
            return False
        # print('\tselect dest. axis 1:', tt)

        #/*	Execute the initialization of the drive (ENDINIT) */
        tt = self.mydll1.TS_DriveInitialisation()
        if tt<=0:
            print("\tFailed to initialzie drive 1")
            return False
        # print('\tinit successful 1:', tt)

        #----------------------axis 2 -------------------------------------------
        #/*	Load the *.t.zip with setup data generated with EasyMotion Studio or EasySetUp */
        config_file2 = b".\config\LEFS25.t.zip"
        # print('config file path:', config_file2)
        idxSetup2 = self.mydll1.TS_LoadSetup(config_file2)

        if (idxSetup2 < 0):
            # print('cannot load setup 2')
            return False
        else:
            print("\tsetup 2 loaded sucessfully")

        #/*	Setup the axis based on the setup data previously loaded */
        tt = self.mydll1.TS_SetupAxis(self.AXIS_ID_02, idxSetup2)
        if tt<=0:
            print("\tFailed to setup axis 2")
            return False
        # print('\tsetup axis 2:', tt)

        #	Select the destination axis of the TML commands 
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_02)
        if tt<=0:
            print("\tFailed to select axis 2")
            return False        
        # print('\tselect dest. axis 2:', tt)

        #/*	Execute the initialization of the drive (ENDINIT) */
        tt = self.mydll1.TS_DriveInitialisation()
        if tt<=0:
            print("\tFailed to initialzie drive 2")
            return False
        # print('\tinit successful 2:', tt)

        #---------------- broadcasting ------------------------------------------

        # /*	Setup the Broadcast based on the file previously loaded */
        tt= self.mydll1.TS_SetupBroadcast(idxSetup2)
        if tt<=0:
            print("\tFailed to setup broadcase")
            return False
        # print("setup broadcase:", tt)
        # /*	Select all the axes as the destination of the TML commands */
        tt = self.mydll1.TS_SelectBroadcast()
        if tt<=0:
            print("\tFailed tos select broadcase")
            return False
        # print("\t broadcast select all axes:", tt)		
                

        #/*	Enable the power stage of the drive (AXISON) */ 
        tt = self.mydll1.TS_Power(POWER_ON)
        if tt<=0:
            print("\tFailed to power on  drives")
            return False
        # print('\tPower On successful 1:', tt)

        # Wait for power stage to be enabled */    
        REG_SRL =3    
        y = self.mydll1.TS_ReadStatus   # Read drive/motor status info.
        y.restype = c_bool
        y.argtypes = [c_int,POINTER(c_int)]
        p = c_int()
        AxisOn_flag_1 = False
        AxisOn_flag_2 = False

        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_01)
        if (tt<=0):
            print("\tcan't select axis 1")
            return False
        else:
            while ( (p.value & (1<<15)) == 0):
                tt = y(REG_SRL,  byref(p))
                if tt<=0:
                    print("\tproblem reading axis 1")
                    return False

        p = c_int()
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_02)
        if (tt<=0):
            print("\tcan't select axis 2")
            return False
        else:
            while ( (p.value & (1<<15)) == 0):
                tt = y(REG_SRL,  byref(p))
                if tt<=0:
                    print("\tproblem reading axis 2")
                    return False

        print('\tAll axes are  initialzed and ready...')
        return True


    def get_firmware_version(self):
        # print("---------get FM VER -------------------")
        y = self.mydll1.TS_GetFirmwareVersion
        y.restype = c_bool
        y.argtypes = [POINTER(c_int)]
        p = c_int()
        tt = y(byref(p))
        # print("tt-->", tt)        
        print('\tfirmware version: {:X}'.format(p.value))


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
        
        if (tt==True):
            print("\tmoving to relative position is done")
        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(WAIT_EVENT,NO_STOP) == False):
            print("\terror in set event on motion complete")


    def move_absolute_position(self, abs_pos, speed, acceleration):
        # print("----------MOVE Relative-----------------")
        x = self.mydll1.TS_MoveAbsolute
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double,  c_short, c_short]

        tt = x(abs_pos, speed, acceleration,UPDATE_IMMEDIATE,FROM_REFERENCE)
        
        if (tt==True):
            print("\tmoving to absolute position is done")
        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(WAIT_EVENT,NO_STOP) == False):
            print("\terror in set event on motion complete")
    
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
        print('\tPOSOKLIM = {} '.format(p.value))

    def set_speed(self, speed,acceleration):
        # speed = 300.
        

        x = self.mydll1.TS_MoveVelocity
        x.restype = c_bool
        x.argtypes = [c_double,c_double, c_int, c_int]
        # tt = x(100., .01,1,0)
        tt = x(speed, acceleration,1,0)
        if tt<=0:
            print("\tFailed to set the speed")
            return False
        else:
            return True
    
    def select_axis(self, axisid):
        tt = self.mydll1.TS_SelectAxis(axisid)
        if (tt<=0):
            print("\tcan't select axis 1")
            return False
        else:
            print('\tstarting mixing motor')
        
    def close_port(self):
        self.mydll1.TS_CloseChannel(-1)


if __name__ == "__main__":

    # self.mydll1 =CDLL("./TML_LIB.dll")
    # fd = self.mydll1.TS_OpenChannel(b"COM6",0, AXIS_ID_01, 115200)
    # print("result:", fd)
    AXIS_ID_01 = 24
    AXIS_ID_02 = 1
    com_port = b"COM7"
    primary_axis =  b"Mixer"
    motor = motor_2axes(com_port, AXIS_ID_01, AXIS_ID_02, primary_axis)


    #/*	Setup and initialize the axis */	
    if (motor.InitAxis()==False):
        print("\tFailed to start up the drive")


    motor.select_axis(AXIS_ID_02)
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




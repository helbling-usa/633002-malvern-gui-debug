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
POWER_OFF = 0



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
    global POWER_OFF


    def __init__(self, CHANNEL_NAME, AXIS_ID_01, motor_type) -> None:
        self.CHANNEL_NAME = CHANNEL_NAME
        self.AXIS_ID_01 = AXIS_ID_01 
        self.mydll1 =CDLL("./config/TML_LIB.dll")
        #/*	Load the *.t.zip with setup data generated with EasyMotion Studio or EasySetUp */
        config_file = b"./config/"+motor_type + b".t.zip"
        print('config file = ', config_file)
        # self.idxSetup = self.mydll1.TS_LoadSetup(b"./config/LEFS25.t.zip")
        self.idxSetup = self.mydll1.TS_LoadSetup(config_file)
        if (self.idxSetup < 0):
            print('cannot load setup')
            return False
        else:
            print("setup loaded sucessfully")

        # print("---------initialize the motor  -------------------")
        print("connecting to com porst:",self.CHANNEL_NAME)
        if self.InitCommunicationChannel() == False:
            print("Commumication error!", self.mydll1.TS_GetLastErrorText())
        else:
            print("Communication established")

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
            print(' setup axis:', tt)

        #	Select the destination axis of the TML commands 
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_01)
        if (tt==0):
            print("can find axis")
            return False
        else:
            print(' select dest. axis:', tt)

        time.sleep(.5)
        #/*	Execute the initialization of the drive (ENDINIT) */
        tt = self.mydll1.TS_DriveInitialisation()
        if (tt==0):
            print("Can't init. drive")
            return False
        else:
            print('init successful:', tt)

        #/*	Enable the power stage of the drive (AXISON) */ 
        tt = self.mydll1.TS_Power(POWER_ON)
        if (tt==0):
            print("Can't power on")
        else:
            print('Power On successful:', tt)

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

    def homing_ESM(self):
        #/*	Homing parameters */
        high_speed = 100         #;		/* the homing travel speed [drive internal speed units, encoder counts/slow loop sampling] */
        low_speed = 10.          #;		/* the homing brake speed [drive internal speed units, encoder counts/slow loop sampling] */
        acceleration = 0.93      #;	/* the acceleration rate [drive internal acceleration units, encoder counts/slow loop sampling^2] */
        deceleration = 1.5      #;	/* the decceleration rate [drive internal acceleration units, encoder counts/slow loop sampling^2] */
        home_position = 1000    #;	/* the homing position [drive internal position units, encoder counts]  */
        
        # /*	Set the homing parameters on the drive */
        # /*	--------------------------------------------------------------------*/
        y = self.mydll1.TS_SetFixedVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, c_double]
        tt = y(b"CACC",  acceleration)
        if tt<=0:
            print("CACC error!")
            return False

        # /*	Set the deceleration rate for homing */
        # tt =self.mydll1.TS_QuickStopDecelerationRate(deceleration)
        y = self.mydll1.TS_QuickStopDecelerationRate
        y.restype = c_bool
        y.argtypes = [c_double]
        tt = y( deceleration)
        if tt<=0:
            print("deceleration error!")
            return False
        
        if tt<=0:
            print("deceleration error!")
            return False              

        y = self.mydll1.TS_SetFixedVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, c_double]
        tt = y(b"CSPD",  high_speed)
        if tt<=0:
            print("CSPD error!")
            return False
        
        # /*	Set the low speed for homing */
        y = self.mydll1.TS_SetFixedVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, c_double]
        tt = y(b"HOMESPD",  low_speed)
        if tt<=0:
            print("HOMESPD error!")
            return False

        #/*	Setup the home position at the end of the homing procedure */
        y = self.mydll1.TS_SetFixedVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, c_double]
        tt = y(b"HOMEPOS",  home_position)
        if tt<=0:
            print("HOMEPOS error!")
            return False

        # /*	--------------------------------------------------------------------*/
        # /*	Call the homing procedure stored in the non-volatile memory of the drive */
        
        # y = self.mydll1.TS_CancelableCALL_Label
        # y.restype = c_bool
        # y.argtypes = [c_char_p]
        # tt = y(b"Homing18")
        # if tt<=0:
        #     print("Homing18 error!")
        #     return False


        tt = self.mydll1.TS_Homing(18)
        # print('-->tt:', tt)

        # /*	Wait for homing procedure to end */	
        homing_done = 0
        # while(homing_done == 0):  
        # Check the SRL.8 bit - Homing active flag*/     
        y = self.mydll1.TS_ReadStatus   # Read drive/motor status info.
        y.restype = c_bool
        y.argtypes = [c_int,POINTER(c_int)]
        p = c_int()
            
        while ((p.value & (1<<8)) == 0):
            tt = y(REG_SRL,  byref(p))
            print('p.value:',p.value)


        print("everything looks good so far!")
        return True       
    


    def homing(self):
        #print("----------MOVE Relative-----------------")
        position = 1000000	#	/* position command [drive internal position units, encoder counts] */
        home_position = 1000	#	/* the homing position [drive internal position units, encoder counts] */
        cap_position = 0		#	/* the position captures at HIGH-LOW transition of negative limit switch */
        high_speed = 10	    	#	/* the homing travel speed [drive internal speed units, encoder counts/slow loop sampling]*/
        low_speed = 1.0 		#	/* the homing brake speed [drive internal speed units, encoder counts/slow loop sampling] */
        acceleration = 0.6
        #/*Constants used for LSWType*/
        LSW_NEGATIVE = -1
        LSW_POSITIVE = 1
        # /*Constants used for TransitionType*/
        TRANSITION_HIGH_TO_LOW =-1
        TRANSITION_DISABLE =0
        TRANSITION_LOW_TO_HIGH =1
        

        # self.set_position()

        # #/*	Command a trapezoidal positioning to search the negative limit switch */
        x = self.mydll1.TS_MoveRelative
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double, c_bool, c_short, c_short]
        tt = x(position, low_speed, acceleration,NO_ADDITIVE,UPDATE_IMMEDIATE,FROM_REFERENCE)
        if tt<=0:
            print("Error moving relative")
            return False
        

        # speed = 1.0;		#/* jogging speed [drive internal speed units, encoder counts/slow loop sampling] */
        # acceleration = 1.0#0.015;#/* acceleration rate [drive internal acceleration units, encoder counts/slow loop sampling^2] */
        # rel_pos = 10000
        # self.move_relative_position(rel_pos, speed, acceleration)



        ##/*	Wait for the LOW-HIGH transition on positive limit switch */
        x = self.mydll1.TS_SetEventOnLimitSwitch
        x.restype = c_bool
        x.argtypes = [c_short, c_short, c_bool, c_bool]
        EnableStop = True
        tt = x(LSW_POSITIVE, TRANSITION_LOW_TO_HIGH, WAIT_EVENT, EnableStop)
        if tt<=0:
            print("Error in set event on limit switch",tt)
            return False
            

  

        x = self.mydll1.TS_SetEventOnMotionComplete
        x.restype = c_bool
        x.argtypes = [c_bool, c_bool]        
        
        if (x(WAIT_EVENT,NO_STOP) == False):
            print("error in set event on motion complete")
            error = self.mydll1.TS_GetLastErrorText()
            print('---->',error)
            self.mydll1.TS_ResetFault()
            return False
        else:
            print('no error with set event on motion')


        # if (self.mydll1.TS_SetEventOnMotionComplete(WAIT_EVENT,NO_STOP) == False):
        #     print("error in set event on motion complete")
        #     error = self.mydll1.TS_GetLastErrorText()
        #     print('---->',error)
        #     self.mydll1.TS_ResetFault()
        #     return False
        # else:
        #     print('no error with set event on motion')


        # #/*	Read the captured position on limit switch transition */
        # y = self.mydll1.TS_GetLongVariable
        # y.restype = c_bool
        # y.argtypes = [c_char_p, POINTER(c_long)]
        # p = c_long()
        # tt = y(b"CAPPOS",  byref(p))
        # print(" The captured position is: {} [drive internal position units]\n".format( p.value));

        # set that spot as home position
        self.set_position()

        #/*	Command an absolute positioning on the captured position */
        x = self.mydll1.TS_MoveAbsolute
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double,  c_short, c_short]
        abs_pos = -2000
        tt = x(abs_pos, low_speed, acceleration,UPDATE_IMMEDIATE,FROM_REFERENCE)
        if (tt == False):
            print("error in moving to absolute position")
            return False

        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(WAIT_EVENT,NO_STOP) == False):
            print("error in set event on motion complete")
            return False
        
        return True


    def reset_fault(self):
        self.mydll1.TS_ResetFault()




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
        # tt=self.mydll1.TS_MoveRelative(rel_pos, speed, acceleration,NO_ADDITIVE,UPDATE_IMMEDIATE,FROM_REFERENCE)
        if (tt==True):
            print("moving to relative position is done")
        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(WAIT_EVENT,NO_STOP) == False):
            print("error in set event on motion complete")
            return False

        # x = self.mydll1.TS_SetEventOnTime
        # x.restype = c_bool
        # x.argtypes = [c_int, c_bool,c_bool]

        # time = 12000
        # tt = x(time, WAIT_EVENT,NO_STOP )
        # if tt<=0:
        #     print('------problem--------------')
        #     return False



        return True

    def move_absolute_position(self, abs_pos, speed, acceleration):
        # print("----------MOVE Absolute-----------------")
        x = self.mydll1.TS_MoveAbsolute
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double,  c_short, c_short]

        tt = x(abs_pos, speed, acceleration,UPDATE_IMMEDIATE,FROM_REFERENCE)
        
        if (tt==True):
            print("moving to absolute position is done")
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

    def disable_motor(self):
        #/*	Enable the power stage of the drive (AXISON) */ 
        tt = self.mydll1.TS_Power(POWER_OFF)
        if (tt==0):
            print("Can't power off")
        else:
            print('Power Off successful:')

        self.mydll1.TS_CloseChannel(-1)


# if __name__ == "__main__":

#     # self.mydll1 =CDLL("./TML_LIB.dll")
#     # fd = self.mydll1.TS_OpenChannel(b"COM6",0, AXIS_ID_01, 115200)
#     # print("result:", fd)

#     motor = motor_Linear()

#     # # print("---------initialize the motor  -------------------")
#     # if motor.InitCommunicationChannel() == False:
#     #     print("Commumication error!")
#     # else:
#     #      print("Communication established")


#     #/*	Setup and initialize the axis */	
#     if (motor.InitAxis()==False):
#         print("Failed to start up the drive")





#     # print("---------get FM VER -------------------")
#     motor.get_firmware_version()

#     # print("----------set position-----------------")
#     motor.set_position()

#     # print("------------set int var ------------------------------")
#     motor.set_POSOKLIM(2)

#     # print("------------get int var ------------------------------")
#     motor.get_POSOKLIM()



#     #print("----------MOVE Relative-----------------")
#     speed = 15.0;		#/* jogging speed [drive internal speed units, encoder counts/slow loop sampling] */
#     acceleration = 1.0#0.015;#/* acceleration rate [drive internal acceleration units, encoder counts/slow loop sampling^2] */
#     rel_pos = -5000
#     motor.move_relative_position(rel_pos, speed, acceleration)

#     time.sleep(3)
#     speed = 30.0
#     rel_pos = 5000 # 5000/800 *6 = 0.0075*5000=3.25mm
#     motor.move_relative_position(rel_pos, speed, acceleration)





#     # print("------------Read actual position ------------------------------")
#     motor.read_actual_position()

#     motor.read_target_position()




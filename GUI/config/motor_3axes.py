from ctypes import *
import time
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
formatter = logging.Formatter('%(levelname)s:%(message)s')
file_handler = logging.FileHandler('error.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Constants used as values for 'MoveMoment' parameters
UPDATE_NONE			=-1
UPDATE_ON_EVENT		=0
UPDATE_IMMEDIATE	=1    
FROM_MEASURE	=0
FROM_REFERENCE	=1
NO_ADDITIVE		=0
ADDITIVE		=1
WAIT_EVENT		=1
NO_WAIT_EVENT   =0
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






class motor_3axes():
    global FROM_REFERENCE
    global NO_ADDITIVE
    global ADDITIVE
    global WAIT_EVENT
    global NO_WAIT_EVENT
    global NO_STOP
    global REG_SRL
    global CHANNEL_TYPE
    # global HOST_ID	
    global BAUDRATE 
    global POWER_ON 
    global TIM_LIB_PATH


    def __init__(self, CHANNEL_NAME, AXIS_ID_01, AXIS_ID_02, AXIS_ID_03, motor_type) -> None:
        self.CHANNEL_NAME = CHANNEL_NAME
        self.AXIS_ID_01 = AXIS_ID_01 
        self.AXIS_ID_02 = AXIS_ID_02
        self.AXIS_ID_03 = AXIS_ID_03
        self.mydll1 =CDLL(TIM_LIB_PATH)
        #/*	Load the *.t.zip with setup data generated with EasyMotion Studio or EasySetUp */
        config_file = b"./config/"+motor_type + b".t.zip"
        logger.info('\t\tconfig file = {}'.format( config_file))
        # self.idxSetup = self.mydll1.TS_LoadSetup(b"./config/LEFS25.t.zip")
        self.idxSetup = self.mydll1.TS_LoadSetup(config_file)
        if (self.idxSetup < 0):
            logger.error('\t\tcannot load setup')
            return False
        else:
            logger.info("\t\tsetup loaded sucessfully")

        # logger.info("\t\t---------initialize the motor  -------------------")
        logger.info("\t\tconnecting to com port:{}".format(self.CHANNEL_NAME))
        if self.InitCommunicationChannel() == False:
            logger.error("\tCommumication error! {}".format( self.mydll1.TS_GetLastErrorText()))
        else:
            logger.info("\t\tCommunication established")

        # self.set_position()
        # # logger.info("\t\t------------set int var ------------------------------")
        # self.set_POSOKLIM(2)

        
        
    def InitCommunicationChannel(self):
        # /*	Open the comunication channel: COM1, RS232, 1, 115200 */
        if (self.mydll1.TS_OpenChannel (self.CHANNEL_NAME, CHANNEL_TYPE, self.AXIS_ID_01, BAUDRATE) < 0):
                logger.info("\t\tCan't initilaze com port (Technosoft)")
                return False

        return True



    def InitAxis(self):
        #----------------------axis 1 -------------------------------------------       
        config_file1 = b".\config\Mixer.t.zip"
        # logger.info('config file path:', config_file1)
        idxSetup1 = self.mydll1.TS_LoadSetup(config_file1)

        if (idxSetup1 < 0):
            # logger.info('cannot load setup 1')
            return False
        else:
            logger.info("\t\tsetup 1 loaded sucessfully")

        #/*	Setup the axis based on the setup data previously loaded */
        tt = self.mydll1.TS_SetupAxis(self.AXIS_ID_01, idxSetup1)
        if tt<=0:
            logger.info("\t\tFailed to setup axis 1")
            return False
        # logger.info('\tsetup axis 1:', tt)

        #	Select the destination axis of the TML commands 
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_01)
        if tt<=0:
            logger.info("\t\tFailed to select axis 1")
            return False
        # logger.info('\tselect dest. axis 1:', tt)

        #/*	Execute the initialization of the drive (ENDINIT) */
        tt = self.mydll1.TS_DriveInitialisation()
        if tt<=0:
            logger.info("\t\tFailed to initialzie drive 1")
            return False
        # logger.info('\tinit successful 1:', tt)

        #----------------------axis 2 -------------------------------------------
        #/*	Load the *.t.zip with setup data generated with EasyMotion Studio or EasySetUp */
        config_file2 = b".\config\LEFS25.t.zip"
        # logger.info('config file path:', config_file2)
        idxSetup2 = self.mydll1.TS_LoadSetup(config_file2)

        if (idxSetup2 < 0):
            # logger.info('cannot load setup 2')
            return False
        else:
            logger.info("\t\tsetup 2 loaded sucessfully")

        #/*	Setup the axis based on the setup data previously loaded */
        tt = self.mydll1.TS_SetupAxis(self.AXIS_ID_02, idxSetup2)
        if tt<=0:
            logger.info("\t\tFailed to setup axis 2")
            return False
        # logger.info('\tsetup axis 2:', tt)

        #	Select the destination axis of the TML commands 
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_02)
        if tt<=0:
            logger.error("\tFailed to select axis 2")
            return False        
        # logger.info('\tselect dest. axis 2:', tt)

        #/*	Execute the initialization of the drive (ENDINIT) */
        tt = self.mydll1.TS_DriveInitialisation()
        if tt<=0:
            logger.error("\tFailed to initialzie drive 2")
            return False
        # logger.info('\tinit successful 2:', tt)

        #----------------------axis 3 -------------------------------------------
        #/*	Load the *.t.zip with setup data generated with EasyMotion Studio or EasySetUp */
        config_file3 = b".\config\LEFS32.t.zip"
        # logger.info('config file path:', config_file3)
        idxSetup3 = self.mydll1.TS_LoadSetup(config_file3)

        if (idxSetup3 < 0):
            # logger.info('cannot load setup 3')
            return False
        else:
            logger.info("\t\tsetup 3 loaded sucessfully")

        #/*	Setup the axis based on the setup data previously loaded */
        tt = self.mydll1.TS_SetupAxis(self.AXIS_ID_03, idxSetup3)
        if tt<=0:
            logger.info("\t\tFailed to setup axis 3")
            return False
        # logger.info('\tsetup axis 3:', tt)

        #	Select the destination axis of the TML commands 
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_03)
        if tt<=0:
            logger.error("\tFailed to select axis 3")
            return False        
        # logger.info('\tselect dest. axis 2:', tt)

        #/*	Execute the initialization of the drive (ENDINIT) */
        tt = self.mydll1.TS_DriveInitialisation()
        if tt<=0:
            logger.error("\tFailed to initialzie drive 3")
            return False
        # logger.info('\tinit successful 3:', tt)
        #---------------- broadcasting ------------------------------------------

        # /*	Setup the Broadcast based on the file previously loaded */
        tt= self.mydll1.TS_SetupBroadcast(idxSetup3)
        if tt<=0:
            logger.error("\tFailed to setup broadcase")
            return False
        # logger.info("\t\tsetup broadcase:", tt)
        # /*	Select all the axes as the destination of the TML commands */
        tt = self.mydll1.TS_SelectBroadcast()
        if tt<=0:
            logger.error("\tFailed tos select broadcase")
            return False
        # logger.info("\t\t broadcast select all axes:", tt)		
                

        #/*	Enable the power stage of the drive (AXISON) */ 
        tt = self.mydll1.TS_Power(POWER_ON)
        if tt<=0:
            logger.error("\tFailed to power on  drives")
            return False
        # logger.info('\tPower On successful 1:', tt)

        # Wait for power stage to be enabled */    
        REG_SRL =3    
        y = self.mydll1.TS_ReadStatus   # Read drive/motor status info.
        y.restype = c_bool
        y.argtypes = [c_int,POINTER(c_int)]
        p = c_int()
        AxisOn_flag_1 = False
        AxisOn_flag_2 = False
        AxisOn_flag_3 = False

        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_01)
        if (tt<=0):
            logger.error("\tcan't select axis 1")
            return False
        else:
            while ( (p.value & (1<<15)) == 0):
                tt = y(REG_SRL,  byref(p))
                if tt<=0:
                    logger.error("\tproblem reading axis 1")
                    return False

        p = c_int()
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_02)
        if (tt<=0):
            logger.error("\tcan't select axis 2")
            return False
        else:
            while ( (p.value & (1<<15)) == 0):
                tt = y(REG_SRL,  byref(p))
                if tt<=0:
                    logger.error("\tproblem reading axis 2")
                    return False


        p = c_int()
        tt = self.mydll1.TS_SelectAxis(self.AXIS_ID_03)
        if (tt<=0):
            logger.error("\tcan't select axis 3")
            return False
        else:
            while ( (p.value & (1<<15)) == 0):
                tt = y(REG_SRL,  byref(p))
                if tt<=0:
                    logger.error("\tproblem reading axis 2")
                    return False



        logger.info('\t\tAll axes are  initialzed and ready...')
        return True




    def homing(self, AXIS_ID):
        #logger.info("\t\t----------MOVE Relative-----------------")
        position = -1000000	#	/* position command [drive internal position units, encoder counts] */
        home_position = -1000	#	/* the homing position [drive internal position units, encoder counts] */
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


        self.set_POSOKLIM(1)
        logger.info("\t\tHoming started for axis id: {}".format( AXIS_ID))
        tt = self.mydll1.TS_SelectAxis(AXIS_ID)
        if tt<=0:
            logger.error("\t\tFailed to select axis id: {}".format(AXIS_ID))
            return False        
                
        # #/*	Command a trapezoidal positioning to search the positive limit switch */
        logger.info("\t\tSearching for positive limit switch .....")
        x = self.mydll1.TS_MoveRelative
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double, c_bool, c_short, c_short]
        tt = x(position, low_speed, acceleration,NO_ADDITIVE,UPDATE_IMMEDIATE,FROM_REFERENCE)
        if tt<=0:
            logger.error("\t\tError moving relative")
            return False

        ##/*	Wait for the LOW-HIGH transition on positive limit switch */
        x = self.mydll1.TS_SetEventOnLimitSwitch
        x.restype = c_bool
        x.argtypes = [c_short, c_short, c_bool, c_bool]
        EnableStop = True
        tt = x(LSW_NEGATIVE, TRANSITION_LOW_TO_HIGH, WAIT_EVENT, EnableStop)
        if tt<=0:
            logger.info("\t\tError in set event on limit switch",tt)
            return False
            
        # /*	Wait until the motor stops */
        x = self.mydll1.TS_SetEventOnMotionComplete
        x.restype = c_bool
        x.argtypes = [c_bool, c_bool]        
        if (x(WAIT_EVENT,NO_STOP) == False):
            logger.error("\t\tError in set event on motion complete")
            error = self.mydll1.TS_GetLastErrorText()
            print('---->',error)
            self.mydll1.TS_ResetFault()
            return False
        
        #/*	Read the captured position on imit switch transition */
        y = self.mydll1.TS_GetLongVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, POINTER(c_long)]
        p = c_long()
        tt = y(b"CAPPOS",  byref(p))
        cap_position = p.value
        logger.info("\t\tThe captured position is: {} [drive internal position units]\n".format( cap_position));

        
        #/*	Command an absolute positioning on the captured position */
        x = self.mydll1.TS_MoveAbsolute
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double,  c_short, c_short]
        # abs_pos = -2000
        tt = x(cap_position, low_speed, acceleration,UPDATE_IMMEDIATE,FROM_REFERENCE)
        if (tt == False):
            logger.error("\t\terror in moving to absolute position")
            return False

        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(WAIT_EVENT,NO_STOP) == False):
            logger.error("\t\terror in set event on motion complete")
            return False
        
        # set that spot as home position
        self.set_position(home_position)

        logger.info("\t\tThe limit switchmotor position is set to {} [position internal units]!".format( home_position));
        logger.info("\t\tHoming procedure done!\n")
        logger.info("\t\tAfter homing, the limit switch position is set to: {}".format(self.read_actual_position()))
        self.move_absolute_position(0 , low_speed, acceleration)
        time.sleep(3)
        # print("----------set position-----------------")
        tt = self.read_actual_position()
        print('position is:{}'.format(tt))
        

        return True


    def get_firmware_version(self):
        # logger.info("\t\t---------get FM VER -------------------")
        y = self.mydll1.TS_GetFirmwareVersion
        y.restype = c_bool
        y.argtypes = [POINTER(c_int)]
        p = c_int()
        tt = y(byref(p))
        # logger.info("\t\ttt-->", tt)        
        logger.info('\t\tfirmware version: {:X}'.format(p.value))


    def set_position(self,position=0):
        # logger.info("\t\t----------set position-----------------")
        x = self.mydll1.TS_SetPosition
        x.restype = c_bool
        x.argtypes = [c_long]
        tt = x(position)
        # if (tt==True):
        #     logger.info('position is set')
        return tt


    def move_relative_position(self, rel_pos, speed, acceleration):
        LSW_NEGATIVE = -1
        LSW_POSITIVE = 1
        # /*Constants used for TransitionType*/
        TRANSITION_HIGH_TO_LOW =-1
        TRANSITION_DISABLE =0
        TRANSITION_LOW_TO_HIGH =1  
        
        
        xx = self.mydll1.TS_GetLongVariable
        xx.restype = c_bool
        xx.argtypes = [c_char_p, POINTER(c_long)]
        pxx = c_long()
        tt = xx(b"APOS",  byref(pxx))
        final_pos = pxx.value + rel_pos
        # logger.info("\t\tcurrent pos:", pxx.value, " rel pos:", rel_pos, " final pos:", final_pos)
        
        # print("----------MOVE Relative-----------------")
        x = self.mydll1.TS_MoveRelative
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double, c_bool, c_short, c_short]

        tt = x(rel_pos, speed, acceleration,NO_ADDITIVE,UPDATE_IMMEDIATE,FROM_REFERENCE)
        
        if (tt==True):
            logger.info("\t\tmoving to relative position is done")
        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(NO_WAIT_EVENT,STOP) == False):
            logger.error("\t\terror in set event on motion complete")
            return -1

        x = self.mydll1.TS_SetEventOnLimitSwitch
        x.restype = c_bool
        x.argtypes = [c_short, c_short, c_bool, c_bool]
        EnableStop = True
        tt = x(LSW_POSITIVE, TRANSITION_LOW_TO_HIGH, NO_WAIT_EVENT, EnableStop)

        y = self.mydll1.TS_CheckEvent
        y.restype = c_bool
        y.argtypes = [POINTER(c_bool)]
        py = c_bool()

        start = time.time()
        while (py.value == False and pxx.value<final_pos and time.time()-start<5):
            self.mydll1.TS_CheckEvent(byref(py))
            xx(b"APOS",  byref(pxx))

        if py.value == True:
            self.mydll1.TS_Stop()
            logger.warn("\t\t=================================================")
            logger.warn("\t\tWARNING!!! WARNING!!! WARNING!!!")
            logger.warn("\t\tLIEANR ACTUATOR IS AT THE END OF ITS TRAVEL")
            logger.warn("\t\tTHE LIMIT SWITCH IS ACTIVATED")        
            logger.warn("\t\tPLEASE RETURN THE LINEAR ACTUAOR WITHIN LIMITS")
            logger.warn("\t\t=================================================")
            return -2
        return 1



    def move_absolute_position(self, abs_pos, speed, acceleration):
        # print("----------MOVE Relative-----------------")
        x = self.mydll1.TS_MoveAbsolute
        x.restype = c_bool
        x.argtypes = [c_long,c_double, c_double,  c_short, c_short]

        tt = x(abs_pos, speed, acceleration,UPDATE_IMMEDIATE,FROM_REFERENCE)
        
        if (tt==True):
            logger.info("\t\tmoving to absolute position is done")
        # /*	Wait until the positioning is ended */
        if (self.mydll1.TS_SetEventOnMotionComplete(NO_WAIT_EVENT,STOP) == False):
            logger.error("\t\terror in set event on motion complete")

            

    def read_actual_position(self):
        # tt = self.mydll1.TS_SelectAxis(AXIS_ID)
        # if tt<=0:
        #     logger.error("\tFailed to select axis 2")
        #     return False  
        # logger.info("\t\t------------Read actual position ------------------------------")
        y = self.mydll1.TS_GetLongVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, POINTER(c_long)]
        p = c_long()
        tt = y(b"APOS",  byref(p))
        # logger.info("\t\ttt-->", tt)        
        # logger.info('actual position = {} '.format(p.value))
        return p.value

    def read_target_position(self):
        # tt = self.mydll1.TS_SelectAxis(AXIS_ID)
        # if tt<=0:
        #     logger.error("\tFailed to select axis 2")
        #     return False          
        # logger.info("\t\t------------Read target position ------------------------------")
        y = self.mydll1.TS_GetLongVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, POINTER(c_long)]
        p = c_long()
        tt = y(b"TPOS",  byref(p))
        # logger.info("\t\ttt-->", tt)        
        # logger.info('target position = {} '.format(p.value))
        return p.value


    def set_POSOKLIM(self, limit):
        # logger.info("\t\t------------set  posoklim ------------------------------")
        y = self.mydll1.TS_SetIntVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, c_int]
        tt = y(b"POSOKLIM",  limit)
        # logger.info("\t\ttt-->", tt)        
        # logger.info('POSOKLIM = {} '.format(p.value))

    def get_POSOKLIM(self):
        # logger.info("\t\t------------get posoklim ------------------------------")
        y = self.mydll1.TS_GetIntVariable
        y.restype = c_bool
        y.argtypes = [c_char_p, POINTER(c_int)]
        p = c_int()
        tt = y(b"POSOKLIM",  byref(p))
        # logger.info("\t\ttt-->", tt)        
        logger.info('\t\tPOSOKLIM = {} '.format(p.value))

    def set_speed(self, speed,acceleration):
        # speed = 300.
        x = self.mydll1.TS_MoveVelocity
        x.restype = c_bool
        x.argtypes = [c_double,c_double, c_int, c_int]
        # tt = x(100., .01,1,0)
        tt = x(speed, acceleration,1,0)
        if tt<=0:
            logger.error("\tFailed to set the speed")
            return False
        else:
            return True
    
    def select_axis(self, axisid):
        tt = self.mydll1.TS_SelectAxis(axisid)
        if (tt<=0):
            logger.error("\tcan't select axis 1")
            return False
        else:
            # logger.info('\t\tstarting mixing motor')
            return True
        
    def close_port(self):
        self.mydll1.TS_CloseChannel(-1)


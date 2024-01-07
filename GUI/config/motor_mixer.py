from ctypes import *
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')

file_handler = logging.FileHandler('error.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

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
# self.AXIS_ID = 24
POWER_ON = 1
POWER_OFF =0

class motor_mixer():
    def __init__(self, port, axis_id, motor_type,acceleration):
        
        self.AXIS_ID = axis_id
        # self.speed = speed
        # self.acceleration = acceleration        
        self.mydll1 =CDLL("./config/TML_LIB.dll")
        self.PORTNAME=port
        self.acceleration = acceleration
        # self.fd = self.mydll1.TS_OpenChannel(port,0, self.AXIS_ID, 115200)
        # # logger.info("motor 1 - openning COM7 port:", fd)


        #/*	Load the *.t.zip with setup data generated with EasyMotion Studio or EasySetUp */
        config_file = b"./config/"+motor_type + b".t.zip"
        logger.info('config file = {}'.format( config_file))

        self.idxSetup = self.mydll1.TS_LoadSetup(config_file)
        if (self.idxSetup < 0):
            logger.info('cannot load setup')
            return False
        else:
            logger.info("setup loaded sucessfully")

        # logger.info("---------initialize the motor  -------------------")
        logger.info("connecting to com port:",self.PORTNAME)

        if self.InitCommunicationChannel() == False:
            logger.info("Commumication error!", self.mydll1.TS_GetLastErrorText())
        else:
            logger.info("Communication established")



    def InitAxis(self):

        #/*	Setup the axis based on the setup data previously loaded */
        tt = self.mydll1.TS_SetupAxis(self.AXIS_ID, self.idxSetup)
        # logger.info(' setup axis:', tt)

        #	Select the destination axis of the TML commands 
        tt =self. mydll1.TS_SelectAxis(self.AXIS_ID)
        # logger.info(' select dest. axis:', tt)

        #/*	Execute the initialization of the drive (ENDINIT) */
        tt = self.mydll1.TS_DriveInitialisation()
        # logger.info('init successful:', tt)

        tt = self.mydll1.TS_Power(POWER_ON)
        # logger.info('Power On successful:', tt)

        # motor 1 power on:
        y = self.mydll1.TS_ReadStatus
        y.restype = c_bool
        y.argtypes = [c_int,POINTER(c_int)]
        p = c_int()
        REG_SRL =3
        while ((p.value & (1<<15)) == 0):
            tt = y(REG_SRL,  byref(p))
    
        # logger.info('{:X} = {:b} '.format(p.value,p.value))
            return True
    

    def InitCommunicationChannel(self):
        # /*	Open the comunication channel: COM1, RS232, 1, 115200 */
        if (self.mydll1.TS_OpenChannel (self.PORTNAME, CHANNEL_TYPE, HOST_ID, BAUDRATE) < 0):
                return False

        return True
    

    def set_speed(self, speed):
        # speed = 300.
        

        x = self.mydll1.TS_MoveVelocity
        x.restype = c_bool
        x.argtypes = [c_double,c_double, c_int, c_int]
        # tt = x(100., .01,1,0)
        tt = x(speed, self.acceleration,1,0)
        # logger.info(tt)


    def stop(self):
        speed = 0
        x = self.mydll1.TS_MoveVelocity
        x.restype = c_bool
        x.argtypes = [c_double,c_double, c_int, c_int]

        tt = x(speed, self.acceleration,1,0)
        # logger.info(tt)


        tt = self.mydll1.TS_Power(POWER_OFF)
        # logger.info('Power Off successful:', tt)

        self.mydll1.TS_CloseChannel(self.fd);
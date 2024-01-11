import serial
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

file_handler = logging.FileHandler('error.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)




class Pump():
    def __init__(self,port, position=0, speed=1000, acceleration=30000):
        self.position = position
        self.speed = speed
        self.acceleration = acceleration
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.ser.timeout = 3
        self.ser.port = port
        # logger.info(self.ser)

        self.ser.open()
        # logger.info("port is open?", self.ser.is_open)

        # clear buffers
        self.ser.reset_output_buffer()
        self.ser.reset_input_buffer()
        self.config_valve(1, 4)
        
        
    def pump_Zinit(self, axis):
        str1 = '/'+ str(axis)+'ZR\r\n'
        self.ser.write(str1.encode())
        self.read()
        # self.ser.write(b'/1ZR\r\n')
        # self.ser.flush()

    def pump_Yinit(self, axis):
        str1 = '/'+ str(axis)+'YR\r\n'
        self.ser.write(str1.encode())
        self.read()
    

    def set_pos_absolute(self, axis, position):
        
        str1 = '/'+str(axis)+'A'+str(position)+'R\r\n'
        # logger.info('str1 = ', str1)
        self.ser.write(str1.encode())
        self.read()
        # self.ser.write(b'/1A1000R\r\n')
        # self.ser.write(b'/1A0R\r\n')


    def set_pickup(self, axis, position):
        str1 = '/'+str(axis)+'P'+str(position)+'R\r\n'
        # logger.info('str1 = ', str1)
        self.ser.write(str1.encode())
        self.read()

    def set_dispense(self, axis, position):
        str1 = '/'+str(axis)+'D'+str(position)+'R\r\n'
        # logger.info('str1 = ', str1)
        self.ser.write(str1.encode())
        self.read()


    def set_speed(self, axis, speed):
        str1 = '/'+str(axis)+'V'+str(speed)+'R\r\n'
        # logger.info('set speed:',str1)
        self.ser.write(str1.encode())
        self.read()

    def set_valve(self, axis, pos):
        str1 = '/'+str(axis)+pos+'R\r\n'
        # logger.info('set valve:',str1)
        self.ser.write(str1.encode())
        self.read()


    def set_multiwayvalve(self, axis, pos):
        str1 = '/'+str(axis)+'I'+str(pos)+'R\r\n'
        # logger.info('set valve:',str1)
        self.ser.write(str1.encode())
        self.read()


    def config_valve(self, axis, valve_type):
        str1 = '/'+str(axis)+'U'+str(valve_type)+'\r\n'
        # logger.info('config valve:',str1)
        self.ser.write(str1.encode())
        str1 = self.read()
        # logger.info('set valve type respone:', str1)

        # str1 = '/'+str(axis)+'?27R\r\n'        
        # self.ser.write(str1.encode())
        # str1 = self.read()
        # logger.info('detected valve type respone:', str1)

    def get_valve(self, axis):
        str1 = '/'+str(axis)+'?6\r\n'
        # logger.info('get valve :',str1)
        self.ser.write(str1.encode())
        str1 = self.read()
        str1 = str1.decode('ascii')
        # logger.info("---->", str1)
        # logger.info('the valve is in position:',str1[4])
        return str1[4]


    def get_peakspeed(self, axis):
        str1 = '/'+str(axis)+'?2\r\n'
        # logger.info('get valve :',str1)
        self.ser.write(str1.encode())
        str1 = self.read()
        str1 = str1.decode('ascii')
        # logger.info('the peak speed string is:',str1)
        str1 = str1.split("`")
        # logger.info('--->', str1)
        str1 = str1[-1][:-1]
        # logger.info('--->', str1)
        # logger.info('the peak speed string is:',str1[-1], float(str1[-1]))
        
        return str1
    

    def get_plunger_position(self, axis):
        str1 = '/'+str(axis)+'?0R\r\n'
        # logger.info('get valve :',str1)
        self.ser.write(str1.encode())
        str1 = self.read() 
        # logger.info("1==============>", str1)
        # str1 = str1.decode()
        # logger.info("2==============>", str1[4:])       
        if (is_float(str1[4:-1]) == True):
            # logger.info('the plunger position is:',str1[4:] , '-->', int(str1[4:-1] ))
            return  int(str1[4:-1])
        else:
            return 0
        
    

    def set_microstep_position(self, axis, mode):
        if (mode==0):
            str1 = '/'+str(axis)+'N'+str(0)+'R\r\n'
        elif (mode==1):
            str1 = '/'+str(axis)+'N'+str(1)+'R\r\n'
        elif (mode==2):
            str1 = '/'+str(axis)+'N'+str(2)+'R\r\n'
        else:
            logger.error('undefined mode')
        # logger.info('set speed:',str1)
        self.ser.write(str1.encode())
        self.read()


    def stop(self, axis):
        str1 = '/'+str(axis)+'TR\r\n'
        self.ser.write(str1.encode())
        self.read()

    def close(self):
        self.ser.close()



    def read(self):
        try:
            cr = "\r".encode()
            response_frame = b''
            response_byte = self._read(size=1)  # read one byte at a time, timeout is set on instance level

            # read until stop byte
            while response_byte != cr:
                response_frame += response_byte
                
                response_byte = self._read(size=1)
                # logger.info(response_byte)
        except:
            # logger.info(response_byte)
            logger.error("exception happened in pump!!")
        else:    
            # logger.info(response_frame)            
            return response_frame
        # res = ser.readline()
        return response_frame




    def _read(self, size):
        """
        Read n=size bytes from serial, if <n bytes are received (serial.read() return because of timeout), raise a timeout.
        """
        recv = self.ser.read(size=size)
        if len(recv) < size:
            logger.error("Error reading pump!!!")
        else:
            return recv


def is_float(element: any) -> bool:
    #If you expect None to be passed:
    if element is None: 
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False
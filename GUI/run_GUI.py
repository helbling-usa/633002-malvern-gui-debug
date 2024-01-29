import  GUI
from    tkinter import * 
import  tkinter.messagebox 
from    config.motor_3axes import motor_3axes as Motors
import  config.Pump as P
import  time
import  u6
import  threading
import  config.MeerstetterTEC as TEC
import  json
import  logging


#------------------- CONSTANTS  -----------------------------------------
BS_THRESHOLD                = 2.5       # Threshold value for bubble sensor 1
BUBBLE_DETECTION_PUMP_SPEED = 50        # speed of pump during bubble detection
DEFAULT_PUMP_SPEEED         = 1000      # speed of pump at start up
GANTRY_VER_SPEED            = 15.0      # vertical gantry speed
GANTRY_HOR_SPEED            = 15.0      # horizontal gantry speed
GANTRY_VER_ACCELERATION     = 1         # vertical gantry acceleration
GANTRY_HOR_ACCELERATION     = 1         # horizontal gantry acceleration
MIXING_ACCELERATION         = 1         # mixing motor acceleration
RPM_2_TML_SPEED             = 0.1365    # conversion from rpm to mixing motor TML unit  (0.267 for Reza's mixer)
TML_LENGTH_2_MM             = 7.5 /1000      # tml unit for length to um
# pumps/valves RS485 addresses
TIRRANT_PUMP_ADDRESS        = 1         # Pump 1
TITRANT_LOOP_ADDRESS        = 2         # pump 1 loop valve
TITRANT_PIPETTE_ADDRESS     = 4         # titrant line: pipette valve
TITRANT_CLEANING_ADDRESS    = 3         # titrant line: cleaning valve
SAMPLE_PUMP_ADDRESS         = 5         # pump 2
SAMPLE_LOOP_ADDRESS         = 6         # pump 2 loop valve
TITRANT_PORT_ADDRESS        = 7         # sample line: titrant port valve
DEGASSER_ADDRESS            = 8         # sample line: degasser valve
SAMPLE_CLEANING_ADDRESS     = 9         # sample line: cleaning valve


#------------------ initialize logger -------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s:%(message)s')
file_handler = logging.FileHandler('error.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)






class run_GUI(GUI.GUI):
    global BUBBLE_DETECTION_PUMP_SPEED
    global DEFAULT_PUMP_SPEEED
    def __init__(self,root):
        super().__init__( root)
        self.root = root
        logger.info("Initializing hardware -------------------------------------")
        self.PortAssignment()
        # self.InitMixerMotor()
        self.Init_Pumps_Valves()
        self.Init__motors_all_axes()            
        self.InitLabjack()
        self.InitTecController()
        self.InitTimer()
        logger.info("Hardware initialiation done")        

        #------------ Setting the inital states/values of the hardware ----------------------
        # self.scalefactor_p1 = 1
        self.microstep_p1 = False         
        self.pump1_scale_factor(9)
        logger.info('\t\tpump 1 mircostep off')
        self.set_step_mode_p1(False)

        self.microstep_p2 = False         
        self.pump2_scale_factor(9)
        logger.info('\t\tpump 2 mircostep off')
        self.set_step_mode_p2(False)
        
        # default bubble sensor = sensor 1
        self.BS= 1        
        
        # logger.info(self.mc.set_temp(35.3))
        # logger.info("----------------------------------------------")
        # #-------- set the motor1 speed to 0
        # self.m1_cur_spd.config(text="0")        
        
        logger.info("------------------------------------------------------------------")
        logger.info('System started successfully.')
        logger.info("Please use the GUI to enter a commamnd ...")
        

    def timerCallback_1(self):  
        global TIRRANT_PUMP_ADDRESS
        global SAMPLE_PUMP_ADDRESS
        # logger.info('--->timer tick')
        #------------------------------- update pump 1 position
        p1_cur_pos = self.pump1.get_plunger_position(TIRRANT_PUMP_ADDRESS)            
        p1_cur_pos = int(p1_cur_pos / self.scalefactor_p1)
        self.p1_cur_pos.config(text = str(p1_cur_pos))
        # logger.info('cur pos:', p1_cur_pos)
        #------------------------------- update pump 2 position
        
        p2_cur_pos = self.pump1.get_plunger_position(SAMPLE_PUMP_ADDRESS)            
        p2_cur_pos = int(p2_cur_pos / self.scalefactor_p2)
        self.p2_cur_pos.config(text = str(p2_cur_pos))
        # logger.info('p2 cur pos:{}'.format( p2_cur_pos))
        # #------------------------------- update  of TEC controller parameters
        self.updateGUI_TectController()
        #-------- update Gantry vertical motor position on GUI ------------------
        self.motors.select_axis(self.AXIS_ID_03)
        p= self.motors.read_actual_position()
        p_mm = TML_LENGTH_2_MM * p
        p_mm_str = "{:.2f}".format(p_mm)
        self.m3_cur_spd.config(text = p_mm_str)
        #-------- update Gantry horizontal motor position on GUI ------------------
        self.motors.select_axis(self.AXIS_ID_02)
        p= self.motors.read_actual_position()
        p_mm = TML_LENGTH_2_MM * p
        p_mm_str = "{:.2f}".format(p_mm)
        self.m2_cur_spd.config(text = p_mm_str)
        #-------- read bubble sensor and update the GUI -------------------------
        self.read_BubbleSensors()
        self.updateGUI_BubbleSensorLEDs()

        #-------- repeat the timer ----------------------------------------------
        self.timer = threading.Timer(1.0, self.timerCallback_1)
        self.timer.start()

        


    def updateGUI_TectController(self):
        # # logger.info(self.mc.get_data())
        tec_dic =  self.mc.get_data()
        obj_temp = round(tec_dic['object temperature'][0], 1)
        target_temp = round(tec_dic['target object temperature'][0], 1)
        TEC_cur_status = tec_dic['loop status'][0]        
        # logger.info('--->obj temp:{} , target temp:{}    status:{}'.format(obj_temp,  target_temp,TEC_cur_status))        
        if (TEC_cur_status== 1):    # 1: ON, 0:OFF, 
            self.t_status.config(text = "ON")                        
        else:
            self.t_status.config(text = "OFF")        
        self.tec_cur_tmp.config(text=str(obj_temp))
        self.tec_desired_tmp.config(text=str(target_temp))


    def Init_Pumps_Valves(self):        
        global TIRRANT_PUMP_ADDRESS, TITRANT_LOOP_ADDRESS, TITRANT_CLEANING_ADDRESS
        global TITRANT_PIPETTE_ADDRESS, SAMPLE_PUMP_ADDRESS, SAMPLE_LOOP_ADDRESS 
        global TITRANT_PORT_ADDRESS, DEGASSER_ADDRESS, SAMPLE_CLEANING_ADDRESS 
        # # #------ init. Pump 1
        # logger.info("Initializing Pumps/Valves.....")
        com_port = self.PUMP1_PORT
        self.pump1 = P.Pump(com_port)
        
        # self.pump1.pump_Zinit(1)
        # logger.info("\t\tPump1 initialized")
        # time.sleep(3)
        
        # self.pump1.pump_Zinit(5)
        # logger.info("\t\tPump2 initialized")
        # time.sleep(3)

        #init. pumps speeds
        self.pump1.set_speed(TIRRANT_PUMP_ADDRESS,DEFAULT_PUMP_SPEEED)
        logger.info("\t\tPump1 speed is set to {}".format(DEFAULT_PUMP_SPEEED))
        self.p1_cur_spd.config(text = str(DEFAULT_PUMP_SPEEED))

        self.p1_top_spd = DEFAULT_PUMP_SPEEED

        self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,DEFAULT_PUMP_SPEEED)
        logger.info("\t\tPump2 speed is set to {}".format(DEFAULT_PUMP_SPEEED))
        self.p2_cur_spd.config(text = str(DEFAULT_PUMP_SPEEED))

        self.p2_top_spd = DEFAULT_PUMP_SPEEED



        logger.info("\t\tSetting valves to default positions")
        self.pump1.set_valve(TIRRANT_PUMP_ADDRESS, 'E')
        self.v1_cur_pos.config(text="Pump to Air (P1)")
        self.combo1.current(0)

        self.pump1.set_valve(TITRANT_LOOP_ADDRESS, 'E')
        self.v3_cur_pos.config(text="Pump to Line (P1)")
        self.combo3.current(0)

        self.pump1.set_multiwayvalve(TITRANT_PIPETTE_ADDRESS,3)
        self.v5_cur_pos.config(text="Titrant Cannula(P3)")
        self.combo5.current(2)

        self.pump1.set_multiwayvalve(TITRANT_CLEANING_ADDRESS,1)        
        self.v9_cur_pos.config(text="Air (P1)")
        self.combo9.current(0)

        self.pump1.set_valve(SAMPLE_PUMP_ADDRESS, 'E')
        self.v2_cur_pos.config(text="Pump to Line (P1)")
        self.combo2.current(0)

        self.pump1.set_valve(SAMPLE_LOOP_ADDRESS, 'E')
        self.v4_cur_pos.config(text="Pump to Line (P1)")
        self.combo4.current(0)

        self.pump1.set_multiwayvalve(TITRANT_PORT_ADDRESS,3)
        self.v6_cur_pos.config(text="Titrant Cannula(P3)")
        self.combo6.current(2)

        self.pump1.set_multiwayvalve(DEGASSER_ADDRESS,1)        
        self.v7_cur_pos.config(text="Sample Port (P2)")
        self.combo7.current(1)

        self.pump1.set_multiwayvalve(SAMPLE_CLEANING_ADDRESS,1)        
        self.v8_cur_pos.config(text="WI Water(P4)")
        self.combo8.current(3)

        # init. scale factors 
        self.comboCfg1.current(8)
        self.pump1_scale_factor(9)

        self.comboCfg2.current(8)
        self.pump2_scale_factor(9)



    def InitLabjack(self):
        # # initialize labjack
        logger.info("Initializing Labjack.....")
        self.labjack = u6.U6()
        self.labjack.writeRegister(50590, 15)        
        logger.info('\t\tlabjack initialized')
        # pass


    def InitTimer(self):
        # #------ Starts timer
        logger.info('starting internal timer')
        self.timer = threading.Timer(1.0, self.timerCallback_1)
        self.timer.start()
        logger.info('\t\tInternal timer started')
        #pass


    def InitTecController(self):
        # ------create object of TEC5 
        logger.info("Initialzing TEC Temperature Controller---------------------")
        # self.mc = TEC.MeerstetterTEC("COM5")
        self.mc = TEC.MeerstetterTEC(self.TEC_PORT)
        # logger.info(self.mc.get_data())
        logger.info("\t\tTEC controller initialized ")


    def read_BubbleSensors(self):
        # read bubble sensor and update the LEDs
        self.BS0 = (self.labjack.getAIN(0))
        self.BS1 = (self.labjack.getAIN(1))
        self.BS2 = (self.labjack.getAIN(2))
        self.BS3 = (self.labjack.getAIN(3))
        self.BS4 = (self.labjack.getAIN(4))
        self.BS5 = (self.labjack.getAIN(5))
        self.BS6 = (self.labjack.getAIN(6))
        self.BS7 = (self.labjack.getAIN(7))
        self.BS8 = (self.labjack.getAIN(8))
        self.BS9 = (self.labjack.getAIN(9))
        self.BS10 = (self.labjack.getAIN(10))
        self.BS11 = (self.labjack.getAIN(11))
        self.BS12 = (self.labjack.getAIN(12))
        self.BS13 = (self.labjack.getAIN(13))


    def updateGUI_BubbleSensorLEDs(self):
        global BS_THRESHOLD
        
        # Update The GUI with current value of bubble sensors
        X3 = 1050
        Y1 = 100
        dY1 = 40
        dd=50
        if (self.BS0 < BS_THRESHOLD):
            self.led_on_1.place_forget()
            self.led_off_1.pack()
            self.led_off_1.place(x = X3+50,y = Y1 + 0*dY1)
        else:
            self.led_off_1.place_forget()
            self.led_on_1.pack()            
            self.led_on_1.place(x = X3+50,y = Y1 + 0*dY1)

        if (self.BS1 < BS_THRESHOLD):
            self.led_on_2.place_forget()
            # self.led_off_14.pack()
            self.led_off_2.place(x = X3+50,y = Y1 + 1*dY1)
        else:
            self.led_off_2.place_forget()
            # self.led_on_14.pack()            
            self.led_on_2.place(x = X3+50,y = Y1 + 1*dY1)

        if (self.BS2 < BS_THRESHOLD):
            self.led_on_3.place_forget()
            # self.led_off_14.pack()
            self.led_off_3.place(x = X3+50,y = Y1 + 2*dY1)
        else:
            self.led_off_3.place_forget()
            # self.led_on_14.pack()            
            self.led_on_3.place(x = X3+50,y = Y1 + 2*dY1)

        if (self.BS3 < BS_THRESHOLD):
            self.led_on_4.place_forget()
            # self.led_off_14.pack()
            self.led_off_4.place(x = X3+50,y = Y1 + 3*dY1)
        else:
            self.led_off_4.place_forget()
            # self.led_on_14.pack()            
            self.led_on_4.place(x = X3+50,y = Y1 + 3*dY1)

        if (self.BS4 < BS_THRESHOLD):
            self.led_on_5.place_forget()
            # self.led_off_14.pack()
            self.led_off_5.place(x = X3+50,y = Y1 + 4*dY1)
        else:
            self.led_off_5.place_forget()
            # self.led_on_14.pack()            
            self.led_on_5.place(x = X3+50,y = Y1 + 4*dY1)
            
        if (self.BS5 < BS_THRESHOLD):
            self.led_on_6.place_forget()
            # self.led_off_14.pack()
            self.led_off_6.place(x = X3+50,y = Y1 + 5*dY1)
        else:
            self.led_off_6.place_forget()
            # self.led_on_14.pack()            
            self.led_on_6.place(x = X3+50,y = Y1 + 5*dY1)

        if (self.BS6 < BS_THRESHOLD):
            self.led_on_7.place_forget()
            # self.led_off_14.pack()
            self.led_off_7.place(x = X3+50,y = Y1 + 6*dY1)
        else:
            self.led_off_7.place_forget()
            # self.led_on_14.pack()            
            self.led_on_7.place(x = X3+50,y = Y1 + 6*dY1)
        
        if (self.BS7 < BS_THRESHOLD):
            self.led_on_8.place_forget()
            # self.led_off_14.pack()
            self.led_off_8.place(x = X3+50,y = Y1 + 7*dY1)
        else:
            self.led_off_8.place_forget()
            # self.led_on_14.pack()            
            self.led_on_8.place(x = X3+50,y = Y1 + 7*dY1)

        if (self.BS8 < BS_THRESHOLD):
            self.led_on_9.place_forget()
            # self.led_off_14.pack()
            self.led_off_9.place(x = X3+50,y = Y1 + 8*dY1)
        else:
            self.led_off_9.place_forget()
            # self.led_on_14.pack()            
            self.led_on_9.place(x = X3+50,y = Y1 + 8*dY1)

        if (self.BS9< BS_THRESHOLD):
            self.led_on_10.place_forget()
            # self.led_off_14.pack()
            self.led_off_10.place(x = X3+50,y = Y1 + 9*dY1)
        else:
            self.led_off_10.place_forget()
            # self.led_on_14.pack()            
            self.led_on_10.place(x = X3+50,y = Y1 + 9*dY1)

        if (self.BS10 < BS_THRESHOLD):
            self.led_on_11.place_forget()
            # self.led_off_14.pack()
            self.led_off_11.place(x = X3+50,y = Y1 + 10*dY1)
        else:
            self.led_off_11.place_forget()
            # self.led_on_14.pack()            
            self.led_on_11.place(x = X3+50,y = Y1 + 10*dY1)

        if (self.BS11 < BS_THRESHOLD):
            self.led_on_12.place_forget()
            # self.led_off_14.pack()
            self.led_off_12.place(x = X3+50,y = Y1 + 11*dY1)
        else:
            self.led_off_12.place_forget()
            # self.led_on_14.pack()            
            self.led_on_12.place(x = X3+50,y = Y1 + 11*dY1)

        if (self.BS13 < BS_THRESHOLD):
            self.led_on_13.place_forget()
            # self.led_off_14.pack()
            self.led_off_13.place(x = X3+50,y = Y1 + 12*dY1)
        else:
            self.led_off_13.place_forget()
            # self.led_on_14.pack()            
            self.led_on_13.place(x = X3+50,y = Y1 + 12*dY1)

        if (self.BS13 < BS_THRESHOLD):
            self.led_on_14.place_forget()
            self.led_off_14.pack()
            self.led_off_14.place(x = X3+50,y = Y1 + 13*dY1)
        else:
            self.led_off_14.place_forget()
            self.led_on_14.pack()
            self.led_on_14.place(x = X3+50,y = Y1 + 13*dY1)  




    def PortAssignment(self):
        global TIRRANT_PUMP_ADDRESS, TITRANT_LOOP_ADDRESS, TITRANT_CLEANING_ADDRESS
        global TITRANT_PIPETTE_ADDRESS, SAMPLE_PUMP_ADDRESS ,SAMPLE_LOOP_ADDRESS 
        global TITRANT_PORT_ADDRESS, DEGASSER_ADDRESS ,SAMPLE_CLEANING_ADDRESS

        logger.info("Assigning Ports .....")
        # #---- extract port numbers for config.json
        with open('./config/config.json') as json_file:
            ports = json.load(json_file)
        #assign port numbers to the hardware
        # logger.info('ports:', ports)
        self.TEC_PORT = ports['TEC']
        self.PUMP1_PORT = ports['PUMP']
        self.TECHNOSOFT_PORT = ports['TECHNOSOFT']
        self.GANTRY_VER_AXIS_ID = int(ports['GANTRY_VER_AXIS_ID'])
        self.GANTRY_HOR_AXIS_ID = int(ports['GANTRY_HOR_AXIS_ID'])
        self.MIXER_AXIS_ID = int(ports['MIXER_AXIS_ID'])        

        self.AXIS_ID_01 = self.MIXER_AXIS_ID
        self.AXIS_ID_02 = self.GANTRY_HOR_AXIS_ID
        self.AXIS_ID_03 = self.GANTRY_VER_AXIS_ID
        
        logger.info('\t\tTEC:'+ self.TEC_PORT)
        logger.info('\t\tTechnosoft:'+self.TECHNOSOFT_PORT )
        logger.info('\t\tPump:'+ self.PUMP1_PORT)
        logger.info('\t\tMixer Axis ID:'+ str(self.MIXER_AXIS_ID))
        logger.info('\t\tGantry Vertical Axis ID:'+ str(self.GANTRY_VER_AXIS_ID))
        logger.info("\t\tPort Assignment done")
        # # Display port numbers on the GUI (config tab)
        self.Ltecport.config(text=self.TEC_PORT)
        self.Lpump1port.config(text=self.PUMP1_PORT)
        self.Ltechnosoftport.config(text=self.TECHNOSOFT_PORT)
        self.Lver_gant_axis_id.config(text=self.GANTRY_VER_AXIS_ID)
        self.Lmixer_axis_id.config(text=self.MIXER_AXIS_ID)
        self.Lhor_gant_axis_id.config(text=self.GANTRY_HOR_AXIS_ID)
        self.Lpump1_id.config(text=str(TIRRANT_PUMP_ADDRESS))
        self.Lvalv3_id.config(text=str(TITRANT_LOOP_ADDRESS))
        self.Lvalv5_id.config(text=str(TITRANT_PIPETTE_ADDRESS))
        self.Lvalv9_id.config(text=str(TITRANT_CLEANING_ADDRESS))
        self.Lpump2_id.config(text=str(SAMPLE_PUMP_ADDRESS))
        self.Lvalv4_id.config(text=str(SAMPLE_LOOP_ADDRESS))
        self.Lvalv6_id.config(text=str(TITRANT_PORT_ADDRESS))
        self.Lvalv7_id.config(text=str(DEGASSER_ADDRESS))
        self.Lvalv8_id.config(text=str(SAMPLE_CLEANING_ADDRESS))

        



    def p1_b_init_pump1(self):
        logger.debug("child:init pump 1")
        self.pump1.pump_Zinit(1)
        logger.info("\t\tPump1 initialized")
        time.sleep(3)


    def p2_b_init_pump2(self):
        logger.debug("child:init pump 2")
        
        self.pump1.pump_Zinit(5)
        logger.info("\t\tPump2 initialized")
        time.sleep(3)



    def gantry_vertical_set_rel_click(self):
        global GANTRY_VER_SPEED
        global GANTRY_VER_ACCELERATION
        s = self.ent_gnt_ver_rel.get()
        # logger.info('child-->'+s)
        if (is_float(s) == True):
            #logger.info("----------MOVE Relative-----------------")
            rel_pos_mm =float(s)
            self.motors.select_axis(self.AXIS_ID_03)
            self.motors.set_POSOKLIM(1)
            rel_pos_tml = int(rel_pos_mm / TML_LENGTH_2_MM )
            val = self.motors.move_relative_position(rel_pos_tml, GANTRY_VER_SPEED, GANTRY_VER_ACCELERATION)
            if val == -2:
                tkinter.messagebox.showwarning("WARNING!!!",  "The actuator has reached its POSITIVE LIMIT."
                                "\nPlease move thea actuator within the limit") 
        else:
            logger.info("Not a number. Please enter an integer for VG rel. position")



    def gantry_vertical_set_abs_click(self):
        global GANTRY_VER_SPEED
        global GANTRY_VER_ACCELERATION
        s = self.ent_gnt_ver_abs.get()
        if (is_float(s) == True):
            #logger.info("----------MOVE Absolute-----------------")
            abs_pos_mm =float(s)
            self.motors.select_axis(self.AXIS_ID_03)
            self.motors.set_POSOKLIM(1)
            abs_pos_tml = int(abs_pos_mm / TML_LENGTH_2_MM )
            self.motors.move_absolute_position(abs_pos_tml, GANTRY_VER_SPEED, GANTRY_VER_ACCELERATION)
        else:
            logger.info("Not a number. Please enter an integer for VG abs. position")        
        

    def gantry_vertical_homing_click(self):
        logger.debug('Homing Gantry Vertical')
        self.motors.homing(self.AXIS_ID_03)
        
        
    def gantry_horizontal_homing_click(self):
        logger.debug('Homing Gantry Horizontal')
        self.motors.homing(self.AXIS_ID_02)


    def gantry_horizontal_set_rel_click(self):
        global GANTRY_HOR_SPEED
        global GANTRY_HOR_ACCELERATION
        s = self.ent_gnt_hor_rel.get()
        if (is_float(s) == True):
            #logger.info("----------MOVE Relative-----------------")
            rel_pos_mm =float(s)
            self.motors.select_axis(self.AXIS_ID_02)
            self.motors.set_POSOKLIM(1)
            rel_pos_tml = int(rel_pos_mm / TML_LENGTH_2_MM )
            val = self.motors.move_relative_position(rel_pos_tml, GANTRY_HOR_SPEED, GANTRY_HOR_ACCELERATION)
            if val == -2:
                tkinter.messagebox.showwarning("WARNING!!!",  "The actuator has reached its POSITIVE LIMIT."
                                "\nPlease move thea actuator within the limit") 

        else:
            logger.info("Not a number. Please enter an integer for VG rel. position")




    def gantry_horizontal_set_abs_click(self):
        global GANTRY_HOR_SPEED
        global GANTRY_HOR_ACCELERATION
        s = self.ent_gnt_hor_abs.get()
        if (is_float(s) == True):
            #logger.info("----------MOVE Absolute-----------------")
            abs_pos_mm =float(s)
            self.motors.select_axis(self.AXIS_ID_02)
            self.motors.set_POSOKLIM(1)
            abs_pos_tml = int(abs_pos_mm / TML_LENGTH_2_MM )
            self.motors.move_absolute_position(abs_pos_tml, GANTRY_HOR_SPEED, GANTRY_HOR_ACCELERATION)
        else:
            logger.info("Not a number. Please enter an integer for VG abs. position")        
                
        

    def Init__motors_all_axes(self):
        logger.info("Initializing motors .....")        
        com_port = self.TECHNOSOFT_PORT.encode()        
        primary_axis =  b"Mixer"
        self.motors = Motors(com_port, self.AXIS_ID_01, self.AXIS_ID_02, self.AXIS_ID_03 ,primary_axis)   
        #/*	Setup and initialize the axis */	
        if (self.motors.InitAxis()==False):
            logger.error("Failed to start up the Technosoft drive")    
        logger.info("\t\tMotors are Initialized")        


        self.motors.select_axis(self.AXIS_ID_02)

            # print("---------get FM VER -------------------")
        self.motors.get_firmware_version()

        # print("----------set position-----------------")
        self.motors.set_position()

        # print("------------set int var ------------------------------")
        self.motors.set_POSOKLIM(2)


    def InitMixerMotor(self):
        # # #------ init. motor 1
        # # logger.info("Initializing Motors.....")
        # # self.motor1 = Motor1.motor_1(0,1.5)
        # # logger.info("\t\tMotors Initialized")

        # #------ init. motors: Gantry vertical 
        pass


    def tec_b_tmpset_click(self):        
        s =   self.ent_tmp.get()
        logger.info("TEC Controller new target tmp: {}".format(s))
        if (is_float(s) == True):
            self.mc.set_temp(float(s))
        else:
            logger.error("invalid input")


    def tec_b_start_click(self):
        logger.info("TEC Controller Enabled")
        self.mc.enable()


    def tec_b_stop_click(self):
        logger.info("TEC Controller Disabled")
        self.mc.disable()


    def checkComboCfg1(self, event):
        s = self.comboCfg1.get()
        logger.debug('pump1 config: :{}'.format( s))
        ss=s.partition(')')
        # index = self.comboCfg1.get(0, "end") 
        index = ss[0]
        # logger.info('int number:{}'.format( int(index)))        
        # logger.info("INDEX = ", index)
        self.pump1_scale_factor(int(index))
        if (self.microstep_p1 == False):
            logger.info('pump 1 mircostep off')
            self.set_step_mode_p1(False)            
        else:  #self.microstep_p1 = True
            logger.info('pump 1 mircostep on')
            self.set_step_mode_p1(True)
            

    def p2_b_top_spd_click(self):    
        global SAMPLE_PUMP_ADDRESS    
        s =   self.ent_top_spd2.get()        
        logger.info("pump2 top speed: {}".format(s))
        if (is_float(s) == True):
            self.p2_top_spd = int(s)
            self.pump1.set_speed(SAMPLE_PUMP_ADDRESS, self.p2_top_spd)
            time.sleep(.25)
            self.p2_cur_spd.config(text = s)
            




    def checkComboCfg2(self, event):
        # def option_selected(event):
        # logger.info('child:{}'.format( self.comboCfg2.get()))
        s = self.comboCfg2.get()
        logger.debug('pump2 config: :{}'.format( s))
        ss=s.partition(')')
        # index = self.comboCfg1.get(0, "end") 
        index = ss[0]
        # logger.info('int number:{}'.format( int(index)))        
        # logger.info("INDEX = ", index)
        self.pump2_scale_factor(int(index))
        if (self.microstep_p2 == False):
            logger.info('pump 2 mircostep off')
            self.set_step_mode_p2(False)            
        else:  #self.microstep_p1 = True
            logger.info('pump 2 mircostep on')
            self.set_step_mode_p2(True)



    def p2_b_abs_pos_click(self):
        global SAMPLE_PUMP_ADDRESS
        s =   self.ent_abs_pos2.get()
        # print("=========================")
        logger.info(s)
        if (is_float(s) == True):
            val = int(s)            
            abs_pos = int(val * self.scalefactor_p2)
            logger.debug("pump2: set abs. pos:{} . after scaling:{}".format(s, abs_pos))
            self.pump1.set_pos_absolute(SAMPLE_PUMP_ADDRESS, abs_pos)


    def p2_b_pickup_pos_click(self):
        global SAMPLE_PUMP_ADDRESS
        logger.info("P2_pickup ")
        s =   self.ent_pickup_pos2.get()
        if (is_float(s) == True):
            val = int(s)
            logger.debug("pump2: set pickup pos:{}".format(s))
            rel_pos = int(val * self.scalefactor_p2)            
            self.pump1.set_pickup(SAMPLE_PUMP_ADDRESS, rel_pos)


    def p2_b_dispense_pos_click(self):
        global SAMPLE_PUMP_ADDRESS
        s =   self.ent_dispemse_pos2.get()
        logger.info("P2_dispense ")
        if (is_float(s) == True):
            val = int(s)
            logger.debug("pump2: set dispense pos:{}".format(s))
            rel_pos = int(val * self.scalefactor_p2)            
            self.pump1.set_dispense(SAMPLE_PUMP_ADDRESS, rel_pos)


                
    def m1_b_stop_click(self):
        global MIXING_ACCELERATION
        self.motors.select_axis(self.AXIS_ID_01)
        speed =0
        acceleration = MIXING_ACCELERATION#1
        self.motors.set_speed(speed,acceleration)       
        self.m1_cur_spd.config(text='0')


    def m1_b_SetSpeed(self):
        global MIXING_ACCELERATION
        global RPM_2_TML_SPEED
        # logger.info("child: m1_new_spd")
        s =   self.ent_m1_spd_.get()
        # logger.info(s)
        if (is_float(s) == True):            
            self.motors.select_axis(self.AXIS_ID_01)
            speed =float(s)
            acceleration = MIXING_ACCELERATION#1
            new_speed = speed  * RPM_2_TML_SPEED
            logger.debug('\t\tmixing motor speed:{}rpm = {}TML unit'.format( speed, new_speed))
            self.motors.set_speed(new_speed,acceleration)    

            self.m1_cur_spd.config(text=s)    
        else:
            logger.warning("Not a number. Plaese enter an integer for speed.")
            


    def p1_b_abs_pos_click(self):
        global TIRRANT_PUMP_ADDRESS        
        s =   self.ent_abs_pos.get()
        if (is_float(s) == True):
            val = int(s)
            logger.debug("pump1: set abs. pos:{}".format(s))
            abs_pos = int(val * self.scalefactor_p1)
            self.pump1.set_pos_absolute(TIRRANT_PUMP_ADDRESS, abs_pos)



    def p1_b_pickup_pos_click(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info("P1_pickup ")
        s =   self.ent_pickup_pos.get()
        if (is_float(s) == True):
            val = int(s)
            logger.debug("pump1: set pickup pos:{}".format(s))
            # logger.info(int(s))
            rel_pos = int(val * self.scalefactor_p1)            
            self.pump1.set_pickup(TIRRANT_PUMP_ADDRESS, rel_pos)


    def p1_b_dispense_pos_click(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info("P1_dispense ")
        s =   self.ent_dispemse_pos.get()
        if (is_float(s) == True):
            val = int(s)
            logger.debug("pump1: set dispense pos:{}".format(s))
            # logger.info(int(s))
            rel_pos = int(val * self.scalefactor_p1)            
            self.pump1.set_dispense(TIRRANT_PUMP_ADDRESS,rel_pos)


    def p1_b_teminateP1(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info('Termnate pump1')
        self.pump1.stop(TIRRANT_PUMP_ADDRESS)



    def p1_b_dispenseUntillbubble(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info('Dispense until bubble')
        self.pump1.set_speed(TIRRANT_PUMP_ADDRESS, BUBBLE_DETECTION_PUMP_SPEED)
        time.sleep(1)        
        self.pump1.set_pos_absolute(TIRRANT_PUMP_ADDRESS, 0)
        # input0 = (self.labjack.getAIN(0))
        input0 = (self.labjack.getAIN(self.BS - 1))
        #check if the bubble semsor detect air or liquid
        cur_state = self.air_or_liquid(input0)
        prev_state = cur_state
        while (cur_state == prev_state):
            prev_state = cur_state
            input0 = (self.labjack.getAIN(self.BS - 1))
            cur_state = self.air_or_liquid(input0)
            logger.info('        selcted BS {}  , position:{}'.format(self.BS,self.pump1.get_plunger_position(TIRRANT_PUMP_ADDRESS)))
            time.sleep(.05)
        self.pump1.stop(TIRRANT_PUMP_ADDRESS)
        logger.info('\t\tBubble detection terminated')
        self.pump1.set_speed(TIRRANT_PUMP_ADDRESS, DEFAULT_PUMP_SPEEED)




    def p1_b_pickupUntillbubble(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info("Pump 1: Pickup until bubble")
        self.pump1.set_speed(TIRRANT_PUMP_ADDRESS, BUBBLE_DETECTION_PUMP_SPEED)
        time.sleep(1)        
        self.pump1.set_pos_absolute(TIRRANT_PUMP_ADDRESS, 20000)
        input0 = (self.labjack.getAIN(self.BS - 1))
        #check if the bubble semsor detect air or liquid
        cur_state = self.air_or_liquid(input0)
        prev_state = cur_state
        while (cur_state == prev_state):
            prev_state = cur_state
            input0 = (self.labjack.getAIN(self.BS - 1))
            cur_state = self.air_or_liquid(input0)
            logger.info('        selcted BS {}  , position:{}'.format(self.BS,self.pump1.get_plunger_position(TIRRANT_PUMP_ADDRESS)))
            time.sleep(.05)
        self.pump1.stop(TIRRANT_PUMP_ADDRESS)
        logger.info('\t\tBubble detection terminated')
        self.pump1.set_speed(TIRRANT_PUMP_ADDRESS,DEFAULT_PUMP_SPEEED)




    def air_or_liquid(self, voltage):
        if voltage > BS_THRESHOLD:
            return 'liquid'
        else:
            return 'air'




    def p2_b_pickupUntillbubble(self):
        global SAMPLE_PUMP_ADDRESS
        logger.info("Pump 2: Pickup until bubble")
        self.pump1.set_speed(SAMPLE_PUMP_ADDRESS, BUBBLE_DETECTION_PUMP_SPEED)
        time.sleep(1)        
        self.pump1.set_pos_absolute(SAMPLE_PUMP_ADDRESS, 20000)
        # input0 = (self.labjack.getAIN(0))
        input0 = (self.labjack.getAIN(self.BS - 1))
        #check if the bubble semsor detect air or liquid
        cur_state = self.air_or_liquid(input0)
        prev_state = cur_state
        while (cur_state == prev_state):
            prev_state = cur_state
            input0 = (self.labjack.getAIN(self.BS - 1))
            cur_state = self.air_or_liquid(input0)
            logger.info('        selcted BS {}  , position:{}'.format(self.BS,self.pump1.get_plunger_position(SAMPLE_PUMP_ADDRESS)))
            time.sleep(.05)
        self.pump1.stop(SAMPLE_PUMP_ADDRESS)
        logger.info('\t\tBubble detection terminated')
        self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,DEFAULT_PUMP_SPEEED)




    def p2_b_dispenseUntillbubble(self):
        global SAMPLE_PUMP_ADDRESS
        logger.info('Pump 2: Dispense until bubble')
        self.pump1.set_speed(SAMPLE_PUMP_ADDRESS, BUBBLE_DETECTION_PUMP_SPEED)
        time.sleep(1)        
        self.pump1.set_pos_absolute(SAMPLE_PUMP_ADDRESS, 0)
        input0 = (self.labjack.getAIN(self.BS - 1))
        #check if the bubble semsor detect air or liquid
        cur_state = self.air_or_liquid(input0)
        prev_state = cur_state
        while (cur_state == prev_state):
            prev_state = cur_state
            input0 = (self.labjack.getAIN(self.BS - 1))
            cur_state = self.air_or_liquid(input0)
            logger.info('        selcted BS {}  , position:{}'.format(self.BS,self.pump1.get_plunger_position(SAMPLE_PUMP_ADDRESS)))
            time.sleep(.05)
        self.pump1.stop(SAMPLE_PUMP_ADDRESS)
        logger.info('\t\tBubble detection terminated')
        self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,DEFAULT_PUMP_SPEEED)




        
    def p2_b_teminateP2(self):
        global SAMPLE_PUMP_ADDRESS
        logger.info('Termnate pump2')
        self.pump1.stop(SAMPLE_PUMP_ADDRESS)


    def p1_b_top_spd_click(self):   
        global TIRRANT_PUMP_ADDRESS     
        s =   self.ent_top_spd.get()
        logger.info("p1_top speed: {}".format(s))
        if (is_float(s) == True):
            self.p1_top_spd = int(s)
            self.pump1.set_speed(TIRRANT_PUMP_ADDRESS, self.p1_top_spd)
            time.sleep(.25)
            self.p1_cur_spd.config(text = s)




    #Pump Valve (Titrant line)
    def checkCombo1(self,event):
        global TIRRANT_PUMP_ADDRESS
        s = self.combo1.get()
        # logger.info('child -->'+s)
        # ("Pump to Air (P1)","Air to Gas (P2)","Gas to Line (P3)",
        #                          "Line to Pump (P4)")
        if (s == "Pump to Air (P1)"):
            # logger.info(" P1   --- E ")
            new_valve_pos = 'E'
        elif (s == "Air to Gas (P2)"):
            # logger.info(" P2 ---- O")
            new_valve_pos = 'O'
        elif (s == "Gas to Line (P3)"):
            # logger.info(" P3 --- I")
            new_valve_pos = 'I'
        elif (s == "Line to Pump (P4)"):
            # logger.info(" P4 ---- B ")
            new_valve_pos = 'B'
        else:
            logger.info(' invalid valve selection')
            new_valve_pos = 'E'
        self.pump1.set_valve(TIRRANT_PUMP_ADDRESS, new_valve_pos)
        time.sleep(1)
        s = self.pump1.get_valve(TIRRANT_PUMP_ADDRESS)
        # logger.info("-----> ",s)
        cur_valve = "----"
        if (s=='e'):
            cur_valve = "Pump to Air (P1)"
            # logger.info('EEEE')
        elif(s=='o'):
            cur_valve = "Air to Gas (P2)"
            # logger.info('OOOO')
        elif(s=="i"):
            cur_valve = "Gas to Line (P3)"
            # logger.info("IIII")
        elif(s=="b"):
            cur_valve = "Line to Pump (P4)"
            # logger.info("BBBB")
        else:
            cur_valve = "error"

        self.v1_cur_pos.config(text=cur_valve)


    #Loop Valve (Titrant line)
    def checkCombo3(self, event):
        global TITRANT_LOOP_ADDRESS
        s = self.combo3.get()
        if (s == "Gas to Line (P1)"):
            new_valve_pos = 'E'
        elif (s == "Line to Pump (P2)"):
            new_valve_pos = 'O'
        elif (s == "Pump to Air (P3)"):
            new_valve_pos = 'I'
        elif (s == "Air to Pump (P4)"):
            new_valve_pos = 'B'
        else:
            logger.info(' invalid valve selection')
            new_valve_pos = 'E'
        self.pump1.set_valve(TITRANT_LOOP_ADDRESS, new_valve_pos)
        time.sleep(1)
        s = self.pump1.get_valve(TITRANT_LOOP_ADDRESS)
        cur_valve = "----"
        if (s=='e'):
            cur_valve = "Gas to Line (P1)"
        elif(s=='o'):
            cur_valve = "Line to Pump (P2)"
        elif(s=="i"):
            cur_valve = "Pump to Air (P3)"
        elif(s=="b"):
            cur_valve = "Air to Pump (P4)"
        else:
            cur_valve = "error"
        self.v3_cur_pos.config(text=cur_valve)


    #Pipette Valve (Titrant line)
    def checkCombo5(self, event):
        global TITRANT_PIPETTE_ADDRESS
        s = self.combo5.get()
        if (s == "Titrant Port (P1)"):
            vlv = 1
        elif (s == "Reservoirs (P2)"):
            vlv = 2
        elif (s == "Titrant Cannula(P3)"):
            vlv = 3
        else:
            logger.info(' invalid valve selection')
            vlv = 2

        self.pump1.set_multiwayvalve(TITRANT_PIPETTE_ADDRESS,vlv)
        time.sleep(1)
        s = self.pump1.get_valve(TITRANT_PIPETTE_ADDRESS)
        cur_valve = "----"
        if (s=='1'):
            cur_valve = "Titr. Port (P1)"
        elif(s=='2'):
            cur_valve = "Reservoirs (P2)"
        elif(s=='3'):
            cur_valve = "Titr. Cann.(P3)"
        else:
            cur_valve = "error"

        self.v5_cur_pos.config(text=cur_valve)


    #Cleaning Vlave (Titrant line)
    def checkCombo9(self, event):
        global TITRANT_CLEANING_ADDRESS
        s = self.combo9.get()
        if (s == "Air (P1)"):
            new_valve_pos = 1
        elif (s == "MeOH (P2)"):
            new_valve_pos = 2
        elif (s == "Detergent (P3)"):
            new_valve_pos = 3
        elif (s == "DI Water (P4)"):
            new_valve_pos = 4
        elif (s == "Waster (P5)"):
            new_valve_pos = 5
        elif (s == "Cleaning Port (P6)"):
            new_valve_pos = 6
        else:
            logger.info(' invalid valve selection')
            new_valve_pos = 1

        self.pump1.set_multiwayvalve(TITRANT_CLEANING_ADDRESS,new_valve_pos)
        time.sleep(1)
        s = self.pump1.get_valve(TITRANT_CLEANING_ADDRESS)
        cur_valve = "----"
        if (s=='1'):
            cur_valve = "Air (P1)"
        elif(s=='2'):
            cur_valve = "MeOH (P2)"
        elif(s=="3"):
            cur_valve = "Detergent (P3)"
        elif(s=="4"):
            cur_valve = "DI Water (P4)"
        elif(s=="5"):
            cur_valve = "Waster (P5)"
        elif(s=="6"):
            cur_valve = "Clean. Port (P6)"
        else:
            cur_valve = "error"

        self.v9_cur_pos.config(text=cur_valve)




    #Pump Valve (Sample line)
    def checkCombo2(self,event):
        global SAMPLE_PUMP_ADDRESS
        s = self.combo2.get()
        if (s == "Pump to  Line(P1)"):
            new_valve_pos = 'E'
        elif (s == "Line to Gas(P2)"):
            new_valve_pos = 'O'
        elif (s == "Gas to Air(P3)"):
            new_valve_pos = 'I'
        elif (s == "Air to Pump(P4)"):
            new_valve_pos = 'B'
        else:
            logger.info(' invalid valve selection')
            new_valve_pos = 'E'
        self.pump1.set_valve(SAMPLE_PUMP_ADDRESS, new_valve_pos)
        time.sleep(1)
        s = self.pump1.get_valve(SAMPLE_PUMP_ADDRESS)
        cur_valve = "----"
        if (s=='e'):
            cur_valve = "Pump to  Line(P1)"
        elif(s=='o'):
            cur_valve = "Line to Gas(P2)"
        elif(s=="i"):
            cur_valve = "Gas to Air(P3)"
        elif(s=="b"):
            cur_valve = "Air to Pump(P4)"
        else:
            cur_valve = "error"

        self.v2_cur_pos.config(text=cur_valve)


    #Loop Valve (Sample line)
    def checkCombo4(self,event):
        global SAMPLE_LOOP_ADDRESS
        s = self.combo4.get()        
        if (s == "Pump to Line(P1)"):
            new_valve_pos = 'E'
        elif (s == "Line to Gas(P2)"):
            new_valve_pos = 'O'
        elif (s == "Gas to Air(P3)"):
            new_valve_pos = 'I'
        elif (s == "Air to Pump(P4)"):
            new_valve_pos = 'B'
        else:
            logger.info(' invalid valve selection')
            new_valve_pos = 'E'
        self.pump1.set_valve(SAMPLE_LOOP_ADDRESS, new_valve_pos)
        time.sleep(1)
        s = self.pump1.get_valve(SAMPLE_LOOP_ADDRESS)
        cur_valve = "----"
        if (s=='e'):
            cur_valve = "Pump to Line(P1)"
        elif(s=='o'):
            cur_valve = "Line to Gas(P2)"
        elif(s=="i"):
            cur_valve = "Gas to Air(P3)"
        elif(s=="b"):
            cur_valve = "Air to Pump(P4)"
        else:
            cur_valve = "error"
        
        self.v4_cur_pos.config(text=cur_valve)


    #Titrant Port Valve (Sample line)
    def checkCombo6(self,event):
        global TITRANT_PORT_ADDRESS
        s = self.combo6.get()
        if (s == "Titrant Port(P1)"):
            vlv = 1
        elif (s == "Reservoirs(P2)"):
            vlv = 2
        elif (s == "Titrant Cannula(P3)"):
            vlv = 3
        else:
            logger.error(' invalid valve selection')
            vlv = 2

        self.pump1.set_multiwayvalve(TITRANT_PORT_ADDRESS,vlv)
        time.sleep(1)
        s = self.pump1.get_valve(TITRANT_PORT_ADDRESS)
        # logger.info("----->{}".format(s))
        # print(type(s))
        cur_valve = "----"
        if (s=='1'):
            cur_valve = "Titrant Port(P1)"
            # logger.info('EEEE')
        elif(s=='2'):
            cur_valve = "Reservoirs(P2)"
            # logger.info('OOOO')
        elif(s=='3'):
            cur_valve = "Titrant Cannula(P3)"
            # logger.info("IIII")
        else:
            cur_valve = "error"

        self.v6_cur_pos.config(text=cur_valve)


    #Degrasser Valve (Sample line)         
    def checkCombo7(self,event):
        global DEGASSER_ADDRESS
        s = self.combo7.get()
        if (s == "Titrant Port(P1)"):
            new_valve_pos = 1
        elif (s == "Sample Port(P2)"):
            new_valve_pos = 2
        elif (s == "Ref Port(P3)"):
            new_valve_pos = 3
        elif (s == "Rec Port(P4)"):
            new_valve_pos = 4
        elif (s == "Reservoirs(P5)"):
            new_valve_pos = 5
        elif (s == "Cell(P6)"):
            new_valve_pos = 6
        else:
            logger.error(' invalid valve selection')
            new_valve_pos = 1

        self.pump1.set_multiwayvalve(DEGASSER_ADDRESS,new_valve_pos)
        time.sleep(1)
        s = self.pump1.get_valve(DEGASSER_ADDRESS)
        cur_valve = "----"
        if (s=='1'):
            cur_valve = "Titrant Port(P1)"
        elif(s=='2'):
            cur_valve = "Sample Port(P2)"
        elif(s=="3"):
            cur_valve = "Ref Port(P3)"
        elif(s=="4"):
            cur_valve = "Rec Port(P4)"
        elif(s=="5"):
            cur_valve = "Reservoirs(P5)"
        elif(s=="6"):
            cur_valve = "Cell(P6)"
        else:
            cur_valve = "error"

        self.v7_cur_pos.config(text=cur_valve)


    #Cleaning Valve (Sample line)  
    def checkCombo8(self, event):
        global SAMPLE_CLEANING_ADDRESS 
        s = self.combo8.get()
        if (s == "Air(P1)"):
            new_valve_pos = 1
        elif (s == "MeOH(P2)"):
            new_valve_pos = 2
        elif (s == "Detergent(P3)"):
            new_valve_pos = 3
        elif (s == "WI Water(P4)"):
            new_valve_pos = 4
        elif (s == "Reservoirs(P5)"):
            new_valve_pos = 5
        elif (s == "Cell(P6)"):
            new_valve_pos = 6
        else:
            logger.error(' invalid valve selection')
            new_valve_pos = 1

        self.pump1.set_multiwayvalve(SAMPLE_CLEANING_ADDRESS,new_valve_pos)
        time.sleep(1)
        s = self.pump1.get_valve(SAMPLE_CLEANING_ADDRESS)
        cur_valve = "----"
        if (s=='1'):
            cur_valve = "Air(P1)"
        elif(s=='2'):
            cur_valve = "MeOH(P2)"
        elif(s=="3"):
            cur_valve = "Detergent(P3)"
        elif(s=="4"):
            cur_valve = "WI Water(P4)"
        elif(s=="5"):
            cur_valve = "Reservoirs(P5)"
        elif(s=="6"):
            cur_valve = "Cell(P6)"
        else:
            cur_valve = "error"

        self.v8_cur_pos.config(text=cur_valve)



    #BUBBLE SENSOR SELECTION FOR PUMP 1
    def checkCombob0(self,event):        
        s = self.combo0.get()        
        ss=s.partition('S')
        index = int(ss[2])
        logger.info('pump 1: bubble sensor number:{}'.format(index))
        X3 = 1050
        Y1 = 100
        dY1 = 40
        # Label(self.tab1, text = "     ",font=("Arial", 15) , bg='#D9D9D9',fg='red').place(x = X3-40,y = Y1 + 0*dY1)         
        self.lbs1.place_forget()
        self.lbs2.place_forget()
        self.lbs3.place_forget()
        self.lbs4.place_forget()
        self.lbs5.place_forget()
        self.lbs6.place_forget()
        self.lbs7.place_forget()
        self.lbs8.place_forget()
        self.lbs9.place_forget()
        self.lbs10.place_forget()
        self.lbs11.place_forget()
        self.lbs12.place_forget()
        self.lbs13.place_forget()
        self.lbs14.place_forget()

        if (index == 1):
            self.lbs2.pack()
            self.lbs2.place(x = X3-40,y = Y1 + 0*dY1)
            self.BS = 1
        elif (index == 2):
            self.lbs2.pack()
            self.lbs2.place(x = X3-40,y = Y1 + 1*dY1)
            self.BS = 2
        elif (index == 3):
            self.lbs3.pack()
            self.lbs3.place(x = X3-40,y = Y1 + 2*dY1)  
            self.BS = 3
        elif (index == 4):
            self.lbs4.pack()
            self.lbs4.place(x = X3-40,y = Y1 + 3*dY1)
            self.BS = 4
        elif (index == 5):
            self.lbs5.pack()
            self.lbs5.place(x = X3-40,y = Y1 + 4*dY1)
            self.BS = 5
        elif (index == 6):
            self.lbs6.pack()
            self.lbs6.place(x = X3-40,y = Y1 + 5*dY1)
            self.BS = 6
        elif (index == 7):
            self.lbs7.pack()
            self.lbs7.place(x = X3-40,y = Y1 + 6*dY1)
            self.BS = 7
        elif (index == 8):
            self.lbs8.pack()
            self.lbs8.place(x = X3-40,y = Y1 + 7*dY1)
            self.BS = 8
        elif (index == 9):
            self.lbs9.pack()
            self.lbs9.place(x = X3-40,y = Y1 + 8*dY1)
            self.BS = 9
        elif (index == 10):
            self.lbs10.pack()
            self.lbs10.place(x = X3-40,y = Y1 + 9*dY1)
            self.BS = 10
        elif (index == 11):
            self.lbs11.pack()
            self.lbs11.place(x = X3-40,y = Y1 + 10*dY1)
            self.BS = 11
        elif (index == 12):
            self.lbs12.pack()
            self.lbs12.place(x = X3-40,y = Y1 + 11*dY1)
            self.BS = 12
        elif (index == 13):
            self.lbs13.pack()
            self.lbs13.place(x = X3-40,y = Y1 + 12*dY1)  
            self.BS = 13
        elif (index == 14):
            self.lbs14.pack()
            self.lbs14.place(x = X3-40,y = Y1 + 13*dY1)
            self.BS = 14


    #BUBBLE SENSOR SELECTION FOR PUMP 2
    def checkCombob1(self,event):        
        s = self.combob1.get()        
        ss=s.partition('S')
        index = int(ss[2])
        logger.info('pump 2: bubble sensor number:{}'.format( index))
        X3 = 1050
        Y1 = 100
        dY1 = 40
        # Label(self.tab1, text = "     ",font=("Arial", 15) , bg='#D9D9D9',fg='red').place(x = X3-40,y = Y1 + 0*dY1)         
        self.lbs1.place_forget()
        self.lbs2.place_forget()
        self.lbs3.place_forget()
        self.lbs4.place_forget()
        self.lbs5.place_forget()
        self.lbs6.place_forget()
        self.lbs7.place_forget()
        self.lbs8.place_forget()
        self.lbs9.place_forget()
        self.lbs10.place_forget()
        self.lbs11.place_forget()
        self.lbs12.place_forget()
        self.lbs13.place_forget()
        self.lbs14.place_forget()

        if (index == 1):
            self.lbs2.pack()
            self.lbs2.place(x = X3-40,y = Y1 + 0*dY1)
            self.BS = 1
        elif (index == 2):
            self.lbs2.pack()
            self.lbs2.place(x = X3-40,y = Y1 + 1*dY1)
            self.BS = 2
        elif (index == 3):
            self.lbs3.pack()
            self.lbs3.place(x = X3-40,y = Y1 + 2*dY1)  
            self.BS = 3
        elif (index == 4):
            self.lbs4.pack()
            self.lbs4.place(x = X3-40,y = Y1 + 3*dY1)
            self.BS = 4
        elif (index == 5):
            self.lbs5.pack()
            self.lbs5.place(x = X3-40,y = Y1 + 4*dY1)
            self.BS = 5
        elif (index == 6):
            self.lbs6.pack()
            self.lbs6.place(x = X3-40,y = Y1 + 5*dY1)
            self.BS = 6
        elif (index == 7):
            self.lbs7.pack()
            self.lbs7.place(x = X3-40,y = Y1 + 6*dY1)
            self.BS = 7
        elif (index == 8):
            self.lbs8.pack()
            self.lbs8.place(x = X3-40,y = Y1 + 7*dY1)
            self.BS = 8
        elif (index == 9):
            self.lbs9.pack()
            self.lbs9.place(x = X3-40,y = Y1 + 8*dY1)
            self.BS = 9
        elif (index == 10):
            self.lbs10.pack()
            self.lbs10.place(x = X3-40,y = Y1 + 9*dY1)
            self.BS = 10
        elif (index == 11):
            self.lbs11.pack()
            self.lbs11.place(x = X3-40,y = Y1 + 10*dY1)
            self.BS = 11
        elif (index == 12):
            self.lbs12.pack()
            self.lbs12.place(x = X3-40,y = Y1 + 11*dY1)
            self.BS = 12
        elif (index == 13):
            self.lbs13.pack()
            self.lbs13.place(x = X3-40,y = Y1 + 12*dY1)  
            self.BS = 13
        elif (index == 14):
            self.lbs14.pack()
            self.lbs14.place(x = X3-40,y = Y1 + 13*dY1)
            self.BS = 14



    def set_step_mode_p1(self, flag):

        if (flag == False):
            logger.info('switch pump1 to normal mode')
            self.pump1.set_microstep_position(1,0)
        else:
            logger.info(" switched pump1 to p&v  ")
            self.pump1.set_microstep_position(1,2)


    def set_step_mode_p2(self, flag):

        if (flag == False):
            logger.info('switch pump2 to normal mode')
            self.pump1.set_microstep_position(5,0)
        else:
            logger.info(" switched pump2 to p&v  ")
            self.pump1.set_microstep_position(5,2)



    def pump1_scale_factor(self, N):        
        if (N == 1):
            STEP_RANGE = 48000.
            VOLUME = 1000.
            self.microstep_p1 = False
        elif (N == 2):
            STEP_RANGE = 48000.* 8
            VOLUME = 1000. 
            self.microstep_p1 = True
        elif (N == 3):
            STEP_RANGE = 48000.
            VOLUME = 500.
            self.microstep_p1 = False
        elif (N == 4):
            STEP_RANGE = 48000.* 8
            VOLUME = 500. 
            self.microstep_p1 = True
        elif (N == 5):
            STEP_RANGE = 48000.
            VOLUME = 250.
            self.microstep_p1 = False
        elif (N == 6):
            STEP_RANGE = 48000.* 8
            VOLUME = 250. 
            self.microstep_p1 = True
        elif (N == 7):
            STEP_RANGE = 24000.
            VOLUME = 2500.
            self.microstep_p1 = False
        elif (N == 8):
            STEP_RANGE = 24000.* 8
            VOLUME = 2500. 
            self.microstep_p1 = True
        elif (N == 9):
            STEP_RANGE = 1
            VOLUME = 1
            self.microstep_p1 = False
            pass
        elif (N == 10):
            STEP_RANGE = 1
            VOLUME = 1
            self.microstep_p1 = True
            pass
        else:
            logger.info("\t\tp1 invalid scale factor")
            STEP_RANGE = 1
            VOLUME = 1


        if (self.microstep_p1 == False):
            logger.info('pump 1 mircostep off')
            self.set_step_mode_p1(False)            
        else:  #self.microstep_p1 = True
            logger.info('pump 1 mircostep on')
            self.set_step_mode_p1(True)

            
        # self.p1_top_spd = DEFAULT_PUMP_SPEEED
        if self.microstep_p1 == False:
            self.pump1.set_speed(TIRRANT_PUMP_ADDRESS,self.p1_top_spd)
            time.sleep(.25)
            logger.info("\t\tPump1 speed is set to {}".format(self.p1_top_spd))
            self.p1_cur_spd.config(text = str(self.p1_top_spd))
        else:
            new_speed = self.p1_top_spd * 8
            self.pump1.set_speed(TIRRANT_PUMP_ADDRESS,new_speed)
            time.sleep(.25)            
            logger.info("\t\tPump1 speed is set to {}".format(new_speed))
            self.p1_cur_spd.config(text = str(new_speed))
   
        self.scalefactor_p1 = STEP_RANGE / VOLUME
        logger.info('\t\tpump 1 scale factor:{}'.format( self.scalefactor_p1))


    def pump2_scale_factor(self, N):        
        if (N == 1):
            STEP_RANGE = 48000.
            VOLUME = 1000.
            self.microstep_p2 = False
        elif (N == 2):
            STEP_RANGE = 48000.* 8
            VOLUME = 1000. 
            self.microstep_p2 = True
        elif (N == 3):
            STEP_RANGE = 48000.
            VOLUME = 500.
            self.microstep_p2 = False
        elif (N == 4):
            STEP_RANGE = 48000.* 8
            VOLUME = 500. 
            self.microstep_p2 = True
        elif (N == 5):
            STEP_RANGE = 48000.
            VOLUME = 250.
            self.microstep_p2 = False
        elif (N == 6):
            STEP_RANGE = 48000. * 8
            VOLUME = 250.
            self.microstep_p2 = True
        elif (N == 7):
            STEP_RANGE = 24000.
            VOLUME = 2500.
            self.microstep_p2 = False
        elif (N == 8):
            STEP_RANGE = 24000.* 8
            VOLUME = 2500. 
            self.microstep_p2 = True
        elif (N == 9):
            STEP_RANGE = 1
            VOLUME = 1
            self.microstep_p2 = False
            pass
        elif (N == 10):
            STEP_RANGE = 1
            VOLUME = 1
            self.microstep_p2 = True
            pass
        else:
            logger.info("\t\tp2 invalid scale factor")
            STEP_RANGE = 1
            VOLUME = 1

        if (self.microstep_p2 == False):
            logger.info('pump 2 mircostep off')
            self.set_step_mode_p2(False)            
        else: 
            logger.info('pump 2 mircostep on')
            self.set_step_mode_p2(True)

        # self.p2_top_spd = DEFAULT_PUMP_SPEEED
        if self.microstep_p2 == False:
            self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,self.p2_top_spd)
            time.sleep(.25)
            logger.info("\t\tPump2 speed is set to {}".format(self.p2_top_spd))
            self.p2_cur_spd.config(text = str(self.p2_top_spd))
        else:
            new_speed = self.p2_top_spd * 8
            self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,new_speed)
            time.sleep(.25)            
            logger.info("\t\tPump2 speed is set to {}".format(new_speed))
            self.p2_cur_spd.config(text = str(new_speed))


        self.scalefactor_p2 = STEP_RANGE / VOLUME
        logger.info('\t\tpump2 scale factor:{}'.format( self.scalefactor_p2))


    ###------------------- END OF CLASS DEFINITION ------------------------------------------------------








def is_float(element: any) -> bool:
    #If you expect None to be passed:
    if element is None: 
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False
    



def main(): #run mianloop 
    
    root = Tk()
    # app = GUI.GUI(root)
    run_GUI(root)

    root.mainloop()

if __name__ == '__main__':
    main()
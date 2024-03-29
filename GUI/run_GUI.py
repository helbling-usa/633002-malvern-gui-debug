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
# BUBBLE_DETECTION_PUMP_SPEED = 50        # speed of pump during bubble detection
DEFAULT_PUMP_SPEEED         = 1000      # speed of pump at start up
GANTRY_VER_SPEED            = 1.0      # vertical gantry speed
GANTRY_HOR_SPEED            = 1.0      # horizontal gantry speed
GANTRY_VER_ACCELERATION     = 1         # vertical gantry acceleration
GANTRY_HOR_ACCELERATION     = 1         # horizontal gantry acceleration
MIXING_ACCELERATION         = 1         # mixing motor acceleration
RPM_2_TML_SPEED             = 0.1365    # conversion from rpm to mixing motor TML unit  (0.267 for Reza's mixer)
TML_LENGTH_2_MM_VER         = 10. /1000      # tml unit for length to um
TML_LENGTH_2_MM_HOR         = 7.5 /1000      # tml unit for length to um
# pumps/valves RS485 addresses
TIRRANT_PUMP_ADDRESS        = 1         # Pump 1
TITRANT_LOOP_ADDRESS        = 3         # pump 1 loop valve
TITRANT_PIPETTE_ADDRESS     = 5         # titrant line: pipette valve
TITRANT_CLEANING_ADDRESS    = 9         # titrant line: cleaning valve
SAMPLE_PUMP_ADDRESS         = 2         # pump 2
SAMPLE_LOOP_ADDRESS         = 4         # pump 2 loop valve
TITRANT_PORT_ADDRESS        = 6         # sample line: titrant port valve
DEGASSER_ADDRESS            = 7         # sample line: degasser valve
SAMPLE_CLEANING_ADDRESS     = 8         # sample line: cleaning valve
BUBBLE_DETECTION_PUMP_SPEED_TITRANT         = 20         # ????step/sec
BUBBLE_DETECTION_PUMP_SPEED_SAMPLE          = 20         # ????setp/sec
PICKUP_UNTIL_BUBBLE_TARGET_SAMPLE_VOLUME    = 2500      # ul
PICKUP_UNTIL_BUBBLE_TARGET_TITRANT_VOLUME   = 500       # ul
TITRANT_MAX_FULL_STEPS                      = 48000     # max tirtant  pump steps in full step
SAMPLE_MAX_FULL_STEPS                       = 24000     # max sample pump steps in full step
STOP_BUBBLE_DETECTION                       = False     # Global var used to stop bubble detection 
                                                        #  on pressing 'Terminate' button
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
    # global BUBBLE_DETECTION_PUMP_SPEED
    global DEFAULT_PUMP_SPEEED
    def __init__(self,root):
        super().__init__( root)
        self.root = root
        logger.info("Initializing hardware -------------------------------------")
        self.PortAssignment()
        self.Init_Pumps_Valves()
        self.Init__motors_all_axes()            
        self.InitLabjack()
        self.InitTecController()
        self.InitTimer()
        logger.info("Hardware initialiation done")        

        #------------ Setting the inital states/values of the hardware ----------------------
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
        logger.info("------------------------------------------------------------------")
        logger.info('System started successfully.')
        logger.info("Please use the GUI to enter a commamnd ...")
        

    def timerCallback_1(self):  
        global TIRRANT_PUMP_ADDRESS
        global SAMPLE_PUMP_ADDRESS
        #------------------------------- update pump 1 position
        p1_cur_pos = self.pump1.get_plunger_position(TIRRANT_PUMP_ADDRESS)            
        p1_cur_pos =  int(10.0 * p1_cur_pos / self.scalefactor_p1) / 10.0
        self.p1_cur_pos.config(text = str(p1_cur_pos))
        #------------------------------- update pump 2 position
        time.sleep(.1)
        p2_cur_pos = self.pump1.get_plunger_position(SAMPLE_PUMP_ADDRESS)            
        p2_cur_pos = int(10.0 * p2_cur_pos / self.scalefactor_p2) / 10.0
        self.p2_cur_pos.config(text = str(p2_cur_pos))
        # #------------------------------- update  of TEC controller parameters
        self.updateGUI_TectController()
        #-------- update Gantry vertical motor position on GUI ------------------
        self.motors.select_axis(self.AXIS_ID_03)
        p= self.motors.read_actual_position()
        p_mm = TML_LENGTH_2_MM_VER * p
        p_mm_str = "{:.2f}".format(p_mm)
        self.m3_cur_spd.config(text = p_mm_str)
        #-------- update Gantry horizontal motor position on GUI ------------------
        self.motors.select_axis(self.AXIS_ID_02)
        p= self.motors.read_actual_position()
        p_mm = TML_LENGTH_2_MM_HOR * p
        p_mm_str = "{:.2f}".format(p_mm)
        self.m2_cur_spd.config(text = p_mm_str)
        #-------- read bubble sensor and update the GUI -------------------------
        self.read_BubbleSensors()
        self.updateGUI_BubbleSensorLEDs()
        #-------- repeat the timer ----------------------------------------------
        self.timer = threading.Timer(1.0, self.timerCallback_1)
        self.timer.start()


    def updateGUI_TectController(self):
        tec_dic =  self.mc.get_data()
        obj_temp = round(tec_dic['object temperature'][0], 1)
        target_temp = round(tec_dic['target object temperature'][0], 1)
        TEC_cur_status = tec_dic['loop status'][0]        
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
        com_port = self.PUMP1_PORT
        self.pump1 = P.Pump(com_port)
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

        self.config_valve1()
        self.combo1.current(4)

        self.config_valve2()
        self.combo2.current(4)

        self.config_valve3()
        self.combo3.current(4)

        self.config_valve4()
        self.combo4.current(4)

        self.config_valve5()
        self.combo5.current(3)

        self.config_valve6()
        self.combo6.current(3)

        self.config_valve7()
        self.combo7.current(6)

        self.config_valve8()
        self.combo8.current(6)

        self.config_valve9()
        self.combo9.current(6)

        # init. scale factors 
        self.comboCfg1.current(8)
        self.pump1_scale_factor(9)

        self.comboCfg2.current(8)
        self.pump2_scale_factor(9)


    def config_valve1(self):
        time.sleep(0.5)
        s = self.pump1.get_valve(TIRRANT_PUMP_ADDRESS)
        cur_valve = "----"
        if (s=='e'):
            cur_valve = "Gas to Line (P1)"
        elif(s=='o'):
            cur_valve = "Pump to Line (P2)"
        elif(s=='i'):
            cur_valve = "Pump to Air (P3)"
        elif(s=='b'):
            cur_valve = "Gas to Air (P4)"
        else:
            cur_valve = "error"
        self.v1_cur_pos.config(text=cur_valve)


    def config_valve2(self):
        time.sleep(0.5)
        s = self.pump1.get_valve(SAMPLE_PUMP_ADDRESS)
        cur_valve = "----"
        if (s=='e'):
            cur_valve = "Gas to Air (P1)"
        elif(s=='o'):
            cur_valve = "Pump to Air (P2)"
        elif(s=='i'):
            cur_valve = "Pump to Line (P3)"
        elif(s=='b'):
            cur_valve = "Gas to Line (P4)"
        else:
            cur_valve = "error"
        self.v2_cur_pos.config(text=cur_valve)


    def config_valve3(self):
        time.sleep(0.5)
        s = self.pump1.get_valve(TITRANT_LOOP_ADDRESS)
        cur_valve = "----"
        if (s=='e'):
            cur_valve = "Gas to Air (P1)"
        elif(s=='o'):
            cur_valve = "Pump to Air (P2)"
        elif(s=='i'):
            cur_valve = "Line to Pump (P3)"
        elif(s=='b'):
            cur_valve = "Line to Gas (P4)"
        else:
            cur_valve = "error"
        self.v3_cur_pos.config(text=cur_valve)        


    def config_valve4(self):
            time.sleep(0.5)
            s = self.pump1.get_valve(SAMPLE_LOOP_ADDRESS)
            cur_valve = "----"
            if (s=='e'):
                cur_valve = "Line to Gas (P1)"
            elif(s=='o'):
                cur_valve = "Line to Pump (P2)"
            elif(s=='i'):
                cur_valve = "Pump to Air (P3)"
            elif(s=='b'):
                cur_valve = "Gas to Air (P4)"
            else:
                cur_valve = "error"
            self.v4_cur_pos.config(text=cur_valve)

    def config_valve5(self):
        time.sleep(0.5)
        s = self.pump1.get_valve(TITRANT_PIPETTE_ADDRESS)
        # logger.info("----->{}".format(s))
        cur_valve = "----"
        if (s=='i'):
            cur_valve = "Titrant Cannula (P1)"
        elif(s=='e'):
            cur_valve = "Titrant Port (P2)"
        elif(s=='o'):
            cur_valve = "Reservoirs (P3)"
        else:
            cur_valve = "error"
        self.v5_cur_pos.config(text=cur_valve)        

    def config_valve6(self):
        time.sleep(0.5)
        s = self.pump1.get_valve(TITRANT_PORT_ADDRESS)
        cur_valve = "----"
        if (s=='i'):
            cur_valve = "N/A (P1)"
        elif(s=='e'):
            cur_valve = "Titrant Line (P2)"
        elif(s=='o'):
            cur_valve = "Sample Line (P3)"
        else:
            cur_valve = "error"
        self.v6_cur_pos.config(text=cur_valve)


    def config_valve7(self):
        time.sleep(0.5)
        s = self.pump1.get_valve(DEGASSER_ADDRESS)
        cur_valve = "----"
        if (s=='1'):
            cur_valve = "Reservoirs (P1)"
        elif(s=='2'):
            cur_valve = "Rec Port (P2)"
        elif(s=='3'):
            cur_valve = "Sample Port (P3)"
        elif(s=='4'):
            cur_valve = "Ref Port (P4)"
        elif(s=='5'):
            cur_valve = "Titrant Port (P5)"
        elif(s=='6'):
            cur_valve = "Cell (P6)"
        else:
            cur_valve = "error"
        self.v7_cur_pos.config(text=cur_valve)


    def config_valve8(self):
        time.sleep(0.5)
        s = self.pump1.get_valve(SAMPLE_CLEANING_ADDRESS)        
        cur_valve = "----"
        if (s=='1'):
            cur_valve = "Waste (P1)"
        elif(s=='2'):
            cur_valve = "MeOH (P2)"
        elif(s=='3'):
            cur_valve = "Detergent (P3)"
        elif(s=='4'):
            cur_valve = "DI Water (P4)"
        elif(s=='5'):
            cur_valve = "Cleaning Port (P5)"
        elif(s=='6'):
            cur_valve = "Air (P6)"
        else:
            cur_valve = "error"
        self.v8_cur_pos.config(text=cur_valve)


    def config_valve9(self):
        time.sleep(0.5)
        s = self.pump1.get_valve(TITRANT_CLEANING_ADDRESS)
        cur_valve = "----"
        if (s=='1'):
            cur_valve = "N/A (P1)"
        elif(s=='2'):
            cur_valve = "Air (P2)"
        elif(s=='3'):
            cur_valve = "DI Water (P3)"
        elif(s=='4'):
            cur_valve = "Detergent (P4)"
        elif(s=='5'):
            cur_valve = "MeOH (P5)"
        elif(s=='6'):
            cur_valve = "Waste (P6)"
        else:
            cur_valve = "error"
        self.v9_cur_pos.config(text=cur_valve)


    def InitLabjack(self):
        # # initialize labjack
        logger.info("Initializing Labjack.....")
        self.labjack = u6.U6()
        self.labjack.writeRegister(50590, 15)        
        logger.info('\t\tlabjack initialized')


    def InitTimer(self):
        # #------ Starts timer
        logger.info('starting internal timer')
        self.timer = threading.Timer(1.0, self.timerCallback_1)
        self.timer.start()
        logger.info('\t\tInternal timer started')


    def InitTecController(self):
        # ------create object of TEC5 
        logger.info("Initialzing TEC Temperature Controller---------------------")
        self.mc = TEC.MeerstetterTEC(self.TEC_PORT)
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
            self.led_off_2.place(x = X3+50,y = Y1 + 1*dY1)
        else:
            self.led_off_2.place_forget()
            self.led_on_2.place(x = X3+50,y = Y1 + 1*dY1)

        if (self.BS2 < BS_THRESHOLD):
            self.led_on_3.place_forget()
            self.led_off_3.place(x = X3+50,y = Y1 + 2*dY1)
        else:
            self.led_off_3.place_forget()
            self.led_on_3.place(x = X3+50,y = Y1 + 2*dY1)

        if (self.BS3 < BS_THRESHOLD):
            self.led_on_4.place_forget()
            self.led_off_4.place(x = X3+50,y = Y1 + 3*dY1)
        else:
            self.led_off_4.place_forget()
            self.led_on_4.place(x = X3+50,y = Y1 + 3*dY1)

        if (self.BS4 < BS_THRESHOLD):
            self.led_on_5.place_forget()
            self.led_off_5.place(x = X3+50,y = Y1 + 4*dY1)
        else:
            self.led_off_5.place_forget()
            self.led_on_5.place(x = X3+50,y = Y1 + 4*dY1)
            
        if (self.BS5 < BS_THRESHOLD):
            self.led_on_6.place_forget()
            self.led_off_6.place(x = X3+50,y = Y1 + 5*dY1)
        else:
            self.led_off_6.place_forget()
            self.led_on_6.place(x = X3+50,y = Y1 + 5*dY1)

        if (self.BS6 < BS_THRESHOLD):
            self.led_on_7.place_forget()
            self.led_off_7.place(x = X3+50,y = Y1 + 6*dY1)
        else:
            self.led_off_7.place_forget()
            self.led_on_7.place(x = X3+50,y = Y1 + 6*dY1)
        
        if (self.BS7 < BS_THRESHOLD):
            self.led_on_8.place_forget()
            self.led_off_8.place(x = X3+50,y = Y1 + 7*dY1)
        else:
            self.led_off_8.place_forget()
            self.led_on_8.place(x = X3+50,y = Y1 + 7*dY1)

        if (self.BS8 < BS_THRESHOLD):
            self.led_on_9.place_forget()
            self.led_off_9.place(x = X3+50,y = Y1 + 8*dY1)
        else:
            self.led_off_9.place_forget()
            self.led_on_9.place(x = X3+50,y = Y1 + 8*dY1)

        if (self.BS9< BS_THRESHOLD):
            self.led_on_10.place_forget()
            self.led_off_10.place(x = X3+50,y = Y1 + 9*dY1)
        else:
            self.led_off_10.place_forget()
            self.led_on_10.place(x = X3+50,y = Y1 + 9*dY1)

        if (self.BS10 < BS_THRESHOLD):
            self.led_on_11.place_forget()
            self.led_off_11.place(x = X3+50,y = Y1 + 10*dY1)
        else:
            self.led_off_11.place_forget()
            self.led_on_11.place(x = X3+50,y = Y1 + 10*dY1)

        if (self.BS11 < BS_THRESHOLD):
            self.led_on_12.place_forget()
            self.led_off_12.place(x = X3+50,y = Y1 + 11*dY1)
        else:
            self.led_off_12.place_forget()
            self.led_on_12.place(x = X3+50,y = Y1 + 11*dY1)

        if (self.BS12 < BS_THRESHOLD):
            self.led_on_13.place_forget()
            self.led_off_13.place(x = X3+50,y = Y1 + 12*dY1)
        else:
            self.led_off_13.place_forget()
         
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
        self.pump1.pump_Zinit(TIRRANT_PUMP_ADDRESS)
        logger.info("\t\tPump1 initialized")
        time.sleep(3)


    def p2_b_init_pump2(self):
        self.pump1.pump_Zinit(SAMPLE_PUMP_ADDRESS)
        logger.info("\t\tPump2 initialized")
        time.sleep(3)


    def gantry_vertical_set_rel_click(self):
        global GANTRY_VER_SPEED
        global GANTRY_VER_ACCELERATION
        s = self.ent_gnt_ver_rel.get()
        if (is_float(s) == True):
            rel_pos_mm =float(s)
            self.motors.select_axis(self.AXIS_ID_03)
            self.motors.set_POSOKLIM(1)
            rel_pos_tml = int(rel_pos_mm / TML_LENGTH_2_MM_VER )
            val = self.motors.move_relative_position(rel_pos_tml, GANTRY_VER_SPEED, GANTRY_VER_ACCELERATION)
            if val == -2:
                tkinter.messagebox.showwarning("WARNING!!!",  "The actuator has reached its POSITIVE LIMIT."
                                "\nPlease move thea actuator within the limit") 
        else:
            logger.warning("Not a number. Please enter an integer for VG rel. position")



    def gantry_vertical_set_abs_click(self):
        global GANTRY_VER_SPEED
        global GANTRY_VER_ACCELERATION
        s = self.ent_gnt_ver_abs.get()
        if (is_float(s) == True):
            abs_pos_mm =float(s)
            self.motors.select_axis(self.AXIS_ID_03)
            self.motors.set_POSOKLIM(1)
            abs_pos_tml = int(abs_pos_mm / TML_LENGTH_2_MM_VER )
            self.motors.move_absolute_position(abs_pos_tml, GANTRY_VER_SPEED, GANTRY_VER_ACCELERATION)
        else:
            logger.warning("Not a number. Please enter an integer for VG abs. position")        
        

    def gantry_vertical_homing_click(self):
        logger.info('\t\tHoming Gantry Vertical')
        self.motors.homing(self.AXIS_ID_03)
        
        
    def gantry_horizontal_homing_click(self):
        logger.info('\t\tHoming Gantry Horizontal')
        self.motors.homing(self.AXIS_ID_02)


    def gantry_horizontal_stop_click(self):
        logger.info("\t\tStopping H gantry")
        self.motors.select_axis(self.AXIS_ID_02)
        self.motors.stop_motor()


    def gantry_vertical_stop_click(self):
        logger.info("\t\tStopping V gantry")
        self.motors.select_axis(self.AXIS_ID_03)
        self.motors.stop_motor()


    def gantry_horizontal_set_rel_click(self):
        global GANTRY_HOR_SPEED
        global GANTRY_HOR_ACCELERATION
        s = self.ent_gnt_hor_rel.get()
        if (is_float(s) == True):
            logger.info("----------MOVE Relative-----------------")
            rel_pos_mm =float(s)
            self.motors.select_axis(self.AXIS_ID_02)
            self.motors.set_POSOKLIM(1)
            rel_pos_tml = int(rel_pos_mm / TML_LENGTH_2_MM_HOR )
            val = self.motors.move_relative_position(rel_pos_tml, GANTRY_HOR_SPEED, GANTRY_HOR_ACCELERATION)
            if val == -2:
                tkinter.messagebox.showwarning("WARNING!!!",  "The actuator has reached its POSITIVE LIMIT."
                                "\nPlease move thea actuator within the limit") 
        else:
            logger.warning("Not a number. Please enter an integer for VG rel. position")




    def gantry_horizontal_set_abs_click(self):
        global GANTRY_HOR_SPEED
        global GANTRY_HOR_ACCELERATION
        s = self.ent_gnt_hor_abs.get()
        if (is_float(s) == True):
            abs_pos_mm =float(s)
            self.motors.select_axis(self.AXIS_ID_02)
            self.motors.set_POSOKLIM(1)
            abs_pos_tml = int(abs_pos_mm / TML_LENGTH_2_MM_HOR )
            self.motors.move_absolute_position(abs_pos_tml, GANTRY_HOR_SPEED, GANTRY_HOR_ACCELERATION)
        else:
            logger.warning("Not a number. Please enter an integer for VG abs. position")        
                
        

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
        self.motors.get_firmware_version()
        self.motors.set_position()
        self.motors.set_POSOKLIM(2)


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
        logger.info('\t\tPump1 config: :{}\n\t\tPress set button to confirm'.format( s))
            

    def p1_b_config_set_click(self):
        s = self.comboCfg1.get()
        logger.info('\t\tPump1 config is set to {}'.format( s))
        ss=s.partition(')')
        index = ss[0]
        self.pump1_scale_factor(int(index))
        if (self.microstep_p1 == False):
            logger.info('\t\tpump 1 mircostep off')
            self.set_step_mode_p1(False)            
        else:  #self.microstep_p1 = True
            logger.info('\t\tpump 1 mircostep on')
            self.set_step_mode_p1(True)




    def checkComboCfg2(self, event):
        s = self.comboCfg2.get()
        logger.info('\t\tPump2 config: :{}\n\t\tPress set button to confirm'.format( s))


    def p2_b_config_set_click(self):
        s = self.comboCfg2.get()
        logger.info('\t\tPump2 config is set to {}'.format( s))        
        ss=s.partition(')')
        index = ss[0]
        self.pump2_scale_factor(int(index))
        if (self.microstep_p2 == False):
            logger.info('\t\tpump 2 mircostep off')
            self.set_step_mode_p2(False)            
        else:  #self.microstep_p1 = True
            logger.info('\t\tpump 2 mircostep on')
            self.set_step_mode_p2(True)


    def p2_b_top_spd_click(self):    
        global SAMPLE_PUMP_ADDRESS    
        s =   self.ent_top_spd2.get()        
        if (is_float(s) == True):
            physical_speed = float(s)
            self.p2_top_spd = int(physical_speed * self.scalefactor_p2)
            if self.microstep_p2 == False:                
                self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,self.p2_top_spd)
            else:
                self.p2_top_spd = self.p2_top_spd * 1
                self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,self.p2_top_spd)

            time.sleep(.5)            
            logger.info("\t\tPump1 speed is set to {} logical  = {} physical.   scale factor:{}".format(self.p2_top_spd, physical_speed,
                                                                                                        self.scalefactor_p2 ))
            time.sleep(.25)
            self.p2_cur_spd.config(text = s)


    def p2_b_abs_pos_click(self):
        global SAMPLE_PUMP_ADDRESS
        s =   self.ent_abs_pos2.get()
        logger.info(s)
        if (is_float(s) == True):
            val = float(s)            
            abs_pos = int(val * self.scalefactor_p2)
            logger.info("\t\tpump2: set abs. pos:{} . after scaling:{}".format(s, abs_pos))
            self.pump1.set_pos_absolute(SAMPLE_PUMP_ADDRESS, abs_pos)


    def p2_b_pickup_pos_click(self):
        global SAMPLE_PUMP_ADDRESS
        logger.info("P2_pickup ")
        s =   self.ent_pickup_pos2.get()
        if (is_float(s) == True):
            val = float(s)
            logger.info("\t\tpump2: set pickup pos:{}".format(s))
            rel_pos = int(val * self.scalefactor_p2)            
            self.pump1.set_pickup(SAMPLE_PUMP_ADDRESS, rel_pos)


    def p2_b_dispense_pos_click(self):
        global SAMPLE_PUMP_ADDRESS
        s =   self.ent_dispemse_pos2.get()
        logger.info("P2_dispense ")
        if (is_float(s) == True):
            val = float(s)
            logger.info("\t\tpump2: set dispense pos:{}".format(s))
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
        s =   self.ent_m1_spd_.get()
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
            val = float(s)
            logger.info("\t\tpump1: set abs. pos:{}".format(s))
            abs_pos = int(val * self.scalefactor_p1)
            self.pump1.set_pos_absolute(TIRRANT_PUMP_ADDRESS, abs_pos)


    def p1_b_pickup_pos_click(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info("P1_pickup ")
        s =   self.ent_pickup_pos.get()
        if (is_float(s) == True):
            val = float(s)
            logger.info("\t\tpump1: set pickup pos:{}".format(s))
            rel_pos = int(val * self.scalefactor_p1)            
            self.pump1.set_pickup(TIRRANT_PUMP_ADDRESS, rel_pos)


    def p1_b_dispense_pos_click(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info("P1_dispense ")
        s =   self.ent_dispemse_pos.get()
        if (is_float(s) == True):
            val = float(s)
            logger.info("\t\tpump1: set dispense pos:{}".format(s))
            rel_pos = int(val * self.scalefactor_p1)            
            self.pump1.set_dispense(TIRRANT_PUMP_ADDRESS,rel_pos)


    def p1_b_teminateP1(self):
        global TIRRANT_PUMP_ADDRESS
        global STOP_BUBBLE_DETECTION
        STOP_BUBBLE_DETECTION = True
        logger.info('Termnate pump1')        
        self.pump1.stop(TIRRANT_PUMP_ADDRESS)


    def p1_b_pickupUntillbubble(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info("Pump 1: Pickup until bubble")
        logger.info("Scale facotr  -->   titrant pump: {}".format(self.scalefactor_p1))
        s = self.comboCfg1.get()
        print("=====================================",s)
        if (s == "9) Full steps"):
            pump1_speed = int(BUBBLE_DETECTION_PUMP_SPEED_TITRANT * 10)
            titrant_pump_fill_position = int(TITRANT_MAX_FULL_STEPS)
        elif (s ==  "10) Microsteps"):
            pump1_speed = int(BUBBLE_DETECTION_PUMP_SPEED_TITRANT * 80)
            titrant_pump_fill_position = int( TITRANT_MAX_FULL_STEPS * 8.0)
        else:
            pump1_speed = int(BUBBLE_DETECTION_PUMP_SPEED_TITRANT * self.scalefactor_p1)
            titrant_pump_fill_position =  int(PICKUP_UNTIL_BUBBLE_TARGET_TITRANT_VOLUME * self.scalefactor_p1)

        logger.info("\t\t=====> titrant pump taraget position: {}".format(titrant_pump_fill_position))
        logger.info('\t\tpump 1 pickup speed: {}'.format(pump1_speed))
        logger.info("\t\tPickup target position: {}".format(titrant_pump_fill_position))
        pump_address = TIRRANT_PUMP_ADDRESS
        self.t1 = threading.Thread(target=self.find_bubble, args=(pump1_speed, titrant_pump_fill_position, pump_address,))
        self.b_pickupUntillbubble_p1["state"] = DISABLED
        self.b_dispenseUntillbubble_p1["state"] = DISABLED
        self.t1.start()
        


    def find_bubble(self, pump_speed, pump_position, pump_address):
        global STOP_BUBBLE_DETECTION
        time.sleep(0.5)
        self.pump1.set_speed(pump_address, pump_speed)
        time.sleep(1)
        self.pump1.set_pos_absolute(pump_address, pump_position)
        time.sleep(0.25)
        input0 = (self.labjack.getAIN(self.BS - 1))
        #check if the bubble semsor detect air or liquid
        cur_state = self.air_or_liquid(input0)
        prev_state = cur_state
        counter = 0
        while (cur_state == prev_state and STOP_BUBBLE_DETECTION == False)              :
            prev_state = cur_state
            input0 = (self.labjack.getAIN(self.BS - 1))
            cur_state = self.air_or_liquid(input0)
            counter += 1
            if counter == 50:
                logger.info("\t\tBS{} -> {}\tposition= {}".format(self.BS, cur_state,
                                                                  self.pump1.get_plunger_position(pump_address)))
                counter = 0                      
            time.sleep(.01)
        
        logger.info("\t\tBS{} -> {}\tposition= {}".format(self.BS, cur_state,
                                                          self.pump1.get_plunger_position(pump_address)))
        self.pump1.stop(pump_address)
        logger.info('\t\tBubble detection terminated')
        time.sleep(.5)
        STOP_BUBBLE_DETECTION = False
        self.pump1.set_speed(pump_address,DEFAULT_PUMP_SPEEED)
        time.sleep(.5)
        self.b_pickupUntillbubble_p1["state"] = NORMAL
        self.b_dispenseUntillbubble_p1["state"] = NORMAL
        self.b_pickupUntillbubble_p2["state"] = NORMAL
        self.b_dispenseUntillbubble_p2["state"] = NORMAL        
        

    def p1_b_dispenseUntillbubble(self):
        global TIRRANT_PUMP_ADDRESS
        logger.info('Dispense until bubble')
        logger.info("Scale facotr  -->   titrant pump: {}".format(self.scalefactor_p1))
        s = self.comboCfg1.get()
        print("=====================================",s)
        if (s == "9) Full steps"):
            pump1_speed = int(BUBBLE_DETECTION_PUMP_SPEED_TITRANT * 10)            
        elif (s ==  "10) Microsteps"):
            pump1_speed = int(BUBBLE_DETECTION_PUMP_SPEED_TITRANT * 80)
        else:
            pump1_speed = int(BUBBLE_DETECTION_PUMP_SPEED_TITRANT * self.scalefactor_p1)

        titrant_pump_fill_position = 0
        logger.info("Dispemse target position: {}".format(titrant_pump_fill_position))
        pump_address = TIRRANT_PUMP_ADDRESS
        self.t1 = threading.Thread(target=self.find_bubble, args=(pump1_speed, titrant_pump_fill_position,
                                                                  pump_address,))
        self.b_pickupUntillbubble_p1["state"] = DISABLED
        self.b_dispenseUntillbubble_p1["state"] = DISABLED
        self.t1.start()


    def p2_b_pickupUntillbubble(self):
        global SAMPLE_PUMP_ADDRESS
        logger.info("Pump 2: Pickup until bubble")
        logger.info("\t\tScale facotr  -->   sample pump: {}".format(self.scalefactor_p2)) 
        s = self.comboCfg1.get()
        print("=====================================",s)
        if (s == "9) Full steps"):
            pump2_speed = int(BUBBLE_DETECTION_PUMP_SPEED_SAMPLE * 10)
            sample_pump_fill_position = int(SAMPLE_MAX_FULL_STEPS)
        elif (s ==  "10) Microsteps"):
            pump2_speed = int(BUBBLE_DETECTION_PUMP_SPEED_SAMPLE * 80)
            sample_pump_fill_position = int( SAMPLE_MAX_FULL_STEPS * 8.0)
        else:
            pump2_speed = int(BUBBLE_DETECTION_PUMP_SPEED_SAMPLE * self.scalefactor_p2)
            sample_pump_fill_position =  int(PICKUP_UNTIL_BUBBLE_TARGET_SAMPLE_VOLUME * self.scalefactor_p2)

        logger.info('\t\tpump 2 pickup speed: {}'.format(pump2_speed))
        logger.info("\t\tPickup target position: {}".format(sample_pump_fill_position))
        pump_address = SAMPLE_PUMP_ADDRESS
        self.t1 = threading.Thread(target=self.find_bubble, args=(pump2_speed, sample_pump_fill_position,
                                                                  pump_address,))
        self.b_pickupUntillbubble_p2["state"] = DISABLED
        self.b_dispenseUntillbubble_p2["state"] = DISABLED        
        self.t1.start()        


    def p2_b_dispenseUntillbubble(self):
        global SAMPLE_PUMP_ADDRESS
        logger.info('\t\tpump 2: Dispense until bubble')
        logger.info("\t\tScale facotr  -->   sample pump: {}".format(self.scalefactor_p2))
        s = self.comboCfg2.get()
        print("=====================================",s)
        if (s == "9) Full steps"):
            pump2_speed = int(BUBBLE_DETECTION_PUMP_SPEED_SAMPLE * 10)            
        elif (s ==  "10) Microsteps"):
            pump2_speed = int(BUBBLE_DETECTION_PUMP_SPEED_SAMPLE * 80)
        else:
            pump2_speed = int(BUBBLE_DETECTION_PUMP_SPEED_SAMPLE * self.scalefactor_p2)

        logger.info('\t\tpump 2 pickup speed: {}'.format(pump2_speed))
        sample_pump_fill_position =  0
        logger.info("\t\tDispense target position: {}".format(sample_pump_fill_position))
        pump_address = SAMPLE_PUMP_ADDRESS
        self.t1 = threading.Thread(target=self.find_bubble, args=(pump2_speed, sample_pump_fill_position,
                                                                  pump_address,))
        self.b_pickupUntillbubble_p2["state"] = DISABLED
        self.b_dispenseUntillbubble_p2["state"] = DISABLED
        self.t1.start()        


    def air_or_liquid(self, voltage):
        if voltage > BS_THRESHOLD:
            return 'liquid'
        else:
            return 'air'

        
    def p2_b_teminateP2(self):
        global SAMPLE_PUMP_ADDRESS
        global STOP_BUBBLE_DETECTION
        STOP_BUBBLE_DETECTION = True        
        logger.info('Terminate pump2')
        self.pump1.stop(SAMPLE_PUMP_ADDRESS)


    def p1_b_top_spd_click(self):   
        global TIRRANT_PUMP_ADDRESS     
        s =   self.ent_top_spd.get()
        if (is_float(s) == True):
            physical_speed = float(s)
            self.p1_top_spd = int(physical_speed * self.scalefactor_p1)
            if self.microstep_p1 == False:                
                self.pump1.set_speed(TIRRANT_PUMP_ADDRESS,self.p1_top_spd)
            else:
                self.p1_top_spd = self.p1_top_spd * 1
                self.pump1.set_speed(TIRRANT_PUMP_ADDRESS,self.p1_top_spd)

            time.sleep(.5)            
            logger.info("\t\tPump1 speed is set to {} logical  = {} physical.   scale factor:{}".format(self.p1_top_spd, physical_speed,
                                                                                                        self.scalefactor_p1 ))
            self.pump1.set_speed(TIRRANT_PUMP_ADDRESS, self.p1_top_spd)
            time.sleep(.25)
            self.p1_cur_spd.config(text = s)


    #Pump Valve (Titrant line)
    def checkCombo1(self,event):
        global TIRRANT_PUMP_ADDRESS
        valve_is_valid = True
        s = self.combo1.get()
        if (s == "Gas to Line (P1)"):
            new_valve_pos = 'E'
        elif (s == "Pump to Line (P2)"):
            new_valve_pos = 'O'
        elif (s == "Pump to Air (P3)"):
            new_valve_pos = 'I'
        elif (s == "Gas to Air (P4)"):
            new_valve_pos = 'B'
        else:
            logger.info(' invalid valve selection')
            valve_is_valid = False
        
        if valve_is_valid:
            self.pump1.set_valve(TIRRANT_PUMP_ADDRESS, new_valve_pos)
            time.sleep(1)
            s = self.pump1.get_valve(TIRRANT_PUMP_ADDRESS)
            cur_valve = "----"
            if (s=='e'):
                cur_valve = "Gas to Line (P1)"
            elif(s=='o'):
                cur_valve = "Pump to Line (P2)"
            elif(s=='i'):
                cur_valve = "Pump to Air (P3)"
            elif(s=='b'):
                cur_valve = "Gas to Air (P4)"
            else:
                cur_valve = "error"
            self.v1_cur_pos.config(text=cur_valve)


    #Pump Valve (Sample line)
    def checkCombo2(self,event):
        global SAMPLE_PUMP_ADDRESS
        valve_is_valid = True
        s = self.combo2.get()
        if (s == "Gas to Air (P1)"):
            new_valve_pos = 'E'
        elif (s == "Pump to Air (P2)"):
            new_valve_pos = 'O'
        elif (s == "Pump to Line (P3)"):
            new_valve_pos = 'I'
        elif (s == "Gas to Line (P4)"):
            new_valve_pos = 'B'
        else:
            logger.info(' invalid valve selection')
            valve_is_valid = False
        
        if valve_is_valid:
            self.pump1.set_valve(SAMPLE_PUMP_ADDRESS, new_valve_pos)
            time.sleep(1)
            s = self.pump1.get_valve(SAMPLE_PUMP_ADDRESS)
            cur_valve = "----"
            if (s=='e'):
                cur_valve = "Gas to Air (P1)"
            elif(s=='o'):
                cur_valve = "Pump to Air (P2)"
            elif(s=='i'):
                cur_valve = "Pump to Line (P3)"
            elif(s=='b'):
                cur_valve = "Gas to Line (P4)"
            else:
                cur_valve = "error"
            self.v2_cur_pos.config(text=cur_valve)


    #Loop Valve (Titrant line)
    def checkCombo3(self, event):
        global TITRANT_LOOP_ADDRESS
        valve_is_valid = True
        s = self.combo3.get()
        if (s == "Gas to Air (P1)"):
            new_valve_pos = 'E'
        elif (s == "Pump to Air (P2)"):
            new_valve_pos = 'O'
        elif (s == "Line to Pump (P3)"):
            new_valve_pos = 'I'
        elif (s == "Line to Gas (P4)"):
            new_valve_pos = 'B'
        else:
            logger.info(' invalid valve selection')
            valve_is_valid = False

        if valve_is_valid:
            self.pump1.set_valve(TITRANT_LOOP_ADDRESS, new_valve_pos)
            time.sleep(1)
            s = self.pump1.get_valve(TITRANT_LOOP_ADDRESS)
            cur_valve = "----"
            if (s=='e'):
                cur_valve = "Gas to Air (P1)"
            elif(s=='o'):
                cur_valve = "Pump to Air (P2)"
            elif(s=='i'):
                cur_valve = "Line to Pump (P3)"
            elif(s=='b'):
                cur_valve = "Line to Gas (P4)"
            else:
                cur_valve = "error"
            self.v3_cur_pos.config(text=cur_valve)


    #Loop Valve (Sample line)
    def checkCombo4(self,event):
        global SAMPLE_LOOP_ADDRESS
        valve_is_valid = True
        s = self.combo4.get()        
        if (s == "Line to Gas (P1)"):
            new_valve_pos = 'E'
        elif (s == "Line to Pump (P2)"):
            new_valve_pos = 'O'
        elif (s == "Pump to Air (P3)"):
            new_valve_pos = 'I'
        elif (s == "Gas to Air (P4)"):
            new_valve_pos = 'B'
        else:
            logger.info(' invalid valve selection')
            valve_is_valid = False
        
        if valve_is_valid:
            self.pump1.set_valve(SAMPLE_LOOP_ADDRESS, new_valve_pos)
            time.sleep(1)
            s = self.pump1.get_valve(SAMPLE_LOOP_ADDRESS)
            cur_valve = "----"
            if (s=='e'):
                cur_valve = "Line to Gas (P1)"
            elif(s=='o'):
                cur_valve = "Line to Pump (P2)"
            elif(s=='i'):
                cur_valve = "Pump to Air (P3)"
            elif(s=='b'):
                cur_valve = "Gas to Air (P4)"
            else:
                cur_valve = "error"
            
            self.v4_cur_pos.config(text=cur_valve)


    #Pipette Valve (Titrant line)
    def checkCombo5(self, event):
        global TITRANT_PIPETTE_ADDRESS
        valve_is_valid = True
        s = self.combo5.get()
        if (s == "Titrant Cannula (P1)"):
            vlv = 'I'
        elif (s == "Titrant Port (P2)"):
            vlv = 'E'
        elif (s == "Reservoirs (P3)"):
            vlv = 'O'
        else:
            logger.info(' invalid valve selection')
            valve_is_valid = False

        if valve_is_valid:
            self.pump1.set_valve(TITRANT_PIPETTE_ADDRESS,vlv)
            time.sleep(1)
            s = self.pump1.get_valve(TITRANT_PIPETTE_ADDRESS)
            cur_valve = "----"
            if (s=='i'):
                cur_valve = "Titrant Cannula (P1)"
            elif(s=='e'):
                cur_valve = "Titrant Port (P2)"
            elif(s=='o'):
                cur_valve = "Reservoirs (P3)"
            else:
                cur_valve = "error"
            self.v5_cur_pos.config(text=cur_valve)


 
    #Titrant Port Valve (Sample line)
    def checkCombo6(self,event):
        global TITRANT_PORT_ADDRESS
        valve_is_valid = True
        s = self.combo6.get()
        if (s == "N/A (P1)"):
            vlv = 'I'
        elif (s == "Titrant Line (P2)"):
            vlv = 'E'
        elif (s == "Sample Line (P3)"):
            vlv = 'O'
        else:
            logger.error(' invalid valve selection')
            valve_is_valid = False

        if valve_is_valid:
            self.pump1.set_valve(TITRANT_PORT_ADDRESS,vlv)
            time.sleep(1)
            s = self.pump1.get_valve(TITRANT_PORT_ADDRESS)
            cur_valve = "----"
            if (s=='i'):
                cur_valve = "N/A (P1)"
            elif(s=='e'):
                cur_valve = "Titrant Line (P2)"
            elif(s=='o'):
                cur_valve = "Sample Line (P3)"
            else:
                cur_valve = "error"
            self.v6_cur_pos.config(text=cur_valve)


    #Degrasser Valve (Sample line)         
    def checkCombo7(self,event):
        global DEGASSER_ADDRESS
        valve_is_valid = True
        s = self.combo7.get()
        if (s == "Reservoirs (P1)"):
            new_valve_pos = '1'
        elif (s == "Rec Port (P2)"):
            new_valve_pos = '2'
        elif (s == "Sample Port (P3)"):
            new_valve_pos = '3'
        elif (s == "Ref Port (P4)"):
            new_valve_pos = '4' 
        elif (s == "Titrant Port (P5)"):
            new_valve_pos = '5'
        elif (s == "Cell (P6)"):
            new_valve_pos = '6'
        else:
            logger.error(' invalid valve selection')
            valve_is_valid = False

        if valve_is_valid:
            self.pump1.set_multiwayvalve(DEGASSER_ADDRESS,new_valve_pos)
            time.sleep(1)
            s = self.pump1.get_valve(DEGASSER_ADDRESS)
            cur_valve = "----"
            if (s=='1'):
                cur_valve = "Reservoirs (P1)"
            elif(s=='2'):
                cur_valve = "Rec Port (P2)"
            elif(s=='3'):
                cur_valve = "Sample Port (P3)"
            elif(s=='4'):
                cur_valve = "Ref Port (P4)"
            elif(s=='5'):
                cur_valve = "Titrant Port (P5)"
            elif(s=='6'):
                cur_valve = "Cell (P6)"
            else:
                cur_valve = "error"
            self.v7_cur_pos.config(text=cur_valve)


    #Cleaning Valve (Sample line)  
    def checkCombo8(self, event):
        global TITRANT_CLEANING_ADDRESS
        valve_is_valid = True
        s = self.combo8.get()
        if (s == "Waste (P1)"):
            new_valve_pos = '1'
        elif (s == "MeOH (P2)"):
            new_valve_pos = '2'
        elif (s == "Detergent (P3)"):
            new_valve_pos = '3'
        elif (s == "DI Water (P4)"):
            new_valve_pos = '4'
        elif (s == "Cleaning Port (P5)"):
            new_valve_pos = '5'
        elif (s == "Air (P6)"):
            new_valve_pos = '6'
        else:
            logger.info(' invalid valve selection')
            valve_is_valid = False

        if valve_is_valid:
            self.pump1.set_multiwayvalve(SAMPLE_CLEANING_ADDRESS,new_valve_pos)
            time.sleep(1)
            s = self.pump1.get_valve(SAMPLE_CLEANING_ADDRESS)        
            cur_valve = "----"
            if (s=='1'):
                cur_valve = "Waste (P1)"
            elif(s=='2'):
                cur_valve = "MeOH (P2)"
            elif(s=='3'):
                cur_valve = "Detergent (P3)"
            elif(s=='4'):
                cur_valve = "DI Water (P4)"
            elif(s=='5'):
                cur_valve = "Cleaning Port (P5)"
            elif(s=='6'):
                cur_valve = "Air (P6)"
            else:
                cur_valve = "error"
            self.v8_cur_pos.config(text=cur_valve)


    #Cleaning Vlave (Titrant line)
    def checkCombo9(self, event):
        valve_is_valid = True
        global TITRANT_CLEANING_ADDRESS
        s = self.combo9.get()
        if (s == "N/A (P1)"):
            new_valve_pos = '1'
        elif (s == "Air (P2)"):
            new_valve_pos = '2'
        elif (s == "DI Water (P3)"):
            new_valve_pos = '3'
        elif (s == "Detergent (P4)"):
            new_valve_pos = '4'
        elif (s == "MeOH (P5)"):
            new_valve_pos = '5'
        elif (s == "Waste (P6)"):
            new_valve_pos = '6'
        else:
            logger.info(' invalid valve selection')
            valve_is_valid = False

        if valve_is_valid:
            self.pump1.set_multiwayvalve(TITRANT_CLEANING_ADDRESS,new_valve_pos)
            time.sleep(1)
            s = self.pump1.get_valve(TITRANT_CLEANING_ADDRESS)
            cur_valve = "----"
            if (s=='1'):
                cur_valve = "N/A (P1)"
            elif(s=='2'):
                cur_valve = "Air (P2)"
            elif(s=='3'):
                cur_valve = "DI Water (P3)"
            elif(s=='4'):
                cur_valve = "Detergent (P4)"
            elif(s=='5'):
                cur_valve = "MeOH (P5)"
            elif(s=='6'):
                cur_valve = "Waste (P6)"
            else:
                cur_valve = "error"
            self.v9_cur_pos.config(text=cur_valve)


    #BUBBLE SENSOR SELECTION FOR PUMP 1
    def checkCombob0(self,event):        
        s = self.combo0.get()        
        ss=s.partition('S')
        index = int(ss[2])
        logger.info('\t\tpump 1: bubble sensor number:{}'.format(index))
        X3 = 1050
        Y1 = 100
        dY1 = 40
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
        logger.info('\t\tpump 2: bubble sensor number:{}'.format( index))
        X3 = 1050
        Y1 = 100
        dY1 = 40
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
        global TIRRANT_PUMP_ADDRESS        
        if (flag == False):
            logger.info('\t\tswitch pump1 to normal mode')
            self.pump1.set_microstep_position(TIRRANT_PUMP_ADDRESS,0)
        else:
            logger.info("\t\tswitched pump1 to p&v  ")
            self.pump1.set_microstep_position(TIRRANT_PUMP_ADDRESS,2)


    def set_step_mode_p2(self, flag):
        global SAMPLE_PUMP_ADDRESS
        if (flag == False):
            logger.info('\t\tswitch pump2 to normal mode')
            self.pump1.set_microstep_position(SAMPLE_PUMP_ADDRESS,0)
        else:
            logger.info("\t\tswitched pump2 to p&v  ")
            self.pump1.set_microstep_position(SAMPLE_PUMP_ADDRESS,2)


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
            logger.info('\t\tpump 1 mircostep off')
            self.set_step_mode_p1(False)            
        else:  
            logger.info('\t\tpump 1 mircostep on')
            self.set_step_mode_p1(True)

        self.scalefactor_p1 = STEP_RANGE / VOLUME    
        logger.info('\t\tpump 1 scale factor:{}'.format( self.scalefactor_p1))
        if self.microstep_p1 == False:
            self.pump1.set_speed(TIRRANT_PUMP_ADDRESS,self.p1_top_spd)
            time.sleep(.25)
            str1 =  "{:.2f}".format(self.p1_top_spd / self.scalefactor_p1)
            self.p1_cur_spd.config(text = str1)
            logger.info("\t\tPump1 speed is set to {} logical  = {} physical".format(self.p1_top_spd, str1))
        else:
            new_speed = self.p1_top_spd * 8
            self.pump1.set_speed(TIRRANT_PUMP_ADDRESS,new_speed)
            time.sleep(.25)            
            str1 =  "{:.2f}".format(new_speed / self.scalefactor_p1)
            self.p1_cur_spd.config(text = str1) 
            logger.info("\t\tPump1 speed is set to {} logical  = {} physical".format(new_speed, str1))
              

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
            logger.info('\t\tpump 2 mircostep off')
            self.set_step_mode_p2(False)            
        else: 
            logger.info('\t\tpump 2 mircostep on')
            self.set_step_mode_p2(True)

        self.scalefactor_p2 = STEP_RANGE / VOLUME
        logger.info('\t\tpump2 scale factor:{}'.format( self.scalefactor_p2))
        if self.microstep_p2 == False:
            self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,self.p2_top_spd)
            time.sleep(.25)
            str1 =  "{:.2f}".format(self.p2_top_spd / self.scalefactor_p2)
            self.p2_cur_spd.config(text = str1)            
            logger.info("\t\tPump2 speed is set to {} logical  = {} physical".format(self.p2_top_spd, str1))
        else:
            new_speed = self.p2_top_spd * 8
            self.pump1.set_speed(SAMPLE_PUMP_ADDRESS,new_speed)
            time.sleep(.25)            
            str1 =  "{:.2f}".format(new_speed / self.scalefactor_p2)
            self.p2_cur_spd.config(text = str1)            
            logger.info("\t\tPump2 speed is set to {} logical  = {} physical".format(new_speed, str1))


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
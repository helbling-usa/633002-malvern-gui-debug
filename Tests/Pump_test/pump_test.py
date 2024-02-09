import time
import Pump as P





    


# p1.pump_Zinit(1)
# p1.pump_Zinit(2)
# p1.pump_Zinit(3)
# p1.pump_Zinit(4)
# time.sleep(5)


def test_pump(p1):
    #--------------- testing pump + valve1    
    p1.set_speed(1,2000)
    time.sleep(2)
    p1.set_pos_absolute(1, 5000)

    time.sleep(3)
    a = p1.get_plunger_position(1)    
    print('plunger pos:', a)
    time.sleep(1)
    p1.set_pos_absolute(1, 0)
    

    # a = p1.set_valve(1,'E')
    # time.sleep(.5)
    # a = p1.get_valve(1)
    # print('valve 1  pos:', a)


def test_4way_valve(p1, axis):
    # -------------- testing 4 port valve: address=2
    p1.config_valve(5,4)
    for i in ['I', 'O', 'E', 'B']:
        time.sleep(.5)
        a = p1.set_valve(axis,i)  
        time.sleep(.5)
        a = p1.get_valve(axis)
        print('valve pos:', a)

    




def test_3way_valve(p1,axis):
    ##------------------- testing 3 way valvue: address=4
    # set valve in address 4 as 3 way valve:
    # p1.config_valve(4, 3)
    for i in range(3):
        time.sleep(1)
        #set the positon of 6 way valve
        a = p1.set_multiwayvalve(axis,str(i+1))
        time.sleep(1)    
        #now, read the position of 6 way valve
        a = p1.get_valve(axis)
        print('valve pos:', a)


def test_6way_valve(p1,axis):
    ##------------------- testing 6 way valvue: address=3
    # set valve in address 4 as 3 way valve:
    # p1.config_valve(4, 3)
    for i in range(6):
        time.sleep(1)
        #set the positon of 6 way valve
        a = p1.set_multiwayvalve(axis,str(i+1))
        # p1.set_valve(4,'I')
        time.sleep(1)    
        #now, read the position of 6 way valve
        a = p1.get_valve(axis)
        print('valve pos:', a)
    

def show_message():
    print('Please choose an option:')
    print("1) Initialze Pump 1")
    print("2) Initialze VALVE 2 (axis 2)")
    print("3) Initialze VALVE 3 (axis 3)")
    print("4) Initialze VALVE 4 (axis 4)")
    print("5) Test pump")
    print("6) Test pump1 valve")
    print("7) Test 4 way valve (axis 2)")
    print("8) Test 3 way valve (axis 4)")
    print("9) Test 6 way valve (axis 3)")
    print("10) Initialze Pump 2")
    print("11) Test pump2 valve")

if __name__ == "__main__":
    p1 = P.Pump("COM6")
    val = '-'

    while val != 'q':
        show_message()
        val = input("Enter a number from 1 to 8. Enter 'q' to stop:  ")
        
        print('You selected:', val)
        if val not in ['1','2','3','4','5','6','7','8','9','10','11','q','Q']:
            print('ERROR. Input must be a number from 1 to 5')
            continue
       
        if val=='1':
            p1.pump_Zinit(1)
        elif val=='2':
            p1.pump_Zinit(2)
        elif val=='3':
            p1.pump_Zinit(3)
        elif val=='4':
            p1.pump_Zinit(4)
        elif val=='5':
            test_pump(p1)
        elif val=='6':
            # p1.config_valve(1, 4)
            test_4way_valve(p1,1)
        elif val=='7':
            # p1.config_valve(2, 4)
            test_4way_valve(p1,2)
        elif val=='8':
            test_3way_valve(p1,4)
        elif val=='9':
            test_6way_valve(p1,3)
        elif val=='10':
            p1.pump_Zinit(2)
        elif val=='11':
            test_4way_valve(p1,5)
        time.sleep(2)



    p1.close()
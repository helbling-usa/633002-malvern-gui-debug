import time
import Pump as P




def test_3way_valve(p1,axis):
    ##------------------- testing 3 way valvue: address=4
    # set valve in address 4 as 3 way valve:
    # p1.config_valve(4, 3)
    for i in ['I', 'O', 'E']:
        time.sleep(.5)
        a = p1.set_valve(axis,i)  
        time.sleep(.5)
        a = p1.get_valve(axis)
        print('for:',i,'  valve pos is:', a)

        
    for i in range(3):
        time.sleep(1)
        #set the positon of 6 way valve
        a = p1.set_multiwayvalve(axis,str(i+1))
        time.sleep(1)    
        #now, read the position of 6 way valve
        a = p1.get_valve(axis)
        print('for:', i+1, '  valve pos is:', a)

    
    
if __name__ == "__main__":
    p1 = P.Pump("COM6")

    # p1.pump_setAutoinit(1)
    # time.sleep(2)
    # p1.pump_setAutoinit(5)
    p1.pump_set3wayPumpPortAssignment(5)


    time.sleep(1)
    test_3way_valve(p1,5)

    p1.close()
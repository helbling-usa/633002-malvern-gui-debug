import time
import Pump as P





    
if __name__ == "__main__":
    p1 = P.Pump("COM6")

    p1.pump_setAutoinit(1)
    time.sleep(2)
    p1.pump_setAutoinit(5)



    p1.close()
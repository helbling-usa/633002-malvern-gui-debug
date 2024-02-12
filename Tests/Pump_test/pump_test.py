import time
import Pump as P


# p1.pump_Zinit(1)
# p1.pump_Zinit(2)
# p1.pump_Zinit(3)
# p1.pump_Zinit(4)
# time.sleep(5)


def test_pump(p1):
    # --------------- testing pump + valve1
    p1.set_speed(1, 2000)
    time.sleep(2)
    p1.set_pos_absolute(1, 5000)

    time.sleep(3)
    a = p1.get_plunger_position(1)
    print("plunger pos:", a)
    time.sleep(1)
    p1.set_pos_absolute(1, 0)

    # a = p1.set_valve(1,'E')
    # time.sleep(.5)
    # a = p1.get_valve(1)
    # print('valve 1  pos:', a)


def test_4way_valve(p1, axis):
    # -------------- testing 4 port valve: address=2
    p1.config_valve(5, 4)
    a = p1.get_valve(axis)
    print("initial valve positionm:", a)
    for i in ["I", "B", "E", "O"]:
        time.sleep(0.5)
        a = p1.set_valve(axis, i)
        time.sleep(0.5)
        a = p1.get_valve(axis)
        print("target valve:", i, ",  current valve pos:", a)


def test_3way_valve(p1, axis):
    ##------------------- testing 3 way valvue: address=4
    # set valve in address 4 as 3 way valve:
    # p1.config_valve(4, 3)
    for i in ["I", "O", "B"]:
        time.sleep(0.5)
        a = p1.set_valve(axis, i)
        time.sleep(0.5)
        a = p1.get_valve(axis)
        print("for:", i, "  valve pos is:", a)

    for i in range(3):
        time.sleep(1)
        # set the positon of 6 way valve
        a = p1.set_multiwayvalve(axis, str(i + 1))
        time.sleep(1)
        # now, read the position of 6 way valve
        a = p1.get_valve(axis)
        print("for:", i + 1, "  valve pos is:", a)


def test_6way_valve(p1, axis):
    ##------------------- testing 6 way valvue: address=3
    # set valve in address 4 as 3 way valve:
    # p1.config_valve(4, 3)
    for i in range(6):
        time.sleep(1)
        # set the positon of 6 way valve
        a = p1.set_multiwayvalve(axis, str(i + 1))
        # p1.set_valve(4,'I')
        time.sleep(1)
        # now, read the position of 6 way valve
        a = p1.get_valve(axis)
        print("valve pos:", a)


def show_message():
    print("---------------------------------------")
    print("Please choose an option:")
    print("1) Initialze axis 1            ", end="")
    print("\t\t2) Initialze axis 2")
    print("3) Initialze axis 3            ", end="")
    print("\t\t4) Initialze axis 4")
    print("5) Initialze axis 5            ", end="")
    print("\t\t6) Initialze axis 6")
    print("7) Initialze axis 7            ", end="")
    print("\t\t8) Initialze axis 8")
    print("9) Initialze axis 9            ", end="")
    print("\t\t10) Test pump")
    print("11) Test pump1 valve           ", end="")
    print("\t\t12) Test pump2 valve")
    print("13) Test valve 3 (4 way)       ", end="")
    print("\t\t14) Test valve 4 (3 way)")
    print("15) Test valve 5 (3 way)       ", end="")
    print("\t\t16) Test valve 6 (3 way)")
    print("17) Test valve 7 (6 way)       ", end="")
    print("\t\t18) Test valve 8 (6 way)")
    print("19) Test valve 9 (6 way)")


if __name__ == "__main__":
    p1 = P.Pump("COM6")
    val = "-"

    while val != "0":
        show_message()
        val = input("Enter a number from 1 to 16. Enter '0' to stop:  ")

        print("You selected:", val)

        if int(val) not in range(
            20
        ):  # ['1','2','3','4','5','6','7','8','9','10','11','q','Q']:
            print("ERROR. Input must be a number from 1 to 5")
            continue

        if val == "1":
            p1.pump_Zinit(1)
        elif val == "2":
            p1.pump_Zinit(2)
        elif val == "3":
            p1.pump_Zinit(3)
        elif val == "4":
            p1.pump_Zinit(4)
        elif val == "5":
            p1.pump_Zinit(5)
        elif val == "6":
            p1.pump_Zinit(6)
        elif val == "7":
            p1.pump_Zinit(7)
        elif val == "8":
            p1.pump_Zinit(8)
        elif val == "9":
            p1.pump_Zinit(9)
        elif val == "10":
            test_pump(p1)
        elif val == "11":
            # p1.config_valve(1, 4)
            test_4way_valve(p1, 1)
        elif val == "12":
            # p1.config_valve(2, 4)
            test_4way_valve(p1, 2)
        elif val == "13":
            test_4way_valve(p1, 3)
        elif val == "14":
            test_4way_valve(p1, 4)
        elif val == "15":
            test_3way_valve(p1, 5)
        elif val == "16":
            test_3way_valve(p1, 6)
        elif val == "17":
            test_3way_valve(p1, 7)
        elif val == "18":
            test_3way_valve(p1, 8)
        elif val == "19":
            test_6way_valve(p1, 9)
        # elif val == "15":
        #     test_6way_valve(p1, 9)
        # elif val == "16":
        #     p1.pump_Zinit(2)
        # elif val == "17":
        #     test_4way_valve(p1, 5)
        else:
            print("wrong choice")
        time.sleep(2)

    p1.close()

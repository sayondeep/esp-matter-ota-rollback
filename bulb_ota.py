import threading
import time
from enum import Enum
import curses
import subprocess
import os
from multiprocessing import Process, Lock
import textwrap

# pairing_codes=["MT:634J0KQS02KA0648G00"]
# pairing_codes=["MT:634J0CEK01KA0648G00"]
pairing_codes=["MT:634J0KQS02KA0648G00","MT:634J0CEK01KA0648G00"]

# pairing_codes=["MT:Q3R000QV17-HKA3K.00"] #real_bulb

base_nodeid=7700

SSID="TP-Link_2EA4"
passphrase="14754210"

# SSID="DIR-825-5723"
# passphrase="32129434"

ota_provider_node_id = "0xDEADBEEF"

device_statuses = {
    # 7700: "waiting for commission.",
    # 7701: "waiting for commission.",
}

commission_successful_log="CHIP:TOO: Device commissioning completed with success"

class device_state(Enum):
    waiting_for_commission=0
    commissioning_started=1
    commision_completed = 2
    getting_old_firmware=3
    got_old_firmware=4
    waiting_for_ota_complete = 5
    ongoing_ota=6
    ota_completed = 7
    getting_new_firmware=8
    got_new_firmware=9
    resetting_to_factory=10
    factory_reset_success=11
    operation_completed=12


current_state = [device_state.waiting_for_commission]* len(pairing_codes)
ota_progress_tracker = [[0 for _ in range(101)] for _ in range(len(pairing_codes))]
ota_null_tracker = [0]* len(pairing_codes)

# create a lock
chip_lock = Lock()
ota_lock = Lock()


def error_(node_id):

    index = node_id-base_nodeid
    
    chip_lock.acquire()
    color_change_command = ['chip-tool', 'colorcontrol', 'move-to-hue', '0','0', '0', '0', '0', str(node_id), '0x1']
    result = subprocess.run(color_change_command, capture_output=True, text=True)
    
    current_state[index] = device_state.operation_completed
    device_statuses[node_id] += "-->Error Occured."
    chip_lock.release()
    ota_lock.release()

def perform_operations(node_id,qr_code):
    index = node_id-base_nodeid

    while current_state[index] is not device_state.operation_completed:
        if(current_state[index]==device_state.waiting_for_commission):
            time.sleep(5)
            trigger_commissioning(node_id,qr_code)
        if(current_state[index]==device_state.commision_completed):
            current_state[index]= device_state.getting_old_firmware
            time.sleep(10)
            check_for_firmware_version(node_id)
        if(current_state[index]==device_state.got_old_firmware):
            trigger_ota(node_id,ota_provider_node_id)
        if(current_state[index]==device_state.waiting_for_ota_complete):
            time.sleep(10)
            check_for_ota_percentage(node_id)
        if(current_state[index]==device_state.ota_completed):
            curr_percent=check_for_ota_percentage(node_id)
            while str(curr_percent) != 'null':
                device_statuses[node_id]+="-->"+str(curr_percent)
                time.sleep(10)
                curr_percent=check_for_ota_percentage(node_id)

            ota_lock.release()
            current_state[index]= device_state.getting_new_firmware
            time.sleep(10)
            check_for_firmware_version(node_id)
        if(current_state[index]==device_state.got_new_firmware):
            time.sleep(10)
            current_state[index]= device_state.resetting_to_factory
            device_statuses[node_id]+="-->resetting to factory."
            reset_to_factory(node_id)
        if(current_state[index]==device_state.factory_reset_success):
            current_state[index]=device_state.operation_completed


def trigger_commissioning(node_id,qr_code):
    
    # chip_tool_command = ['chip-tool', 'pairing', 'code-wifi',str(node_id), str(SSID), str(passphrase),str(qr_code),'--paa-trust-store-path','/home/sayon/esp/ESP-PAA/main_net']
    chip_lock.acquire()
    chip_tool_command = ['chip-tool', 'pairing', 'code-wifi',str(node_id), str(SSID), str(passphrase),str(qr_code)]
    current_state[node_id-base_nodeid]=device_state.commissioning_started
    device_statuses[node_id]+="-->ongoing commission."

    result = subprocess.run(chip_tool_command, capture_output=True, text=True)

    lines = result.stdout.split("\n")

    for line in lines:
        if commission_successful_log in line:
            current_state[node_id-base_nodeid]=device_state.commision_completed
            device_statuses[node_id]+="-->commission success."
    
    chip_lock.release()


def check_for_firmware_version(node_id):
    # print("checking firmware version")
    index = node_id-base_nodeid
    chip_lock.acquire()
    chip_tool_command = ['chip-tool', 'basicinformation', 'read', 'software-version', str(node_id), '0x0']

    result = subprocess.run(chip_tool_command, capture_output=True, text=True)

    lines = result.stdout.split("\n")

    sw_ver = -1

    for line in lines:
        if "CHIP:TOO:   SoftwareVersion:" in line:
            line_parts = line.split("SoftwareVersion: ")
            sw_ver = line_parts[1]
            break

    # print("\nS/W version: " + str(sw_ver) + "for" +str(node_id), end="")
    if(float(sw_ver)>0 and current_state[index]== device_state.getting_old_firmware):
        device_statuses[node_id]+= "-->has software version:" + str(sw_ver)
        current_state[node_id-base_nodeid]=device_state.got_old_firmware
    
    if(float(sw_ver)>0 and current_state[index]== device_state.getting_new_firmware):
        device_statuses[node_id]+= "-->has software version:" + str(sw_ver)
        current_state[node_id-base_nodeid]=device_state.got_new_firmware
    
    chip_lock.release()


def trigger_ota(node_id, ota_provider_node_id):

    index = node_id-base_nodeid
    time.sleep(25)
    ota_lock.acquire(timeout=700)
    chip_lock.acquire()
    color_change_command = ['chip-tool', 'colorcontrol', 'move-to-hue', '120','0', '0', '0', '0', str(node_id), '0x1']
    result = subprocess.run(color_change_command, capture_output=True, text=True)
    
    time.sleep(10)
    current_state[index] = device_state.waiting_for_ota_complete

    ota_trigger_command = ['chip-tool', 'otasoftwareupdaterequestor', 'announce-otaprovider', ota_provider_node_id, '0', '0', '0', str(node_id), '0x0']

    result = subprocess.run(ota_trigger_command, capture_output=True, text=True)
    device_statuses[node_id] += "-->OTA triggered."

    chip_lock.release()

def check_for_ota_percentage(node_id):
    ota_progress = 0
    chip_lock.acquire()
    result = subprocess.run(['chip-tool', 'otasoftwareupdaterequestor', 'read', 'update-state-progress', str(node_id), '0x0'], capture_output=True, text=True)
    lines = result.stdout.split("\n")

    for line in lines:
        if "CHIP:TOO:   UpdateStateProgress:" in line:
            line_parts = line.split("UpdateStateProgress: ")
            ota_progress = line_parts[1]
            break
    chip_lock.release()

    index = node_id-base_nodeid
    if str(ota_progress)!='null' and int(ota_progress)>=0:
        ota_progress_tracker [index][int(ota_progress)]+=1
        if(ota_progress_tracker [index][int(ota_progress)]>=4):
            error_(node_id)
    elif str(ota_progress)=='null':
        ota_null_tracker [index]+=1
        if(ota_null_tracker [index]>=4):
            error_(node_id)




    if current_state[node_id-base_nodeid]==device_state.waiting_for_ota_complete:

        if(device_statuses[node_id][-1]=='%'):
            device_statuses[node_id]=device_statuses[node_id][:-23]
        
        device_statuses[node_id]+="--> ota progress at "+ str(ota_progress)+"%"

        if str(ota_progress)!='null' and int(ota_progress)>=90:
            chip_lock.acquire()
            color_change_command = ['chip-tool', 'colorcontrol', 'move-to-hue', '60','0', '0', '0', '0', str(node_id), '0x1']
            result = subprocess.run(color_change_command, capture_output=True, text=True)
            chip_lock.release()
            time.sleep(5)
            current_state[node_id-base_nodeid]=device_state.ota_completed
            device_statuses[node_id]+="--> ota completing..."

    if current_state[node_id-base_nodeid]==device_state.ota_completed:
        return ota_progress

def reset_to_factory(node_id):
    index= node_id-base_nodeid
    fabric_id = -1
    chip_lock.acquire()
    result = subprocess.run(['chip-tool', 'operationalcredentials', 'read', 'current-fabric-index', str(node_id), '0x0'], capture_output=True, text=True)
    lines = result.stdout.split("\n")

    for line in lines:
        if "CHIP:TOO:   CurrentFabricIndex:" in line:
            line_parts = line.split("CurrentFabricIndex: ")
            fabric_id = line_parts[1]
            break
    chip_lock.release()
    if str(fabric_id)!='null' and int(fabric_id)>0:
        chip_lock.acquire()
        result = subprocess.run(['chip-tool', 'operationalcredentials', 'remove-fabric', str(fabric_id), str(node_id), '0x0'], capture_output=True, text=True)
        current_state[index]=device_state.factory_reset_success
        device_statuses[node_id]+="-->device reset to factory."
        chip_lock.release()

stop_event = threading.Event()
    
def setup_for_ota(pairing_codes):

    # Create a thread for each node and start operations

    threads = []
    for index in range(len(pairing_codes)):
        node_id = base_nodeid + index
        qr_code = pairing_codes[index]
        device_statuses[int(node_id)]= "waiting for commissioning.."
        thread = threading.Thread(target=perform_operations, args=(node_id, qr_code))
        threads.append(thread)
        thread.start()
        # thread.join(1000)
    


    # Wait for all threads to finish
    for thread in threads:

        thread.join(1000)




def main(stdscr):

    # curses.wrapper(setup_for_ota,pairing_codes)
    
    for index in range(len(pairing_codes)):
        node_id = base_nodeid+index
        device_statuses[node_id]=""
    
    set_up_ota_thread = threading.Thread(target=setup_for_ota,args=(pairing_codes,))
    set_up_ota_thread.start()

    curses.curs_set(0)
    stdscr.clear()
    try:
        while True:
            for index in range(len(pairing_codes)):
                node_id = base_nodeid + index
                status = device_statuses[node_id]

                stdscr.addstr(index*2, 0,f"{node_id} : {pairing_codes[index]} : {status}")

            stdscr.refresh()
            time.sleep(1)  # Adjust the sleep interval as needed
            
    
    except KeyboardInterrupt:
        pass

    set_up_ota_thread.join()

    print("All processes finished.")


if __name__ == '__main__':
    # main()
    curses.wrapper(main)














































# def ota_progress(stdscr):
#     stdscr.clear()
#     try:
#         while True:
#             # Print all lines at once
#             for index, line in enumerate(lines):
#                 stdscr.addstr(index, 0, line)
#             stdscr.refresh()
#             time.sleep(1)  # Adjust the sleep interval as needed
#             stdscr.clear()  # Clear all lines
#     except KeyboardInterrupt:
#         pass

#     for flag in exit_flags:
#         flag.set()
#     for thread in update_threads:
#         thread.join()

# curses.wrapper(main)
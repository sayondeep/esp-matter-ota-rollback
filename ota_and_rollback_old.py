import serial
import os
import argparse
import sys
import glob
import time
from datetime import datetime
from enum import Enum
import subprocess

class device_firmware(Enum):
    old_firmware = 1
    new_firmware = 2

class device_state(Enum):
    bootup_completed = 1
    waiting_for_bootup = 2
    waiting_for_ota_complete = 3
    ota_completed = 3
    waiting_for_rollback_complete = 4

current_firmware = device_firmware.old_firmware
current_state = device_state.waiting_for_rollback_complete
prev_time = 0
bootup_complete_time = 0
ota_start_time = 0
ota_success_count = 0
ota_failure_count = 0

old_version_log = "cpu_start: App version:      1.1.0-6ff791c-dirty"
new_version_log = "cpu_start: App version:      1.1.1-6ff791c-dirty"

reboot_log = "cpu_start: Unicore app"
bootup_completed_log = "matter_one_rollback: ********** Matter one ready **********"
ota_completed_log = "matter_one_event: OTA state started"
ota_start_failed_log = "chip[SWU]: Failed to connect to node"
ota_failed_log = "matter_one_event: OTA state download failed"
ota_aborted_log = "matter_one_event: OTA state download aborted"

def check_for_firmware_version(data):
    global current_firmware
    if old_version_log in data:
        print("Old firmware")
        current_firmware = device_firmware.old_firmware
    if new_version_log in data:
        print("New firmware")
        current_firmware = device_firmware.new_firmware

def check_for_bootup_complete(data):
    global current_state
    global bootup_complete_time

    if reboot_log in data:
        print("Rebooted")

    if bootup_completed_log in data:
        print("Bootup Completed")
        bootup_complete_time = time.time()
        current_state = device_state.bootup_completed

def check_for_ota_percentage(node_id):
    global prev_time
    global ota_start_time
    ota_progress = 0

    if current_state != device_state.waiting_for_ota_complete:
        return

    current_time = time.time()
    if current_time - prev_time < 10:
        return

    result = subprocess.run(['chip-tool', 'otasoftwareupdaterequestor', 'read', 'update-state-progress', '0x7283', '0x0'], capture_output=True, text=True)
    lines = result.stdout.split("\n")

    for line in lines:
        if "[TOO]   UpdateStateProgress:" in line:
            line_parts = line.split("UpdateStateProgress: ")
            ota_progress = line_parts[1]
            break

    if str(ota_progress) == "null":
        print("Could not get OTA Progress")
    else:
        print("\rOTA progress: " + str(ota_progress) + "%" + " in " + str(int(current_time - ota_start_time)) + " seconds", end="")
    prev_time = time.time()

def check_for_ota_complete(data):
    global current_state
    global ota_success_count
    global ota_failure_count

    if ota_completed_log in data:
        print("OTA Completed")
        current_state = device_state.ota_completed
        ota_success_count += 1
    if ota_start_failed_log in data:
        print("OTA Start Failed")
        current_state = device_state.bootup_completed
        ota_failure_count += 1
    if ota_failed_log in data:
        print("OTA Failed")
        current_state = device_state.bootup_completed
        ota_failure_count += 1
    if ota_aborted_log in data:
        print("OTA Aborted")
        current_state = device_state.bootup_completed
        ota_failure_count += 1

def trigger_ota(node_id, ota_provider_node_id):
    global current_firmware
    global current_state
    global ota_success_count
    global ota_failure_count
    global bootup_complete_time
    global ota_start_time

    if current_firmware == device_firmware.old_firmware and current_state == device_state.bootup_completed:
        current_time = time.time()
        if current_time - bootup_complete_time < 20:
            return

        print("OTA Success count: " + str(ota_success_count))
        print("OTA Failure count: " + str(ota_failure_count))
        current_state = device_state.waiting_for_ota_complete
        print("Trigger OTA")
        ota_trigger_command = ['chip-tool', 'otasoftwareupdaterequestor', 'announce-otaprovider', ota_provider_node_id, '0', '0', '0', node_id, '0x0']
        print("Running: " + str(ota_trigger_command))
        result = subprocess.run(ota_trigger_command, capture_output=True, text=True)
        ota_start_time = time.time()

def trigger_rollback(device_serial):
    global current_firmware
    global current_state
    global bootup_complete_time

    if current_firmware == device_firmware.new_firmware and current_state == device_state.bootup_completed:
        current_time = time.time()
        if current_time - bootup_complete_time < 20:
            return

        print("Trigger Rollback")
        current_state = device_state.waiting_for_rollback_complete
        rollback_command = "\nmatter esp utils rollback\n"
        device_serial.write(rollback_command.encode())

def process_logs(device_serial, data, node_id, ota_provider_node_id):
    check_for_firmware_version(data)
    check_for_bootup_complete(data)
    trigger_ota(node_id, ota_provider_node_id)
    check_for_ota_percentage(node_id)
    check_for_ota_complete(data)
    trigger_rollback(device_serial)

def capture_device_log(path, output_file_name, port, node_id, ota_provider_node_id):
    log_file = open(os.path.join(path, output_file_name), 'a')
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_file.write("\n")
    log_file.write("\n")
    log_file.write("*****************************")
    log_file.write("\n")
    log_file.write("********** New log **********")
    log_file.write("\n")
    log_file.write("****** " + current_datetime + " *****")
    log_file.write("\n")
    log_file.write("*****************************")
    log_file.write("\n")
    log_file.write("\n")

    print("Capturing device logs")
    device_serial = serial.Serial(port, 115200)

    while True:
        data = device_serial.readline()
        data = data.decode(encoding="unicode_escape")
        log_file.write(data)
        process_logs(device_serial, data, node_id, ota_provider_node_id)

def get_serial_port(port):
    if port != None:
        return port

    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.usbserial*')
    else:
        raise EnvironmentError('Unsupported platform')

    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            print("Port detected is: " + port)
            return port
        except (OSError, serial.SerialException):
            pass
    return None

def create_default_dirs(path, output_file_name):
    if not os.path.exists(path):
        os.makedirs(path)
    if not os.path.exists(os.path.join(path, output_file_name)):
        with open(os.path.join(path, output_file_name), 'w') as file:
            file.write("**********  Start  **********")
            log_file.write("\n")

def get_args():
    parser = argparse.ArgumentParser(description='Parse OTA Header for ZeroCode')

    parser.add_argument('--port', default=None, type=str, help="Port if not detected automatically.")
    parser.add_argument('--node_id', default="0x7283", type=str, help="Node ID of commissioned device.")
    parser.add_argument('--ota_provider_node_id', default="1", type=str, help="Nodee ID of the commissioned OTA provider.")
    args = parser.parse_args()

    return args.port, args.node_id, args.ota_provider_node_id

def main():
    port, node_id, ota_provider_node_id = get_args()

    path = 'output'
    output_file_name = 'device_output.log'

    create_default_dirs(path, output_file_name)
    port = get_serial_port(port)

    capture_device_log(path, output_file_name, port, node_id, ota_provider_node_id)

if __name__ == '__main__':
    main()

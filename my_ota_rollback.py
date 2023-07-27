import serial

def clear_serial_buffer(ser):
    # Read and discard any existing data in the serial buffer
    ser.reset_input_buffer()

def monitor_serial_data(serial_port, baud_rate):
    try:
        # Create a serial object
        ser = serial.Serial(serial_port, baud_rate)

        # Clear the serial buffer before starting monitoring
        clear_serial_buffer(ser)

        print(f"Monitoring data from {serial_port} at {baud_rate} baud...")
        
        while True:
            # Read a line of data from the serial port (change to ser.read() for raw bytes)
            data = ser.readline().decode().strip()
            if data:
                print("Received:", data)

    except KeyboardInterrupt:
        print("Keyboard interrupt. Stopping serial monitoring.")
        
    except serial.SerialException as e:
        print(f"Serial error: {e}")

    finally:
        # Close the serial port on program exit
        ser.close()

if __name__ == "__main__":
    # Define the serial port and baud rate here
    serial_port = '/dev/ttyUSB0'  # Change this to your specific serial port (e.g., 'COM3' on Windows)
    baud_rate = 115200  # Set the baud rate based on your ESP32/ESP8266 configuration
    
    monitor_serial_data(serial_port, baud_rate)

import os
import struct
import argparse
import json

from tlv import TLVReader, TLVWriter, uint

ota_image_details_data = {
    "vendorId": 0,
    "productId": 0,
    "softwareVersion": 0,
    "softwareVersionString": "",
    "cDVersionNumber": 18,
    "softwareVersionValid": True,
    "minApplicableSoftwareVersion": 0,
    "maxApplicableSoftwareVersion": 0,
    "otaURL": ""
}

def parse_image_header(input_file_path):
    with open(input_file_path, 'rb') as file:
        FIXED_HEADER_FORMAT = '<IQI'
        fixed_header = file.read(struct.calcsize(FIXED_HEADER_FORMAT))
        magic, total_size, header_size = struct.unpack(FIXED_HEADER_FORMAT, fixed_header)
        header_tlv = TLVReader(file.read(header_size)).get()['Any']

    vendor_id = header_tlv[0]
    product_id = header_tlv[1]
    software_version = header_tlv[2]
    software_version_string = header_tlv[3]

    return vendor_id, product_id, software_version, software_version_string

def get_image_json(vendor_id, product_id, software_version, software_version_string, input_file_path):
    ota_image_details_data['vendorId'] = vendor_id
    ota_image_details_data['productId'] = product_id
    ota_image_details_data['softwareVersion'] = software_version
    ota_image_details_data['softwareVersionString'] = software_version_string
    ota_image_details_data['maxApplicableSoftwareVersion'] = software_version - 1
    ota_image_details_data['otaURL'] = str(os.path.join(os.getcwd(), input_file_path))

    return ota_image_details_data

def add_to_json(path, output_file_name, image_details):
    with open(os.path.join(path, output_file_name), 'r') as file:
        json_data = file.read()

    data = json.loads(json_data)
    data['deviceSoftwareVersionModel'].append(image_details)
    json_data = json.dumps(data, indent=4)

    with open(os.path.join(path, output_file_name), 'w') as file:
        file.write(json_data)

def get_args():
    parser = argparse.ArgumentParser(description='Parse OTA Header for ZeroCode')

    supported_files = []
    input_path = os.path.join(os.getcwd(), 'input')
    for input_file in os.listdir(input_path):
        supported_files.append(input_file)
    parser.add_argument("--file_name", choices=supported_files, type=str, help='File to be signed', required=True)

    args = parser.parse_args()

    return args.file_name

def create_default_dirs(path, output_file_name):
    if not os.path.exists(path):
        os.makedirs(path)
    if os.path.exists(os.path.join(path, output_file_name)):
        os.remove(os.path.join(path, output_file_name))
    with open(os.path.join(path, output_file_name), 'w') as file:
        json_data = "{\"deviceSoftwareVersionModel\":[]}"
        file.write(json_data)

def main():
    file_name = get_args()

    path = 'output'
    input_path = 'input'
    input_file_path = os.path.join(input_path, file_name)
    output_file_name = 'ota_image_list.json'

    create_default_dirs(path, output_file_name)

    vendor_id, product_id, software_version, software_version_string = parse_image_header(input_file_path)
    image_details = get_image_json(vendor_id, product_id, software_version, software_version_string, input_file_path)
    add_to_json(path, output_file_name, image_details)

    print('Added ' + file_name + ' to json: ' + str(os.path.join(path, output_file_name)))

if __name__ == '__main__':
    main()

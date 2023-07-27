#!/usr/bin/env bash

set -e

file_name=""
folder_path="input"
node_id="0x7283"
ota_provider_node_id="0xDEADBEEF"

stop_processes() {
    echo ""
    echo "Stopping background processes: $ota_provider_process_id"
    kill "$ota_provider_process_id"
    exit
}


mkdir -p output

# Kill any previous instances
#ota_provider_process_id=$(ps -eo pid,command | grep "chip-ota-provider-app" | grep -v grep | awk '{print $1}')
#if [[ -n "$ota_provider_process_id" ]]; then
    #echo "Stopping previous processes: $ota_provider_process_id"
    #kill "$ota_provider_process_id"
#fi

echo "Starting OTA provider in background"
#$ESP_MATTER_PATH/connectedhomeip/connectedhomeip/out/debug/chip-ota-provider-app --secured-device-port 5565 --filepath /home/sayon/esp/myproj/light-matter-ota_v11.bin > output/ota_provider_output.log 2>&1 &

gnome-terminal -- bash -c "\"$ESP_MATTER_PATH\"/connectedhomeip/connectedhomeip/out/debug/chip-ota-provider-app  --secured-device-port 5565 --filepath /home/sayon/esp/myproj/light-matter-ota_v11.bin |tee output/ota_provider_output.log ; exec bash"

#ota_provider_process_id=$(ps -eo pid,command | grep "chip-ota-provider-app" | grep -v grep | awk '{print $1}')
#echo "process id: $ota_provider_process_id"
#trap stop_processes SIGINT
#trap stop_processes ERR

echo "Setting up OTA provider"
# chip-tool pairing onnetwork $ota_provider_node_id 20202021 >> output/chip_tool_output.log
#chip-tool accesscontrol write acl '[{"fabricIndex": 1, "privilege": 5, "authMode": 2, "subjects": [112233], "targets": null}, {"fabricIndex": 1, "privilege": 3, "authMode": 2, "subjects": null, "targets": [{"cluster": 41, "endpoint": null, "deviceType": null}]}]' $ota_provider_node_id 0x0 >> output/chip_tool_output.log

gnome-terminal -- bash -c "PATH=\"$PATH\":~/esp/esp-matter/connectedhomeip/connectedhomeip/out/host && chip-tool accesscontrol write acl '[{\"fabricIndex\": 1, \"privilege\": 5, \"authMode\": 2, \"subjects\": [112233], \"targets\": null}, {\"fabricIndex\": 1, \"privilege\": 3, \"authMode\": 2, \"subjects\": null, \"targets\": [{\"cluster\": 41, \"endpoint\": null, \"deviceType\": null}]}]' \"$ota_provider_node_id\" 0 |tee output/chip_tool_output.log; exec bash"

echo "Performing OTA and Rollback"
python3 ota_and_rollback.py --node_id $node_id --ota_provider_node_id $ota_provider_node_id

stop_processes

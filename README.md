# Automation

## OTA Test

### Device

*   Commission the device using chip-tool
    ```
    chip-tool pairing code-wifi node_id ssid password qr_code_text
    ```

### OTA provider

*   Copy the ota image in input folder
*   Build the OTA provider
    ```
    scripts/examples/gn_build_example.sh examples/ota-provider-app/linux out/debug chip_config_network_layer_ble=false
    ```

### Trigger OTA

*   Run the script to setup the provider and trigger OTA continuously
    ```
    ./ota_test.sh node_id
    ```

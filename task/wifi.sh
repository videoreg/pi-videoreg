#!/usr/bin/bash
# Manages WiFi state via nmcli/rfkill: block/unblock the radio, bring connections up/down, toggle autoconnect.

wifi_block() {
    sudo nmcli radio wifi off
    sudo rfkill block wifi
    echo "WiFi blocked"
    return 0
}

wifi_unblock() {
    if sudo rfkill list wifi | grep -q "Soft blocked: no"; then
        echo "WiFi already unblocked, ensuring radio is on..."
    fi
    
    sudo rfkill unblock wifi
    sudo nmcli radio wifi on
    echo "WiFi unblocked"
    return 0
}

wifi_connection_up() {
    local connection_name="$1"
    
    if [[ -z "$connection_name" ]]; then
        echo "Error: connection name should not be empty."
        exit 1
    fi
    
    # Check if the WiFi module is blocked via rfkill
    if sudo rfkill list wifi | grep -q "Soft blocked: yes"; then
        echo "Error: WiFi is blocked. Unblock it first using: $0 unblock"
        exit 1
    fi

    # Check if the connection is already active
    if sudo nmcli connection show --active | grep "^$connection_name " > /dev/null 2>&1; then
        echo "Connection $connection_name is already active, skipping..."
        return 0
    fi
    
    echo "Up connection $connection_name..."
    sudo nmcli connection up "$connection_name"
    echo "Done"
    return 0
}

wifi_connection_down() {
    local connection_name="$1"
    
    if [[ -z "$connection_name" ]]; then
        echo "Error: connection name should not be empty."
        exit 1
    fi
    
    echo "Down connection $connection_name..."
    sudo nmcli connection down "$connection_name"
    echo "Done"
    return 0
}

wifi_autoconnect() {
    local connection_name="$1"
    local enable="$2"
    
    if [[ -z "$connection_name" ]]; then
        echo "Error: connection name should not be empty."
        exit 1
    fi
    
    if [[ -z "$enable" ]]; then
        echo "Error: autoconnect value should not be empty (use 1 or 0)."
        exit 1
    fi
    
    local autoconnect_value
    if [[ "$enable" == "1" ]]; then
        autoconnect_value="yes"
    elif [[ "$enable" == "0" ]]; then
        autoconnect_value="no"
    else
        echo "Error: invalid autoconnect value '$enable' (use 1 or 0)."
        exit 1
    fi
    
    echo "Setting autoconnect to $autoconnect_value for connection $connection_name..."
    sudo nmcli connection modify "$connection_name" connection.autoconnect "$autoconnect_value"
    echo "Done"
    return 0
}

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 {block|unblock|up <connection_name>|autoconnect <connection_name> <1|0>}"
    exit 1
fi

case "$1" in
    block)
        wifi_block
        ;;
    unblock)
        wifi_unblock
        ;;
    up)
        if [ "$#" -ne 2 ]; then
            echo "Error: 'up' command requires connection name"
            echo "Usage: $0 up <connection_name>"
            exit 1
        fi
        wifi_connection_up "$2"
        ;;
    down)
        if [ "$#" -ne 2 ]; then
            echo "Error: 'up' command requires connection name"
            echo "Usage: $0 down <connection_name>"
            exit 1
        fi
        wifi_connection_down "$2"
        ;;
    autoconnect)
        if [ "$#" -ne 3 ]; then
            echo "Error: 'autoconnect' command requires connection name and value (1 or 0)"
            echo "Usage: $0 autoconnect <connection_name> <1|0>"
            exit 1
        fi
        wifi_autoconnect "$2" "$3"
        ;;
    *)
        echo "Invalid parameter: $1"
        echo "Usage: $0 {block|unblock|up <connection_name>|autoconnect <connection_name> <1|0>}"
        exit 1
        ;;
esac

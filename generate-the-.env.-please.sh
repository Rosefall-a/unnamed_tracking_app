#!/bin/bash

# --- Get gateway IP ---
gateway_ip=$(ip route | awk '/default/ {print $3}')

default_url="http://${gateway_ip}:5173/"

echo "gib to me ur ip address for my vite-api-min"
read -p "VITE_API_BASE_URL (default: $default_url): " vite_url

# If empty, use gateway suggestion
vite_url=${vite_url:-$default_url}

# --- IPv4 validation function ---
validate_ip() {
    local ip=$1
    local stat=1

    # Basic IPv4 regex
    if [[ $ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        OIFS=$IFS
        IFS='.'
        read -r -a octets <<< "$ip"
        IFS=$OIFS

        # Ensure each octet is 0–255
        if (( octets[0] <= 255 && octets[1] <= 255 && octets[2] <= 255 && octets[3] <= 255 )); then
            stat=0
        fi
    fi

    return $stat
}

# Extract IP from URL
ip_only=$(echo "$vite_url" | sed -E 's#https?://([^:/]+).*#\1#')

# Validate
if ! validate_ip "$ip_only"; then
    echo "Invalid IP address detected: $ip_only"
    echo "Please run again with a valid IPv4 address."
    exit 1
fi

echo "IP validated successfully."

# --- Write .env ---
cat <<EOF > .env
VITE_API_BASE_URL=$vite_url
POSTGRES_USER=post_user
POSTGRES_PASSWORD=dwagshhes
POSTGRES_DB=the_db
EOF

echo ".env file created."

# --- Optional encryption ---
read -p "Encrypt .env using openssl? (y/N): " enc

if [[ "$enc" =~ ^[Yy]$ ]]; then
    openssl enc -aes-256-cbc -salt -in .env -out .env.enc
    echo "Encrypted .env.enc created."
fi
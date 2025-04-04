#!/usr/bin/bash

# Fetch DigitalOcean API token from the system's secret storage using secret-tool.
# This assumes the token is stored with the key "token do".
DIGITALOCEAN_TOKEN=$(secret-tool lookup token do)

# Deploy a new DigitalOcean droplet specifically configured to run the nuclei scanner.
curl -X POST \
    -H "Content-Type: application/json" \ # Specifies that the request body is in JSON format.
    -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \ # Includes the API token for authentication.
    -d '{ # Begins the JSON data payload for the droplet creation.
        "name": "<your_droplet_name>", # Sets the name of the new droplet.
        "region": "nyc1", # Specifies the region where the droplet will be created (New York 1).
        "size": "s-2vcpu-4gb", # Specifies the droplet size (2 vCPUs, 4GB RAM).
        "image": "<your_image_id>", # Specifies the image ID to use for the droplet (custom image, presumably with nuclei installed).
        "ssh_keys": [111111111] # Specifies the SSH key ID to add to the droplet for remote access.
    }' \
    "https://api.digitalocean.com/v2/droplets" # The DigitalOcean API endpoint for creating droplets.
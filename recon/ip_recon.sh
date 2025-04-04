#!/bin/bash

# Script: ip_reverse_host.sh
# Description: Processes IP addresses from a file, performs reverse DNS lookups, and validates the resulting hostnames.
# Usage: ip_reverse_host.sh <ip_file>

# Check if the correct number of command-line arguments is provided.
if [ $# -ne 1 ]; then
  echo "Usage: $0 <ip_file>" # Print usage instructions.
  exit 1 # Exit with an error code.
fi

# Assign the first command-line argument to the 'ip_file' variable.
ip_file="$1"

# Check if the specified IP file exists.
if [ ! -f "$ip_file" ]; then
  echo "Error: IP file '$ip_file' not found." # Print an error message if the file is not found.
  exit 1 # Exit with an error code.
fi

# 1. Reverse lookup and output to tmp.txt
# Read each line (IP address) from the input file.
while IFS= read -r ip; do
  # Check if the line is a valid IPv4 address using a regular expression.
  if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    # Perform a reverse DNS lookup using 'dig -x' and append the short result to 'tmp.txt'.
    # Standard error is redirected to /dev/null to suppress error messages.
    dig -x "$ip" +short 2>/dev/null >> tmp.txt
  fi
done < "$ip_file"

# 2. host lookup and output to tmp.txt
# Read each line (IP address) from the input file again.
while IFS= read -r ip; do
    # Check if the line is a valid IPv4 address using a regular expression.
    if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        # Perform a reverse DNS lookup using 'host', filter for the 'pointer' record, and extract the hostname.
        # The result is appended to 'tmp.txt'. Standard error is redirected to /dev/null.
        host "$ip" 2>/dev/null | grep "pointer" | awk '{print $5}' >> tmp.txt
    fi
done < "$ip_file"

# 3. Sort tmp.txt to unique lines
# Sort the contents of 'tmp.txt' and remove duplicate lines, storing the result in 'tmp2.txt'.
sort -u tmp.txt > tmp2.txt
# Replace 'tmp.txt' with the sorted and unique lines from 'tmp2.txt'.
mv tmp2.txt tmp.txt

# 4, 5, 6. Process tmp.txt and output to out.txt
# Read each line (hostname) from 'tmp.txt'.
while IFS= read -r host; do
  # Check if the line is not empty.
  if [ -n "$host" ]; then
    # Remove the trailing dot from the hostname.
    host_stripped="${host%.}"
    # Validate the hostname using a regular expression to ensure it's a valid domain name.
    if [[ "$host_stripped" =~ ^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$ ]]; then
      # If the hostname is valid, append it to 'out.txt'.
      echo "$host_stripped" >> out.txt
    fi
  fi
done < "tmp.txt"

# Clean up the temporary file 'tmp.txt'.
rm tmp.txt

# Print a completion message.
echo "IP processing complete. Results in out.txt"

# Exit with a success code.
exit 0
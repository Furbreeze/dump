#!/bin/bash

# Script: run_chaos.sh
# Description: This script executes the 'chaos' command against each host listed in a provided file.
#              The 'chaos' command is run with the '-d' and '-silent' flags.
#              This suggests 'chaos' is a tool that performs some kind of network or host analysis.
#              The '-d' flag likely specifies the target host, and '-silent' probably suppresses verbose output.
# Usage: run_chaos.sh <hosts_file>
#        Where <hosts_file> is a file containing a list of hostnames or IP addresses, one per line.

# Check if the script was called with exactly one command-line argument.
if [ $# -ne 1 ]; then
  # If not, print a usage message to standard output.
  echo "Usage: $0 <hosts_file>"
  # Exit the script with an error code (1).
  exit 1
fi

# Assign the first command-line argument (the hosts file) to the 'hosts_file' variable.
hosts_file="$1"

# Check if the file specified by 'hosts_file' exists and is a regular file.
if [ ! -f "$hosts_file" ]; then
  # If the file does not exist, print an error message to standard output.
  echo "Error: Hosts file '$hosts_file' not found."
  # Exit the script with an error code (1).
  exit 1
fi

# Begin a loop that reads each line from the 'hosts_file' into the 'host' variable.
while IFS= read -r host; do
  # Check if the 'host' variable is not empty.
  if [ -n "$host" ]; then
    # If the host is not empty, execute the 'chaos' command.
    # The '-d' flag specifies the target host, and '-silent' suppresses output.
    chaos -d "$host" -silent
  fi
# End of the loop, reading input from the specified 'hosts_file'.
done < "$hosts_file"

# Exit the script with a success code (0).
exit 0
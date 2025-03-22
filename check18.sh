#!/bin/bash

INPUT_FILE="splitblock18"

while IFS= read -r domain; do
    # Skip empty lines
    [ -z "$domain" ] && continue

    RESULT=$(pyfunceble -s -d "$domain")
    
    # Check if the output contains "ACTIVE"
    if echo "$RESULT" | grep -q "ACTIVE"; then
         # removed: echo "$domain is active"
    else
         # removed: echo "$domain is not active"
         echo "$domain" >> deadblock18
    fi
done < "$INPUT_FILE"
#!/bin/bash

INPUT_FILE="splitblock12"

while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    
    # Check if the output contains "ACTIVE"
    if echo "$RESULT" | grep -q "ACTIVE"; then
         :
    else
         :
         echo "$domain" >> deadblock12
    fi
done < "$INPUT_FILE"
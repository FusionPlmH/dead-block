#!/bin/bash

INPUT_FILE="splitblock15"

while IFS= read -r domain; do
    [ -z "$domain" ] && continue
    RESULT=$(pyfunceble -s -d "$domain")
    if echo "$RESULT" | grep -q "ACTIVE"; then
         :
    else
         echo "$domain" >> deadblock15
    fi
done < "$INPUT_FILE"
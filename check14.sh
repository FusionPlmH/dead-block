#!/bin/bash

INPUT_FILE="splitblock14"

while IFS= read -r domain; do
    [ -z "$domain" ] && continue
    RESULT=$(pyfunceble -s -d "$domain")
    if echo "$RESULT" | grep -q "ACTIVE"; then
         :
    else
         echo "$domain" >> deadblock14
    fi
done < "$INPUT_FILE"
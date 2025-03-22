#!/bin/bash

INPUT_FILE="splitblock03"

while IFS= read -r domain; do
    [ -z "$domain" ] && continue
    RESULT=$(pyfunceble -s -d "$domain")
    if echo "$RESULT" | grep -q "ACTIVE"; then
         # removed: echo "$domain is active"
    else
         # removed: echo "$domain is not active"
         echo "$domain" >> deadblock3
    fi
done < "$INPUT_FILE"
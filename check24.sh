#!/bin/bash
INPUT_FILE="splitblock24"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    echo "$RESULT"
    if echo "$RESULT" | grep -q 'INACTIVE'; then
         echo "$domain" >> deadblock24
    fi
done < "$INPUT_FILE"
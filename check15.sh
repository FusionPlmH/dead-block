#!/bin/bash
INPUT_FILE="splitblock15"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    echo "$RESULT"
    if echo "$RESULT" | grep -q 'INACTIVE'; then
         echo "$domain" >> deadblock15
    fi
done < "$INPUT_FILE"
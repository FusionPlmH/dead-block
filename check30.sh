#!/bin/bash
INPUT_FILE="splitblock30"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    echo "$RESULT"  # added print of result
    if echo "$RESULT" | grep -q 'INACTIVE'; then  # changed condition
         echo "$domain" >> deadblock30
    fi
done < "$INPUT_FILE"
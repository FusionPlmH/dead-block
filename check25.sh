#!/bin/bash
INPUT_FILE="splitblock25"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock25
    fi
done < "$INPUT_FILE"
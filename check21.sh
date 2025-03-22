#!/bin/bash
INPUT_FILE="splitblock21"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock21
    fi
done < "$INPUT_FILE"
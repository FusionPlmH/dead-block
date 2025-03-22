#!/bin/bash
INPUT_FILE="splitblock15"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock15
    fi
done < "$INPUT_FILE"
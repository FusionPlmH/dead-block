#!/bin/bash
INPUT_FILE="splitblock00"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock0
    fi
done < "$INPUT_FILE"
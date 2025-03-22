#!/bin/bash
INPUT_FILE="splitblock22"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock22
    fi
done < "$INPUT_FILE"
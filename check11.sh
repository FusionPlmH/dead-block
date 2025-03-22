#!/bin/bash
INPUT_FILE="splitblock11"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock11
    fi
done < "$INPUT_FILE"
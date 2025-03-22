#!/bin/bash
INPUT_FILE="splitblock05"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock5
    fi
done < "$INPUT_FILE"
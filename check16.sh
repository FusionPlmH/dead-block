#!/bin/bash
INPUT_FILE="splitblock16"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock16
    fi
done < "$INPUT_FILE"
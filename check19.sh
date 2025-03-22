#!/bin/bash
INPUT_FILE="splitblock19"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock19
    fi
done < "$INPUT_FILE"
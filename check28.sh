#!/bin/bash
INPUT_FILE="splitblock28"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock28
    fi
done < "$INPUT_FILE"
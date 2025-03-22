#!/bin/bash
INPUT_FILE="splitblock29"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock29
    fi
done < "$INPUT_FILE"
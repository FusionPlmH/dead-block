#!/bin/bash
INPUT_FILE="splitblock03"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock3
    fi
done < "$INPUT_FILE"
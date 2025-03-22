#!/bin/bash
INPUT_FILE="splitblock23"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock23
    fi
done < "$INPUT_FILE"
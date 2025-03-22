#!/bin/bash
INPUT_FILE="splitblock13"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock13
    fi
done < "$INPUT_FILE"
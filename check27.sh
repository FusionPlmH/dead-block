#!/bin/bash
INPUT_FILE="splitblock27"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock27
    fi
done < "$INPUT_FILE"
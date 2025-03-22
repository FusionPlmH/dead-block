#!/bin/bash
INPUT_FILE="splitblock17"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock17
    fi
done < "$INPUT_FILE"